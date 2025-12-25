# Waveform Widget with Zoom, Scroll, and Animated Playhead

import numpy as np
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QPen, QFont
from PySide6.QtCore import Qt, Signal
import soundfile as sf

from core.utils import format_time, get_logarithmic_volume

class WaveformWidget(QWidget):
    """
    Widget pasivo para dibujar la onda y manejar eventos de usuario (zoom, scroll, doble clic para seek).
    No reproduce audio; la reproducción y reloj son responsabilidad de `MultiTrackPlayer`/`PlaybackManager`.
    """
    # Señal para notificar que el usuario ha cambiado la posición (segundos)
    position_changed = Signal(float)

    def __init__(self, audio_path=None, parent=None): # audio_path ahora es opcional
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
        self.playhead_sample = 0

        # --- Beats / Downbeats (seconds and sample indices)
        self._beats_seconds = []      # list of beat times in seconds
        self._downbeats_seconds = []  # list of downbeat times in seconds
        self._beats_samples = []      # cached sample indices corresponding to beats
        self._downbeat_samples = []   # cached sample indices corresponding to downbeats
        
        # --- Interaction ---
        self._dragging = False
        self._last_mouse_x = None

        self.setMinimumHeight(120)
        self.setFocusPolicy(Qt.StrongFocus)

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
        # Clear any beat/downbeat metadata
        self._beats_seconds = []
        self._downbeats_seconds = []
        self._beats_samples = []
        self._downbeat_samples = []
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

            # Recompute any beat/downbeat sample positions (if metadata was loaded earlier)
            self._recompute_beat_samples()

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
        factor = max(1.0, factor)
        self.zoom_factor = factor
        self.center_sample = int(np.clip(self.center_sample, 0, len(self.samples)-1))
        self.update()

    def load_audio_from_master(self, master_path):
        """Convenience alias to maintain old usage in MainWindow (accepts Path)."""
        if isinstance(master_path, (str,)):
            self.load_audio(master_path)
        else:
            self.load_audio(str(master_path))
    
    def load_metadata(self, meta_data):
        """Load metadata dictionary to extract beats/downbeats.

        Expected meta_data['beats'] format:
        - a list of [time_seconds, position_flag] rows (as produced by the Beats extractor),
          where position_flag==1 typically indicates a downbeat (first beat of the bar).
        - or a list of numeric times (seconds).
        """
        self._beats_seconds = []
        self._downbeats_seconds = []

        if not meta_data:
            # nothing to do
            self._beats_samples = []
            self._downbeat_samples = []
            self.update()
            return

        beats = meta_data.get("beats", []) if isinstance(meta_data, dict) else []

        for item in beats:
            try:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    t = float(item[0])
                    pos = int(item[1])
                    self._beats_seconds.append(t)
                    if pos == 1:
                        self._downbeats_seconds.append(t)
                else:
                    # simple numeric time
                    t = float(item)
                    self._beats_seconds.append(t)
            except Exception:
                # ignore malformed items
                continue

        # Once we have seconds, convert to sample indices if sr is known
        self._recompute_beat_samples()
        self.update()

    def _recompute_beat_samples(self):
        """Convert stored beat/downbeat times in seconds to sample indices using current sample rate."""
        if not hasattr(self, "sr") or self.sr <= 0:
            # can't compute sample indices yet
            self._beats_samples = []
            self._downbeat_samples = []
            return

        try:
            self._beats_samples = [int(max(0, min(int(t * self.sr), self.total_samples-1))) for t in self._beats_seconds]
            self._downbeat_samples = [int(max(0, min(int(t * self.sr), self.total_samples-1))) for t in self._downbeats_seconds]
        except Exception:
            self._beats_samples = []
            self._downbeat_samples = []

    def zoom_by(self, ratio: float, cursor_x: int = None):
        if self.total_samples == 0:
            return

        old_zoom = self.zoom_factor
        new_zoom = max(1.0, old_zoom * ratio)

        if cursor_x is None:
            self.zoom_factor = new_zoom
        else:
            w = max(1, self.width())
            old_spp = self._samples_per_pixel(old_zoom, w)
            sample_at_cursor = int(self.center_sample - (w/2 - cursor_x) * old_spp)
            new_spp = self._samples_per_pixel(new_zoom, w)
            new_center = int(sample_at_cursor + (w/2 - cursor_x) * new_spp)
            self.center_sample = int(np.clip(new_center, 0, len(self.samples)-1))
            self.zoom_factor = new_zoom

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
            self.set_playhead_sample(new_sample)
            
            # Emitir la nueva posición en segundos al receptor (e.g., Audio Player)
            current_time = self.playhead_sample / self.sr
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
            
    def set_playhead_sample(self, sample):
        # Asegurarse de que no falle con total_samples = 0
        if self.total_samples == 0:
            self.playhead_sample = 0
            return
            
        self.playhead_sample = int(max(0, min(sample, len(self.samples)-1)))
        self.update()

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
        if len(window) < w:
            indices = np.linspace(0, len(window) - 1, num=w)
            interp = np.interp(indices, np.arange(len(window)), window)
            for x in range(w):
                val = float(interp[x])
                y = int(val * (h/2 - 2))
                painter.drawLine(x, mid - y, x, mid + y)
        else:
            samples_per_bucket = len(window) / w
            for x in range(w):
                b_start = int(x * samples_per_bucket)
                b_end = int((x + 1) * samples_per_bucket)

                if b_end <= b_start:
                    val = float(window[min(b_start, len(window)-1)])
                    y = int(val * (h/2 - 2))
                    painter.drawLine(x, mid - y, x, mid + y)
                else:
                    block = window[b_start:b_end]
                    min_v = float(np.min(block))
                    max_v = float(np.max(block))
                    y1 = int(min_v * (h/2 - 2))
                    y2 = int(max_v * (h/2 - 2))
                    painter.drawLine(x, mid - y2, x, mid - y1)

        # ----------------------------------------------------------
        # DIBUJAR BEATS / DOWNBEATS (líneas verticales)
        # ----------------------------------------------------------
        # Beats: thin cyan lines; Downbeats: thicker yellow/orange lines
        if hasattr(self, '_beats_samples') and start < end:
            beat_pen = QPen(QColor(0, 150, 255), 1)
            down_pen = QPen(QColor(255, 200, 0), 2)

            # Draw beats
            painter.setPen(beat_pen)
            for b in self._beats_samples:
                if start <= b <= end:
                    rel_b = (b - start) / (end - start)
                    x_b = int(rel_b * w)
                    painter.drawLine(x_b, 0, x_b, h)

            # Draw downbeats on top
            painter.setPen(down_pen)
            for d in self._downbeat_samples:
                if start <= d <= end:
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