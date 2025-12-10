from PySide6.QtCore import QObject, Signal

LIBRARY_PATH = 'library'
MULTIS_PATH = 'library/multis'
LOOPS_PATH = 'library/loops'
MASTER_TRACK = 'master.wav'
VIDEO_FILE = 'video'
TRACKS_PATH = 'tracks'

class AppState(QObject):
    video_is_playing_changed = Signal(bool)

    def __init__(self):
        super().__init__()
        self._video_is_playing = False
        self._volume = 50

    # --- video_is_playing ---
    @property
    def video_is_playing(self):
        return self._video_is_playing

    @video_is_playing.setter
    def video_is_playing(self, value):
        if self._video_is_playing != value:
            self._video_is_playing = value
            self.video_is_playing_changed.emit(value)


# Instancia global
app_state = AppState()