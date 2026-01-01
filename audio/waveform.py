# Waveform Widget with Zoom, Scroll, and Animated Playhead

import numpy as np
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QPen, QFont
from PySide6.QtCore import Qt, Signal
import soundfile as sf
from typing import Optional

from core.utils import format_time, get_logarithmic_volume
from core.timeline_model import TimelineModel

# Performance & zoom/downsampling settings
MIN_SAMPLES_PER_PIXEL = 10   # Do not allow fewer than 10 samples per pixel (visual limit)
MAX_ZOOM_LEVEL = 500.0      # Max zoom factor multiplier
GLOBAL_DOWNSAMPLE_FACTOR = 1024  # For global view, aggregate at least this many samples per visual bucket

class WaveformWidget(QWidget):
    """
    Widget pasivo para dibujar la onda y manejar eventos de usuario (zoom, scroll, doble clic para seek).
    No reproduce audio; la reproducción y reloj son responsabilidad de `MultiTrackPlayer`/`PlaybackManager`.
    """
    # Señal para notificar que el usuario ha cambiado la posición (segundos)
    position_changed = Signal(float)

    def __init__(self, audio_path=None, parent=None, timeline: Optional[TimelineModel] = None): # audio_path ahora es opcional
        super().__init__(parent)

        # --- Estado inicial por defecto (sin audio) ---
        self.samples = np.array([], dtype=np.float32)
        self.sr = 44100
        self.total_samples = 0
        self.duration_seconds = 0.0
        self.volume = 1.0  # Factor de amplitud de volumen (0.0 a 1.0)
        
        # --- View parameters ---
        self.zoom_factor = 1.0
        self.center_sample = 0 # Centro inicial (se ajustará si se carga audio)

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

        # NOTE: Beats, downbeats and chords are intended to be owned by
        # TimelineModel; however, to preserve backward compatibility we keep a
        # lightweight cache of the most recently loaded metadata so it can be
        # forwarded to a timeline if the timeline is attached later. This
        # avoids cases where metadata is loaded before the UI constructs or
        # attaches the TimelineModel and would otherwise be lost.
        self._cached_beats_seconds = []
        self._cached_downbeat_flags = []
        self._cached_chords = []
        
        # --- Interaction ---
        self._dragging = False
        self._last_mouse_x = None

        self.setMinimumHeight(120)
        self.setFocusPolicy(Qt.StrongFocus)

        # Render cache (to avoid repeated heavy reductions when repainting)
        self._last_render_params = None  # (start, end, width, zoom_factor)
        self._last_render_envelope = None  # (mins, maxs)

        # Cargar audio si se proporciona una ruta
        if audio_path:
            self.load_audio(audio_path)
    
    # --------------------------------------------------------------------
    #   FUNCIONES PRINCIPALES DEL SINCRONIZADOR
    # --------------------------------------------------------------------
    # Waveform is passive; sync handled by SyncController/PlaybackManager
    # No need for a timer nor sample clock here.
    def _set_empty_state(self):
        """Establece las variables internas en un estado seguro sin audio."""
        self.samples = np.array([], dtype=np.float32)
        self.sr = 44100
        self.total_samples = 0
        self.duration_seconds = 0.0
        self.zoom_factor = 1.0
        self.center_sample = 0
        self.playhead_sample = 0
        # Clear metadata caches
        self._cached_beats_seconds = []
        self._cached_downbeat_flags = []
        self._cached_chords = []
        # Clear render cache
        self._last_render_params = None
        self._last_render_envelope = None
        self.update()


    def load_audio(self, audio_path):
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

            # Clear render cache (new audio -> new envelope)
            self._last_render_params = None
            self._last_render_envelope = None

            # We no longer maintain beat/chord samples locally — timeline holds
            # that information. Nothing to recompute here.

            self.update()
            return True
        
        except Exception as e:
            print(f"Error al cargar el audio '{audio_path}': {e}")
            self._set_empty_state()
            return False

    
    # ==============================================================
    # VOLUME CONTROL (LOGARÍTMICO) 
    # ==============================================================
    def set_volume(self, slider_value: int):
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
    def set_zoom(self, factor: float):
        if self.total_samples == 0:
            return
        w = max(1, self.width())
        # Clamp to allowed range & ensure samples-per-pixel >= MIN_SAMPLES_PER_PIXEL
        new_factor = max(1.0, min(factor, MAX_ZOOM_LEVEL))
        new_factor = self._clamp_zoom_for_width(new_factor, w)
        self.zoom_factor = new_factor
        self.center_sample = int(np.clip(self.center_sample, 0, len(self.samples)-1))
        # Clear render cache since zoom changed
        self._last_render_params = None
        self._last_render_envelope = None
        self.update()

    def load_audio_from_master(self, master_path):
        """Convenience alias to maintain old usage in MainWindow (accepts Path)."""
        if isinstance(master_path, (str,)):
            self.load_audio(master_path)
        else:
            self.load_audio(str(master_path))

    def _clamp_zoom_for_width(self, factor: float, width: int):
        """Ensure zoom factor keeps samples-per-pixel >= MIN_SAMPLES_PER_PIXEL and within limits."""
        if self.total_samples == 0 or width <= 0:
            return max(1.0, min(factor, MAX_ZOOM_LEVEL))
        max_factor_by_spp = self.total_samples / (MIN_SAMPLES_PER_PIXEL * width)
        max_allowed = max(1.0, min(MAX_ZOOM_LEVEL, max_factor_by_spp))
        return max(1.0, min(factor, max_allowed))
    
    def load_metadata(self, meta_data):
        """Load metadata dictionary to extract beats/downbeats.

        Instead of storing beats/chords locally, forward metadata to the
        attached TimelineModel (if present). The TimelineModel is the
        canonical place to keep musical timeline metadata.

        If no timeline is attached, the widget will not store metadata and
        will render as if no beats/chords are present (fallback behavior).
        """
        if not meta_data:
            # nothing to do
            self.update()
            return

        # Parse metadata into canonical lists (always keep a lightweight cache
        # so metadata isn't lost if the timeline isn't yet attached).
        beats_input = meta_data.get("beats", []) if isinstance(meta_data, dict) else []
        beats_seconds = []
        downbeat_flags = []
        for item in beats_input:
            try:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    t = float(item[0])
                    pos = int(item[1])
                    beats_seconds.append(t)
                    downbeat_flags.append(1 if pos == 1 else 0)
                else:
                    t = float(item)
                    beats_seconds.append(t)
                    downbeat_flags.append(0)
            except Exception:
                continue

        chords_input = meta_data.get("chords", []) if isinstance(meta_data, dict) else []
        chords_parsed = []
        for item in chords_input:
            try:
                if isinstance(item, (list, tuple)) and len(item) >= 3:
                    s = float(item[0])
                    e = float(item[1])
                    name = str(item[2]).strip()
                    if e < s:
                        s, e = e, s
                    chords_parsed.append((s, e, name))
            except Exception:
                continue

        # Update cache (so metadata is available if a timeline is attached later)
        self._cached_beats_seconds = beats_seconds
        self._cached_downbeat_flags = downbeat_flags
        self._cached_chords = chords_parsed

        # If a timeline is attached, forward parsed metadata to it immediately.
        if getattr(self, 'timeline', None) is not None:
            try:
                self.timeline.set_beats(beats_seconds, downbeat_flags)
            except Exception:
                pass
            try:
                self.timeline.set_chords(chords_parsed)
            except Exception:
                pass

        # Fallback rendering behavior: if no timeline is attached, there will
        # simply be no beats/chords to draw.
        self.update()

    # NOTE: Beat/chord sample caches were removed from the widget. Events are
    # queried from TimelineModel at render time and converted to samples on the
    # fly in paintEvent(). This avoids duplicating timeline data in the widget.

    def zoom_by(self, ratio: float, cursor_x: int = None):
        if self.total_samples == 0:
            return

        old_zoom = self.zoom_factor
        tentative_zoom = max(1.0, old_zoom * ratio)
        w = max(1, self.width())
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

        # After zoom, ensure the playhead remains visible in the current viewport
        try:
            self._ensure_playhead_visible()
        except Exception:
            pass

        # Zoom changed -> invalidate render cache
        self._last_render_params = None
        self._last_render_envelope = None

        self.update()

    def _samples_per_pixel(self, zoom_factor, width_pixels):
        if width_pixels <= 0:
            return 1.0
            
        total_samples = len(self.samples)
        if total_samples == 0:
            return 1.0 # Si no hay audio, 1 muestra por pixel (dummy)

        visible_samples = max(1.0, total_samples / zoom_factor)
        spp = visible_samples / width_pixels
        return max(1e-6, spp)

    def _compute_envelope(self, start: int, end: int, w: int):
        """Compute (mins, maxs) arrays of length `w` summarizing samples[start:end+1].
        Results are cached keyed by (start, end, w, zoom_factor) to avoid repeated heavy reductions."""
        key = (start, end, w, self.zoom_factor)
        if self._last_render_params == key and self._last_render_envelope is not None:
            return self._last_render_envelope

        window = self.samples[start:end+1]
        L = len(window)
        if L == 0:
            mins = np.zeros(w, dtype=np.float32)
            maxs = np.zeros(w, dtype=np.float32)
        elif L < w:
            indices = np.linspace(0, L - 1, num=w)
            interp = np.interp(indices, np.arange(L), window)
            mins = interp.astype(np.float32)
            maxs = interp.astype(np.float32)
        else:
            # bin edges (fast and stable)
            edges = np.linspace(0, L, num=w+1, dtype=int)
            mins = np.empty(w, dtype=np.float32)
            maxs = np.empty(w, dtype=np.float32)
            for i in range(w):
                s = edges[i]
                e = edges[i+1]
                if e <= s:
                    v = float(window[min(s, L-1)])
                    mins[i] = v
                    maxs[i] = v
                else:
                    block = window[s:e]
                    mins[i] = float(np.min(block))
                    maxs[i] = float(np.max(block))

        self._last_render_params = key
        self._last_render_envelope = (mins, maxs)
        return mins, maxs

    # ==============================================================
    # SCROLL (Mouse + Keyboard)
    # ==============================================================
    def wheelEvent(self, event):
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
    def mouseDoubleClickEvent(self, event):
        if self.total_samples == 0:
            return
            
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
                try:
                    self.timeline.set_playhead_time(current_time)
                except Exception:
                    # If timeline update fails for some reason, fall back to the
                    # old behavior and update local playhead for rendering.
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
    def mousePressEvent(self, event):
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
        # Unsubscribe previous observer if present
        if getattr(self, '_timeline_unsubscribe', None):
            try:
                self._timeline_unsubscribe()
            except Exception:
                pass
            self._timeline_unsubscribe = None

        self.timeline = timeline
        if timeline is not None:
            # Register observer and initialize widget position from timeline
            try:
                self._timeline_unsubscribe = timeline.on_playhead_changed(self._on_timeline_playhead_changed)
                # Initialize playhead to timeline's current value
                self.set_position_seconds(timeline.get_playhead_time())
                # Forward any cached metadata that was loaded before a timeline
                # was attached. This preserves previous behavior where metadata
                # loaded into the widget would be visible even if the timeline
                # wasn't yet available.
                if self._cached_beats_seconds:
                    try:
                        self.timeline.set_beats(self._cached_beats_seconds, self._cached_downbeat_flags)
                    except Exception:
                        pass
                if self._cached_chords:
                    try:
                        self.timeline.set_chords(self._cached_chords)
                    except Exception:
                        pass
                # Once forwarded, we can clear the cache (the timeline holds it)
                self._cached_beats_seconds = []
                self._cached_downbeat_flags = []
                self._cached_chords = []            
            except Exception:
                # If registration fails, ensure internal state remains consistent
                self._timeline_unsubscribe = None

    def _on_timeline_playhead_changed(self, new_time: float) -> None:
        """Callback invoked synchronously when the TimelineModel playhead changes.

        Updates the widget's cached playhead (in samples) and triggers a repaint
        if visible. This method intentionally does not call back into the
        TimelineModel to avoid feedback loops; the TimelineModel is the
        single source of truth for canonical time.
        """
        try:
            # Use existing conversion and clamping logic
            self.set_position_seconds(float(new_time))
        except Exception:
            # Keep observer lightweight: swallow exceptions to avoid breaking
            # timeline updates from other sources.
            pass

    def closeEvent(self, event):
        # Ensure we unsubscribe observer to avoid holding references after
        # the widget is closed/destroyed.
        if getattr(self, '_timeline_unsubscribe', None):
            try:
                self._timeline_unsubscribe()
            except Exception:
                pass
            self._timeline_unsubscribe = None
        super().closeEvent(event)

    def __del__(self):
        # Defensive cleanup if the widget is garbage collected without being
        # closed (may not run reliably but helps avoid leaks).
        try:
            if getattr(self, '_timeline_unsubscribe', None):
                try:
                    self._timeline_unsubscribe()
                except Exception:
                    pass
                self._timeline_unsubscribe = None
        except Exception:
            pass
            
    def set_playhead_sample(self, sample):
        # Asegurarse de que no falle con total_samples = 0
        if self.total_samples == 0:
            self.playhead_sample = 0
            return

        self.playhead_sample = int(max(0, min(sample, len(self.samples)-1)))
        # Ensure playhead stays visible within the current viewport (similar to Audacity behavior)
        self._ensure_playhead_visible()
        self.update()

    def _ensure_playhead_visible(self, margin_px: int = None):
        """Ensure the playhead is inside the visible area with optional pixel margins.

        Behavior: The playhead is allowed to move inside the visible window. When it
        reaches within `margin_px` of the left or right edge, the waveform recenters
        so the playhead remains visible (mimics Audacity-like behavior).
        """
        if self.total_samples == 0:
            return

        w = max(1, self.width())
        if margin_px is None:
            margin_px = max(20, int(w * 0.1))

        spp = self._samples_per_pixel(self.zoom_factor, w)
        half_visible = (w * spp) / 2.0
        start = int(np.clip(self.center_sample - half_visible, 0, self.total_samples - 1))
        end = int(np.clip(self.center_sample + half_visible, 0, self.total_samples - 1))

        if end <= start:
            return

        # Compute playhead x position in pixels relative to widget
        rel = (self.playhead_sample - start) / (end - start)
        x_pos = int(rel * w)

        left_margin = margin_px
        right_margin = w - margin_px

        if x_pos < left_margin or x_pos > right_margin:
            # move center so playhead sits at the nearest margin (clamped)
            target_x = max(left_margin, min(x_pos, right_margin))
            new_center = int(self.playhead_sample + (w / 2 - target_x) * spp)
            self.center_sample = int(np.clip(new_center, 0, self.total_samples - 1))
            # Do not call update() here (caller will update)

    def set_position_seconds(self, seconds: float):
        """Set playhead based on seconds and update widget.

        This is the public API for PlaybackManager to update waveform position.
        """
        if self.total_samples == 0:
            return
        sample = int(max(0, min(int(seconds * self.sr), len(self.samples)-1)))
        self.set_playhead_sample(sample)


    def mouseMoveEvent(self, event):
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
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(30, 30, 30))

        w = max(1, self.width())
        h = max(2, self.height())
        mid = h // 2

        total_samples = len(self.samples)
        
        # Si no hay muestras, dibujar solo una línea central gris y salir
        if total_samples == 0:
            pen = QPen(QColor(60, 60, 60), 1)
            painter.setPen(pen)
            painter.drawLine(0, mid, w, mid)
            return

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

        window = self.samples[start:end+1]

        pen = QPen(QColor(0, 200, 255), 1)
        painter.setPen(pen)

        # ----------------------------------------------------------
        # DIBUJAR ONDA
        # ----------------------------------------------------------
        # Use a cached, downsampled envelope (mins/maxs per pixel bucket) for performance
        mins, maxs = self._compute_envelope(start, end, w)
        for x in range(w):
            y1 = int(mins[x] * (h/2 - 2))
            y2 = int(maxs[x] * (h/2 - 2))
            painter.drawLine(x, mid - y2, x, mid - y1)

        # ----------------------------------------------------------
        # DIBUJAR CHORDS (rectángulos y texto en la parte superior)
        # ----------------------------------------------------------
        # Chords are now provided by the TimelineModel (if attached). Query the
        # timeline for chords that overlap the visible time window and render
        # them. If no timeline is attached, fall back to no chords.
        if start < end:
            start_s = start / float(self.sr)
            end_s = end / float(self.sr)

            chords = []
            if getattr(self, 'timeline', None) is not None:
                try:
                    chords = self.timeline.chords_in_range(start_s, end_s)
                except Exception:
                    chords = []

            if chords:
                font = QFont("Arial", 8, QFont.Bold)
                painter.setFont(font)
                box_h = min(18, max(12, h // 10))
                box_y = 2

                for s0_t, s1_t, name in chords:
                    # convert times back to sample indices to reuse existing layout logic
                    s0 = int(max(0, min(int(s0_t * self.sr), total_samples - 1)))
                    s1 = int(max(0, min(int(s1_t * self.sr), total_samples - 1)))

                    # skip if chord outside visible range
                    if s1 < start or s0 > end:
                        continue
                    # clip chord to visible window
                    vis_s0 = max(s0, start)
                    vis_s1 = min(s1, end)
                    rel0 = (vis_s0 - start) / (end - start)
                    rel1 = (vis_s1 - start) / (end - start)
                    x0 = int(rel0 * w)
                    x1 = int(rel1 * w)
                    if x1 <= x0:
                        x1 = x0 + 1

                    # color: empty chord 'N' shown grey; others greenish
                    if str(name).strip().upper() == 'N':
                        fill = QColor(80, 80, 80, 120)
                        text_col = QColor(200, 200, 200)
                    else:
                        fill = QColor(0, 120, 80, 150)
                        text_col = QColor(255, 255, 255)

                    painter.fillRect(x0, box_y, x1 - x0, box_h, fill)
                    painter.setPen(QColor(0, 0, 0, 100))
                    painter.drawRect(x0, box_y, x1 - x0, box_h)
                    painter.setPen(text_col)
                    # Draw chord name left-aligned at chord start with a small padding
                    text_padding = 4
                    text_w = max(1, x1 - x0 - text_padding)
                    painter.drawText(x0 + text_padding, box_y, text_w, box_h, Qt.AlignLeft | Qt.AlignVCenter, str(name))

        # ----------------------------------------------------------
        # DIBUJAR BEATS / DOWNBEATS (líneas verticales)
        # ----------------------------------------------------------
        if start < end:
            # Make lines thinner and slightly translucent to avoid visual saturation
            beat_pen = QPen(QColor(0, 150, 255, 150))  # cyan, semi-transparent
            beat_pen.setWidth(1)
            down_pen = QPen(QColor(255, 200, 0, 120))  # yellow/orange, less opaque
            down_pen.setWidth(2)

            # Query timeline for beats in the visible time range. If no timeline
            # is attached, no beats will be drawn.
            beats_samples = []
            downbeat_samples = []
            if getattr(self, 'timeline', None) is not None:
                try:
                    start_s = start / float(self.sr)
                    end_s = end / float(self.sr)
                    beats_seconds = self.timeline.beats_in_range(start_s, end_s)
                    beats_samples = [int(max(0, min(int(b * self.sr), total_samples - 1))) for b in beats_seconds]

                    # Use the public downbeats API if available; avoid accessing
                    # timeline internals directly.
                    if hasattr(self.timeline, 'downbeats_in_range'):
                        downbeats_all = self.timeline.downbeats_in_range(start_s, end_s)
                        downbeat_samples = [int(max(0, min(int(d * self.sr), total_samples - 1))) for d in downbeats_all]
                except Exception:
                    beats_samples = []
                    downbeat_samples = []

            # Draw beats (thin, subtle)
            painter.setPen(beat_pen)
            for b in beats_samples:
                rel_b = (b - start) / (end - start)
                x_b = int(rel_b * w)
                painter.drawLine(x_b, 0, x_b, h)

            # Draw downbeats on top (also thin and translucent)
            painter.setPen(down_pen)
            for d in downbeat_samples:
                rel_d = (d - start) / (end - start)
                x_d = int(rel_d * w)
                painter.drawLine(x_d, 0, x_d, h)

        # ----------------------------------------------------------
        # DIBUJAR PLAYHEAD
        # ----------------------------------------------------------
        if start <= self.playhead_sample <= end:
            rel = (self.playhead_sample - start) / (end - start)
            x_pos = int(rel * w)

            play_pen = QPen(QColor(255, 50, 50), 2)
            painter.setPen(play_pen)
            painter.drawLine(x_pos, 0, x_pos, h)

        # ----------------------------------------------------------
        # DIBUJAR TIEMPO TOTAL (Opcional, pero útil)
        # ----------------------------------------------------------
        painter.setFont(QFont("Arial", 8))
        painter.setPen(QColor(200, 200, 200)) # Color gris claro
        
        total_time_str = format_time(self.duration_seconds)
        # Dibujar en la esquina superior derecha
        painter.drawText(w - 150, 20, 140, 20, Qt.AlignRight, total_time_str)

        # ----------------------------------------------------------
        # DIBUJAR TIEMPO TRANSCURRIDO (En la posición del playhead si es visible)
        # ----------------------------------------------------------
        if start <= self.playhead_sample <= end:
            current_time = self.playhead_sample / self.sr
            current_time_str = format_time(current_time)
            
            # Usar un color diferente y fuente un poco más grande
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Arial", 9, QFont.Bold))
            
            # Posición x: justo a la derecha del playhead
            text_x = x_pos + 5 
            
            # Asegurar que el texto no se salga del borde derecho
            if text_x + 100 > w:
                text_x = x_pos - 105 # Dibujar a la izquierda si no hay espacio
                
            painter.drawText(text_x, 20, 100, 20, Qt.AlignLeft, current_time_str)