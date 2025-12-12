from PySide6.QtCore import QObject, Signal, Slot
import numpy as np

from core.clock import AudioClock

class SyncController(QObject):
    """
    Controlador centralizado de sincronización audio-video.
    
    Responsabilidades:
    - Mantener reloj de audio suavizado desde callback de sounddevice
    - Recibir posición de video desde VideoLyrics
    - Calcular diferencias y decidir correcciones
    - Emitir señales para que VideoLyrics ejecute las correcciones
    
    Umbrales de sincronización (en ms):
    - SOFT_THRESHOLD: si diff está dentro, corrección suave
    - HARD_THRESHOLD: si diff supera, corrección dura (salto directo)
    - CORR_MAX_MS: máxima corrección suave por frame
    """

    # Señales de salida
    audioTimeUpdated = Signal(float)          # tiempo de audio suavizado para UI
    videoCorrectionNeeded = Signal(dict)      # dict con tipo y parámetros de corrección

    def __init__(self, samplerate: int = 44100, parent=None):
        super().__init__(parent)
        self.clock = AudioClock(samplerate)
        self.samplerate = samplerate
        self._smooth_audio_time = 0.0
        self.alpha = 0.1  # coeficiente de suavizado EMA
        
        # Umbrales de sincronización (ms)
        self.SOFT_THRESHOLD = 80
        self.HARD_THRESHOLD = 300
        self.CORR_MAX_MS = 20
        
        # Estado video
        self._video_time = 0.0
        self.is_syncing = False  # flag para evitar correcciones durante buscas

    # ----------------------------------------------------------
    #  PROPIEDAD PARA LEER EL TIEMPO ACTUAL DEL AUDIO SUAVIZADO
    # ----------------------------------------------------------
    @property
    def audio_time(self) -> float:
        """Retorna el tiempo actual del audio (suavizado)."""
        return self._smooth_audio_time

    # ----------------------------------------------------------
    #  LLAMADO DESDE EL CALLBACK DE SOUNDDEVICE
    # ----------------------------------------------------------
    def audio_callback(self, frames: int):
        """
        Llamar desde el callback de sounddevice.
        Actualiza reloj, suaviza tiempo y emite signal para UI.
        """
        # 1) Actualizar contador base
        self.clock.update(frames)
        raw_time = self.clock.get_time()

        # 2) Suavizar (EMA)
        self._smooth_audio_time = (
            (1 - self.alpha) * self._smooth_audio_time +
            self.alpha * raw_time
        )

        # 3) Emitir para UI
        self.audioTimeUpdated.emit(self._smooth_audio_time)
        
        # 4) Si estamos sincronizando, calcular correcciones
        if self.is_syncing:
            self._calculate_video_correction()

    # ----------------------------------------------------------
    #  RECIBIR POSICIÓN DE VIDEO
    # ----------------------------------------------------------
    @Slot(float)
    def on_video_position_updated(self, video_time: float):
        """
        Conectar al evento de posición del reproductor de video.
        Actualiza la posición conocida del video.
        """
        self._video_time = video_time

    # ----------------------------------------------------------
    #  CALCULAR Y EMITIR CORRECCIONES
    # ----------------------------------------------------------
    def _calculate_video_correction(self):
        """
        Calcula la diferencia audio-video y emite corrección si es necesaria.
        Interna, se llama desde audio_callback si is_syncing es True.
        """
        audio_ms = int(self._smooth_audio_time * 1000)
        video_ms = int(self._video_time * 1000)
        diff = audio_ms - video_ms  # positivo → video atrasado

        correction = None

        # Corrección suave (dentro de rangos)
        if abs(diff) > self.SOFT_THRESHOLD and abs(diff) < self.HARD_THRESHOLD:
            adjustment = max(-self.CORR_MAX_MS,
                            min(self.CORR_MAX_MS, diff // 5))
            new_time = video_ms + adjustment
            correction = {
                'type': 'soft',
                'diff_ms': diff,
                'adjustment_ms': adjustment,
                'new_time_ms': new_time
            }

        # Corrección dura (salto directo)
        elif abs(diff) >= self.HARD_THRESHOLD:
            correction = {
                'type': 'hard',
                'diff_ms': diff,
                'new_time_ms': audio_ms
            }

        # Emitir si hay corrección
        if correction:
            self.videoCorrectionNeeded.emit(correction)

    # ----------------------------------------------------------
    #  CONTROL DE SINCRONIZACIÓN
    # ----------------------------------------------------------
    def start_sync(self):
        """Habilita la sincronización automática de video."""
        self.is_syncing = True

    def stop_sync(self):
        """Detiene la sincronización automática de video."""
        self.is_syncing = False

    def reset(self):
        """Reinicia el reloj y estado de sincronización."""
        self.clock.reset()
        self._smooth_audio_time = 0.0
        self._video_time = 0.0
        self.is_syncing = False