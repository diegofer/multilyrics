from PySide6.QtCore import QObject, Signal

class PlaybackManager(QObject):
    """
    Coordina tiempo actual y duración total.
    Se conecta con SyncController y expone señales para la UI.
    También centraliza solicitudes de seek para audio/video.
    """

    positionChanged = Signal(float)    # tiempo actual (s)
    durationChanged = Signal(float)    # duración total (s)
    playingChanged = Signal(bool)      # emit when playing state changes

    def __init__(self, sync_controller, parent=None):
        super().__init__(parent)
        self.sync = sync_controller
        self.total_duration = 0.0

        # Referencias a reproductores (se asignan desde MainWindow)
        self.audio_player = None
        self.video_player = None

        # SyncController emite el audio clock suavizado
        self.sync.audioTimeUpdated.connect(self._on_audio_time)

    def set_duration(self, duration_seconds: float):
        """ Usado cuando cargas una canción. """
        self.total_duration = duration_seconds
        self.durationChanged.emit(self.total_duration)

    def set_audio_player(self, audio_player):
        """Asignar la referencia al `MultiTrackPlayer` para control centralizado."""
        self.audio_player = audio_player
        # If audio player supports a play state callback, hook it to propagate
        try:
            if hasattr(self.audio_player, 'playStateCallback'):
                self.audio_player.playStateCallback = self._on_audio_play_state_changed
            # Emit initial state if available
            if hasattr(self.audio_player, 'is_playing'):
                self.playingChanged.emit(bool(self.audio_player.is_playing()))
        except Exception:
            pass

    def _on_audio_play_state_changed(self, playing: bool):
        """Called by the audio player's callback to notify state changes."""
        try:
            self.playingChanged.emit(bool(playing))
        except Exception:
            pass

    def set_video_player(self, video_player):
        """Asignar la referencia al `VideoLyrics` para control centralizado."""
        self.video_player = video_player

    def request_seek(self, seconds: float):
        """Request a seek to `seconds` and synchronize audio/video/clocks.

        This method centralizes seek behavior so UI components or widgets
        can call `playback.request_seek(t)` instead of calling players directly.
        """
        # Clamp within known duration if available
        if self.total_duration and seconds > self.total_duration:
            seconds = float(self.total_duration)
        if seconds < 0:
            seconds = 0.0

        # Seek audio player
        try:
            if self.audio_player is not None:
                self.audio_player.seek_seconds(seconds)
        except Exception:
            pass

        # Seek video player
        try:
            if self.video_player is not None:
                self.video_player.seek_seconds(seconds)
        except Exception:
            pass

        # Update sync controller clock/time so smoothing resumes from correct point
        try:
            if hasattr(self.sync, 'set_audio_time'):
                self.sync.set_audio_time(seconds)
        except Exception:
            pass

        # Emit position change to update UI or other listeners
        self.positionChanged.emit(seconds)

    def _on_audio_time(self, t: float):
        """ Viene desde SyncController. """
        self.positionChanged.emit(t)
