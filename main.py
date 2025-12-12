from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QPushButton
from ui.shell import Ui_MainWindow
from PySide6.QtGui import QIcon, QCloseEvent
from PySide6.QtCore import Qt, QThread, Slot
from pathlib import Path
from typing import List

from core.utils import get_mp4, get_tracks, get_logarithmic_volume
from core import global_state
from ui.widgets.controls_widget import ControlsWidget
from ui.widgets.track_widget import TrackWidget
from ui.widgets.spinner_dialog import SpinnerDialog
from ui.widgets.add import AddDialog

from audio.waveform import WaveformWidget
from audio.extract import AudioExtractWorker
from audio.multitrack_player import MultiTrackPlayer
from video.video import VideoLyrics
from core.sync import SyncController
from core.playback_manager import PlaybackManager

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
        master_track_layout = QHBoxLayout(self.ui.frame_6_master)
        master_track_layout.addWidget(self.master_track)

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

        #Instanciar Player y enlazar con SyncController
        self.audio_player = MultiTrackPlayer()
        self.sync = SyncController(44100)
        self.audio_player.audioTimeCallback = self.sync.audio_callback
        self.playback = PlaybackManager(self.sync)
        
        # Asignar SyncController a VideoLyrics para que reporte posición
        self.video_player.sync_controller = self.sync
        
        #Conectar Signals
        self.plus_btn.clicked.connect(self.open_add_dialog)
        self.add_dialog.search_widget.multi_selected.connect(self.on_multi_selected)
        self.add_dialog.drop_widget.file_imported.connect(self.extract_audio)
        #self.waveform.time_updated.connect(self.controls.update_time_label)
        #self.waveform.sync_player.connect(self.on_sync_player)
        self.playback.positionChanged.connect(self.controls.update_time_position_label)
        self.playback.durationChanged.connect(self.controls.update_total_duration_label)
        self.sync.videoCorrectionNeeded.connect(self.video_player.apply_correction)
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
        self.audio_player.play()
        #self.waveform.start_play()
        self.video_player.start_playback()
    
    @Slot()
    def on_pause_clicked(self):
        self.audio_player.pause()
        #self.waveform.pause_play()
        self.video_player.pause()

    @Slot()
    def extract_audio(self, video_path: str):
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
        #actualizar lista de multis en el buscador. Se puede optimizar solo agregrando este multi a la lista en vez de llamar todos de nuevo
        self.add_dialog.search_widget.get_fresh_multis_list()
    
    @Slot()
    def handle_error(self, msg):
        print(f"ERROR: {msg}")


    # ----------------------------
    # Zona de carga de multis
    # ----------------------------

    def set_active_song(self, song_path):
        song_path = Path(song_path)

        tracks_path = song_path / global_state.TRACKS_PATH
        tracks = get_tracks(tracks_path)
        
        self.audio_player.load_tracks(tracks)
        
        # Set duration in PlaybackManager para notificar a UI
        self.playback.set_duration(self.audio_player.get_duration_seconds())

        tracks_layout = QHBoxLayout(self.ui.frame_5_tracks)
        
        """  if layout_tracks.itemAt(0) is not None:

            for i in reversed(range(layout_tracks.count())):
                widget_to_remove = layout_tracks.itemAt(i).widget()
                layout_tracks.removeWidget(widget_to_remove)
                widget_to_remove.setParent(None) """
       
        for i, track in enumerate(tracks):
            track_widget = TrackWidget(Path(track).stem, False)
            track_widget.volume_changed.connect(lambda gain, index=i: self.set_gain(index, gain))
            track_widget.mute_toggled.connect(lambda checked, index=i: self.set_mute(index, checked))
            track_widget.solo_toggled.connect(lambda checked, index=i: self.set_solo(index, checked))
            tracks_layout.addWidget(track_widget)
        tracks_layout.addStretch()

        #master_path = Path(multi_path) / global_state.MASTER_TRACK
        #self.waveform.load_audio(master_path)
        
        mp4_path = get_mp4(song_path)
        VIDEO_PATH = song_path / mp4_path
        self.video_player.set_media(VIDEO_PATH)

    @Slot()
    def set_mute(self, track_index: int, mute: bool):
        self.audio_player.mute(track_index, mute)

    @Slot()
    def set_solo(self, track_index: int, solo: bool):
        self.audio_player.solo(track_index, solo)

    @Slot()
    def set_gain(self, track_index: int, gain: float):
        gain_log = get_logarithmic_volume(gain)
        self.audio_player.set_gain(track_index, gain_log)

    def closeEvent(self, event: QCloseEvent):
        # cerrar ventana videoplayer
        if self.video_player:
             self.video_player.close()
        # cerrar ventana principal
        event.accept()


# ----------------------------
# Valores iniciales
# ----------------------------



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