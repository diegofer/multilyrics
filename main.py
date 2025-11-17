from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QPushButton
from shell import Ui_MainWindow
from waveform import WaveformWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Layout para el waveform
        self.wave_layout = QVBoxLayout(self.ui.frame_2)
        self.wave_layout.setContentsMargins(4,4,4,4)
        self.wave_layout.setSpacing(4)

        # Waveform widget
        self.waveform = WaveformWidget("example.wav")
        self.wave_layout.addWidget(self.waveform)

        # ----------- Controles de reproducción -----------
        controls_layout = QHBoxLayout()

        self.btn_play = QPushButton("Play")
        self.btn_stop = QPushButton("Stop")

        controls_layout.addWidget(self.btn_play)
        controls_layout.addWidget(self.btn_stop)

        self.wave_layout.addLayout(controls_layout)

        # Conectar botones
        self.btn_play.clicked.connect(self.on_play)
        self.btn_stop.clicked.connect(self.on_stop)

    def on_play(self):
        self.waveform.start_play()

    def on_stop(self):
        self.waveform.stop_play()


if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()
