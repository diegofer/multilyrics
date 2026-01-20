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

        # Umbrales de sincronización (ms) - Fase 3: Elastic correction
        self.DEAD_ZONE = 40          # < 40ms: No correction (imperceptible)
        self.ELASTIC_THRESHOLD = 150 # 40-150ms: Playback rate adjustment
        self.HARD_THRESHOLD = 300    # > 150ms: Hard seek

        # Elastic correction parameters
        self.ELASTIC_RATE_MIN = 0.95  # 5% slower
        self.ELASTIC_RATE_MAX = 1.05  # 5% faster
        self.RATE_RESET_DELAY = 2000  # ms to hold rate before resetting to 1.0

        # Estado video
        self._video_time = 0.0
        self.is_syncing = False  # flag para evitar correcciones durante buscas

        # Audio engine reference (set externally after construction)
        self.audio_engine = None

        # Video player reference (set externally, optional)
        self.video_player = None

        # Flag to disable dynamic corrections (for legacy hardware)
        self.disable_dynamic_corrections = False

        # QTimer for polling audio position (prevents Qt Signal emission from audio thread)
        # Polls at ~60 FPS for smooth playhead updates
        self._position_timer = QTimer(self)
        self._position_timer.setInterval(16)  # ~60 FPS (16ms)
        self._position_timer.timeout.connect(self._poll_audio_position)

        # Track last known frames to calculate delta
        self._last_frames_processed = 0

        # Diagnostic logging timer (1 Hz - low overhead)
        self._diag_timer = QTimer(self)
        self._diag_timer.setInterval(1000)  # 1 second
        self._diag_timer.timeout.connect(self._log_sync_stats)
        self._diag_enabled = False  # Enable manually for debugging

        # Correction timer (1 Hz - elastic sync)
        self._correction_timer = QTimer(self)
        self._correction_timer.setInterval(1000)  # 1 second
        self._correction_timer.timeout.connect(self._apply_elastic_correction)

        # Correction state tracking
        self._last_correction_time = 0.0
        self._last_correction_type = None
        self._current_rate = 1.0

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
        DEPRECATED: Use _apply_elastic_correction() instead.
        Kept for backward compatibility.
        """
        pass

    def _apply_elastic_correction(self):
        """
        Aplicar corrección elástica periódica (llamado cada ~1 segundo).

        Estrategia de corrección:
        - Dead zone (0-40ms): Sin corrección (imperceptible)
        - Elastic zone (40-150ms): Ajuste de playback rate (95-105%)
        - Hard zone (>150ms): Seek directo
        """
        if not self.is_syncing:
            return

        # FASE 5.1: Skip if video is not enabled
        if not self._is_video_enabled():
            return

        # FASE 5.2: Skip dynamic corrections if disabled (legacy hardware)
        if self.disable_dynamic_corrections:
            return

        audio_ms = int(self._smooth_audio_time * 1000)
        video_ms = int(self._video_time * 1000)
        drift_ms = audio_ms - video_ms  # positivo = video atrasado

        abs_drift = abs(drift_ms)
        correction = None

        # Zone 1: Dead zone (no correction needed)
        if abs_drift < self.DEAD_ZONE:
            # Reset rate to normal if was adjusted
            if abs(self._current_rate - 1.0) > 0.01:
                correction = {
                    'type': 'rate_reset',
                    'drift_ms': drift_ms,
                    'new_rate': 1.0
                }
                self._current_rate = 1.0

        # Zone 2: Elastic correction (playback rate adjustment)
        elif abs_drift < self.ELASTIC_THRESHOLD:
            # Calculate target rate based on drift
            # drift > 0: video behind → speed up (rate > 1.0)
            # drift < 0: video ahead → slow down (rate < 1.0)
            rate_adjustment = drift_ms / 1000.0  # Convert to rate delta
            target_rate = 1.0 + (rate_adjustment * 0.05)  # Scale to 5% max
            target_rate = max(self.ELASTIC_RATE_MIN,
                            min(self.ELASTIC_RATE_MAX, target_rate))

            # Only adjust if significant change (avoid jitter)
            if abs(target_rate - self._current_rate) > 0.02:
                correction = {
                    'type': 'elastic',
                    'drift_ms': drift_ms,
                    'new_rate': target_rate,
                    'current_rate': self._current_rate
                }
                self._current_rate = target_rate

        # Zone 3: Hard correction (seek)
        elif abs_drift >= self.HARD_THRESHOLD:
            correction = {
                'type': 'hard',
                'drift_ms': drift_ms,
                'new_time_ms': audio_ms,
                'reset_rate': True
            }
            self._current_rate = 1.0

        # Emit correction if needed
        if correction:
            self._last_correction_time = self._smooth_audio_time
            self._last_correction_type = correction['type']
            self.videoCorrectionNeeded.emit(correction)
            logger.debug(
                f"📐 [ELASTIC_SYNC] drift={drift_ms:+d}ms "
                f"type={correction['type']} "
                f"rate={self._current_rate:.3f}"
            )

    # ----------------------------------------------------------
    #  CONTROL DE SINCRONIZACIÓN Y POLLING
    # ----------------------------------------------------------
    def _log_sync_stats(self):
        """
        Log sync statistics at 1 Hz for diagnosis.
        Called by diagnostic timer (low frequency, non-invasive).
        """
        if not self.is_syncing:
            return

        audio_ms = int(self._smooth_audio_time * 1000)
        video_ms = int(self._video_time * 1000)
        drift_ms = audio_ms - video_ms  # positive = video lagging

        # Determine state
        state = "playing" if self.is_syncing else "paused"

        # Log format: [SYNC] audio=12.345s video=12.265s drift=-80ms state=playing
        logger.info(
            f"[SYNC_DIAG] audio={self._smooth_audio_time:.3f}s "
            f"video={self._video_time:.3f}s drift={drift_ms:+d}ms state={state}"
        )

    def _is_video_enabled(self) -> bool:
        """Check if video is enabled and should participate in sync.

        Returns:
            bool: True if video player exists and is enabled, False otherwise
        """
        if self.video_player is None:
            return False

        # Check if video player has is_video_enabled method
        if hasattr(self.video_player, 'is_video_enabled'):
            return self.video_player.is_video_enabled()

        # Fallback: assume enabled if player exists
        return True

    def enable_diagnostics(self, enable: bool = True):
        """Enable/disable 1 Hz diagnostic logging."""
        self._diag_enabled = enable
        if enable and self.is_syncing and not self._diag_timer.isActive():
            self._diag_timer.start()
            logger.info("🔍 Sync diagnostics enabled (1 Hz logging)")
        elif not enable and self._diag_timer.isActive():
            self._diag_timer.stop()
            logger.info("🔍 Sync diagnostics disabled")

    def start_sync(self):
        """Habilita la sincronización automática de video."""
        self.is_syncing = True
        if not self._position_timer.isActive():
            self._position_timer.start()
        if self._diag_enabled and not self._diag_timer.isActive():
            self._diag_timer.start()

        # FASE 5.1: Start elastic correction timer only if video is enabled
        if self._is_video_enabled():
            if not self._correction_timer.isActive():
                self._correction_timer.start()
                logger.info("🔄 Elastic sync enabled (1 Hz correction loop)")
        else:
            logger.debug("🎬 Sincronización iniciada (sin video - solo audio polling)")

    def stop_sync(self):
        """Detiene la sincronización automática de video."""
        self.is_syncing = False
        if self._position_timer.isActive():
            self._position_timer.stop()
        if self._diag_timer.isActive():
            self._diag_timer.stop()
        if self._correction_timer.isActive():
            self._correction_timer.stop()
        # Reset correction state
        self._current_rate = 1.0
        self._last_correction_type = None

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
