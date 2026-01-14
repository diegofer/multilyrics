from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QMessageBox
from PySide6.QtGui import QIcon, QCloseEvent
from PySide6.QtCore import Qt, QThread, Slot, QTimer
from pathlib import Path
from typing import Optional
import os

from utils.logger import get_logger
from utils.error_handler import safe_operation

logger = get_logger(__name__)

from ui.shell import Ui_MainWindow
from ui.style_manager import StyleManager
from ui import message_helpers

from utils.helpers import get_mp4, get_tracks, get_logarithmic_volume, clear_layout
from core import global_state
from models.timeline_model import TimelineModel
from core.sync import SyncController
from core.playback_manager import PlaybackManager

from ui.widgets.controls_widget import ControlsWidget
from ui.widgets.track_widget import TrackWidget
from ui.widgets.spinner_dialog import SpinnerDialog
from ui.widgets.add import AddDialog

from audio.timeline_view import TimelineView, ZoomMode
from core.extraction_orchestrator import ExtractionOrchestrator
from audio.multitrack_player import MultiTrackPlayer
from utils.lyrics_loader import LyricsLoader
from models.meta import MetaJson

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
        
        # Configurar StatusBar
        self.statusBar().showMessage("Listo")
        self.statusBar().setStyleSheet(f"""
            QStatusBar {{
                background-color: {StyleManager.get_color('bg_panel').name()};
                color: {StyleManager.get_color('text_normal').name()};
                border-top: 1px solid {StyleManager.get_color('blue_deep_medium').name()};
                font-size: 11px;
                padding: 4px;
            }}
        """)
        
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
        
        # Initialize master gain to slider's initial value (70% for headroom)
        self.set_master_gain(self.master_track.slider.value())

        # Waveform user seeks -> central request via PlaybackManager
        self.timeline_view.position_changed.connect(self.playback.request_seek)

        self.controls.play_clicked.connect(self.on_play_clicked)
        self.controls.pause_clicked.connect(self.on_pause_clicked)
        self.controls.edit_mode_toggled.connect(self.on_edit_mode_toggled)
        
        # Connect zoom mode controls
        self.controls.zoom_mode_changed.connect(self.on_zoom_mode_changed)
        self.timeline_view.zoom_mode_changed.connect(self.on_timeline_zoom_mode_changed)
        
        # Connect edit mode buttons from timeline
        self.timeline_view.edit_metadata_clicked.connect(self._on_edit_metadata_clicked)
        self.timeline_view.reload_lyrics_clicked.connect(self._on_reload_lyrics_clicked)


        # Extraction orchestrator (lazily initialized)
        self.extraction_orchestrator = None
        
        # Track active multi path for edit mode operations
        self.active_multi_path = None

    # ----------------------------
    # Helper Methods
    # ----------------------------
    
    def _load_metadata(self, multi_path: Path) -> Optional[dict]:
        """Load metadata from a multi directory.
        
        Centralized helper to load meta.json from a multi directory,
        with error handling and validation.
        
        Args:
            multi_path: Path to the multi directory
            
        Returns:
            Dictionary with metadata, or None if file doesn't exist
            
        Raises:
            Exception: If metadata file exists but can't be read
        """
        meta_path = multi_path / global_state.META_FILE_PATH
        
        if not meta_path.exists():
            logger.error(f"Archivo de metadata no encontrado: {meta_path}")
            return None
        
        meta_json = MetaJson(meta_path)
        return meta_json.read_meta()

    # ----------------------------
    # Event Handlers
    # ----------------------------

    @Slot()
    def open_add_dialog(self) -> None:
        self.add_dialog.exec()

    @Slot()
    def on_multi_selected(self, path: str) -> None:
        logger.debug(f"Multi selected: {path}")
        self.set_active_song(path)

    @Slot()
    def on_play_clicked(self) -> None:
        #considerar correr primero video y luego audio para evitar delay en video
        self.audio_player.play()
        self.video_player.start_playback()
        # Update UI toggle
        self.controls.set_playing_state(True)
        
        # Auto-switch to PLAYBACK zoom mode if enabled
        if self.timeline_view.get_auto_zoom_enabled():
            self.timeline_view.set_zoom_mode(ZoomMode.PLAYBACK, auto=True)
    
    @Slot()
    def on_pause_clicked(self) -> None:
        self.audio_player.pause()
        #self.waveform.pause_play()
        self.video_player.pause()
        # Update UI toggle
        self.controls.set_playing_state(False)
    
    @Slot()
    def on_edit_mode_toggled(self, enabled: bool) -> None:
        self.timeline_view.set_lyrics_edit_mode(enabled)
    
    @Slot(str)
    def on_zoom_mode_changed(self, mode: str) -> None:
        """Handler para cuando el usuario cambia el modo desde la UI."""
        zoom_mode_map = {
            "GENERAL": ZoomMode.GENERAL,
            "PLAYBACK": ZoomMode.PLAYBACK,
            "EDIT": ZoomMode.EDIT
        }
        if mode in zoom_mode_map:
            self.timeline_view.set_zoom_mode(zoom_mode_map[mode], auto=False)
    
    @Slot(object)
    def on_timeline_zoom_mode_changed(self, mode: ZoomMode) -> None:
        """Handler para cuando el timeline cambia de modo (actualizar UI)."""
        mode_str_map = {
            ZoomMode.GENERAL: "GENERAL",
            ZoomMode.PLAYBACK: "PLAYBACK",
            ZoomMode.EDIT: "EDIT"
        }
        if mode in mode_str_map:
            self.controls.set_zoom_mode(mode_str_map[mode])

    @Slot()
    def extraction_process(self, video_path: str) -> None:
        """Start the extraction pipeline for a video file.
        
        Delegates to ExtractionOrchestrator which handles:
        - Audio extraction (FFmpeg)
        - Beat/downbeat detection (madmom)
        - Chord recognition (madmom)
        
        Progress updates appear in status bar.
        """
        self.loader.show()
        logger.info("Iniciando extracción: audio, metadatos, beats y acordes")
        
        # Create orchestrator if needed
        if not self.extraction_orchestrator:
            self.extraction_orchestrator = ExtractionOrchestrator(
                status_callback=lambda msg: self.statusBar().showMessage(msg),
                parent=self
            )
            
            # Connect completion signals
            self.extraction_orchestrator.extraction_completed.connect(self.on_extraction_process)
            self.extraction_orchestrator.extraction_error.connect(self.handle_error)
        
        # Start extraction
        self.extraction_orchestrator.start_extraction(video_path)



    @Slot()
    def on_extraction_process(self, audio_path: str) -> None:
        """
        Callback after audio/beats/chords extraction completes.
        Attempts silent auto-download first, shows dialog only if needed.
        """
        logger.info(f"Procesando audio extraído: {audio_path}")
        multi_path = Path(audio_path).parent
        
        # Load metadata
        meta_path = multi_path / global_state.META_FILE_PATH
        self.meta = MetaJson(meta_path)
        meta_data = self.meta.read_meta()
        
        # Store for later use
        self._current_multi_path = multi_path
        self._current_meta_data = meta_data
        
        # Try silent auto-download with original metadata
        logger.info("Intentando descarga automática de letras con metadata original...")
        results = self.lyrics_loader.search_all(
            meta_data.get('track_name', ''),
            meta_data.get('artist_name', '')
        )
        
        if results:
            # Filter by exact duration match (≤1s tolerance)
            duration = meta_data.get('duration_seconds', 0)
            exact_matches = [
                r for r in results 
                if r.get('duration') and abs(r['duration'] - duration) <= 1.0
            ]
            
            if len(exact_matches) == 1:
                # ✨ SUCCESS: Single exact match - download automatically
                logger.info("Coincidencia exacta encontrada - descargando automáticamente")
                self.statusBar().showMessage("Descargando letras automáticamente...")
                self.loader.show()
                lyrics_model = self.lyrics_loader.download_and_save(
                    exact_matches[0],
                    self._current_multi_path
                )
                self.loader.hide()
                logger.info(f"Letras descargadas: {len(lyrics_model.lines) if lyrics_model else 0} líneas")
                
                if lyrics_model:
                    message_helpers.show_success_toast(
                        self, 
                        f"Letras descargadas: {len(lyrics_model.lines)} líneas"
                    )
                    self.statusBar().showMessage(f"Letras cargadas: {len(lyrics_model.lines)} líneas", 5000)
                
                self._finalize_multi_creation(lyrics_model)
                return
        
        # Auto-download failed or multiple matches - show search dialog
        logger.info(f"Descarga automática no disponible. Mostrando diálogo de búsqueda ({len(results)} resultados)")
        self.loader.hide()
        self._show_lyrics_search_dialog(meta_data, results)
    
    def _show_lyrics_search_dialog(self, meta_data: dict, initial_results: list = None, is_reload: bool = False) -> None:
        """Show unified search dialog with metadata editing and results selection
        
        Args:
            meta_data: Metadata dictionary with track/artist info
            initial_results: Pre-fetched search results (optional)
            is_reload: True if called from reload button (edit mode), False for creation flow
        """
        from ui.widgets.lyrics_search_dialog import LyricsSearchDialog
        
        dialog = LyricsSearchDialog(
            meta_data,
            initial_results or [],
            self.lyrics_loader,
            parent=self,
            skip_initial_search=is_reload  # En modo edición, no mostrar búsqueda automática
        )
        
        # Connect signals
        def on_lyrics_selected(result: dict):
            """User selected specific lyrics from search dialog"""
            self.loader.show()
            
            if is_reload:
                # Reload mode: download to existing multi
                lyrics_model = self.lyrics_loader.download_and_save(
                    result,
                    self.active_multi_path
                )
                
                self.loader.hide()
                
                if lyrics_model:
                    logger.info(f"Letras recargadas: {len(lyrics_model.lines)} líneas")
                    message_helpers.show_success_toast(
                        self,
                        f"Letras recargadas: {len(lyrics_model.lines)} líneas"
                    )
                    self.statusBar().showMessage(f"Letras recargadas exitosamente", 4000)
                    self._reload_lyrics_track(lyrics_model)
                else:
                    message_helpers.show_error_toast(
                        self,
                        "No se pudieron cargar las letras"
                    )
            else:
                # Creation mode: download to new multi
                lyrics_model = self.lyrics_loader.download_and_save(
                    result,
                    self._current_multi_path
                )
                
                self.loader.hide()
                
                if lyrics_model:
                    logger.info(f"Letras descargadas: {len(lyrics_model.lines)} líneas")
                    message_helpers.show_success_toast(
                        self,
                        f"Letras descargadas: {len(lyrics_model.lines)} líneas"
                    )
                    self._finalize_multi_creation(lyrics_model)
                else:
                    message_helpers.show_warning_toast(
                        self,
                        "No se pudieron descargar las letras"
                    )
                    self._finalize_multi_creation(None)
        
        def on_search_skipped():
            """User skipped lyrics"""
            if is_reload:
                # Reload mode: just close dialog
                logger.info("Usuario omitió recarga de letras")
            else:
                # Creation mode: load multi without lyrics
                logger.info("Usuario omitió búsqueda de letras - cargando sin letras")
                self._finalize_multi_creation(None)
        
        dialog.lyrics_selected.connect(on_lyrics_selected)
        dialog.search_skipped.connect(on_search_skipped)
        dialog.exec()
    
    def _finalize_multi_creation(self, lyrics_model: Optional['LyricsModel']) -> None:
        """Complete multi creation and load it into the player"""
        # Set lyrics model (may be None)
        self.timeline_model.set_lyrics_model(lyrics_model)
        
        # Reload lyrics track in timeline view
        self.timeline_view.reload_lyrics_track()
        
        # Load the multi into player
        self.set_active_song(self._current_multi_path)
        
        # Update status bar
        multi_name = self._current_multi_path.name if self._current_multi_path else "Desconocido"
        self.statusBar().showMessage(f"Multi cargado: {multi_name}", 5000)
        
        # Update multis list in search widget
        self.add_dialog.search_widget.get_fresh_multis_list()
        
        # Clean up stored state
        self._current_multi_path = None
        self._current_meta_data = None
    
    @Slot()
    def _on_edit_metadata_clicked(self) -> None:
        """Edit mode button: Edit display metadata (clean names for UI)"""
        if self.active_multi_path is None:
            logger.warning("No hay multi activo para editar metadata")
            message_helpers.show_warning_toast(self, "No hay multi activo cargado")
            return
        
        # Load current metadata
        meta_data = self._load_metadata(self.active_multi_path)
        if meta_data is None:
            return
        
        # Lazy import to avoid circular dependencies
        from ui.widgets.multi_metadata_editor_dialog import MultiMetadataEditorDialog
        
        # Show simple metadata editor for display fields only
        dialog = MultiMetadataEditorDialog(meta_data, self)
        dialog.metadata_saved.connect(self._on_display_metadata_saved)
        dialog.exec()
    
    @Slot()
    def _on_reload_lyrics_clicked(self) -> None:
        """Edit mode button: Search and reload lyrics using original search metadata"""
        if self.active_multi_path is None:
            logger.warning("No hay multi activo para recargar letras")
            return
        
        # Load current metadata
        meta_data = self._load_metadata(self.active_multi_path)
        if meta_data is None:
            return
        
        # Use ORIGINAL search fields (immutable) - not display fields
        search_metadata = {
            'track_name': meta_data.get('track_name', meta_data.get('title', '')),
            'artist_name': meta_data.get('artist_name', meta_data.get('artist', '')),
            'duration_seconds': meta_data.get('duration_seconds', meta_data.get('duration', 0.0))
        }
        
        # En modo edición: mostrar diálogo vacío, usuario busca manualmente
        # No hacer búsqueda automática previa
        self._show_lyrics_search_dialog(search_metadata, [], is_reload=True)
    
    @Slot(dict)
    def _on_display_metadata_saved(self, display_data: dict) -> None:
        """User saved edited display metadata - update meta.json"""
        if self.active_multi_path is None:
            return
        
        meta_path = self.active_multi_path / global_state.META_FILE_PATH
        if not meta_path.exists():
            return
        
        meta_json = MetaJson(meta_path)
        
        # Update only display fields (track_name and artist_name remain unchanged)
        meta_json.update_meta({
            'track_name_display': display_data['track_name_display'],
            'artist_name_display': display_data['artist_name_display']
        })
        
        logger.info(f"Metadata de visualización actualizada: {display_data['track_name_display']} - {display_data['artist_name_display']}")
        
        # Mostrar feedback al usuario
        message_helpers.show_success_toast(
            self,
            f"Metadata actualizada: {display_data['track_name_display']}"
        )
        self.statusBar().showMessage("Metadata actualizada exitosamente", 4000)
        
        # Refresh playlist to show new display name
        self.add_dialog.search_widget.refresh_multis_list()
    
    def _reload_lyrics_track(self, lyrics_model: 'LyricsModel') -> None:
        """Reload the lyrics track in timeline with new lyrics model"""
        self.timeline_model.set_lyrics_model(lyrics_model)
        self.timeline_view.reload_lyrics_track()
        logger.debug(f"Track de letras recargado: {len(lyrics_model.lines) if lyrics_model else 0} líneas")

    def _show_info_message(self, title: str, message: str) -> None:
        """Show a brief informational message to the user"""
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.setWindowModality(Qt.NonModal)
        
        # Auto-close after 4 seconds
        QTimer.singleShot(4000, msg_box.close)
        
        msg_box.show()
    
        
    
    @Slot()
    def handle_error(self, msg: str) -> None:
        logger.error(f"Error en procesamiento: {msg}")
        self.loader.hide()
        message_helpers.show_error(self, "Error de Procesamiento", msg)
        self.statusBar().showMessage("Error en procesamiento", 10000)


    # ----------------------------
    # Zona de carga de multis
    # ----------------------------

    def set_active_song(self, song_path: str | Path) -> None:
        # Stop current playback if any (fixes audio overlap and state issues)
        if self.audio_player and hasattr(self.audio_player, 'is_playing') and self.audio_player.is_playing():
            self.audio_player.pause()
            self.controls.set_playing_state(False)
        
        # Reset playback position to start
        self.playback.request_seek(0.0)
        
        #obtener rutas
        song_path = Path(song_path)
        self.active_multi_path = song_path  # Track active multi for edit operations
        meta_path = song_path / global_state.META_FILE_PATH
        master_path = song_path / global_state.MASTER_TRACK
        tracks_folder_path = song_path / global_state.TRACKS_PATH
        tracks_paths = get_tracks(tracks_folder_path)
        mp4_path = get_mp4(str(song_path))
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
            # Reset timeline view state for new song (fixes zoom mode bug)
            self.timeline_view.reset_view_state()
            
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
        with safe_operation("Setting master gain", silent=True):
            self.audio_player.set_master_gain(gain)

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