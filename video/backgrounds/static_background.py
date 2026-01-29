"""
StaticFrameBackground - Single frozen frame display.

This background implements the "static" video mode where a single frame
is displayed throughout playback (no video decoding after initial frame).
"""

from typing import TYPE_CHECKING, Optional

from PySide6.QtCore import QTimer

from utils.logger import get_logger
from video.backgrounds.base import VisualBackground

if TYPE_CHECKING:
    from video.engines.base import VisualEngine

logger = get_logger(__name__)


# ================= CONSTANTS =================

# Delay before pausing to ensure frame is loaded (milliseconds)
STATIC_FRAME_LOAD_DELAY_MS = 100


class StaticFrameBackground(VisualBackground):
    """
    Static frame display (frozen video).

    Responsibilities:
    - Seek to specific frame and pause
    - Ensure frame remains frozen during playback

    Extracted from VideoLyrics (video.py L505-512, L673-677).
    """

    def __init__(self, static_frame_seconds: float = 0.0):
        """
        Initialize static frame background.

        Args:
            static_frame_seconds: Frame position to freeze at (default: 0.0)
                                  TODO: Load from meta.json in future
        """
        self.static_frame_seconds = static_frame_seconds
        self._pause_timer: Optional[QTimer] = None  # Store reference to prevent leak
        logger.debug(f"🖼️ StaticFrameBackground initialized (frame={static_frame_seconds}s)")

    def start(self, engine: 'VisualEngine', audio_time: float, offset: float) -> None:
        """
        Seek to static frame and pause.

        Args:
            engine: VisualEngine to control
            audio_time: Ignored (static doesn't sync)
            offset: Ignored (static doesn't sync)

        Extracted from VideoLyrics.start_playback() L505-512
        """
        # Seek to static frame
        engine.seek(self.static_frame_seconds)

        # Play briefly to load frame, then pause
        engine.play()

        # Pause after short delay to ensure frame is loaded
        # Store timer reference to prevent leak
        self._pause_timer = QTimer()
        self._pause_timer.setSingleShot(True)
        self._pause_timer.timeout.connect(lambda: self._ensure_static_frame(engine))
        self._pause_timer.start(STATIC_FRAME_LOAD_DELAY_MS)

        logger.info(f"[STATIC] Freezing at frame {self.static_frame_seconds}s")

    def stop(self, engine: 'VisualEngine') -> None:
        """
        Stop static frame display.

        Args:
            engine: VisualEngine to control
        """
        # Cleanup timer if active
        if self._pause_timer and self._pause_timer.isActive():
            self._pause_timer.stop()
            self._pause_timer = None

        engine.stop()
        logger.debug("[STATIC] Stopped")

    def pause(self, engine: 'VisualEngine') -> None:
        """
        Pause static frame (no-op, already paused).

        Args:
            engine: VisualEngine to control
        """
        # Static frame is already paused, but ensure it
        if engine.is_playing():
            engine.pause()
            logger.debug("[STATIC] Ensured pause state")

    def update(self, engine: 'VisualEngine', audio_time: float) -> None:
        """
        Update static frame (no-op).

        Args:
            engine: VisualEngine (unused)
            audio_time: Ignored (static doesn't sync)

        Note:
            Static frame doesn't need updates - it's frozen.
        """
        pass

    def on_video_end(self, engine: 'VisualEngine') -> None:
        """
        Handle video end event (no-op for static).

        Args:
            engine: VisualEngine that reached end

        Note:
            Static frame shouldn't reach end, but if it does, ignore.
        """
        logger.debug("[STATIC] Video end event (unexpected, ignoring)")

    def seek(self, engine: 'VisualEngine', seconds: float) -> None:
        """
        Seek in static mode (no-op).

        Static frame remains at configured position regardless of seeks.

        Args:
            engine: VisualEngine instance
            seconds: Target time (ignored)
        """
        logger.debug(f"[STATIC] Seek ignored (frame fixed at {self.static_frame_seconds:.2f}s)")

    def _ensure_static_frame(self, engine: 'VisualEngine') -> None:
        """
        Ensure video is paused to display static frame.

        Args:
            engine: VisualEngine to control

        Extracted from VideoLyrics._ensure_static_frame() L673-677
        """
        engine.pause()
        logger.debug("[STATIC] Frame frozen")
