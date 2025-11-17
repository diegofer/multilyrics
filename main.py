from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout
import sys
from shell import Ui_MainWindow
from waveform import WaveformWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)


        self.wave_layout = QVBoxLayout(self.ui.frame_2)
        self.wave_layout.setContentsMargins(0,0,0,0)
        self.wave_layout.setSpacing(0)

        self.waveform = WaveformWidget("example.wav")
        self.wave_layout.addWidget(self.waveform)

if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()