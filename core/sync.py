from PySide6.QtCore import QObject, Signal, Slot
import numpy as np

from core.clock import AudioClock

class SyncController(QObject):
    """
    Controlador de sincronización audio-video usando PySide6.
    Maneja el reloj del audio, lo suaviza y lo expone por Signals + getters.
    """

    audioTimeUpdated = Signal(float)  # tiempo de audio suavizado

    def __init__(self, samplerate: int = 48000, parent=None):
        super().__init__(parent)
        self.clock = AudioClock(samplerate)
        self._smooth_audio_time = 0.0
        self.alpha = 0.1  # coeficiente de suavizado EMA

    # ----------------------------------------------------------
    #  PROPIEDAD PARA LEER EL TIEMPO ACTUAL DEL AUDIO SUAVIZADO
    # ----------------------------------------------------------
    @property
    def audio_time(self) -> float:
        """Retorna el tiempo actual del audio (suavizado)."""
        return self._smooth_audio_time

    # ----------------------------------------------------------
    #  LLAMADO DESDE EL CALLBACK DE SOUNDEVICE
    # ----------------------------------------------------------
    def audio_callback(self, frames: int):
        """
        Llamar desde tu callback de sounddevice:
        sync.audio_callback(frames)
        """

        # 1) Actualizar contador base
        self.clock.update(frames)

        raw_time = self.clock.get_time()

        # 2) Suavizar (EMA)
        self._smooth_audio_time = (
            (1 - self.alpha) * self._smooth_audio_time +
            self.alpha * raw_time
        )

        # 3) Emitir señal
        self.audioTimeUpdated.emit(self._smooth_audio_time)

    # ----------------------------------------------------------
    #  SINCRONIZACIÓN CON VIDEO
    # ----------------------------------------------------------
    @Slot(float)
    def sync_video(self, video_time: float):
        """
        Conectar este slot al evento de posicion del video.
        Recibe tiempo del video en segundos.
        """
        diff = video_time - self._smooth_audio_time

        # Guarda el diff si quieres usarlo externamente
        self.last_diff = diff

        # Opcional: aquí puedes aplicar correcciones al video (set_rate, seek, etc.)
        # pero típicamente lo haces desde donde controles el player.