
from PySide6.QtCore import QObject
import threading

class AudioClock(QObject):
    """ Reloj de audio basado en el conteo de muestras. """
    def __init__(self, samplerate):
        self.samplerate = samplerate
        self.total_frames = 0
        self.lock = threading.Lock()

    def update(self, frames: int):
        """Actualizar el contador desde el callback de SoundDevice."""
        with self.lock:
            self.total_frames += frames

    def get_time(self) -> float:
        """Retorna el tiempo exacto procesado en segundos."""
        with self.lock:
            return self.total_frames / self.samplerate

    def set_time(self, seconds: float):
        """Set the clock time to a specific time in seconds (seek)."""
        with self.lock:
            self.total_frames = int(seconds * self.samplerate)

    def reset(self):
        """Reset the clock to zero."""
        with self.lock:
            self.total_frames = 0