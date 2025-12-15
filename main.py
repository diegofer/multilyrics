from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton
from ui.shell import Ui_MainWindow
from PySide6.QtGui import QIcon, QCloseEvent
from PySide6.QtCore import Qt, QThread, Slot
from pathlib import Path

from core.utils import get_mp4, get_tracks, get_logarithmic_volume, clear_layout
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

        # Agregar y settear Ui principal
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.tracksLayout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.ui.playlistLayout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        #Agregar plus buttom
        self.plus_btn = QPushButton()
        self.plus_btn.setFixedSize(50, 100)
        self.plus_btn.setIcon(QIcon("assets/img/plus-circle.svg"))
        self.plus_btn.setIconSize(self.plus_btn.size()  * 0.7)

        self.ui.playlistLayout.addWidget(self.plus_btn)
        
        #Agregar waveform widget
        self.waveform = WaveformWidget("example.wav")
        self.ui.waveformLayout.addWidget(self.waveform)

        #Agregar tracks widgets
        self.master_track = TrackWidget("Master", True)
        self.ui.masterLayout.addWidget(self.master_track)

        #Agregar controls widget
        self.controls = ControlsWidget()
        self.ui.controlsLayout.addWidget(self.controls)

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

        # Asignar players al PlaybackManager para control centralizado
        self.playback.set_audio_player(self.audio_player)
        self.playback.set_video_player(self.video_player)
        
        #Conectar Signals
        self.plus_btn.clicked.connect(self.open_add_dialog)
        self.add_dialog.search_widget.multi_selected.connect(self.on_multi_selected)
        self.add_dialog.drop_widget.file_imported.connect(self.extract_audio)
        self.playback.positionChanged.connect(self.controls.update_time_position_label)
        self.playback.positionChanged.connect(self.waveform.set_position_seconds)
        self.playback.durationChanged.connect(self.controls.update_total_duration_label)
        self.playback.playingChanged.connect(self.controls.set_playing_state)
        #self.sync.videoCorrectionNeeded.connect(self.video_player.apply_correction)
        # Master fader controls both waveform preview volume and global audio gain
        self.master_track.volume_changed.connect(self.set_master_gain)

        # Waveform user seeks -> central request via PlaybackManager
        self.waveform.position_changed.connect(self.playback.request_seek)

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
        #considerar correr primero video y luego audio para evitar delay en video
        self.audio_player.play()
        self.video_player.start_playback()
        # Update UI toggle
        self.controls.set_playing_state(True)
    
    @Slot()
    def on_pause_clicked(self):
        self.audio_player.pause()
        #self.waveform.pause_play()
        self.video_player.pause()
        # Update UI toggle
        self.controls.set_playing_state(False)

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
        #obtener rutas
        song_path = Path(song_path)
        master_path = Path(song_path) / global_state.MASTER_TRACK
        tracks_folder_path = song_path / global_state.TRACKS_PATH
        tracks_paths = get_tracks(tracks_folder_path)
        mp4_path = get_mp4(song_path)
        video_path = song_path / mp4_path
        
        # Actualizar MultiTrackPlayer
        self.audio_player.load_tracks(tracks_paths)
        self.playback.set_duration(self.audio_player.get_duration_seconds()) # Notificar a PlaybackManager
           
        clear_layout(self.ui.tracksLayout)  # Limpiar layout de tracks
       
        for i, track in enumerate(tracks_paths):
            track_widget = TrackWidget(Path(track).stem, False)
            track_widget.volume_changed.connect(lambda gain, index=i: self.set_gain(index, gain))
            track_widget.mute_toggled.connect(lambda checked, index=i: self.set_mute(index, checked))
            track_widget.solo_toggled.connect(lambda checked, index=i: self.set_solo(index, checked))
            self.ui.tracksLayout.addWidget(track_widget)
        
        # Actualizar Waveform
        if master_path.exists():
            self.waveform.load_audio_from_master(master_path)
        
        # Actualizar Video Player
        self.video_player.set_media(video_path)

    @Slot()
    def set_mute(self, track_index: int, mute: bool):
        self.audio_player.mute(track_index, mute)


    @Slot()
    def set_master_gain(self, slider_value: int):
        """Called from master fader slider (0..100)."""
        gain = get_logarithmic_volume(slider_value)
        # Update waveform preview volume (expects slider int)
        self.waveform.set_volume(slider_value)
        # Set global master gain on audio player
        try:
            self.audio_player.set_master_gain(gain)
        except Exception:
            pass

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