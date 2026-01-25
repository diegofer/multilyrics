"""
VideoLoopBackground - Continuous loop playback without audio sync.

This background implements the "loop" video mode where video plays continuously
in a loop, independent of audio position.
"""

from typing import TYPE_CHECKING

from PySide6.QtCore import QTimer

from utils.logger import get_logger
from video.backgrounds.base import VisualBackground

if TYPE_CHECKING:
    from video.engines.base import VisualEngine

logger = get_logger(__name__)


class VideoLoopBackground(VisualBackground):
    """
    Continuous loop playback without sync.

    Responsibilities:
    - Start video from beginning (ignore audio time)
    - Monitor loop boundaries and restart when reached
    - Handle video end events by restarting

    Extracted from VideoLyrics (video.py L493-503, L642-701).
    """

    def __init__(self):
        """Initialize loop background."""
        # Timer for checking loop boundaries (1 Hz)
        self._loop_timer = QTimer()
        self._loop_timer.setInterval(1000)  # 1000ms = 1 Hz
        self._loop_timer.timeout.connect(self._check_boundary)

        # Reference to engine (set during start)
        self._engine = None

        logger.debug("🔄 VideoLoopBackground initialized (loop mode)")

    def start(self, engine: 'VisualEngine', audio_time: float, offset: float) -> None:
        """
        Start loop playback from beginning.

        Args:
            engine: VisualEngine to control
            audio_time: Ignored (loop doesn't sync with audio)
            offset: Ignored (loop doesn't sync with audio)

        Extracted from VideoLyrics.start_playback() L493-503
        """
        self._engine = engine

        # Always start from beginning
        engine.seek(0)
        engine.play()

        logger.info("[LOOP] Starting loop playback from 0s (no audio sync)")

        # Start boundary monitoring timer
        self._loop_timer.start()
        logger.debug("[LOOP] Boundary timer started (1 Hz)")

    def stop(self, engine: 'VisualEngine') -> None:
        """
        Stop loop playback and monitoring.

        Args:
            engine: VisualEngine to control

        Extracted from VideoLyrics.stop() L521-537
        """
        engine.stop()

        # Stop boundary timer
        if self._loop_timer.isActive():
            self._loop_timer.stop()
            logger.debug("🔄 Loop boundary timer stopped")

        self._engine = None

    def pause(self, engine: 'VisualEngine') -> None:
        """
        Pause loop playback and monitoring.

        Args:
            engine: VisualEngine to control

        Extracted from VideoLyrics.pause() L538-553
        """
        engine.pause()

        # Stop boundary timer when paused
        if self._loop_timer.isActive():
            self._loop_timer.stop()
            logger.debug("[LOOP] Boundary timer paused")

    def update(self, engine: 'VisualEngine', audio_time: float) -> None:
        """
        Update loop state (no-op, timer handles boundary checks).

        Args:
            engine: VisualEngine to query (unused)
            audio_time: Ignored (loop doesn't sync)

        Note:
            Loop boundaries are checked by _loop_timer, not by update().
        """
        pass

    def on_video_end(self, engine: 'VisualEngine') -> None:
        """
        Handle video end event by restarting loop.

        Args:
            engine: VisualEngine that reached end

        Extracted from VideoLyrics._on_video_end() L679-701
        """
        logger.info("[LOOP] VLC EndReached event - scheduling restart")

        # Restart on Qt event loop to avoid VLC thread issues
        QTimer.singleShot(0, self._restart_loop)

    def _check_boundary(self) -> None:
        """
        Check if video reached loop boundary and restart.

        Called by timer every 1 second.

        Extracted from VideoLyrics._check_loop_boundary() L642-671
        """
        if not self._engine:
            return

        # Check if player stopped
        if not self._engine.is_playing():
            logger.debug("[LOOP] Player stopped - restarting loop")
            self._restart_loop()
            return

        video_seconds = self._engine.get_time()
        duration_seconds = self._engine.get_length()

        logger.debug(f"[LOOP_CHECK] video={video_seconds:.2f}s, duration={duration_seconds:.2f}s")

        if duration_seconds <= 0:
            logger.debug("[LOOP] Invalid duration, skipping")
            return

        # Restart if video is at or past 95% of duration
        # This is more reliable than checking exact end
        boundary_threshold = duration_seconds * 0.95
        if video_seconds >= boundary_threshold:
            logger.info(
                f"[LOOP] Boundary reached ({video_seconds:.2f}s >= {boundary_threshold:.2f}s) "
                f"- scheduling restart"
            )
            # Use Qt event loop to restart to avoid blocking
            QTimer.singleShot(0, self._restart_loop)

    def _restart_loop(self) -> None:
        """
        Restart loop playback safely on Qt event loop.

        Extracted from VideoLyrics._restart_loop() L692-701
        """
        if not self._engine:
            return

        try:
            self._engine.seek(0.0)
            self._engine.play()
            logger.debug("[LOOP] Restarted from 0.0s")
        except Exception as exc:
            logger.warning(f"[LOOP] Failed to restart loop: {exc}")
