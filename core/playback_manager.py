"""
Multi Lyrics - Playback Manager Module
Copyright (C) 2026 Diego Fernando

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

from typing import Optional
from PySide6.QtCore import QObject, Signal, QTimer

# Import TimelineModel for optional integration. Keep PlaybackManager UI-agnostic;
# TimelineModel is UI-independent and becomes the single source of truth for
# canonical playhead time when provided to PlaybackManager.
from models.timeline_model import TimelineModel
from utils.logger import get_logger
from utils.error_handler import safe_operation

logger = get_logger(__name__)


class PlaybackManager(QObject):
    """
    Coordina tiempo actual y duración total.
    Se conecta con SyncController y expone señales para la UI.
    También centraliza solicitudes de seek para audio/video.

    Integration note:
    - If a ``TimelineModel`` instance is provided (constructor or via
      ``set_timeline``), PlaybackManager will update the timeline's playhead
      via ``timeline.set_playhead_time(seconds)`` whenever the playback clock
      advances (e.g., from SyncController) or a seek is requested. This makes
      ``TimelineModel`` the canonical owner of playhead time.
    """

    # Removed positionChanged signal: UI should observe TimelineModel directly
    # positionChanged = Signal(float)  # ❌ Redundant - TimelineModel is canonical source
    durationChanged = Signal(float)    # duración total (s)
    playingChanged = Signal(bool)      # emit when playing state changes

    def __init__(self, sync_controller, timeline: Optional[TimelineModel] = None, parent=None):
        super().__init__(parent)
        self.sync = sync_controller
        self.total_duration = 0.0

        # Optional timeline model (canonical source of truth for playhead time)
        # Can be injected in the constructor or set later with `set_timeline`.
        self.timeline: Optional[TimelineModel] = timeline
        if timeline is not None:
            logger.debug(f"Timeline adjuntado en constructor: id={id(timeline)}")

        # Referencias a reproductores (se asignan desde MainWindow)
        self.audio_player = None
        self.video_player = None

        # STEP 1.2: Polling timer for end-of-track detection (100ms interval)
        # Callback in _callback() sets _stop_requested flag instead of calling stream.stop()
        # This timer polls the flag and handles stream stop outside real-time context
        self._end_of_track_timer = QTimer(self)
        self._end_of_track_timer.timeout.connect(self._on_end_of_track_poll)
        self._end_of_track_timer.setInterval(100)  # Poll every 100ms

        # SyncController emite el audio clock suavizado
        self.sync.audioTimeUpdated.connect(self._on_audio_time)

    def set_duration(self, duration_seconds: float):
        """ Usado cuando cargas una canción.

        Also update the ``TimelineModel`` duration if one is attached so the
        timeline remains consistent with the playback manager's known duration.
        """
        self.total_duration = duration_seconds
        self.durationChanged.emit(self.total_duration)

        if self.timeline is not None:
            # Keep timeline duration in sync; timeline remains UI-independent.
            with safe_operation("Setting timeline duration", silent=True):
                self.timeline.set_duration_seconds(float(duration_seconds))

    def set_audio_player(self, audio_player):
        """Asignar la referencia al `MultiTrackPlayer` para control centralizado."""
        self.audio_player = audio_player
        # If audio player supports a play state callback, hook it to propagate
        with safe_operation("Configuring audio player callbacks", silent=True):
            if hasattr(self.audio_player, 'playStateCallback'):
                self.audio_player.playStateCallback = self._on_audio_play_state_changed
            # Emit initial state if available
            if hasattr(self.audio_player, 'is_playing'):
                self.playingChanged.emit(bool(self.audio_player.is_playing()))

    def _on_audio_play_state_changed(self, playing: bool):
        """Called by the audio player's callback to notify state changes."""
        with safe_operation("Emitting playing state change", silent=True):
            self.playingChanged.emit(bool(playing))

        # STEP 1.2: Start/stop end-of-track polling timer based on playback state
        if playing:
            if not self._end_of_track_timer.isActive():
                self._end_of_track_timer.start()
                logger.debug("🔄 Started end-of-track polling timer (100ms)")
        else:
            if self._end_of_track_timer.isActive():
                self._end_of_track_timer.stop()
                logger.debug("⏹️  Stopped end-of-track polling timer")

    def _on_end_of_track_poll(self):
        """Polling handler called every 100ms during playback.

        Checks if audio engine's _stop_requested flag is set (end-of-track detected),
        and calls stream.stop() safely outside the audio callback context.

        This is the SAFE way to stop the audio stream (fulfills real-time safety
        requirement that no driver calls happen inside the audio callback).
        """
        with safe_operation("Polling for end-of-track", silent=True):
            if self.audio_player is None:
                return

            # Call should_stop() which checks and resets the flag
            if hasattr(self.audio_player, 'should_stop') and self.audio_player.should_stop():
                logger.info("🎵 End-of-track detected, stopping stream safely")
                try:
                    if hasattr(self.audio_player, '_stream') and self.audio_player._stream is not None:
                        self.audio_player._stream.stop()
                except Exception as e:
                    logger.warning(f"⚠️  Error stopping stream: {e}")

    def set_video_player(self, video_player):
        """Asignar la referencia al `VideoLyrics` para control centralizado."""
        self.video_player = video_player

    def request_seek(self, seconds: float, video_offset: float = 0.0):
        """Request a seek to `seconds` and synchronize audio/video/clocks.

        Args:
            seconds: Target time in seconds (audio time, master clock)
            video_offset: Video offset from metadata (applied to video seek)

        This method centralizes seek behavior so UI components or widgets
        can call `playback.request_seek(t)` instead of calling players directly.

        Also updates the TimelineModel playhead (if present) so the timeline
        remains the canonical source of truth for playhead time.

        Blocked during playback to prevent WASAPI priming errors.
        """
        # Clamp within known duration if available
        if self.total_duration and seconds > self.total_duration:
            seconds = float(self.total_duration)
        if seconds < 0:
            seconds = 0.0

        # Block seeks while audio is actively playing to avoid stream priming glitches
        with safe_operation("Checking audio playback state before seek", silent=True):
            if self.audio_player is not None:
                is_playing_fn = getattr(self.audio_player, "is_playing", None)
                if callable(is_playing_fn) and bool(is_playing_fn()):
                    logger.warning("⚠️  Seek ignored: playback in progress. Pause first to seek.")
                    return

        # Seek audio player
        with safe_operation("Seeking audio player", silent=True):
            if self.audio_player is not None:
                self.audio_player.seek_seconds(seconds)

        # Seek video via background
        with safe_operation("Seeking video player", silent=True):
            if self.video_player and self.video_player.background:
                video_time = seconds + video_offset
                self.video_player.background.seek(self.video_player.engine, video_time)
                if abs(video_offset) > 0.001:
                    logger.debug(f"🎬 Video seek with offset: {seconds:.3f}s + {video_offset:+.3f}s = {video_time:.3f}s")

        # Update sync controller clock/time so smoothing resumes from correct point
        with safe_operation("Updating sync controller time", silent=True):
            if hasattr(self.sync, 'set_audio_time'):
                self.sync.set_audio_time(seconds)

        # Update timeline model (if present). TimelineModel becomes the
        # canonical playhead owner; keep this update robust to errors.
        if self.timeline is not None:
            with safe_operation("Updating timeline playhead", silent=True):
                self.timeline.set_playhead_time(float(seconds))

        # Timeline model will notify its observers (e.g., TimelineView, Controls)
        # No need to emit positionChanged - removed redundant signal

    def _on_audio_time(self, t: float):
        """Called from SyncController when audio clock advances.

        Updates TimelineModel (canonical playhead owner), which then notifies
        all observers (TimelineView, Controls, etc.) via its callback system.
        This eliminates the redundant positionChanged signal.
        """
        #print(f"[PlaybackManager] _on_audio_time: {t:.3f}s (timeline id: {id(self.timeline) if self.timeline else 'None'})")
        if self.timeline is not None:
            with safe_operation("Updating timeline from audio time", silent=True, log_level="error"):
                self.timeline.set_playhead_time(float(t))

        # Timeline model notifies observers automatically
        # Removed: self.positionChanged.emit(t)  # ❌ Redundant

    def set_timeline(self, timeline: TimelineModel) -> None:
        """Attach or replace the TimelineModel used by this manager.

        The TimelineModel should be UI-independent and will be updated by
        PlaybackManager when the playback clock advances or when seeks occur.
        """
        self.timeline = timeline
