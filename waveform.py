# Waveform Widget with Zoom, Scroll, and Animated Playhead

import numpy as np
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtCore import Qt, QTimer
import soundfile as sf
import sounddevice as sd

class WaveformWidget(QWidget):
    def __init__(self, audio_path, parent=None):
        super().__init__(parent)
        # --- Load audio ---
        data, sr = sf.read(audio_path)
        if data.ndim > 1:
            data = data.mean(axis=1)
        self.samples = np.asarray(data, dtype=np.float32)
        self.sr = sr

        # --- View parameters ---
        self.zoom_factor = 1.0
        self.center_sample = len(self.samples) // 2

        # --- Playhead ---
        self.playhead_sample = 0
        self.playing = False

        # --- Interaction ---
        self._dragging = False
        self._last_mouse_x = None

        self.setMinimumHeight(120)
        self.setFocusPolicy(Qt.StrongFocus)



    # ==============================================================
    # PLAYBACK CONTROL
    # ==============================================================
    def start_play(self):
        self.playing = True

    def stop_play(self):
        self.playing = False

    def set_playhead_sample(self, sample):
        self.playhead_sample = int(max(0, min(sample, len(self.samples)-1)))
        self.update()

    def step_playhead(self, samples):
        self.set_playhead_sample(self.playhead_sample + samples)

    # ================================
    # REAL AUDIO PLAYBACK
    # ================================
    def start_play(self):
        if self.playing:
            return

        self.playing = True

        # reiniciar playhead al comienzo si está al final
        if self.playhead_sample >= len(self.samples) - 1:
            self.playhead_sample = 0

        # abrir stream de audio REAL
        self.stream = sd.OutputStream(
            samplerate=self.sr,
            channels=1,
            callback=self._audio_callback,
            finished_callback=self._on_finished
        )
        self.stream.start()


    def stop_play(self):
        self.playing = False
        try:
            self.stream.stop()
            self.stream.close()
        except:
            pass


    def _on_finished(self):
        """Called automatically when audio ends."""
        self.playing = False
        self.update()


    def _audio_callback(self, outdata, frames, time, status):
        """
        Este callback es llamado por sounddevice para llenar el buffer de audio.
        También es donde sincronizamos el playhead con el audio real.
        """
        if not self.playing:
            outdata.fill(0)
            return

        start = self.playhead_sample
        end = start + frames

        # si llegamos al final
        if end >= len(self.samples):
            end = len(self.samples)
            self.playing = False

        chunk = self.samples[start:end]

        # copiar al buffer de audio
        outdata[:len(chunk), 0] = chunk

        # si faltan muestras, llenar con cero
        if len(chunk) < frames:
            outdata[len(chunk):, 0] = 0

        # Avanzar playhead EXACTAMENTE según el audio real
        self.playhead_sample = end

        # Forzar repintado para mover el playhead en pantalla
        self.update()
    

    # ==============================================================
    # ZOOM
    # ==============================================================
    def set_zoom(self, factor: float):
        factor = max(1.0, factor)
        self.zoom_factor = factor
        self.center_sample = int(np.clip(self.center_sample, 0, len(self.samples)-1))
        self.update()

    def zoom_by(self, ratio: float, cursor_x: int = None):
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
        visible_samples = max(1.0, total_samples / zoom_factor)
        spp = visible_samples / width_pixels
        return max(1e-6, spp)

    # ==============================================================
    # SCROLL (Mouse + Keyboard)
    # ==============================================================
    def wheelEvent(self, event):
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

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._last_mouse_x = event.x()
            self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        if not self._dragging:
            return
        dx = event.x() - self._last_mouse_x
        self._last_mouse_x = event.x()

        w = max(1, self.width())
        spp = self._samples_per_pixel(self.zoom_factor, w)
        self.center_sample = int(np.clip(self.center_sample - dx * spp, 0, len(self.samples)-1))
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = False
            self._last_mouse_x = None
            self.unsetCursor()

    def keyPressEvent(self, event):
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

    def mousePressEvent(self, event):
        # Left-click scrubbing: move playhead to clicked position
        if event.button() == Qt.LeftButton:
            w = max(1, self.width())
            h = self.height()


            # detect click inside waveform area
            x = event.x()
            rel = x / w


            total_samples = len(self.samples)
            spp = self._samples_per_pixel(self.zoom_factor, w)
            half_visible = (w * spp) / 2.0
            start = int(np.clip(self.center_sample - half_visible, 0, total_samples - 1))
            end = int(np.clip(self.center_sample + half_visible, 0, total_samples - 1))


            # new playhead
            new_sample = int(start + rel * (end - start))
            self.set_playhead_sample(new_sample)


            # if playing, reposition playback stream
            if self.playing:
                try:
                    self.stream.stop()
                    self.stream.close()
                except:
                    pass
            #self.start_play()


            # prepare dragging for scroll
            self._dragging = True
            self._last_mouse_x = x
            self.setCursor(Qt.ClosedHandCursor)
        else:
            super().mousePressEvent(event)


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
        spp = self._samples_per_pixel(self.zoom_factor, w)
        half_visible = (w * spp) / 2.0

        start = int(np.clip(self.center_sample - half_visible, 0, total_samples - 1))
        end = int(np.clip(self.center_sample + half_visible, 0, total_samples - 1))

        if end <= start:
            return

        window = self.samples[start:end+1]

        pen = QPen(QColor(0, 200, 255), 1)
        painter.setPen(pen)

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
        # DRAW PLAYHEAD
        # ----------------------------------------------------------
        if start <= self.playhead_sample <= end:
            rel = (self.playhead_sample - start) / (end - start)
            x_pos = int(rel * w)

            play_pen = QPen(QColor(255, 50, 50), 2)
            painter.setPen(play_pen)
            painter.drawLine(x_pos, 0, x_pos, h)
