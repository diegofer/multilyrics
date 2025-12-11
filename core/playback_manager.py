from PySide6.QtCore import QObject, Signal

class PlaybackManager(QObject):
    """
    Coordina tiempo actual y duración total.
    Se conecta con SyncController y expone señales para la UI.
    """

    positionChanged = Signal(float)    # tiempo actual (s)
    durationChanged = Signal(float)    # duración total (s)

    def __init__(self, sync_controller, parent=None):
        super().__init__(parent)
        self.sync = sync_controller
        self.total_duration = 0.0

        # SyncController emite el audio clock suavizado
        self.sync.audioTimeUpdated.connect(self._on_audio_time)

    def set_duration(self, duration_seconds: float):
        """ Usado cuando cargas una canción. """
        self.total_duration = duration_seconds
        self.durationChanged.emit(self.total_duration)

    def _on_audio_time(self, t: float):
        """ Viene desde SyncController. """
        self.positionChanged.emit(t)
