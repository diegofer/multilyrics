from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton
from PySide6.QtGui import QIcon, QCloseEvent
from PySide6.QtCore import Qt, QThread, Slot
from pathlib import Path
import os

from ui.shell import Ui_MainWindow
from ui.style_manager import StyleManager

from core.utils import get_mp4, get_tracks, get_logarithmic_volume, clear_layout
from core import global_state
from core.timeline_model import TimelineModel
from core.sync import SyncController
from core.playback_manager import PlaybackManager
from core.timeline_model import TimelineModel

from ui.widgets.controls_widget import ControlsWidget
from ui.widgets.track_widget import TrackWidget
from ui.widgets.spinner_dialog import SpinnerDialog
from ui.widgets.add import AddDialog
from ui.widgets.metadata_editor_dialog import MetadataEditorDialog
from ui.widgets.lyrics_selector_dialog import LyricsSelectorDialog

from audio.timeline_view import TimelineView, ZoomMode
from audio.extract import AudioExtractWorker
from audio.beats import BeatsExtractorWorker
from audio.chords import ChordExtractorWorker
from audio.multitrack_player import MultiTrackPlayer
from audio.lyrics.loader import LyricsLoader
from audio.meta import MetaJson

from video.video import VideoLyrics

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Agregar y settear Ui principal
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.mixer_tracks_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.ui.playlist_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        #Agregar plus buttom
        self.plus_btn = QPushButton()
        self.plus_btn.setFixedSize(50, 100)
        self.plus_btn.setIcon(QIcon("assets/img/plus-circle.svg"))
        self.plus_btn.setIconSize(self.plus_btn.size()  * 0.7)

        self.ui.playlist_layout.addWidget(self.plus_btn)
        
        #Agregar waveform widget
        self.timeline_view = TimelineView("example.wav")
        self.ui.timeline_layout.addWidget(self.timeline_view)
        #Agregar tracks widgets
        self.master_track = TrackWidget("Master", True)
        self.ui.mixer_master_layout.addWidget(self.master_track)

        #Agregar controls widget
        self.controls = ControlsWidget()
        self.ui.controls_layout.addWidget(self.controls)
        #Agregar modals
        self.loader = SpinnerDialog(self)
        self.add_dialog = AddDialog()

        #Agregar video player
        self.video_player = VideoLyrics()

        #Instanciar Player y enlazar con SyncController
        self.audio_player = MultiTrackPlayer()
        self.sync = SyncController(44100)
        self.audio_player.audioTimeCallback = self.sync.audio_callback
        
        # Create single canonical TimelineModel instance shared across all components
        self.timeline_model = TimelineModel()
        self.playback = PlaybackManager(self.sync, timeline=self.timeline_model)
        self.lyrics_loader = LyricsLoader()
        
        # Asignar SyncController a VideoLyrics para que reporte posición
        self.video_player.sync_controller = self.sync

        # Asignar players al PlaybackManager para control centralizado
        self.playback.set_audio_player(self.audio_player)
        self.playback.set_video_player(self.video_player)
        
        # Attach timeline to waveform widget
        self.timeline_view.set_timeline(self.timeline_model)
        
        #Conectar Signals
        self.plus_btn.clicked.connect(self.open_add_dialog)
        self.add_dialog.search_widget.multi_selected.connect(self.on_multi_selected)
        self.add_dialog.drop_widget.file_imported.connect(self.extraction_process)
        
        # Connect Controls to TimelineModel (canonical source of playhead time)
        self._timeline_unsub_controls = self.timeline_model.on_playhead_changed(
            self.controls.update_time_position_label
        )
        
        self.playback.durationChanged.connect(self.controls.update_total_duration_label)
        self.playback.playingChanged.connect(self.controls.set_playing_state)
        #self.sync.videoCorrectionNeeded.connect(self.video_player.apply_correction)
        # Master fader controls both waveform preview volume and global audio gain
        self.master_track.volume_changed.connect(self.set_master_gain)

        # Waveform user seeks -> central request via PlaybackManager
        self.timeline_view.position_changed.connect(self.playback.request_seek)

        self.controls.play_clicked.connect(self.on_play_clicked)
        self.controls.pause_clicked.connect(self.on_pause_clicked)
        self.controls.edit_mode_toggled.connect(self.on_edit_mode_toggled)
        
        # Connect zoom mode controls
        self.controls.zoom_mode_changed.connect(self.on_zoom_mode_changed)
        self.timeline_view.zoom_mode_changed.connect(self.on_timeline_zoom_mode_changed)


        # definir thread y worker para extraccion de audio
        self.edit_thread = None
        self.extract_worker = None
        self.beats_worker = None
        self.chords_worker = None


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
        
        # Auto-switch to PLAYBACK zoom mode if enabled
        if self.timeline_view.get_auto_zoom_enabled():
            self.timeline_view.set_zoom_mode(ZoomMode.PLAYBACK, auto=True)
    
    @Slot()
    def on_pause_clicked(self):
        self.audio_player.pause()
        #self.waveform.pause_play()
        self.video_player.pause()
        # Update UI toggle
        self.controls.set_playing_state(False)
    
    @Slot()
    def on_edit_mode_toggled(self, enabled: bool):
        self.timeline_view.set_lyrics_edit_mode(enabled)
    
    @Slot(str)
    def on_zoom_mode_changed(self, mode: str):
        """Handler para cuando el usuario cambia el modo desde la UI."""
        zoom_mode_map = {
            "GENERAL": ZoomMode.GENERAL,
            "PLAYBACK": ZoomMode.PLAYBACK,
            "EDIT": ZoomMode.EDIT
        }
        if mode in zoom_mode_map:
            self.timeline_view.set_zoom_mode(zoom_mode_map[mode], auto=False)
    
    @Slot(object)
    def on_timeline_zoom_mode_changed(self, mode):
        """Handler para cuando el timeline cambia de modo (actualizar UI)."""
        mode_str_map = {
            ZoomMode.GENERAL: "GENERAL",
            ZoomMode.PLAYBACK: "PLAYBACK",
            ZoomMode.EDIT: "EDIT"
        }
        if mode in mode_str_map:
            self.controls.set_zoom_mode(mode_str_map[mode])

    @Slot()
    def extraction_process(self, video_path: str):
        self.loader.show()
        print("Archivo importado y empezando extraccion de audio, metadatos, beats y acordes")
        
        # Instanciar thread y workers
        self.edit_thread = QThread()
        self.extract_worker = AudioExtractWorker(video_path)
        self.beats_worker = BeatsExtractorWorker()
        self.chords_worker = ChordExtractorWorker()

        self.extract_worker.moveToThread(self.edit_thread)
        self.beats_worker.moveToThread(self.edit_thread)
        self.chords_worker.moveToThread(self.edit_thread)

        # Conectar señales
        self.edit_thread.started.connect(self.extract_worker.run)

        # Paso del path de un worker al otro
        self.extract_worker.signals.result.connect(self.beats_worker.run)
        self.beats_worker.signals.result.connect(self.chords_worker.run)
        self.chords_worker.signals.result.connect(self.on_extraction_process)

        # Manejo de errores
        self.extract_worker.signals.error.connect(self.handle_error)
        self.beats_worker.signals.error.connect(self.handle_error)
        self.chords_worker.signals.error.connect(self.handle_error)
       
        # Finalización ordenada
        self.extract_worker.signals.finished.connect(lambda: print("Extracción terminada"))
        self.beats_worker.signals.finished.connect(lambda: print("Extracción de beats terminada"))
        self.chords_worker.signals.finished.connect(lambda: print("Extracción de acordes terminada"))

        # Cerrar hilo solo cuando todo haya terminado
        self.chords_worker.signals.finished.connect(self.edit_thread.quit)
        self.chords_worker.signals.finished.connect(self.chords_worker.deleteLater)
        self.beats_worker.signals.finished.connect(self.beats_worker.deleteLater)
        self.extract_worker.signals.finished.connect(self.extract_worker.deleteLater)
        self.edit_thread.finished.connect(self.edit_thread.deleteLater)

        self.edit_thread.start()


    @Slot()
    def on_extraction_process(self, audio_path):
        """
        Callback after audio/beats/chords extraction completes.
        Shows MetadataEditorDialog for user to refine metadata before lyrics search.
        """
        print(f"AUDIO_PATH: {audio_path}")
        multi_path = Path(audio_path).parent
        
        # Load metadata
        meta_path = multi_path / global_state.META_FILE_PATH
        self.meta = MetaJson(meta_path)
        meta_data = self.meta.read_meta()
        
        # Store for later use
        self._current_multi_path = multi_path
        self._current_meta_data = meta_data
        
        # Hide spinner before showing dialog
        self.loader.hide()
        
        # Show MetadataEditorDialog for user to refine metadata
        self._show_metadata_editor_dialog(meta_data)
    
    def _show_metadata_editor_dialog(self, meta_data: dict):
        """Show dialog for editing metadata before lyrics search"""
        dialog = MetadataEditorDialog(meta_data, parent=self)
        
        # Connect signals
        dialog.metadata_confirmed.connect(self._on_metadata_confirmed)
        dialog.search_skipped.connect(self._on_lyrics_search_skipped)
        
        # Show modal dialog
        dialog.exec()
    
    @Slot(dict)
    def _on_metadata_confirmed(self, edited_metadata: dict):
        """User confirmed metadata - proceed with lyrics download"""
        # Update metadata with edited values (for future use)
        self._current_meta_data.update(edited_metadata)
        
        # Show spinner during lyrics search
        self.loader.show()
        
        # Try automatic download with edited metadata
        lyrics_model = self.lyrics_loader.auto_download(
            self._current_multi_path,
            edited_metadata['track_name'],
            edited_metadata['artist_name'],
            edited_metadata.get('duration_seconds')
        )
        
        self.loader.hide()
        
        if lyrics_model is not None:
            # Success: lyrics downloaded automatically
            self._finalize_multi_creation(lyrics_model)
        else:
            # No automatic match - try manual selection
            self._try_manual_lyrics_selection(edited_metadata)
    
    def _try_manual_lyrics_selection(self, metadata: dict):
        """Show selector dialog when auto-download fails"""
        # Search all results without duration filtering
        results = self.lyrics_loader.search_all(
            metadata['track_name'],
            metadata['artist_name']
        )
        
        if not results:
            # No results at all - proceed without lyrics
            print(f"No synced lyrics found for: {metadata['track_name']} - {metadata['artist_name']}")
            self._finalize_multi_creation(None)
            return
        
        if len(results) == 1:
            # Only one result - download it directly
            lyrics_model = self.lyrics_loader.download_and_save(
                results[0],
                self._current_multi_path
            )
            self._finalize_multi_creation(lyrics_model)
            return
        
        # Multiple results - show selector dialog
        dialog = LyricsSelectorDialog(
            results,
            metadata.get('duration_seconds'),
            parent=self
        )
        
        # Connect signals
        dialog.lyrics_selected.connect(self._on_lyrics_selected)
        dialog.selection_cancelled.connect(self._on_lyrics_selection_cancelled)
        
        # Show modal dialog
        dialog.exec()
    
    @Slot(dict)
    def _on_lyrics_selected(self, result: dict):
        """User selected specific lyrics from multiple results"""
        self.loader.show()
        
        lyrics_model = self.lyrics_loader.download_and_save(
            result,
            self._current_multi_path
        )
        
        self.loader.hide()
        self._finalize_multi_creation(lyrics_model)
    
    @Slot()
    def _on_lyrics_selection_cancelled(self):
        """User cancelled lyrics selection - proceed without lyrics"""
        print("User cancelled lyrics selection")
        self._finalize_multi_creation(None)
    
    @Slot()
    def _on_lyrics_search_skipped(self):
        """User skipped lyrics search in metadata editor"""
        print("User skipped lyrics search")
        self.loader.hide()
        self._finalize_multi_creation(None)
    
    def _finalize_multi_creation(self, lyrics_model):
        """Complete multi creation and load it into the player"""
        # Set lyrics model (may be None)
        self.timeline_model.set_lyrics_model(lyrics_model)
        
        # Reload lyrics track in timeline view
        self.timeline_view.reload_lyrics_track()
        
        # Load the multi into player
        self.set_active_song(self._current_multi_path)
        
        # Update multis list in search widget
        self.add_dialog.search_widget.get_fresh_multis_list()
        
        # Clean up stored state
        self._current_multi_path = None
        self._current_meta_data = None
    
    @Slot()
    def handle_error(self, msg):
        print(f"ERROR: {msg}")


    # ----------------------------
    # Zona de carga de multis
    # ----------------------------

    def set_active_song(self, song_path):
        #obtener rutas
        song_path = Path(song_path)
        meta_path = song_path / global_state.META_FILE_PATH
        master_path = song_path / global_state.MASTER_TRACK
        tracks_folder_path = song_path / global_state.TRACKS_PATH
        tracks_paths = get_tracks(tracks_folder_path)
        print(f"Cargando multi: {song_path}")
        mp4_path = get_mp4(song_path)
        video_path = song_path / mp4_path

        # Cargar metadatos
        self.meta = MetaJson(meta_path)
        meta_data = self.meta.read_meta()
        #print(f"Metadatos cargados: {meta_data}")
        
        # actualizar controlWidgets
        tempo = meta_data.get("tempo", 120.0)
        compass = meta_data.get("compass", "?/?")
        self.controls.tempo_compass_label.setText(f"{int(tempo)} BPM\n{compass}")

        tracks_paths_final = []

        # Actualizar MultiTrackPlayer si folder tracks existe
        if tracks_folder_path.exists():
            tracks_paths_final = tracks_paths
        else:
            tracks_paths_final = [str(master_path)]

        self.audio_player.load_tracks(tracks_paths_final)  # Cargar tracks o master
        self.playback.set_duration(self.audio_player.get_duration_seconds()) # Notificar a PlaybackManager
           
        clear_layout(self.ui.mixer_tracks_layout)  # Limpiar layout de tracks
       
        for i, track in enumerate(tracks_paths_final):
            track_widget = TrackWidget(Path(track).stem, False)
            track_widget.volume_changed.connect(lambda gain, index=i: self.set_gain(index, gain))
            track_widget.mute_toggled.connect(lambda checked, index=i: self.set_mute(index, checked))
            track_widget.solo_toggled.connect(lambda checked, index=i: self.set_solo(index, checked))
            self.ui.mixer_tracks_layout.addWidget(track_widget)
        
        # Actualizar Waveform TimelineModel
        if master_path.exists():
            # Reuse existing timeline instance, just update its metadata
            self.timeline_view.load_audio_from_master(master_path)
            self.timeline_view.load_metadata(meta_data)

            # Actualizar LyricsModel
            lyrics_model = self.lyrics_loader.load(song_path, meta_data)
            self.timeline_model.set_lyrics_model(lyrics_model)
            
            # Notify timeline_view to initialize lyrics track
            self.timeline_view.reload_lyrics_track()
        
        # Actualizar Video Player
        self.video_player.set_media(video_path)

        # Activar boton de edit mode en controles
        self.controls.set_edit_mode_enabled(True)  # Cuando hay multitrack seleccionado

    @Slot()
    def set_mute(self, track_index: int, mute: bool):
        self.audio_player.mute(track_index, mute)


    @Slot()
    def set_master_gain(self, slider_value: int):
        """Called from master fader slider (0..100)."""
        gain = get_logarithmic_volume(slider_value)
        # Update waveform preview volume (expects slider int)
        self.timeline_view.set_volume(slider_value)
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
    
    # Decirle al sistema operativo cómo manejar el escalado de la ventana.
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"

    app = QApplication(sys.argv)
    # Asegura que los iconos y gráficos no se vean pixelados en pantallas 4K/Retina.
    app.setAttribute(Qt.AA_UseHighDpiPixmaps)

    StyleManager.setup_theme(app)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())