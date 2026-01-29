"""
BackgroundManager - Factory and state manager for VisualBackground instances.

Responsibilities:
- Create appropriate background based on video mode
- Manage background lifecycle
- Provide simple API for main.py integration
"""

from typing import Optional

from utils.logger import get_logger
from video.backgrounds.base import VisualBackground
from video.backgrounds.video_lyrics_background import VideoLyricsBackground
from video.backgrounds.loop_background import VideoLoopBackground
from video.backgrounds.static_background import StaticFrameBackground
from video.backgrounds.blank_background import BlankBackground

logger = get_logger(__name__)


class BackgroundManager:
    """
    Factory and manager for VisualBackground instances.

    Simplifies background selection and creation logic.
    """

    @staticmethod
    def create_background(
        mode: str,
        sync_controller = None,
        static_frame_seconds: float = 0.0
    ) -> VisualBackground:
        """
        Create background instance based on video mode.

        Args:
            mode: Video mode ("full", "loop", "static", "blank")
            sync_controller: SyncController instance (required for "full" mode)
            static_frame_seconds: Frame time for static mode (default: 0.0)

        Returns:
            VisualBackground instance
        """
        if mode == "full":
            if sync_controller is None:
                logger.warning("⚠️ Full mode requires SyncController, falling back to loop")
                return VideoLoopBackground()
            return VideoLyricsBackground(sync_controller=sync_controller)

        elif mode == "loop":
            return VideoLoopBackground()

        elif mode == "static":
            return StaticFrameBackground(static_frame_seconds=static_frame_seconds)

        elif mode == "blank":
            return BlankBackground()

        else:
            logger.warning(f"⚠️ Unknown video mode '{mode}', using blank")
            return BlankBackground()

    @staticmethod
    def is_video_required(mode: str) -> bool:
        """
        Check if mode requires video file to be loaded.

        Args:
            mode: Video mode

        Returns:
            True if video file needed, False otherwise
        """
        return mode in ["full", "loop", "static"]

    @staticmethod
    def get_available_modes() -> list:
        """
        Get list of available video modes.

        Returns:
            List of mode strings
        """
        return ["full", "loop", "static", "blank"]
