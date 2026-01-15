"""
Multi Lyrics - Audio Engine Module
Copyright (C) 2026 Diego Fernando

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

"""
MultiTrackPlayer
A multitrack audio player using sounddevice + soundfile + numpy.

Features:
- Load multiple mono or stereo audio files (they will be resampled/checked to match samplerate)
- Mixer with per-track gain, mute, solo
- Stable callback-based playback using sounddevice.OutputStream
- Minimal work inside callback; simple per-block gain smoothing to avoid clicks
- Example usage at the bottom

Requirements:
pip install sounddevice soundfile numpy

Notes:
- This example assumes all tracks have the same samplerate. If not, you'd need to resample.
- Tracks shorter than the longest will be padded with zeros to align durations.
- By default playback is stereo: mono tracks are duplicated to both channels; stereo tracks are used as-is.
"""
import threading
import numpy as np
import soundfile as sf
import sounddevice as sd
import time
from typing import List, Optional, Union
from utils.logger import get_logger

logger = get_logger(__name__)

class MultiTrackPlayer:
    def __init__(self, samplerate: int = 44100, blocksize: int = 1024, dtype: str = 'float32'):
        self.samplerate = samplerate
        self.blocksize = blocksize
        self.dtype = dtype

        # Data structures
        self._tracks = []            # list of arrays shape (n_samples, channels_per_track) float32
        self._n_tracks = 0
        self._n_output_channels = 2  # stereo output by default
        self._n_frames = 0           # length in samples (frames)
        self._pos = 0                # read head position (in frames)
        self._stream = None

        # Mixer state
        self.target_gains = np.zeros(0, dtype='float32')   # target values set by user
        self.current_gains = np.zeros(0, dtype='float32')  # used inside callback with smoothing
        self.muted = np.zeros(0, dtype=bool)
        self.solo_mask = np.zeros(0, dtype=bool)

        # Control
        self._playing = False
        self._lock = threading.Lock()

        # Smoothing factor for gain transitions (0..1). Higher -> faster changes.
        self.gain_smoothing = 0.15
        # Master gain (global output gain, 0.0 .. 1.0)
        self.master_gain = 1.0

        # Sync controller callback opcional
        self.audioTimeCallback = None  # function to call with current time in seconds

        # Playback state change callback opcional
        # Should be a callable taking a single bool argument (playing)
        self.playStateCallback = None


    def load_tracks(self, paths: List[str]):
        """
        Load a list of file paths. Files may be mono or stereo.
        They will be converted to float32 and stored.
        """
        arrays = []
        srs = []
        max_frames = 0
        for p in paths:
            data, sr = sf.read(p, dtype='float32', always_2d=True)  # shape (frames, channels)
            srs.append(sr)
            if sr != self.samplerate:
                raise ValueError(f"Samplerate mismatch: {p} has {sr}, player expects {self.samplerate}. Resample first.")
            arrays.append(data)
            if data.shape[0] > max_frames:
                max_frames = data.shape[0]

        # Pad to same length
        norm_tracks = []
        for arr in arrays:
            if arr.shape[0] < max_frames:
                pad = np.zeros((max_frames - arr.shape[0], arr.shape[1]), dtype='float32')
                arr = np.concatenate([arr, pad], axis=0)
            norm_tracks.append(arr)
        self._tracks = norm_tracks
        self._n_tracks = len(norm_tracks)
        self._n_frames = max_frames
        # init mixer state
        self.target_gains = np.ones(self._n_tracks, dtype='float32')
        self.current_gains = self.target_gains.copy()
        self.muted = np.zeros(self._n_tracks, dtype=bool)
        self.solo_mask = np.zeros(self._n_tracks, dtype=bool)
        self._pos = 0

    def _mix_block(self, start: int, frames: int) -> np.ndarray:
        """
        Mix a block of 'frames' starting at 'start' into stereo output.
        Returns shape (frames, 2) float32
        """
        # Collect per-track slices (views, no copy until stack)
        # Build an array shape (frames, n_tracks, chan_per_track) but we will handle mono/stereo tracks
        # For performance we do per-track multiplication and accumulate into mono mix
        frames_end = min(start + frames, self._n_frames)
        length = frames_end - start
        if length <= 0:
            return np.zeros((frames, self._n_output_channels), dtype='float32')

        # Smooth current gains toward target gains
        # This operation is cheap and safe to do without locks because it's small and atomicish
        self.current_gains += (self.target_gains - self.current_gains) * self.gain_smoothing

        # Decide which tracks are active considering solo/mute
        # Be robust if arrays weren't initialized (e.g., in tests)
        n_tracks = self._n_tracks
        muted = self.muted if getattr(self, 'muted', None) is not None and self.muted.size == n_tracks else np.zeros(n_tracks, dtype=bool)
        solo_mask = self.solo_mask if getattr(self, 'solo_mask', None) is not None and self.solo_mask.size == n_tracks else np.zeros(n_tracks, dtype=bool)

        if np.any(solo_mask):
            active = solo_mask & (~muted)
        else:
            active = ~muted

        # Start accumulation in mono
        mix_mono = np.zeros((length,), dtype='float32')

        for i, track in enumerate(self._tracks):
            if not active[i]:
                continue
            track_slice = track[start:frames_end]  # shape (length, channels_of_track)
            gain = float(self.current_gains[i])
            # If track is stereo (2 channels), we average to mono before summing (or could pan differently)
            if track_slice.shape[1] == 1:
                mix_mono[:length] += track_slice[:,0] * gain
            else:
                # average channels to mono (simple stereo->mono mix)
                mix_mono[:length] += track_slice.mean(axis=1) * gain

        # Now create stereo output by duplicating mono into both channels
        # Apply master gain to the mixed signal
        mix_mono *= float(self.master_gain)

        out_block = np.zeros((frames, self._n_output_channels), dtype='float32')
        out_block[:length, 0] = mix_mono
        out_block[:length, 1] = mix_mono

        # If we had less than 'frames' (end of track), rest is zeros (already zero)
        return out_block

    def _callback(self, outdata: np.ndarray, frames: int, time_info, status):
        """
        sounddevice callback: must be fast and avoid Python allocation when possible.
        outdata is a writable numpy array shape (frames, channels)
        """
        if status:
            # Log status occasionally; not ideal in tight real-time but useful for debugging.
            logger.warning(f"Stream status: {status}")

        with self._lock:
            if not self._playing:
                # If stopped, output silence
                outdata.fill(0)
                return

            # Mix block
            block = self._mix_block(self._pos, frames)  # returns shape (frames, 2)
            # Write to outdata
            out_len = min(frames, block.shape[0])
            outdata[:out_len] = block[:out_len]
            if out_len < frames:
                outdata[out_len:] = 0.0

            self._pos += out_len
            if self._pos >= self._n_frames:
                # Stop at end
                self._playing = False
                # Fill remainder with zeros (already)
                # Close stream from another thread or let main control stop
                # We'll just stop the stream gracefully here:
                try:
                    # Mark stream to stop; calling stop from callback is allowed in sounddevice
                    self._stream.stop()
                except Exception:
                    pass

            # Call audio time callback if set
            if self.audioTimeCallback is not None:
                self.audioTimeCallback(frames)

    def play(self, start_frame: Optional[int] = None):
        """
        Start playback.

        If `start_frame` is provided (int), playback will start from that frame.
        If `start_frame` is None (the default), playback will resume from the
        current position (useful after a pause).
        """
        with self._lock:
            if self._n_tracks == 0:
                raise RuntimeError("No tracks loaded")
            if start_frame is not None:
                self._pos = int(start_frame)
            self._playing = True

            # Create and start stream if not already
            if self._stream is None:
                self._stream = sd.OutputStream(samplerate=self.samplerate,
                                               blocksize=self.blocksize,
                                               channels=self._n_output_channels,
                                               dtype=self.dtype,
                                               callback=self._callback,
                                               finished_callback=self._on_stream_finished)
                self._stream.start()
            else:
                if not self._stream.active:
                    self._stream.start()
        # Notify play state changed -> playing
        try:
            if self.playStateCallback is not None:
                self.playStateCallback(True)
        except Exception:
            pass

    def _on_stream_finished(self):
        # called when stream finishes
        with self._lock:
            self._playing = False
        # Notify play state change (stream finished -> not playing)
        try:
            if self.playStateCallback is not None:
                self.playStateCallback(False)
        except Exception:
            pass

    def stop(self):
        with self._lock:
            self._playing = False
            if self._stream is not None and self._stream.active:
                try:
                    self._stream.stop()
                except Exception:
                    pass
            self._pos = 0
        # Notify play state changed -> not playing
        try:
            if self.playStateCallback is not None:
                self.playStateCallback(False)
        except Exception:
            pass

    def pause(self):
        with self._lock:
            self._playing = False
        # Notify play state changed -> not playing
        try:
            if self.playStateCallback is not None:
                self.playStateCallback(False)
        except Exception:
            pass

    def resume(self):
        with self._lock:
            if self._stream is not None and not self._stream.active:
                self._stream.start()
            self._playing = True
        # Notify play state changed -> playing
        try:
            if self.playStateCallback is not None:
                self.playStateCallback(True)
        except Exception:
            pass

    def set_gain(self, track_index: int, gain: float):
        """
        Set the target gain for a track (linear, 1.0 = unity).
        """
        with self._lock:
            self.target_gains[track_index] = np.float32(gain)

    def set_master_gain(self, gain: float):
        """Set the global/master gain (0.0 .. 1.0)."""
        with self._lock:
            try:
                g = float(gain)
            except Exception:
                return
            # Clamp
            g = max(0.0, min(1.0, g))
            self.master_gain = g

    def get_master_gain(self) -> float:
        with self._lock:
            return float(self.master_gain)

    def get_gain(self, track_index: int) -> float:
        return float(self.target_gains[track_index])

    def mute(self, track_index: int, yes: bool = True):
        with self._lock:
            self.muted[track_index] = yes

    def solo(self, track_index: int, yes: bool = True):
        with self._lock:
            self.solo_mask[track_index] = yes

    def clear_solo(self):
        with self._lock:
            self.solo_mask[:] = False

    def is_playing(self) -> bool:
        with self._lock:
            return self._playing

    def get_position_seconds(self) -> float:
        with self._lock:
            return float(self._pos) / float(self.samplerate)

    def get_duration_seconds(self) -> float:
        """Return total duration of the loaded tracks in seconds."""
        with self._lock:
            return float(self._n_frames) / float(self.samplerate)

    def seek_seconds(self, seconds: float):
        frame = int(seconds * self.samplerate)
        with self._lock:
            self._pos = min(max(0, frame), self._n_frames)

    def close(self):
        with self._lock:
            if self._stream is not None:
                try:
                    self._stream.close()
                except Exception:
                    pass
                self._stream = None
            self._tracks = []
            self._n_tracks = 0

# Example usage
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Multitrack player demo")
    parser.add_argument("files", nargs='+', help="Paths to audio files (mono or stereo)")
    parser.add_argument("--sr", type=int, default=44100, help="Samplerate expected (default 44100)")
    args = parser.parse_args()

    player = MultiTrackPlayer(samplerate=args.sr, blocksize=1024)
    logger.info("Loading tracks...")
    player.load_tracks(args.files)
    logger.info(f"Loaded {player._n_tracks} tracks, length {player._n_frames} frames ({player._n_frames/player.samplerate:.2f} s)")

    # Example: reduce track 0 to 0.6, mute track 2, solo track 1 (uncomment to test)
    # player.set_gain(0, 0.6)
    # player.mute(2, True)
    # player.solo(1, True)

    logger.info("Starting playback...")
    player.play()
    try:
        while player.is_playing():
            logger.debug(f"Pos: {player.get_position_seconds():.2f}s / {player._n_frames/player.samplerate:.2f}s")
            time.sleep(0.1)
    except KeyboardInterrupt:
        logger.info("\nStopping...")
        player.stop()
    player.close()

# End of module

