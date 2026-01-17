"""
Multi Lyrics - Timeline View Widget
Copyright (C) 2026 Diego Fernando

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

# Waveform Widget with Zoom, Scroll, and Animated Playhead

from enum import Enum, auto
from pathlib import Path
from typing import Optional

import numpy as np
import soundfile as sf
from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import (QCloseEvent, QColor, QFont, QMouseEvent, QPainter,
                           QPen, QWheelEvent)
from PySide6.QtWidgets import QWidget

from models.lyrics_model import LyricsModel
from models.timeline_model import TimelineModel
from ui.styles import StyleManager
from ui.widgets.tracks.beat_track import BeatTrack, ViewContext
from ui.widgets.tracks.chord_track import ChordTrack
from ui.widgets.tracks.lyrics_track import LyricsTrack
from ui.widgets.tracks.playhead_track import PlayheadTrack
from ui.widgets.tracks.waveform_track import WaveformTrack
from utils.error_handler import safe_operation
from utils.helpers import format_time, get_logarithmic_volume
from utils.logger import get_logger

logger = get_logger(__name__)

# Performance & zoom/downsampling settings
MIN_SAMPLES_PER_PIXEL = 10   # Do not allow fewer than 10 samples per pixel (visual limit)
MAX_ZOOM_LEVEL = 500.0      # Max zoom factor multiplier

# ===========================================================================
# HARDWARE OPTIMIZATION PROFILES
# ===========================================================================
# GLOBAL_DOWNSAMPLE_FACTOR: Agregación de samples en vista GENERAL
# - 1024: Hardware moderno (2015+) - Suave y detallado
# - 2048: Hardware medio (2012-2015) - Balance performance/calidad
# - 4096: Hardware antiguo (2008-2012) - Máxima estabilidad en CPU legacy
# ===========================================================================
GLOBAL_DOWNSAMPLE_FACTOR = 4096  # Configurado para i5-2410M (Sandy Bridge)

class ZoomMode(Enum):
    """Tres modos de zoom predefinidos con diferentes comportamientos"""
    GENERAL = auto()    # Vista completa de la forma de onda
    PLAYBACK = auto()   # Zoom adaptado para ver letras durante reproducción
    EDIT = auto()       # Zoom libre para edición precisa

# Rangos de zoom factor para cada modo
ZOOM_RANGES = {
    ZoomMode.GENERAL: (1.0, 5.0),      # Vista panorámica completa
    ZoomMode.PLAYBACK: (8.0, 30.0),    # Vista enfocada en letras (±5-15 segundos)
    ZoomMode.EDIT: (1.0, 500.0)        # Rango completo para edición
}

class TimelineView(QWidget):
    """
    Widget pasivo para dibujar la onda y manejar eventos de usuario (zoom, scroll, doble clic para seek).
    No reproduce audio; la reproducción y reloj son responsabilidad de `MultiTrackPlayer`/`PlaybackManager`.
    """
    # Señal para notificar que el usuario ha cambiado la posición (segundos)
    position_changed = Signal(float)
    # Señal para notificar cambios de modo de zoom
    zoom_mode_changed = Signal(object)  # ZoomMode
    # Señales para botones de edición de lyrics
    edit_metadata_clicked = Signal()
    reload_lyrics_clicked = Signal()

    def __init__(self, parent=None, timeline: Optional[TimelineModel] = None):
        """Initialize TimelineView in empty state.

        Audio will be loaded later via load_audio_from_master() when user selects a multi.
        """
        super().__init__(parent)
        self.setContentsMargins(9, 0, 9, 0) # Margen horizontal consistente
        self.setObjectName("timeline_view")

        # --- Audio data - always starts as None ---
        self.audio_path: Optional[str] = None
        self.audio_data: Optional[np.ndarray] = None
        self.sample_rate: int = 44100  # Default, will be updated when audio loads

        # Legacy aliases for compatibility (deprecated - use audio_data/sample_rate)
        self.samples = np.array([], dtype=np.float32)
        self.sr = 44100
        self.total_samples = 0
        self.duration_seconds = 0.0
        self.volume = 1.0  # Factor de amplitud de volumen (0.0 a 1.0)

        # --- View parameters ---
        self.zoom_factor = 1.0
        self.center_sample = 0

        # --- Zoom Mode System ---
        self.current_zoom_mode = ZoomMode.GENERAL
        self._auto_zoom_mode_enabled = True  # Auto-switch to PLAYBACK on play
        self._user_zoom_override = False     # True if user manually changed zoom in current mode

        # --- Playhead ---
        # NOTE: TimelineModel is the canonical source of time; the widget keeps a
        # cached `playhead_sample` only for rendering and viewport logic.
        self.playhead_sample = 0

        # Optional TimelineModel reference. Use `set_timeline()` to attach
        # after construction. This keeps the widget UI-independent while
        # observing canonical time changes from the timeline model.
        self.timeline: Optional[TimelineModel] = None
        self._timeline_unsubscribe = None
        if timeline is not None:
            self.set_timeline(timeline)

        # Initialize all tracks once at construction
        self._waveform_track = WaveformTrack()
        self._beat_track = BeatTrack()
        self._chord_track = ChordTrack()
        self._playhead_track = PlayheadTrack()
        self._lyrics_track = None  # Will be initialized when lyrics are loaded

        # --- Interaction ---
        self._dragging = False
        self._last_mouse_x = None

        # --- Lyrics Edit Mode ---
        self._lyrics_edit_mode: bool = False

        # --- Edit Mode Buttons ---
        self._edit_buttons_visible = False
        self._button_width = 140
        self._button_height = 32
        self._button_spacing = 10
        self._button_margin = 10
        self._hovered_button = None  # 'edit_metadata' or 'reload_lyrics'

        # Set minimum height for empty state
        self.setMinimumHeight(100)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)  # Enable mouse tracking for hover effects

        logger.info("TimelineView initialized - waiting for multi selection")

    # --------------------------------------------------------------------
    #   FUNCIONES PRINCIPALES DEL SINCRONIZADOR
    # --------------------------------------------------------------------
    # Waveform is passive; sync handled by SyncController/PlaybackManager
    # No need for a timer nor sample clock here.
    def _set_empty_state(self) -> None:
        """Establece las variables internas en un estado seguro sin audio."""
        self.samples = np.array([], dtype=np.float32)
        self.sr = 44100
        self.total_samples = 0
        self.duration_seconds = 0.0
        self.zoom_factor = 1.0
        self.center_sample = 0
        self.playhead_sample = 0
        self._reset_waveform_cache()
        self.update()

    def _reset_waveform_cache(self) -> None:
        """Clear cached waveform envelope/rendering in the track (if any)."""
        if getattr(self, '_waveform_track', None) is not None:
            with safe_operation("Resetting waveform cache", silent=True):
                self._waveform_track.reset_cache()

    def _reset_to_empty_state(self) -> None:
        """Reset timeline to empty state after error or when clearing content.

        This is safer than _set_empty_state as it's specifically for error recovery.
        """
        self.audio_data = None
        self.audio_path = None
        self.sample_rate = 44100
        # Update legacy aliases
        self.samples = np.array([], dtype=np.float32)
        self.sr = 44100
        self.total_samples = 0
        self.duration_seconds = 0.0
        self.setMinimumHeight(100)
        self.update()
        logger.debug("Timeline reset to empty state")

    def reset_view_state(self) -> None:
        """Reset view state when loading a new song.

        This ensures that zoom mode, user overrides, and playhead position
        are reset to defaults, fixing the bug where PLAYBACK zoom mode
        stops working after changing songs.
        """
        logger.debug("Resetting TimelineView state for new song")

        # Reset zoom mode to GENERAL
        self.current_zoom_mode = ZoomMode.GENERAL

        # Clear user zoom override flag (critical for PLAYBACK mode to work)
        self._user_zoom_override = False

        # Re-enable auto zoom mode
        self._auto_zoom_mode_enabled = True

        # Reset playhead to start
        self.playhead_sample = 0

        # Reset zoom and center if we have audio loaded
        if self.total_samples > 0:
            self.center_sample = self.total_samples // 2
            self.zoom_factor = 1.0

        # Clear lyrics edit mode state
        self._lyrics_edit_mode = False
        self._edit_buttons_visible = False
        self._hovered_button = None

        # Clear dragging state
        self._dragging = False
        self._last_mouse_x = None

        # Trigger repaint
        self.update()

    def load_audio(self, audio_path: str) -> bool:
        """Carga nuevos datos de audio en el widget desde una ruta de archivo."""

        if not audio_path:
            self._set_empty_state()
            return False

        try:
            data, sr = sf.read(audio_path)
            if data.ndim > 1:
                data = data.mean(axis=1)

            self.samples = np.asarray(data, dtype=np.float32)
            self.sr = sr
            self.total_samples = len(self.samples)

            if self.total_samples == 0:
                raise ValueError("El archivo de audio está vacío o no contiene datos válidos.")

            self.duration_seconds = self.total_samples / self.sr

            # Resetear la vista y el playhead
            self.zoom_factor = 1.0
            self.center_sample = self.total_samples // 2
            self.playhead_sample = 0

            self._reset_waveform_cache()

            # We no longer maintain beat/chord samples locally — timeline holds
            # that information. Nothing to recompute here.

            self.update()
            return True

        except Exception as e:
            logger.error(f"Error al cargar el audio '{audio_path}': {e}", exc_info=True)
            self._set_empty_state()
            return False


    # ==============================================================
    # VOLUME CONTROL (LOGARÍTMICO)
    # ==============================================================
    def set_volume(self, slider_value: int) -> None:
        # Volume only affects visualization amplitude (optional)
        self.volume = get_logarithmic_volume(slider_value)
        self.update()


    # ==============================================================
    # PLAYBACK CONTROL
    # ==============================================================
    # The WaveformWidget is passive and does not manage audio playback.
    # Playback position is provided via `set_position_seconds()` from PlaybackManager.


    # ==============================================================
    # ZOOM
    # ==============================================================
    def set_zoom(self, factor: float) -> None:
        if self.total_samples == 0:
            return
        w = max(1, self.width())
        # Clamp to allowed range & ensure samples-per-pixel >= MIN_SAMPLES_PER_PIXEL
        new_factor = max(1.0, min(factor, MAX_ZOOM_LEVEL))
        new_factor = self._clamp_zoom_for_width(new_factor, w)
        self.zoom_factor = new_factor
        self.center_sample = int(np.clip(self.center_sample, 0, len(self.samples)-1))
        self._reset_waveform_cache()
        self.update()

    def load_audio_from_master(self, master_path: str | Path) -> None:
        """Load audio from master track file.

        Handles transition from empty state to loaded state.

        Args:
            master_path: Path to master.wav file
        """
        # Convert Path to string if needed
        if not isinstance(master_path, str):
            master_path = str(master_path)

        master_path = Path(master_path)

        if not master_path.exists():
            logger.error(f"Master track not found: {master_path}")
            return

        try:
            # Load audio data
            audio_data, sample_rate = sf.read(str(master_path), dtype='float32')

            # Convert stereo to mono if needed
            if audio_data.ndim > 1:
                audio_data = np.mean(audio_data, axis=1)

            # Update state
            self.audio_data = audio_data
            self.audio_path = str(master_path)
            self.sample_rate = sample_rate

            # Update legacy aliases
            self.samples = audio_data
            self.sr = sample_rate
            self.total_samples = len(audio_data)
            self.duration_seconds = self.total_samples / self.sample_rate

            # Transition from empty state: restore normal height
            self.setMinimumHeight(200)

            # Reset view parameters
            self.zoom_factor = 1.0
            self.center_sample = self.total_samples // 2
            self.playhead_sample = 0

            # Update timeline model with new audio dimensions
            if self.timeline:
                self.timeline.set_sample_rate(self.sample_rate)
                self.timeline.set_duration_seconds(self.duration_seconds)

                logger.info(
                    f"Audio loaded: {self.total_samples:,} samples @ {self.sample_rate}Hz "
                    f"({self.duration_seconds:.2f}s)"
                )

            # Clear cache and force repaint with new audio
            self._reset_waveform_cache()
            self.update()

        except Exception as e:
            logger.error(f"Failed to load audio from {master_path}: {e}")
            self._reset_to_empty_state()

    def has_audio_loaded(self) -> bool:
        """Check if audio data is currently loaded.

        Returns:
            True if audio is loaded and ready for playback, False otherwise
        """
        return self.audio_data is not None and len(self.audio_data) > 0

    def get_audio_info(self) -> Optional[dict]:
        """Get information about currently loaded audio.

        Returns:
            Dictionary with audio metadata, or None if no audio loaded:
            {
                'path': str,           # Path to audio file
                'samples': int,        # Total number of samples
                'sample_rate': int,    # Sample rate in Hz
                'duration': float      # Duration in seconds
            }
        """
        if not self.has_audio_loaded():
            return None

        return {
            'path': self.audio_path,
            'samples': len(self.audio_data),
            'sample_rate': self.sample_rate,
            'duration': len(self.audio_data) / self.sample_rate
        }

    def _clamp_zoom_for_width(self, factor: float, width: int) -> float:
        """Ensure zoom factor keeps samples-per-pixel >= MIN_SAMPLES_PER_PIXEL and within limits."""
        if self.total_samples == 0 or width <= 0:
            return max(1.0, min(factor, MAX_ZOOM_LEVEL))
        max_factor_by_spp = self.total_samples / (MIN_SAMPLES_PER_PIXEL * width)
        max_allowed = max(1.0, min(MAX_ZOOM_LEVEL, max_factor_by_spp))
        return max(1.0, min(factor, max_allowed))

    def load_metadata(self, meta_data: dict) -> None:
        """Load metadata dictionary and forward to TimelineModel.

        Parses beats/chords from metadata and forwards directly to the timeline.
        If no timeline is attached, metadata is discarded (fail-safe).
        """
        if not meta_data or self.timeline is None:
            self.update()
            return

        # Parse beats
        beats_input = meta_data.get("beats", []) if isinstance(meta_data, dict) else []
        beats_seconds = []
        downbeat_flags = []
        for item in beats_input:
            with safe_operation(f"Parsing beat item {item}", silent=True, log_level="debug"):
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    t = float(item[0])
                    pos = int(item[1])
                    beats_seconds.append(t)
                    downbeat_flags.append(1 if pos == 1 else 0)
                else:
                    t = float(item)
                    beats_seconds.append(t)
                    downbeat_flags.append(0)

        # Parse chords
        chords_input = meta_data.get("chords", []) if isinstance(meta_data, dict) else []
        chords_parsed = []
        for item in chords_input:
            with safe_operation(f"Parsing chord item {item}", silent=True, log_level="debug"):
                if isinstance(item, (list, tuple)) and len(item) >= 3:
                    s = float(item[0])
                    e = float(item[1])
                    name = str(item[2]).strip()
                    if e < s:
                        s, e = e, s
                    chords_parsed.append((s, e, name))

        # Forward to timeline immediately
        with safe_operation("Setting timeline beats", silent=True):
            self.timeline.set_beats(beats_seconds, downbeat_flags)

        with safe_operation("Setting timeline chords", silent=True):
            self.timeline.set_chords(chords_parsed)

        self.update()

    def zoom_by(self, ratio: float, cursor_x: int = None) -> None:
        if self.total_samples == 0:
            return

        old_zoom = self.zoom_factor
        tentative_zoom = max(1.0, old_zoom * ratio)
        w = max(1, self.width())

        # Aplicar límites del modo actual
        tentative_zoom = self._clamp_zoom_to_mode(tentative_zoom)
        new_zoom = self._clamp_zoom_for_width(tentative_zoom, w)

        if cursor_x is None:
            self.zoom_factor = new_zoom
        else:
            old_spp = self._samples_per_pixel(old_zoom, w)
            sample_at_cursor = int(self.center_sample - (w/2 - cursor_x) * old_spp)
            new_spp = self._samples_per_pixel(new_zoom, w)
            new_center = int(sample_at_cursor + (w/2 - cursor_x) * new_spp)
            self.center_sample = int(np.clip(new_center, 0, len(self.samples)-1))
            self.zoom_factor = new_zoom

        # Marcar que el usuario ha hecho zoom manual
        self._user_zoom_override = True

        # After zoom, ensure the playhead remains visible in the current viewport
        with safe_operation("Ensuring playhead visible after zoom", silent=True):
            self._ensure_playhead_visible()

        # Zoom changed -> invalidate render cache
        self._reset_waveform_cache()

        self.update()

    def _samples_per_pixel(self, zoom_factor: float, width_pixels: int) -> float:
        if width_pixels <= 0:
            return 1.0

        total_samples = len(self.samples)
        if total_samples == 0:
            return 1.0 # Si no hay audio, 1 muestra por pixel (dummy)

        visible_samples = max(1.0, total_samples / zoom_factor)
        spp = visible_samples / width_pixels
        return max(1e-6, spp)

    # ==============================================================
    # ZOOM MODE SYSTEM
    # ==============================================================

    def set_zoom_mode(self, mode: ZoomMode, auto: bool = True) -> None:
        """
        Cambia el modo de zoom y ajusta la vista según el modo.

        Args:
            mode: Modo de zoom a aplicar (GENERAL, PLAYBACK, EDIT)
            auto: Si es True, es un cambio automático; si es False, es manual del usuario
        """
        if self.total_samples == 0:
            return

        if self.current_zoom_mode == mode:
            return

        old_mode = self.current_zoom_mode
        self.current_zoom_mode = mode

        # Calcular zoom y centro apropiados para el nuevo modo
        self._calculate_zoom_for_mode(mode, auto)

        # Marcar si el usuario hizo un cambio manual
        if not auto:
            self._user_zoom_override = False

        # Notificar cambio de modo
        self.zoom_mode_changed.emit(mode)

        # Invalidar cache y redibujar
        self._reset_waveform_cache()
        self.update()

    def _calculate_zoom_for_mode(self, mode: ZoomMode, auto: bool) -> float:
        """
        Calcula el zoom_factor y center_sample apropiados para el modo dado.
        """
        w = max(1, self.width())

        if mode == ZoomMode.GENERAL:
            # Modo GENERAL: mostrar toda la forma de onda
            self.zoom_factor = 1.0
            self.center_sample = self.total_samples // 2

        elif mode == ZoomMode.PLAYBACK:
            # Modo PLAYBACK: zoom para ver letras (±10 segundos alrededor del playhead)
            # Aproximadamente 20 segundos visibles en pantalla
            target_visible_seconds = 20.0
            target_visible_samples = target_visible_seconds * self.sr
            self.zoom_factor = self.total_samples / target_visible_samples

            # Clamp al rango del modo
            min_zoom, max_zoom = ZOOM_RANGES[mode]
            self.zoom_factor = np.clip(self.zoom_factor, min_zoom, max_zoom)

            # Centrar en el playhead
            self.center_sample = int(np.clip(self.playhead_sample, 0, self.total_samples - 1))

        elif mode == ZoomMode.EDIT:
            # Modo EDIT: mantener zoom actual si viene de otro modo, o usar zoom moderado
            if auto:
                # Si es cambio automático, usar un zoom moderado
                self.zoom_factor = 20.0
            # Si es manual, mantener el zoom actual

            # Clamp al rango del modo
            min_zoom, max_zoom = ZOOM_RANGES[mode]
            self.zoom_factor = np.clip(self.zoom_factor, min_zoom, max_zoom)

            # Centrar en el playhead para no perderlo de vista
            self.center_sample = int(np.clip(self.playhead_sample, 0, self.total_samples - 1))

        # Asegurar que el zoom sea válido para el ancho actual
        self.zoom_factor = self._clamp_zoom_for_width(self.zoom_factor, w)
        return self.zoom_factor

    def _clamp_zoom_to_mode(self, zoom: float) -> float:
        """Restringe el zoom al rango permitido por el modo actual."""
        min_zoom, max_zoom = ZOOM_RANGES[self.current_zoom_mode]
        return np.clip(zoom, min_zoom, max_zoom)

    def get_auto_zoom_enabled(self) -> bool:
        """Retorna si el cambio automático de modo está habilitado."""
        return self._auto_zoom_mode_enabled

    def set_auto_zoom_enabled(self, enabled: bool) -> None:
        """Habilita o deshabilita el cambio automático de modo al reproducir."""
        self._auto_zoom_mode_enabled = enabled

    # Waveform envelope computation moved to WaveformTrack

    # ==============================================================
    # SCROLL (Mouse + Keyboard)
    # ==============================================================
    def wheelEvent(self, event: QWheelEvent) -> None:
        if self.total_samples == 0:
            return

        modifiers = event.modifiers()

        # SHIFT + wheel = horizontal scroll
        if modifiers & Qt.ShiftModifier:
            delta = event.angleDelta().y()
            if delta != 0:
                direction = -1 if delta > 0 else 1
                w = max(1, self.width())
                spp = self._samples_per_pixel(self.zoom_factor, w)
                shift = int(direction * w * 0.1 * spp)
                self.center_sample = int(np.clip(self.center_sample + shift, 0, len(self.samples)-1))
                self.update()
            return

        # normal wheel = zoom
        delta = event.angleDelta().y()
        if delta == 0:
            return
        steps = delta / 120.0
        ratio = 1.15 ** steps
        cursor_x = event.position().x() if hasattr(event, "position") else event.x()
        self.zoom_by(ratio, int(cursor_x))

    # --------------------------------------------------------------
    # mouseDoubleClickEvent: Mover playhead (Doble clic IZQUIERDO)
    # --------------------------------------------------------------
    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if self.total_samples == 0:
            return

        # TODO (Lyrics Edit Mode): When _lyrics_edit_mode is True and user double-clicks
        # on a lyric line, open an inline text editor for that line.
        # For now, handle edit mode separately and fall through to existing behavior.
        if self._lyrics_edit_mode:
            # TODO: Detect if click is on a lyrics track region
            # TODO: If so, activate inline editor and return early
            pass

        # Mover playhead solo con doble clic izquierdo
        if event.button() == Qt.LeftButton:
            w = max(1, self.width())

            # Detectar click dentro del área de la forma de onda
            x = event.x()
            rel = x / w

            total_samples = len(self.samples)
            spp = self._samples_per_pixel(self.zoom_factor, w)
            half_visible = (w * spp) / 2.0
            start = int(np.clip(self.center_sample - half_visible, 0, total_samples - 1))
            end = int(np.clip(self.center_sample + half_visible, 0, total_samples - 1))

            # Nueva posición del playhead
            new_sample = int(start + rel * (end - start))

            # Compute time for the new sample
            current_time = new_sample / float(self.sr)

            # Prefer the TimelineModel as the canonical owner of playhead time.
            # If a timeline is attached, update it rather than setting the widget's
            # internal playhead directly. This keeps a single source of truth.
            if getattr(self, 'timeline', None) is not None:
                with safe_operation("Updating timeline playhead on double-click", silent=True):
                    self.timeline.set_playhead_time(current_time)
                    # Fallback if update fails
                    if not hasattr(self, '_last_timeline_update_success'):
                        self.set_playhead_sample(new_sample)
            else:
                self.set_playhead_sample(new_sample)

            # Emitir la nueva posición en segundos al receptor (e.g., Audio Player)
            # Keep emitting the legacy signal so existing code (seek handlers)
            # continues to work as before.
            self.position_changed.emit(current_time)
        else:
            super().mouseDoubleClickEvent(event)


    # --------------------------------------------------------------
    # mousePressEvent: Iniciar arrastre horizontal (Clic IZQUIERDO)
    # --------------------------------------------------------------
    def mousePressEvent(self, event: QMouseEvent) -> None:
        # Check if clicking on edit mode buttons first
        if self._edit_buttons_visible and event.button() == Qt.LeftButton:
            clicked_button = self._get_button_at_pos(event.x(), event.y())
            if clicked_button == 'edit_metadata':
                self.edit_metadata_clicked.emit()
                return
            elif clicked_button == 'reload_lyrics':
                self.reload_lyrics_clicked.emit()
                return

        # TODO (Lyrics Edit Mode): When _lyrics_edit_mode is True, detect clicks
        # on lyric lines for selection or dragging (future: retiming).
        # For now, fall through to existing pan/scroll behavior.
        if self._lyrics_edit_mode:
            # TODO: Check if click is on a lyrics region
            # TODO: If so, handle selection and prevent scroll/pan
            pass

        # Lógica para scroll/pan (ARRRASTRE CON CLIC IZQUIERDO)
        if event.button() == Qt.LeftButton and self.total_samples > 0:
            # Solo permitir arrastre si hay audio cargado
            self._dragging = True
            self._last_mouse_x = event.x()
            self.setCursor(Qt.ClosedHandCursor) # Cambiar cursor para indicar arrastre
            self.setFocus() # Asegura que el widget mantenga el foco

        # Para el clic derecho, solo llamamos al super.
        elif event.button() == Qt.RightButton:
            self.setFocus() # Asegura que el widget mantenga el foco

        super().mousePressEvent(event)

    # ---------------------- Timeline integration ----------------------
    def set_timeline(self, timeline: Optional[TimelineModel]) -> None:
        """Attach or replace the TimelineModel this widget observes.

        The TimelineModel is the canonical owner of playback time. The widget
        listens for playhead changes and updates its cached `playhead_sample`
        for rendering. If a previous timeline was attached, its observer is
        unsubscribed first.
        """
        logger.debug(f"[TimelineView:set_timeline] timeline id: {id(timeline)}")
        # Unsubscribe previous observer if present
        if getattr(self, '_timeline_unsubscribe', None):
            with safe_operation("Unsubscribing previous timeline observer", silent=True):
                self._timeline_unsubscribe()
            self._timeline_unsubscribe = None

        self.timeline = timeline
        if timeline is not None:
            # Register observer and initialize widget position from timeline
            with safe_operation("Registering timeline observer", silent=True):
                self._timeline_unsubscribe = timeline.on_playhead_changed(
                    self._on_timeline_playhead_changed
                )

                # Initialize lyrics track if lyrics_model is available
                if hasattr(timeline, 'lyrics_model') and timeline.lyrics_model is not None:
                    self._lyrics_track = LyricsTrack()

                self.update()
                # Initialize playhead to timeline's current value
                self.set_position_seconds(timeline.get_playhead_time())

    def reload_lyrics_track(self) -> None:
        """Reinitialize lyrics track when lyrics_model is added to timeline.

        Call this after setting lyrics_model on the timeline to ensure
        the view updates properly.
        """
        if self.timeline is not None:
            if hasattr(self.timeline, 'lyrics_model') and self.timeline.lyrics_model is not None:
                self._lyrics_track = LyricsTrack()
                self.update()
            else:
                self._lyrics_track = None

    def set_lyrics_edit_mode(self, enabled: bool) -> None:
        """Enable or disable lyrics edit mode.

        When enabled, the timeline prepares for inline lyric editing.
        Rendering and playback remain unchanged.
        """
        self._lyrics_edit_mode = enabled
        self._edit_buttons_visible = enabled
        if not enabled:
            self._hovered_button = None
        self.update()

    def _on_timeline_playhead_changed(self, new_time: float) -> None:
        """Callback invoked synchronously when the TimelineModel playhead changes.

        Updates the widget's cached playhead (in samples) and triggers a repaint
        if visible. This method intentionally does not call back into the
        TimelineModel to avoid feedback loops; the TimelineModel is the
        single source of truth for canonical time.
        """
        with safe_operation("Updating widget position from timeline", silent=True):
            # Use existing conversion and clamping logic
            self.set_position_seconds(float(new_time))
        # Schedule repaint on every playhead change (Qt will coalesce updates)
        self.update()

    def closeEvent(self, event: QCloseEvent) -> None:
        # Ensure we unsubscribe observer to avoid holding references after
        # the widget is closed/destroyed.
        if getattr(self, '_timeline_unsubscribe', None):
            with safe_operation("Unsubscribing timeline on close", silent=True):
                self._timeline_unsubscribe()
            self._timeline_unsubscribe = None
        super().closeEvent(event)

    def __del__(self) -> None:
        # Defensive cleanup if the widget is garbage collected without being
        # closed (may not run reliably but helps avoid leaks).
        with safe_operation("Cleanup in __del__", silent=True, log_level="debug"):
            if getattr(self, '_timeline_unsubscribe', None):
                with safe_operation("Unsubscribing timeline in __del__", silent=True, log_level="debug"):
                    self._timeline_unsubscribe()
                self._timeline_unsubscribe = None

    def set_playhead_sample(self, sample: int) -> None:
        # Asegurarse de que no falle con total_samples = 0
        if self.total_samples == 0:
            self.playhead_sample = 0
            return

        self.playhead_sample = int(max(0, min(sample, len(self.samples)-1)))
        # Ensure playhead stays visible within the current viewport (similar to Audacity behavior)
        self._ensure_playhead_visible()
        self.update()

    def _ensure_playhead_visible(self, margin_px: int = None) -> None:
        """Ensure the playhead is inside the visible area with optional pixel margins.

        Behavior: The playhead advances to the center of the screen, then the view
        scrolls automatically to keep it centered. This allows better visibility of
        upcoming lyrics and content.
        """
        if self.total_samples == 0:
            return

        w = max(1, self.width())

        spp = self._samples_per_pixel(self.zoom_factor, w)
        half_visible = (w * spp) / 2.0
        start = int(np.clip(self.center_sample - half_visible, 0, self.total_samples - 1))
        end = int(np.clip(self.center_sample + half_visible, 0, self.total_samples - 1))

        if end <= start:
            return

        # Compute playhead x position in pixels relative to widget
        rel = (self.playhead_sample - start) / (end - start)
        x_pos = int(rel * w)

        # Target position: center of the screen (50% of width)
        center_x = w // 2

        # Allow playhead to move freely until it reaches the center
        # Once at center or beyond, auto-scroll to keep it centered
        if x_pos >= center_x:
            # Auto-scroll: move the view to keep playhead at center
            new_center = self.playhead_sample
            self.center_sample = int(np.clip(new_center, 0, self.total_samples - 1))
            # Do not call update() here (caller will update)

    def set_position_seconds(self, seconds: float) -> None:
        """Set playhead based on seconds and update widget.

        This is the public API for PlaybackManager to update waveform position.
        """
        if self.total_samples == 0:
            return
        sample = int(max(0, min(int(seconds * self.sr), len(self.samples)-1)))
        self.set_playhead_sample(sample)


    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        # Check button hover first (if edit mode is active)
        if self._edit_buttons_visible:
            prev_hovered = self._hovered_button
            self._hovered_button = self._get_button_at_pos(event.x(), event.y())
            if prev_hovered != self._hovered_button:
                self.update()  # Redraw to show hover effect

        # Lógica de arrastre (solo si self._dragging es True, iniciado por clic izquierdo)
        if not self._dragging or self.total_samples == 0:
            return

        dx = event.x() - self._last_mouse_x
        self._last_mouse_x = event.x()

        w = max(1, self.width())
        spp = self._samples_per_pixel(self.zoom_factor, w)
        # Scroll horizontal
        # Se invierte el signo para que arrastrar a la izquierda mueva el centro a la izquierda
        self.center_sample = int(np.clip(self.center_sample - dx * spp, 0, len(self.samples)-1))
        self.update()

    # --------------------------------------------------------------
    # mouseReleaseEvent: Finalizar arrastre horizontal (Clic IZQUIERDO)
    # --------------------------------------------------------------
    def mouseReleaseEvent(self, event):
        # Lógica para finalizar el scroll/pan (ARRRASTRE CON CLIC IZQUIERDO)
        if event.button() == Qt.LeftButton:
            self._dragging = False
            self.setCursor(Qt.ArrowCursor) # Volver al cursor normal

        elif event.button() == Qt.RightButton:
            pass # No hace nada para el RightButton ahora.

        super().mouseReleaseEvent(event)


    def keyPressEvent(self, event):
        if self.total_samples == 0:
            return

        # TODO (Lyrics Edit Mode): When _lyrics_edit_mode is True and a lyric line
        # is selected, handle keyboard shortcuts for editing:
        # - Delete key to remove line
        # - Arrow keys for navigation between lines
        # - Enter to start inline editing
        # For now, fall through to existing navigation behavior.
        if self._lyrics_edit_mode:
            # TODO: Handle edit-mode-specific keyboard shortcuts
            pass

        # Atajos de teclado para cambiar modo de zoom
        if event.key() == Qt.Key_1:
            self.set_zoom_mode(ZoomMode.GENERAL, auto=False)
            return
        elif event.key() == Qt.Key_2:
            self.set_zoom_mode(ZoomMode.PLAYBACK, auto=False)
            return
        elif event.key() == Qt.Key_3:
            self.set_zoom_mode(ZoomMode.EDIT, auto=False)
            return

        w = max(1, self.width())
        spp = self._samples_per_pixel(self.zoom_factor, w)
        page = int(w * spp * 0.8)
        small = int(w * spp * 0.1)

        if event.key() in (Qt.Key_Left, Qt.Key_A):
            self.center_sample = int(np.clip(self.center_sample - small, 0, len(self.samples)-1))
            self.update()
        elif event.key() in (Qt.Key_Right, Qt.Key_D):
            self.center_sample = int(np.clip(self.center_sample + small, 0, len(self.samples)-1))
            self.update()
        elif event.key() == Qt.Key_PageUp:
            self.center_sample = int(np.clip(self.center_sample - page, 0, len(self.samples)-1))
            self.update()
        elif event.key() == Qt.Key_PageDown:
            self.center_sample = int(np.clip(self.center_sample + page, 0, len(self.samples)-1))
            self.update()
        elif event.key() in (Qt.Key_Plus, Qt.Key_Equal):
            self.zoom_by(1.2)
        elif event.key() in (Qt.Key_Minus, Qt.Key_Underscore):
            self.zoom_by(1/1.2)
        else:
            super().keyPressEvent(event)

    # ==============================================================
    # PAINT EVENT (waveform + playhead)
    # ==============================================================
    def paintEvent(self, event):
        # ===========================================================================
        # LEGACY HARDWARE OPTIMIZATION: Paint Throttling
        # ===========================================================================
        # Limita redraws a max 30 FPS (~33ms/frame) en lugar de 60 FPS
        # Reduce carga de CPU en hardware antiguo (Sandy Bridge, Core 2 Duo)
        # Hardware moderno: Puede aumentarse a 60 FPS (0.016 threshold)
        # ===========================================================================
        import time
        if not hasattr(self, '_last_paint_time'):
            self._last_paint_time = 0.0

        current_time = time.time()
        elapsed = current_time - self._last_paint_time

        # Si no ha pasado suficiente tiempo, retornar sin repintar
        if elapsed < 0.033:  # 30 FPS max (1/30 = 0.033s)
            return

        self._last_paint_time = current_time
        # ===========================================================================

        painter = QPainter(self)
        painter.fillRect(self.rect(), StyleManager.get_color("bg_panel"))

        # Check if audio is loaded before painting tracks
        if self.audio_data is None or len(self.audio_data) == 0:
            self._paint_empty_state(painter)
            return

        w = max(1, self.width())
        h = max(2, self.height())
        mid = h // 2

        total_samples = len(self.samples)

        spp = self._samples_per_pixel(self.zoom_factor, w)
        half_visible = (w * spp) / 2.0

        start = int(np.clip(self.center_sample - half_visible, 0, total_samples - 1))
        end = int(np.clip(self.center_sample + half_visible, 0, total_samples - 1))

        if end <= start:
            # Esto puede pasar en zoom extremo, dibujar línea central de audio
            pen = QPen(QColor(0, 200, 255), 1)
            painter.setPen(pen)
            painter.drawLine(0, mid, w, mid)

            # Ajustar el end al mínimo para que la ventana tenga al menos 1 muestra
            end = min(total_samples - 1, start + 1)

            # Si start sigue siendo mayor que end, salimos.
            if end <= start:
                return

        # ----------------------------------------------------------
        # Create ViewContext once for all tracks
        # ----------------------------------------------------------
        ctx = ViewContext(
            start_sample=start,
            end_sample=end,
            total_samples=total_samples,
            sample_rate=self.sr,
            width=w,
            height=h,
            timeline_model=self.timeline,
            zoom_mode=self.current_zoom_mode.name  # Pass current zoom mode
        )

        # ----------------------------------------------------------
        # Paint all tracks in order (bottom to top layering)
        # ----------------------------------------------------------

        # ===========================================================================
        # LEGACY HARDWARE OPTIMIZATION: Mode-Specific Downsampling
        # ===========================================================================
        # Aplicar downsample agresivo en GENERAL y PLAYBACK para reducir CPU usage
        # GENERAL: Vista completa, 4096 samples/bucket (muy agresivo)
        # PLAYBACK: Vista reproducción, 4096 samples/bucket (igualmente agresivo)
        # EDIT: Sin downsample (máxima precisión para edición)
        #
        # Rationale: Durante reproducción en hardware legacy, priorizar estabilidad
        # del audio sobre calidad visual del waveform. El usuario está viendo las
        # letras principalmente, no necesita resolución alta de la forma de onda.
        # ===========================================================================
        downsample_factor = None
        if self.current_zoom_mode == ZoomMode.GENERAL:
            downsample_factor = max(GLOBAL_DOWNSAMPLE_FACTOR, 4096)  # Máximo downsample
        elif self.current_zoom_mode == ZoomMode.PLAYBACK:
            # PLAYBACK también usa downsample agresivo en hardware legacy
            downsample_factor = 4096  # Igual que GENERAL - priorizar audio sobre visual
        # EDIT mode: downsample_factor = None (sin optimización, máxima calidad)

        # 1. Waveform (base layer)
        with safe_operation("Painting waveform track", silent=True):
            self._waveform_track.paint(painter, ctx, self.samples, downsample_factor)

        # 2. Beats and downbeats
        with safe_operation("Painting beat track", silent=True):
            self._beat_track.paint(painter, ctx)

        # 3. Lyrics
        if self._lyrics_track is not None:
            with safe_operation("Painting lyrics track", silent=True):
                self._lyrics_track.paint(painter, ctx)

        # 4. Chords (top layer for better visibility)
        with safe_operation("Painting chord track", silent=True):
            self._chord_track.paint(painter, ctx)

        # 5. Playhead (top layer)
        with safe_operation("Painting playhead track", silent=True):
            self._playhead_track.paint(painter, ctx)

        # ----------------------------------------------------------
        # DIBUJAR TIEMPO TOTAL (Opcional, pero útil)
        # ----------------------------------------------------------
        painter.setFont(StyleManager.get_font(size=10, mono=True))
        painter.setPen(StyleManager.get_color("text_bright")) # Color gris claro

        total_time_str = format_time(self.duration_seconds)
        # Dibujar en la esquina superior derecha
        painter.drawText(w - 150, 20, 140, 20, Qt.AlignRight, total_time_str)

        # ----------------------------------------------------------
        # EDIT MODE BUTTONS (right edge)
        # ----------------------------------------------------------
        if self._edit_buttons_visible:
            self._paint_edit_buttons(painter, w, h)

    # ==============================================================
    # EMPTY STATE RENDERING
    # ==============================================================

    def _paint_empty_state(self, painter: QPainter) -> None:
        """Paint empty state with decorative placeholder waveform."""
        painter.fillRect(self.rect(), StyleManager.get_color('bg_panel'))

        w = max(1, self.width())
        h = max(2, self.height())

        # Load pre-generated placeholder waveform from assets (WAV for testing)
        placeholder_path = Path(__file__).parent.parent.parent / "assets" / "audio" / "placeholder.wav"

        if placeholder_path.exists():
            try:
                # Load placeholder audio
                synthetic_audio, synthetic_sr = sf.read(str(placeholder_path), dtype='float32')
                synthetic_samples_count = len(synthetic_audio)

                # Create ViewContext for the placeholder waveform
                ctx = ViewContext(
                    start_sample=0,
                    end_sample=synthetic_samples_count - 1,
                    total_samples=synthetic_samples_count,
                    sample_rate=synthetic_sr,
                    width=w,
                    height=h,
                    timeline_model=None,
                    zoom_mode="GENERAL"
                )

                # Paint placeholder waveform with reduced opacity
                painter.save()

                # Override waveform color to be more visible
                original_pen = self._waveform_track.pen_waveform
                light_waveform_color = QColor(StyleManager.get_color('waveform'))
                light_waveform_color.setAlpha(120)  # More visible for placeholder
                self._waveform_track.pen_waveform = QPen(light_waveform_color, 1)

                # Paint using the same track renderer WITHOUT downsampling
                # (downsampling flattens the placeholder waveform too much)
                self._waveform_track.paint(painter, ctx, synthetic_audio, downsample_factor=None)

                # Restore original pen
                self._waveform_track.pen_waveform = original_pen
                painter.restore()

            except Exception as e:
                logger.debug(f"Could not load placeholder waveform: {e}")
                # Silently fail - empty state will show just background

    # ==============================================================
    # EDIT MODE BUTTONS (Helper methods)
    # ==============================================================

    def _get_button_rect(self, button_index: int, widget_width: int, widget_height: int):
        """Calculate rectangle for a button by index (0 = top button, 1 = second, etc.)"""
        x = widget_width - self._button_width - self._button_margin
        y = self._button_margin + button_index * (self._button_height + self._button_spacing)
        return (x, y, self._button_width, self._button_height)

    def _get_button_at_pos(self, x: int, y: int) -> str:
        """Return button identifier if position is over a button, else None"""
        if not self._edit_buttons_visible:
            return None

        w = self.width()
        h = self.height()

        # Edit Metadata button (index 0)
        bx, by, bw, bh = self._get_button_rect(0, w, h)
        if bx <= x <= bx + bw and by <= y <= by + bh:
            return 'edit_metadata'

        # Reload Lyrics button (index 1)
        bx, by, bw, bh = self._get_button_rect(1, w, h)
        if bx <= x <= bx + bw and by <= y <= by + bh:
            return 'reload_lyrics'

        return None

    def _paint_edit_buttons(self, painter: QPainter, widget_width: int, widget_height: int):
        """Paint edit mode buttons on the right edge of the timeline"""
        painter.save()

        # Colors from StyleManager
        btn_normal = StyleManager.PALETTE["btn_normal"]
        btn_hover = StyleManager.PALETTE["btn_hover"]
        border_light = StyleManager.PALETTE["border_light"]
        accent = StyleManager.get_color("accent")
        text_normal = StyleManager.get_color("text_normal")

        # Button 1: Edit Metadata
        x1, y1, w1, h1 = self._get_button_rect(0, widget_width, widget_height)
        is_hover_1 = (self._hovered_button == 'edit_metadata')

        # Background
        bg_color_1 = QColor(btn_hover) if is_hover_1 else QColor(btn_normal)
        painter.fillRect(int(x1), int(y1), int(w1), int(h1), bg_color_1)

        # Border
        border_color_1 = accent if is_hover_1 else QColor(border_light)
        border_width_1 = 2 if is_hover_1 else 1
        painter.setPen(QPen(border_color_1, border_width_1))
        painter.drawRect(int(x1), int(y1), int(w1), int(h1))

        # Icon + Text
        painter.setPen(text_normal)
        painter.setFont(StyleManager.get_font(size=11, bold=False))
        painter.drawText(int(x1), int(y1), int(w1), int(h1),
                        Qt.AlignCenter, "📝 Edit Metadata")

        # Button 2: Reload Lyrics
        x2, y2, w2, h2 = self._get_button_rect(1, widget_width, widget_height)
        is_hover_2 = (self._hovered_button == 'reload_lyrics')

        # Background
        bg_color_2 = QColor(btn_hover) if is_hover_2 else QColor(btn_normal)
        painter.fillRect(int(x2), int(y2), int(w2), int(h2), bg_color_2)

        # Border
        border_color_2 = accent if is_hover_2 else QColor(border_light)
        border_width_2 = 2 if is_hover_2 else 1
        painter.setPen(QPen(border_color_2, border_width_2))
        painter.drawRect(int(x2), int(y2), int(w2), int(h2))

        # Icon + Text
        painter.setPen(text_normal)
        painter.setFont(StyleManager.get_font(size=11, bold=False))
        painter.drawText(int(x2), int(y2), int(w2), int(h2),
                        Qt.AlignCenter, "🔄 Reload Lyrics")

        painter.restore()

