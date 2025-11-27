from PySide6.QtCore import QThread, Signal
import ffmpeg
import time

class ExtractAudioThread(QThread):
    result = Signal()

    def __init__(self, video_path):
        super().__init__()
        self.video_path = video_path

    def run(self):
        time.sleep(3)
        self.result.emit()