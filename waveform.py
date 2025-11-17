# waveform.py
import numpy as np
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtCore import Qt
import soundfile as sf

class WaveformWidget(QWidget):
    def __init__(self, audio_path, parent=None):
        super().__init__(parent)
        # --- cargar audio ---
        data, sr = sf.read(audio_path)
        if data.ndim > 1:
            data = data.mean(axis=1)  # convertir a mono
        self.samples = np.asarray(data, dtype=np.float32)
        self.sr = sr

        # --- vista / zoom / pan ---
        # zoom_factor: 1.0 = toda la pista cabe en el ancho del widget
        # zoom_factor > 1 = acercar (menos duración visible)
        self.zoom_factor = 1.0

        # center_sample es el índice de muestra que está centrado en la vista
        self.center_sample = len(self.samples) // 2

        # flags para arrastre (panning)
        self._dragging = False
        self._last_mouse_x = None

        self.setMinimumHeight(120)
        self.setFocusPolicy(Qt.StrongFocus)

    # -------------------------
    # API pública
    # -------------------------
    def set_zoom(self, factor: float):
        """Factor de zoom absoluto (>=1.0). 1.0 = ver toda la pista."""
        if factor < 1.0:
            factor = 1.0
        self.zoom_factor = factor
        # mantener center_sample dentro de rango
        self.center_sample = int(np.clip(self.center_sample, 0, len(self.samples)-1))
        self.update()

    def zoom_by(self, ratio: float, cursor_x: int = None):
        """
        Cambia zoom multiplicativamente (ej: ratio=1.1 -> 10% más zoom).
        Si cursor_x se provee, intenta mantener el punto bajo el cursor en la misma muestra.
        """
        old_zoom = self.zoom_factor
        new_zoom = max(1.0, old_zoom * ratio)

        if cursor_x is None:
            # simplemente ajustar zoom manteniendo center_sample
            self.zoom_factor = new_zoom
        else:
            w = max(1, self.width())
            # muestra actualmente bajo el cursor
            old_samples_per_pixel = self._samples_per_pixel(old_zoom, w)
            cursor_rel = cursor_x / (w - 1) if w > 1 else 0.5
            sample_at_cursor = int(self.center_sample - (w/2 - cursor_x) * old_samples_per_pixel)

            # después del zoom, calcular nuevo center para que sample_at_cursor permanezca en cursor_x
            new_samples_per_pixel = self._samples_per_pixel(new_zoom, w)
            new_center = int(sample_at_cursor + (w/2 - cursor_x) * new_samples_per_pixel)
            self.center_sample = int(np.clip(new_center, 0, len(self.samples)-1))
            self.zoom_factor = new_zoom

        self.update()

    # -------------------------
    # util: muestras por pixel
    # -------------------------
    def _samples_per_pixel(self, zoom_factor, width_pixels):
        """
        Calcula cuántas muestras corresponden a cada píxel horizontal según zoom.
        zoom_factor=1.0 => todo el buffer en width_pixels.
        zoom_factor>1 => menos muestras por píxel (acercamiento).
        """
        if width_pixels <= 0:
            return 1.0
        total_samples = len(self.samples)
        visible_samples = max(1.0, total_samples / zoom_factor)
        spp = visible_samples / width_pixels
        return max(1e-6, spp)

    # -------------------------
    # eventos del mouse (wheel -> zoom; drag -> pan)
    # -------------------------
    def wheelEvent(self, event):
        """
        Rueda del mouse: zoom in/out.
        Qt::angleDelta().y() da el delta. Usamos factor exponencial suave.
        """
        delta = event.angleDelta().y()
        if delta == 0:
            return
        # cada paso de rueda (120) -> zoom 1.15x
        steps = delta / 120.0
        factor_per_step = 1.15
        ratio = factor_per_step ** steps

        cursor_x = event.position().x() if hasattr(event, "position") else event.x()
        self.zoom_by(ratio, int(cursor_x))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._last_mouse_x = event.x()
            self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        if not self._dragging:
            return
        x = event.x()
        dx = x - self._last_mouse_x
        self._last_mouse_x = x

        w = max(1, self.width())
        spp = self._samples_per_pixel(self.zoom_factor, w)
        # mover el centro en sentido inverso al movimiento del mouse
        self.center_sample = int(np.clip(self.center_sample - dx * spp, 0, len(self.samples)-1))
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = False
            self._last_mouse_x = None
            self.unsetCursor()

    # -------------------------
    # dibujado adaptativo
    # -------------------------
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(30, 30, 30))
        pen = QPen(QColor(0, 200, 255), 1)
        painter.setPen(pen)

        w = max(1, self.width())
        h = max(2, self.height())
        mid = h // 2

        total_samples = len(self.samples)
        spp = self._samples_per_pixel(self.zoom_factor, w)
        # rango visible
        half_visible = (w * spp) / 2.0
        start = int(np.clip(self.center_sample - half_visible, 0, total_samples - 1))
        end = int(np.clip(self.center_sample + half_visible, 0, total_samples - 1))
        if end <= start:
            return

        window = self.samples[start:end+1]
        # dividir la ventana en 'w' segmentos y calcular min/max por píxel para representación más correcta
        # si hay menos muestras que pixels, hacemos interpolación simple (pad con ceros)
        if len(window) < w:
            # interpolar la señal a exactamente w puntos (más suave)
            indices = np.linspace(0, len(window) - 1, num=w)
            interp = np.interp(indices, np.arange(len(window)), window)
            for x in range(w):
                val = float(interp[x])
                y = int(val * (h/2 - 2))
                painter.drawLine(x, mid - y, x, mid + y)
        else:
            # por cada píxel, tomar min y max del bloque de muestras que cubre ese pixel
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
                    # dibujar línea desde min hasta max para visualizar amplitud del bloque
                    min_v = float(np.min(block))
                    max_v = float(np.max(block))
                    y1 = int(min_v * (h/2 - 2))
                    y2 = int(max_v * (h/2 - 2))
                    painter.drawLine(x, mid - y2, x, mid - y1)

    # opcional: tecla +/- para zoom
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Plus or event.key() == Qt.Key_Equal:
            self.zoom_by(1.2)
        elif event.key() == Qt.Key_Minus or event.key() == Qt.Key_Underscore:
            self.zoom_by(1/1.2)
        else:
            super().keyPressEvent(event)
