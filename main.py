from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QPushButton
from shell import Ui_MainWindow
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt
from waveform import WaveformWidget
from controls_widget import ControlsWidget
from track_widget import TrackWidget
from drop_dialog import DropDialog
from spinner_dialog import SpinnerDialog
from extract import ExtractAudioThread


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Agregar Ui principal
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        #Agregar plus buttom
        self.plus_btn = QPushButton()
        self.plus_btn.setFixedSize(50, 100)
        self.plus_btn.setIcon(QIcon("assets/img/plus-circle.svg"))
        self.plus_btn.setIconSize(self.plus_btn.size()  * 0.7)

        playlist_layout = QHBoxLayout(self.ui.frame)
        playlist_layout.setContentsMargins(1,1,1,1)
        playlist_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        playlist_layout.addWidget(self.plus_btn)
        
        #Agregar waveform widget
        self.waveform = WaveformWidget("example.wav")
        wave_layout = QVBoxLayout(self.ui.frame_2)
        wave_layout.setContentsMargins(4,1,1,1)
        wave_layout.addWidget(self.waveform)

        #Agregar tracks widgets
        self.master_track = TrackWidget("Master", True)
        tracks_layout = QHBoxLayout(self.ui.frame_6_master)
        tracks_layout.addWidget(self.master_track)

        #Agregar controls widget
        self.controls = ControlsWidget()
        control_layout = QHBoxLayout(self.ui.frame_4)
        control_layout.setContentsMargins(4,4,4,4)
        control_layout.addWidget(self.controls)

        #Agregar modals
        self.loader = SpinnerDialog(self)
        
        #Conectar Signals
        self.plus_btn.clicked.connect(self.open_drop_dialog)
        self.waveform.time_updated.connect(self.controls.update_time_label)
        self.controls.play_clicked.connect(self.waveform.start_play)
        self.controls.pause_clicked.connect(self.waveform.pause_play)

        self.master_track.volume_changed.connect(self.waveform.set_volume)

    def open_drop_dialog(self):
        self.drop_dialog = DropDialog() 
        self.drop_dialog.file_imported.connect(self.extract_audio)
        self.drop_dialog.exec()
        
    
    def extract_audio(self,  file_path: str):
        self.loader.show()
        print("Procesando archivo:", file_path)
        #verificar que sea video. Si es audio, no extraer.

        self.extract_thread = ExtractAudioThread(file_path)
        self.extract_thread.result.connect(self.on_extract_audio)
        self.extract_thread.start()

    def on_extract_audio(self):
        self.loader.hide()

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