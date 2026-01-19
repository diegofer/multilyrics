from PySide6.QtCore import QObject, Signal, Slot, QTimer
import numpy as np

from core.clock import AudioClock
from utils.error_handler import safe_operation
from utils.logger import get_logger

logger = get_logger(__name__)

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

        # Audio engine reference (set externally after construction)
        self.audio_engine = None

        # QTimer for polling audio position (prevents Qt Signal emission from audio thread)
        # Polls at ~60 FPS for smooth playhead updates
        self._position_timer = QTimer(self)
        self._position_timer.setInterval(16)  # ~60 FPS (16ms)
        self._position_timer.timeout.connect(self._poll_audio_position)

        # Track last known frames to calculate delta
        self._last_frames_processed = 0

    # ----------------------------------------------------------
    #  PROPIEDAD PARA LEER EL TIEMPO ACTUAL DEL AUDIO SUAVIZADO
    # ----------------------------------------------------------
    @property
    def audio_time(self) -> float:
        """Retorna el tiempo actual del audio (suavizado)."""
        return self._smooth_audio_time

    # ----------------------------------------------------------
    #  POLLING DESDE QT THREAD (REEMPLAZA audio_callback)
    # ----------------------------------------------------------
    def _poll_audio_position(self):
        """
        Poll audio position from engine's atomic counter (Qt thread safe).
        Called by QTimer every ~16ms (60 FPS) during playback.

        CRITICAL: This method runs in Qt thread, NOT audio thread.
        Safe to emit Qt Signals without causing deadlock on Windows WASAPI.
        """
        if self.audio_engine is None:
            logger.debug("\u26a0\ufe0f  Poll: audio_engine is None")
            return

        # Read atomic counter from audio engine (thread-safe read)
        current_frames = self.audio_engine._frames_processed
        logger.debug(f"\ud83d\udd04 Poll: current_frames={current_frames}, last={self._last_frames_processed}")

        # Calculate delta since last poll
        frames_delta = current_frames - self._last_frames_processed
        if frames_delta > 0:
            # 1) Update clock with delta
            self.clock.update(frames_delta)
            raw_time = self.clock.get_time()

            # 2) Smooth time (EMA)
            self._smooth_audio_time = (
                (1 - self.alpha) * self._smooth_audio_time +
                self.alpha * raw_time
            )

            # 3) Emit signal for UI (SAFE: we're in Qt thread)
            logger.debug(f"\u2705 Emitting audioTimeUpdated: {self._smooth_audio_time:.3f}s")
            self.audioTimeUpdated.emit(self._smooth_audio_time)

            # 4) Calculate video corrections if syncing
            if self.is_syncing:
                self._calculate_video_correction()

            # Update last known position
            self._last_frames_processed = current_frames

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
    #  CONTROL DE SINCRONIZACIÓN Y POLLING
    # ----------------------------------------------------------
    def start_sync(self):
        """Habilita la sincronización automática de video."""
        self.is_syncing = True
        if not self._position_timer.isActive():
            self._position_timer.start()

    def stop_sync(self):
        """Detiene la sincronización automática de video."""
        self.is_syncing = False
        if self._position_timer.isActive():
            self._position_timer.stop()

    def reset(self):
        """Reinicia el reloj y estado de sincronización."""
        self.clock.reset()
        self._smooth_audio_time = 0.0
        self._video_time = 0.0
        self.is_syncing = False
        self._last_frames_processed = 0
        if self._position_timer.isActive():
            self._position_timer.stop()

    def set_audio_time(self, seconds: float):
        """Set audio clock and smooth time to a specific value (seek)."""
        # Update clock absolute time
        with safe_operation("Setting audio clock time", silent=True):
            self.clock.set_time(seconds)
        # Set smoothed value directly so downstream logic immediately sees it
        self._smooth_audio_time = float(seconds)
        # Reset frame tracking to sync with engine after seek
        if self.audio_engine is not None:
            self._last_frames_processed = self.audio_engine._frames_processed
        # Emit updated position for UI
        self.audioTimeUpdated.emit(self._smooth_audio_time)
