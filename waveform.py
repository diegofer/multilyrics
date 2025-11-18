# Waveform Widget with Zoom, Scroll, and Animated Playhead

import numpy as np
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QPen, QFont
from PySide6.QtCore import Qt, Signal
import soundfile as sf
import sounddevice as sd

class WaveformWidget(QWidget):
    # Señal para notificar a la ventana principal sobre el tiempo transcurrido
    # Envía (tiempo_actual_segundos, duracion_total_segundos)
    time_updated = Signal(float, float)

    def __init__(self, audio_path, parent=None):
        super().__init__(parent)
        # --- Load audio ---
        data, sr = sf.read(audio_path)
        if data.ndim > 1:
            data = data.mean(axis=1)
        self.samples = np.asarray(data, dtype=np.float32)
        self.sr = sr
        self.total_samples = len(self.samples)
        self.duration_seconds = self.total_samples / self.sr # Nueva propiedad: duración total en segundos

        # --- View parameters ---
        self.zoom_factor = 1.0
        self.center_sample = self.total_samples // 2

        # --- Playhead ---
        self.playhead_sample = 0
        self.playing = False
        self.stream = None # Añadir el stream como None inicialmente
        
        # Emitir la duración inicial
        self.time_updated.emit(0.0, self.duration_seconds)

        # --- Interaction ---
        # NOTE: El arrastre (dragging) ya no se usa para el scroll horizontal
        # con el clic izquierdo, solo para la lógica interna si fuera necesario.
        self._dragging = False
        self._last_mouse_x = None

        self.setMinimumHeight(120)
        self.setFocusPolicy(Qt.StrongFocus)


    def _format_time(self, seconds):
        """Convierte segundos a formato MM:SS."""
        if seconds is None or seconds < 0:
            return "00:00"
        
        # Redondear al segundo más cercano para un formato simple
        total_seconds = int(round(seconds))
        
        minutes = total_seconds // 60
        secs = total_seconds % 60
        
        return f"{minutes:02d}:{secs:02d}"
    

    # ==============================================================
    # PLAYBACK CONTROL
    # ==============================================================
    def start_play(self):
        # 1. Si ya está reproduciendo, no hacer nada.
        if self.playing:
            return

        self.playing = True

        # 2. Si el stream no existe o está cerrado, crearlo e iniciarlo.
        if self.stream is None or not self.stream.active:
            # reiniciar playhead al comienzo si está al final (solo si no hay stream activo)
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
        
        # 3. Si el stream existe, pero está pausado, reanudarlo (si sounddevice lo permite)
        # En sounddevice, si el stream no se detuvo, solo tenemos que cambiar self.playing.

    def pause_play(self): # Renombrado de stop_play a pause_play
        # Simplemente establecemos el estado de reproducción en False.
        # El callback de audio dejará de escribir datos, logrando la pausa.
        self.playing = False
        self.update()


    def stop_stream(self):
        """Función para detener y cerrar el stream completamente (detener, no pausar)."""
        self.playing = False
        try:
            if self.stream and self.stream.active:
                self.stream.stop()
                self.stream.close()
            self.stream = None
        except Exception:
            # Manejar excepción si el stream ya está detenido/cerrado
            pass


    def _on_finished(self):
        """Called automatically when audio ends."""
        self.stop_stream() # Usamos la función de detener/cerrar
        self.update()
        # Emitir el tiempo final
        self.time_updated.emit(self.duration_seconds, self.duration_seconds)


    def _audio_callback(self, outdata, frames, time, status):
        """
        Este callback es llamado por sounddevice para llenar el buffer de audio.
        También es donde sincronizamos el playhead con el audio real.
        """
        # Si no está reproduciendo (pausado), llenamos con ceros y salimos.
        if not self.playing:
            outdata.fill(0)
            return

        start = self.playhead_sample
        end = start + frames

        # si llegamos al final
        if end >= len(self.samples):
            end = len(self.samples)
            # No cambiamos self.playing a False aquí, solo ajustamos el final.
            # El stream se detendrá al terminar la reproducción.

        chunk = self.samples[start:end]

        # copiar al buffer de audio
        outdata[:len(chunk), 0] = chunk

        # si faltan muestras, llenar con cero
        if len(chunk) < frames:
            outdata[len(chunk):, 0] = 0

            # Si llenamos con ceros porque se acabó el audio, 
            # sounddevice llama a _on_finished
            if end == len(self.samples):
                self.stop_stream()
                # Salimos para evitar actualizar el playhead después del final
                return


        # Avanzar playhead EXACTAMENTE según el audio real
        self.playhead_sample = end
        
        # Emitir la posición actual
        current_time = self.playhead_sample / self.sr
        self.time_updated.emit(current_time, self.duration_seconds)

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
    
    # --------------------------------------------------------------
    # NUEVO: mouseDoubleClickEvent para mover el playhead (scrubbing)
    # --------------------------------------------------------------
    def mouseDoubleClickEvent(self, event):
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
            
            # Emitir la nueva posición
            current_time = self.playhead_sample / self.sr
            self.time_updated.emit(current_time, self.duration_seconds)

            # Si está reproduciendo, pausamos para que la reanudación sea desde la nueva posición
            if self.playing:
                self.pause_play()
        else:
            super().mouseDoubleClickEvent(event)


    def mousePressEvent(self, event):
        # Dejar esta función vacía o solo llamar al super para evitar el movimiento con un solo clic.
        # Si queremos que el clic izquierdo aún tenga el foco:
        if event.button() == Qt.LeftButton:
            self.setFocus() # Asegura que el widget mantenga el foco
        super().mousePressEvent(event)
            
    def set_playhead_sample(self, sample):
        # Mantiene la función de seteo de la muestra de reproducción, 
        # usada por mousePressEvent
        self.playhead_sample = int(max(0, min(sample, len(self.samples)-1)))
        self.update()


    def mouseMoveEvent(self, event):
        if not self._dragging:
            return
        dx = event.x() - self._last_mouse_x
        self._last_mouse_x = event.x()

        w = max(1, self.width())
        spp = self._samples_per_pixel(self.zoom_factor, w)
        # Scroll horizontal
        self.center_sample = int(np.clip(self.center_sample - dx * spp, 0, len(self.samples)-1))
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            pass # No hace nada para el LeftButton ahora.

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
        
        total_time_str = self._format_time(self.duration_seconds)
        # Dibujar en la esquina superior derecha
        painter.drawText(w - 150, 20, 140, 20, Qt.AlignRight, total_time_str)

        # ----------------------------------------------------------
        # DIBUJAR TIEMPO TRANSCURRIDO (En la posición del playhead si es visible)
        # ----------------------------------------------------------
        if start <= self.playhead_sample <= end:
            current_time = self.playhead_sample / self.sr
            current_time_str = self._format_time(current_time)
            
            # Usar un color diferente y fuente un poco más grande
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Arial", 9, QFont.Bold))
            
            # Posición x: justo a la derecha del playhead
            text_x = x_pos + 5 
            
            # Asegurar que el texto no se salga del borde derecho
            if text_x + 100 > w:
                text_x = x_pos - 105 # Dibujar a la izquierda si no hay espacio
                
            painter.drawText(text_x, 20, 100, 20, Qt.AlignLeft, current_time_str)