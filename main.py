from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QPushButton
from shell import Ui_MainWindow
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt, QThread, Slot
from pathlib import Path

from waveform import WaveformWidget
from controls_widget import ControlsWidget
from track_widget import TrackWidget
from spinner_dialog import SpinnerDialog
from extract import AudioExtractWorker
from video import VideoLyrics
from add import AddDialog
import global_state
from utils import get_multis_list, get_mp4
import global_state

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
        self.add_dialog = AddDialog()

        #Agregar video player
        self.video_player = VideoLyrics()
        
        #Conectar Signals
        self.plus_btn.clicked.connect(self.open_add_dialog)
        self.add_dialog.search_widget.multi_selected.connect(self.on_multi_selected)
        self.add_dialog.drop_widget.file_imported.connect(self.extract_audio)
        self.waveform.time_updated.connect(self.controls.update_time_label)
        self.master_track.volume_changed.connect(self.waveform.set_volume)
        self.controls.play_clicked.connect(self.on_play_clicked)
        self.controls.pause_clicked.connect(self.on_pause_clicked)
   
    @Slot()
    def open_add_dialog(self):
        self.add_dialog.exec()

    @Slot()
    def on_multi_selected(self, path):
        print(path)
        self.set_active_song(path)

    @Slot()
    def on_play_clicked(self):

        # waveform debe correr silenciado si hay stems
        self.waveform.start_play()
        self.video_player.start_playback()
    
    @Slot()
    def on_pause_clicked(self):
        self.waveform.pause_play()
        self.video_player.pause()

    @Slot()
    def extract_audio(self,  video_path: str):
        self.loader.show()
        print("Archivo importado y empezando extraccion de audio:", video_path)
        
        # Crear hilo y worker
        self.thread = QThread()
        self.extract_worker = AudioExtractWorker(video_path, None)
        self.extract_worker.moveToThread(self.thread)
        
        # Conectar señales
        self.thread.started.connect(self.extract_worker.run)
        self.extract_worker.signals.result.connect(self.on_extract_audio)
        self.extract_worker.signals.error.connect(self.handle_error)
        
        # Para destruir el thread correctamente
        self.extract_worker.signals.finished.connect(self.thread.quit)
        self.thread.finished.connect(self.thread.deleteLater)
        self.extract_worker.signals.finished.connect(self.extract_worker.deleteLater)

        self.thread.start()

    @Slot()
    def on_extract_audio(self, msg, audio_path):
        print(f"RESULTADO: {msg}")
        muti_path = Path(audio_path).parent
        self.set_active_song(muti_path)
        self.loader.hide()
    
    @Slot()
    def handle_error(self, msg):
        print(f"ERROR: {msg}")


    # ----------------------------
    # Zona de carga de multis
    # ----------------------------

    def set_active_song(self, multi_path):
        # si hay multitrack en el folder silenciar waveform
        #sino, cargar master.wav
        master_path = Path(multi_path) / global_state.MASTER_TRACK
        self.waveform.load_audio(master_path)
        
        mp4_path = get_mp4(multi_path)
        VIDEO_PATH = Path(multi_path) / mp4_path
        self.video_player.set_media(VIDEO_PATH)


# ----------------------------
# Valores iniciales
# ----------------------------

multis_list = get_multis_list(global_state.LIBRARY_PATH)
print(multis_list)


if __name__ == "__main__":
    import sys
    # Se necesita un archivo de audio WAV llamado "example.wav" en el mismo directorio.
    # Si no tienes uno, puedes usar un script de Python simple para crearlo:
    # import soundfile as sf
    # import numpy as np
    # sf.write('example.wav', np.random.uniform(-1, 1, 44100 * 5), 44100) # 5 segundos de ruido

    app = QApplication(sys.argv)
    app.setProperty("multis_list", multis_list)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())