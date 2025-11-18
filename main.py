from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget
from PySide6.QtCore import Qt
from shell import Ui_MainWindow
from waveform import WaveformWidget
from controls_widget import ControlsWidget
from qt_utils import add_widget_to_frame

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        #Agregar waveform widget
        self.waveform = WaveformWidget("example.wav")
        wave_layout = QVBoxLayout(self.ui.frame_2)
        wave_layout.setContentsMargins(4,4,4,4)
        wave_layout.addWidget(self.waveform)

        #Agregar controls widget
        self.controls = ControlsWidget()
        control_layout = QHBoxLayout(self.ui.frame_4)
        control_layout.setContentsMargins(4,4,4,4)
        control_layout.addWidget(self.controls)
        
        #Conectar Signals
        self.waveform.time_updated.connect(self.controls.update_time_label)
        self.controls.play_clicked.connect(self.waveform.start_play)
        self.controls.stop_clicked.connect(self.waveform.stop_play)

if __name__ == "__main__":
    import sys
    # Se necesita un archivo de audio WAV llamado "example.wav" en el mismo directorio.
    # Si no tienes uno, puedes usar un script de Python simple para crearlo:
    # import soundfile as sf
    # import numpy as np
    # sf.write('example.wav', np.random.uniform(-1, 1, 44100 * 5), 44100) # 5 segundos de ruido

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())