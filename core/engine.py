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
import gc
import threading
import time
from collections import deque
from typing import Dict, List, Optional, Union

import numpy as np
import sounddevice as sd
import soundfile as sf

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    import warnings
    warnings.warn("psutil not installed - RAM validation disabled. Install with: pip install psutil")

from utils.logger import get_logger

logger = get_logger(__name__)

class MultiTrackPlayer:
    def __init__(self, samplerate: Optional[int] = None, blocksize: int = 2048, dtype: str = 'float32', gc_policy: str = 'disable_during_playback'):
        """
        Initialize MultiTrack Audio Player.

        Args:
            samplerate: Sample rate (44100 or 48000). If None, auto-detects from first track loaded.
            blocksize: Buffer size in samples. HARDWARE-DEPENDENT:
                       - 512: Low latency (~10ms @ 48kHz) - Modern CPUs only
                       - 1024: Balanced (~21ms @ 48kHz) - Good for most systems
                       - 2048: High stability (~43ms @ 48kHz) - Legacy hardware (2008-2012)
                       - 4096: Very stable (~85ms @ 48kHz) - Very old CPUs
            dtype: Audio data type (always 'float32')
            gc_policy: Garbage collection policy during playback:
                      - 'disable_during_playback': Disable GC during playback to prevent audio glitches (recommended for legacy hardware)
                      - 'normal': Keep GC enabled (for modern systems with sufficient CPU headroom)
        """
        self.samplerate = samplerate  # None until first track loaded
        self.blocksize = blocksize  # Default 2048 for stability on legacy hardware
        self.dtype = dtype
        self.gc_policy = gc_policy
        self._gc_was_enabled = gc.isenabled()  # Store initial GC state

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

        # Latency measurement (Tarea #4)
        self._callback_durations = deque(maxlen=100)  # Last 100 callback durations in seconds
        self._xrun_count = 0  # Count of callbacks exceeding time budget
        self._total_callbacks = 0  # Total callback invocations

    def _disable_gc_if_needed(self):
        """Disable garbage collection during playback to prevent audio glitches on legacy hardware."""
        if self.gc_policy == 'disable_during_playback' and gc.isenabled():
            self._gc_was_enabled = True
            gc.disable()
            logger.info("🗑️  GC disabled during playback (prevents audio glitches on legacy hardware)")

    def _restore_gc_if_needed(self):
        """Restore garbage collection after playback stops."""
        if self.gc_policy == 'disable_during_playback' and self._gc_was_enabled:
            gc.enable()
            logger.info("🗑️  GC re-enabled after playback stopped")

    def _validate_ram(self, total_bytes_needed: int) -> None:
        """Validate sufficient RAM is available before pre-loading tracks.

        Args:
            total_bytes_needed: Total bytes required for all tracks

        Raises:
            MemoryError: If insufficient RAM available (uses <70% safety threshold)
        """
        if not PSUTIL_AVAILABLE:
            logger.warning("⚠️  psutil not available - skipping RAM validation")
            return

        mem = psutil.virtual_memory()
        available_bytes = mem.available
        total_gb = total_bytes_needed / (1024**3)
        available_gb = available_bytes / (1024**3)

        # Use 70% of available RAM as safety threshold
        safe_threshold = available_bytes * 0.70

        logger.info(f"💾 Pre-load size: {total_gb:.2f} GB | Available RAM: {available_gb:.2f} GB")

        if total_bytes_needed > safe_threshold:
            raise MemoryError(
                f"❌ Insufficient RAM for pre-load:\n"
                f"   Required: {total_gb:.2f} GB\n"
                f"   Available: {available_gb:.2f} GB\n"
                f"   Safe threshold (70%): {safe_threshold/(1024**3):.2f} GB\n"
                f"💡 Close other applications or reduce track count"
            )

    def load_tracks(self, paths: List[str]):
        """
        Load a list of file paths. Files may be mono or stereo.
        They will be converted to float32 and stored.

        If samplerate was None at initialization, auto-detects from first track.
        All tracks must have the same sample rate (no live resampling for stability).
        """
        if not paths:
            raise ValueError("No paths provided to load_tracks")

        # Load first track to auto-detect sample rate if needed
        first_data, first_sr = sf.read(paths[0], dtype='float32', always_2d=True)

        if self.samplerate is None:
            self.samplerate = first_sr
            logger.info(f"🎵 Auto-detected sample rate: {self.samplerate} Hz from first track")
        elif first_sr != self.samplerate:
            raise ValueError(
                f"❌ Sample rate mismatch: expected {self.samplerate} Hz, "
                f"got {first_sr} Hz from {paths[0]}\n"
                f"💡 Fix with: ffmpeg -i '{paths[0]}' -ar {self.samplerate} output.wav"
            )

        arrays = [first_data]
        max_frames = first_data.shape[0]

        # Load remaining tracks and validate sample rate
        for p in paths[1:]:
            data, sr = sf.read(p, dtype='float32', always_2d=True)  # shape (frames, channels)
            if sr != self.samplerate:
                raise ValueError(
                    f"❌ Sample rate mismatch: expected {self.samplerate} Hz, "
                    f"got {sr} Hz from {p}\n"
                    f"💡 Fix with: ffmpeg -i '{p}' -ar {self.samplerate} output.wav"
                )
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

        # Tarea #2: RAM Validation - Calculate total bytes and validate before storing
        total_bytes = sum(arr.nbytes for arr in norm_tracks)
        self._validate_ram(total_bytes)

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
        # Tarea #4: Latency measurement - Start timing
        callback_start = time.perf_counter()

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

        # Tarea #4: Latency measurement - End timing and store stats
        callback_end = time.perf_counter()
        callback_duration = callback_end - callback_start

        # Calculate time budget for this blocksize
        time_budget = self.blocksize / self.samplerate if self.samplerate else 0.043  # ~43ms @ 2048/48000

        # Store duration and detect xruns (callback exceeding 80% of budget)
        self._callback_durations.append(callback_duration)
        self._total_callbacks += 1

        if callback_duration > time_budget * 0.80:
            self._xrun_count += 1
            if self._xrun_count % 10 == 1:  # Log every 10th xrun to avoid spam
                logger.warning(
                    f"⚠️  Audio callback xrun detected: {callback_duration*1000:.2f}ms "
                    f"(budget: {time_budget*1000:.2f}ms, usage: {(callback_duration/time_budget)*100:.1f}%)"
                )

    def play(self, start_frame: Optional[int] = None):
        """
        Start playback.

        If `start_frame` is provided (int), playback will start from that frame.
        If `start_frame` is None (the default), playback will resume from the
        current position (useful after a pause).
        """
        # Disable GC during playback to prevent audio glitches
        self._disable_gc_if_needed()

        with self._lock:
            if self._n_tracks == 0:
                raise RuntimeError("No tracks loaded")
            if start_frame is not None:
                self._pos = int(start_frame)
            self._playing = True

            # Create and start stream if not already
            if self._stream is None:
                # ═══════════════════════════════════════════════════════════════
                # AUDIO STREAM CONFIGURATION - OPTIMIZED FOR LEGACY HARDWARE
                # ═══════════════════════════════════════════════════════════════
                # latency='high': Solicita al driver ALSA mayor buffer interno
                #                 Crítico para CPUs antiguas (Sandy Bridge, Core 2 Duo)
                # prime_output_buffers: Pre-llena buffers antes de iniciar stream
                #                       Evita underruns en el primer frame
                # ═══════════════════════════════════════════════════════════════
                self._stream = sd.OutputStream(
                    samplerate=self.samplerate,
                    blocksize=self.blocksize,
                    channels=self._n_output_channels,
                    dtype=self.dtype,
                    callback=self._callback,
                    finished_callback=self._on_stream_finished,
                    latency='high',  # ← CRÍTICO para hardware antiguo
                    prime_output_buffers_using_stream_callback=True  # ← Pre-llenar buffers
                )
                logger.info(f"🔊 Audio stream initialized: {self.samplerate}Hz, blocksize={self.blocksize}, latency=high")
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

        # Restore GC after playback finishes
        self._restore_gc_if_needed()

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

        # Restore GC after playback stops
        self._restore_gc_if_needed()

        # Notify play state changed -> not playing
        try:
            if self.playStateCallback is not None:
                self.playStateCallback(False)
        except Exception:
            pass

    def pause(self):
        with self._lock:
            self._playing = False

        # Restore GC when paused (safe to collect during pause)
        self._restore_gc_if_needed()

        # Notify play state changed -> not playing
        try:
            if self.playStateCallback is not None:
                self.playStateCallback(False)
        except Exception:
            pass

    def resume(self):
        # Disable GC when resuming playback
        self._disable_gc_if_needed()

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
            if self.samplerate is None:
                return 0.0
            return float(self._pos) / float(self.samplerate)

    def get_duration_seconds(self) -> float:
        """Return total duration of the loaded tracks in seconds."""
        with self._lock:
            if self.samplerate is None or self._n_frames == 0:
                return 0.0
            return float(self._n_frames) / float(self.samplerate)

    def seek_seconds(self, seconds: float):
        """Seek to a specific time position in seconds.

        Args:
            seconds: Target position in seconds

        Raises:
            RuntimeError: If no tracks are loaded or samplerate not detected
        """
        if self.samplerate is None:
            logger.warning("⚠️  Cannot seek: no tracks loaded (samplerate not detected)")
            return

        if self._n_tracks == 0:
            logger.warning("⚠️  Cannot seek: no tracks loaded")
            return

        frame = int(seconds * self.samplerate)
        with self._lock:
            self._pos = min(max(0, frame), self._n_frames)

    def get_latency_stats(self) -> Dict[str, float]:
        """Get audio callback latency statistics.

        Returns:
            Dictionary with:
            - mean_ms: Average callback duration in milliseconds
            - max_ms: Peak callback duration in milliseconds
            - min_ms: Minimum callback duration in milliseconds
            - xruns: Count of callbacks exceeding 80% of time budget
            - budget_ms: Time budget for current blocksize in milliseconds
            - usage_pct: Average percentage of time budget used
            - total_callbacks: Total number of callbacks processed
        """
        with self._lock:
            if not self._callback_durations:
                return {
                    'mean_ms': 0.0,
                    'max_ms': 0.0,
                    'min_ms': 0.0,
                    'xruns': 0,
                    'budget_ms': 0.0,
                    'usage_pct': 0.0,
                    'total_callbacks': 0
                }

            durations = list(self._callback_durations)
            mean_duration = sum(durations) / len(durations)
            max_duration = max(durations)
            min_duration = min(durations)

            # Calculate time budget
            time_budget = self.blocksize / self.samplerate if self.samplerate else 0.043

            return {
                'mean_ms': mean_duration * 1000,
                'max_ms': max_duration * 1000,
                'min_ms': min_duration * 1000,
                'xruns': self._xrun_count,
                'budget_ms': time_budget * 1000,
                'usage_pct': (mean_duration / time_budget) * 100 if time_budget > 0 else 0.0,
                'total_callbacks': self._total_callbacks
            }

    def close(self):
        # Restore GC before closing
        self._restore_gc_if_needed()

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

# End of module

