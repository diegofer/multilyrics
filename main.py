"""
Multi Lyrics - Professional multitrack audio/video player for worship teams
Copyright (C) 2026 Diego Fernando

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

import os
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QThread, QTimer, Slot
from PySide6.QtGui import QCloseEvent, QIcon
from PySide6.QtWidgets import (QApplication, QMainWindow, QMessageBox,
                               QPushButton)

from utils.error_handler import safe_operation
from utils.logger import get_logger

logger = get_logger(__name__)

from core import constants
from core.engine import MultiTrackPlayer
from core.extraction_orchestrator import ExtractionOrchestrator
from core.playback_manager import PlaybackManager
from core.sync import SyncController
from models.meta import MetaJson
from models.timeline_model import TimelineModel
from ui import message_helpers
from ui.main_window import Ui_MainWindow
from ui.styles import StyleManager
from ui.widgets.add import AddDialog
from ui.widgets.controls_widget import ControlsWidget
from ui.widgets.spinner_dialog import SpinnerDialog
from ui.widgets.timeline_view import TimelineView, ZoomMode
from ui.widgets.track_widget import TrackWidget
from utils.helpers import (clear_layout, get_logarithmic_volume, get_mp4,
                           get_tracks)
from utils.lyrics_loader import LyricsLoader
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

        #Agregar waveform widget (starts empty, loads when user selects multi)
        self.timeline_view = TimelineView()
        self.ui.timeline_layout.addWidget(self.timeline_view)

        #Instanciar Player (needed before master track creation)
        self.audio_player = MultiTrackPlayer()

        #Agregar tracks widgets (master track receives both engine and timeline_view)
        self.master_track = TrackWidget(
            track_name="Master",
            track_index=0,
            engine=self.audio_player,
            is_master=True,
            timeline_view=self.timeline_view
        )
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
        self.sync = SyncController(44100)
        self.audio_player.audioTimeCallback = self.sync.audio_callback

        # Create single canonical TimelineModel instance shared across all components
        self.timeline_model = TimelineModel()
        self.playback = PlaybackManager(self.sync, timeline=self.timeline_model)
        self.lyrics_loader = LyricsLoader()

        # Asignar SyncController a VideoLyrics para que reporte posición
        self.video_player.sync_controller = self.sync

        # ===========================================================================
        # LEGACY HARDWARE OPTIMIZATION: Initialize UI state
        # ===========================================================================
        # Sincronizar estado del toggle de video con detección automática
        # Si hardware antiguo deshabilitó video, actualizar UI
        # ===========================================================================
        self.controls.set_video_enabled_state(self.video_player.is_video_enabled())

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
        # Auto-switch zoom mode based on playback state
        self.playback.playingChanged.connect(self._on_playback_state_changed)
        #self.sync.videoCorrectionNeeded.connect(self.video_player.apply_correction)

        # Waveform user seeks -> central request via PlaybackManager
        self.timeline_view.position_changed.connect(self.playback.request_seek)

        self.controls.play_clicked.connect(self.on_play_clicked)
        self.controls.pause_clicked.connect(self.on_pause_clicked)
        self.controls.edit_mode_toggled.connect(self.on_edit_mode_toggled)

        # Connect show_video_btn to control video window visibility
        self.controls.show_video_btn.toggled.connect(self._on_show_video_toggled)

        # ===========================================================================
        # LEGACY HARDWARE OPTIMIZATION: Video enable/disable control
        # ===========================================================================
        # Conectar toggle de video para permitir habilitar/deshabilitar manualmente
        # Útil cuando hardware antiguo tiene video deshabilitado por defecto
        # ===========================================================================
        self.controls.video_enabled_changed.connect(self._on_video_enabled_changed)

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
        meta_path = multi_path / constants.META_FILE_PATH

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

    @Slot()
    def on_pause_clicked(self) -> None:
        self.audio_player.pause()
        #self.waveform.pause_play()
        self.video_player.pause()
        # Update UI toggle
        self.controls.set_playing_state(False)

    @Slot()
    def on_edit_mode_toggled(self, enabled: bool) -> None:
        """Handle edit mode toggle from controls.

        When edit mode is enabled, switch to EDIT zoom mode.
        When disabled, return to GENERAL mode.
        """
        self.timeline_view.set_lyrics_edit_mode(enabled)

        # Auto-switch zoom mode based on edit state
        if enabled:
            # Edit mode activated -> switch to EDIT zoom for precise work
            self.timeline_view.set_zoom_mode(ZoomMode.EDIT, auto=True)
        else:
            # Edit mode deactivated -> return to GENERAL overview
            # Unless currently playing, in which case stay in PLAYBACK
            if self.audio_player and hasattr(self.audio_player, 'is_playing') and self.audio_player.is_playing():
                self.timeline_view.set_zoom_mode(ZoomMode.PLAYBACK, auto=True)
            else:
                self.timeline_view.set_zoom_mode(ZoomMode.GENERAL, auto=True)

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
        """Handler para cuando el timeline cambia de modo (actualizar UI y status bar)."""
        mode_str_map = {
            ZoomMode.GENERAL: "GENERAL",
            ZoomMode.PLAYBACK: "PLAYBACK",
            ZoomMode.EDIT: "EDIT"
        }
        mode_display_names = {
            ZoomMode.GENERAL: "Vista General",
            ZoomMode.PLAYBACK: "Reproducción",
            ZoomMode.EDIT: "Edición"
        }

        if mode in mode_str_map:
            self.controls.set_zoom_mode(mode_str_map[mode])

        # Update status bar with zoom mode
        if mode in mode_display_names:
            self.statusBar().showMessage(f"Modo de Zoom: {mode_display_names[mode]}", 3000)

    @Slot(bool)
    def _on_show_video_toggled(self, checked: bool):
        """Show or hide video window based on button state.

        Single click shows, double click hides.
        VLC player remains attached to window handle throughout.
        """
        if checked:
            logger.debug("Mostrando ventana de video")
            self.video_player.show_window()
        else:
            logger.debug("Ocultando ventana de video")
            self.video_player.hide_window()

    @Slot(bool)
    def _on_video_enabled_changed(self, enabled: bool):
        """Handle video enable/disable toggle from UI.

        Args:
            enabled: True to enable video playback, False to disable
        """
        logger.info(f"Usuario {'habilitó' if enabled else 'deshabilitó'} video manualmente")
        self.video_player.enable_video(enabled)

        # Si se deshabilitó video durante reproducción, detenerlo
        if not enabled and self.video_player.player.is_playing():
            self.video_player.stop()

    @Slot(bool)
    def _on_playback_state_changed(self, is_playing: bool) -> None:
        """Auto-switch zoom mode based on playback state.

        Unified mode logic:
        - Playing + auto-zoom enabled → PLAYBACK mode (optimal for reading)
        - Stopped + not in edit mode → GENERAL mode (overview)
        - Edit mode active → EDIT mode (takes precedence)
        """
        # Don't auto-switch if edit mode is active
        if self.timeline_view._lyrics_edit_mode:
            return

        # Don't auto-switch if user manually changed zoom (respect user choice)
        if self.timeline_view._user_zoom_override:
            return

        # Only auto-switch if enabled
        if not self.timeline_view.get_auto_zoom_enabled():
            return

        if is_playing:
            # Playing → switch to PLAYBACK mode for optimal reading
            self.timeline_view.set_zoom_mode(ZoomMode.PLAYBACK, auto=True)
        # Note: When paused, we keep the current zoom mode (don't auto-switch to GENERAL)
        # This allows users to pause and remain in PLAYBACK or EDIT mode for better context

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
        meta_path = multi_path / constants.META_FILE_PATH
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
        from ui.widgets.multi_metadata_editor_dialog import \
            MultiMetadataEditorDialog

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

        meta_path = self.active_multi_path / constants.META_FILE_PATH
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
        meta_path = song_path / constants.META_FILE_PATH
        master_path = song_path / constants.MASTER_TRACK
        tracks_folder_path = song_path / constants.TRACKS_PATH
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

        # ✨ Dependency Injection: TrackWidget receives engine reference directly
        for i, track in enumerate(tracks_paths_final):
            track_widget = TrackWidget(
                track_name=Path(track).stem,
                track_index=i,
                engine=self.audio_player,
                is_master=False
            )
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

        # Reset edit mode state when changing songs
        self.controls.set_edit_mode_enabled(True)  # Enable edit button for new song
        self.controls.set_play_mode_enabled(True)  # Enable play button for new song
        # If edit mode was active, deactivate it
        if self.controls.edit_toggle_btn.isChecked():
            self.controls.edit_toggle_btn.setChecked(False)  # This triggers _on_edit_toggle

        # Activar boton de edit mode en controles
        self.controls.set_edit_mode_enabled(True)  # Cuando hay multitrack seleccionado
        self.controls.set_play_mode_enabled(True)  # Cuando hay multitrack seleccionado

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
