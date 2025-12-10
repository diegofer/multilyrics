import threading

class AudioClock:
    def __init__(self, samplerate):
        self.samplerate = samplerate
        self.sample_counter = 0
        self.lock = threading.Lock()

    def update(self, frames):
        """Actualizar el contador desde el callback de SoundDevice."""
        with self.lock:
            self.sample_counter += frames

    def get_time(self):
        """Retorna el tiempo exacto procesado en segundos."""
        with self.lock:
            return self.sample_counter / self.samplerate