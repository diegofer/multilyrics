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

class TimelineView(QWidget):
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

        # Render cache handled by WaveformTrack; widget remains stateless.
        self._waveform_track = None

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
        self._reset_waveform_cache()
        self.update()

    def _reset_waveform_cache(self):
        """Clear cached waveform envelope/rendering in the track (if any)."""
        if getattr(self, '_waveform_track', None) is not None:
            try:
                self._waveform_track.reset_cache()
            except Exception:
                pass


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

            self._reset_waveform_cache()

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
        self._reset_waveform_cache()
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
        self._reset_waveform_cache()

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

    # Waveform envelope computation moved to WaveformTrack

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
        print("[TimelineView:set_timeline] timeline id:", id(timeline))
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
                self.update()
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
        # Schedule repaint on every playhead change (Qt will coalesce updates)
        self.update()

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

        # ----------------------------------------------------------
        # DIBUJAR ONDA (delegado a WaveformTrack)
        # ----------------------------------------------------------
        from audio.tracks.waveform_track import WaveformTrack
        from audio.tracks.beat_track import ViewContext

        ctx = ViewContext(start_sample=start, end_sample=end, total_samples=total_samples, sample_rate=self.sr, width=w, height=h, timeline_model=self.timeline)
        if getattr(self, '_waveform_track', None) is None:
            self._waveform_track = WaveformTrack()
        try:
            self._waveform_track.paint(painter, ctx, self.samples)
        except Exception:
            # Keep painting robust: if the track fails, don't break waveform
            pass


        # ----------------------------------------------------------
        # DIBUJAR BEATS / DOWNBEATS (líneas verticales)
        # ----------------------------------------------------------
        if start < end:
            # Make lines thinner and slightly translucent to avoid visual saturation
            beat_pen = QPen(QColor(0, 150, 255, 150))  # cyan, semi-transparent
            beat_pen.setWidth(1)
            down_pen = QPen(QColor(255, 200, 0, 120))  # yellow/orange, less opaque
            down_pen.setWidth(2)

                # Delegate beat rendering to BeatTrack for better separation of concerns
            from audio.tracks.beat_track import ViewContext, BeatTrack

            ctx = ViewContext(start_sample=start, end_sample=end, total_samples=total_samples, sample_rate=self.sr, width=w, height=h, timeline_model=self.timeline)
            if getattr(self, '_beat_track', None) is None:
                self._beat_track = BeatTrack()
            try:
                self._beat_track.paint(painter, ctx)
            except Exception:
                # Keep painting robust: if the track fails, don't break waveform
                pass

        # ----------------------------------------------------------
        # DIBUJAR CHORDS (rectángulos y texto en la parte inferior, justo encima de lyrics)
        # ----------------------------------------------------------
        # Delegate chord rendering to ChordTrack for separation of concerns
        if start < end:
            from audio.tracks.chord_track import ChordTrack
            from audio.tracks.beat_track import ViewContext

            ctx = ViewContext(start_sample=start, end_sample=end, total_samples=total_samples, sample_rate=self.sr, width=w, height=h, timeline_model=self.timeline)
            if getattr(self, '_chord_track', None) is None:
                self._chord_track = ChordTrack()
            try:
                self._chord_track.paint(painter, ctx)
            except Exception:
                # Keep painting robust: if the track fails, don't break waveform
                pass        
        
        # ----------------------------------------------------------
        # DIBUJAR PLAYHEAD (línea vertical roja)
        # ----------------------------------------------------------
        from audio.tracks.playhead_track import PlayheadTrack
        from audio.tracks.beat_track import ViewContext

        ctx = ViewContext(start_sample=start, end_sample=end, total_samples=total_samples, sample_rate=self.sr, width=w, height=h, timeline_model=self.timeline)
        if getattr(self, '_playhead_track', None) is None:
            self._playhead_track = PlayheadTrack()
        try:
            self._playhead_track.paint(painter, ctx)
        except Exception:
            # Keep painting robust: if the track fails, don't break waveform
            pass
        
        # ----------------------------------------------------------
        # DIBUJAR LYRICS (Debajo de chords)
        # ----------------------------------------------------------
        if start < end:
            from audio.tracks.lyrics_track import LyricsTrack
            from audio.tracks.beat_track import ViewContext
            from audio.lyrics.model import LyricsModel

            ctx = ViewContext(start_sample=start, end_sample=end, total_samples=total_samples, sample_rate=self.sr, width=w, height=h, timeline_model=self.timeline)
            
            if getattr(self, '_lyrics_track', None) is None:
                self._lyrics_track = LyricsTrack()
                # Connect to the global lyrics model (singleton)
                #self._lyrics_track.set_lyrics_model(LyricsModel.get_instance())
            
            try:
                self._lyrics_track.paint(painter, ctx)
            except Exception:
                # Keep painting robust: if the track fails, don't break waveform
                pass

        # ----------------------------------------------------------
        # DIBUJAR TIEMPO TOTAL (Opcional, pero útil)
        # ----------------------------------------------------------
        painter.setFont(QFont("Arial", 8))
        painter.setPen(QColor(200, 200, 200)) # Color gris claro
        
        total_time_str = format_time(self.duration_seconds)
        # Dibujar en la esquina superior derecha
        painter.drawText(w - 150, 20, 140, 20, Qt.AlignRight, total_time_str)