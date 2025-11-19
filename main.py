from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout
from shell import Ui_MainWindow
from waveform import WaveformWidget
from controls_widget import ControlsWidget
from track_widget import TrackWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Agregar Ui principal
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        #Agregar waveform widget
        self.waveform = WaveformWidget("example.wav")
        wave_layout = QVBoxLayout(self.ui.frame_2)
        wave_layout.setContentsMargins(4,1,1,1)
        wave_layout.addWidget(self.waveform)

        #Agregar tracks widgets
        self.master_track = TrackWidget("Master", True)
        tracks_layout = QHBoxLayout(self.ui.frame_3)
        tracks_layout.addWidget(self.master_track)

        #Agregar controls widget
        self.controls = ControlsWidget()
        control_layout = QHBoxLayout(self.ui.frame_4)
        control_layout.setContentsMargins(4,4,4,4)
        control_layout.addWidget(self.controls)
        
        #Conectar Signals
        self.waveform.time_updated.connect(self.controls.update_time_label)
        self.controls.play_clicked.connect(self.waveform.start_play)
        self.controls.pause_clicked.connect(self.waveform.pause_play)

        self.master_track.volume_changed.connect(self.waveform.set_volume)

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