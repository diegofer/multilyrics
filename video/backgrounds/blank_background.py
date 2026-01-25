"""
BlankBackground - No video playback (blank/black screen).

This background implements the "none" video mode where no video is played.
Useful for audio-only playback or when video is disabled.
"""

from typing import TYPE_CHECKING

from utils.logger import get_logger
from video.backgrounds.base import VisualBackground

if TYPE_CHECKING:
    from video.engines.base import VisualEngine

logger = get_logger(__name__)


class BlankBackground(VisualBackground):
    """
    Blank background (no video playback).

    Responsibilities:
    - Do nothing (no video playback)
    - Provide no-op implementations for all methods

    Used when video mode is "none" or video is disabled.
    """

    def __init__(self):
        """Initialize blank background."""
        logger.debug("⬛ BlankBackground initialized (no video mode)")

    def start(self, engine: 'VisualEngine', audio_time: float, offset: float) -> None:
        """
        Start blank background (no-op).

        Args:
            engine: VisualEngine (unused)
            audio_time: Ignored
            offset: Ignored
        """
        logger.debug("[NONE] Blank background - no video playback")

    def stop(self, engine: 'VisualEngine') -> None:
        """
        Stop blank background (no-op).

        Args:
            engine: VisualEngine (unused)
        """
        pass

    def pause(self, engine: 'VisualEngine') -> None:
        """
        Pause blank background (no-op).

        Args:
            engine: VisualEngine (unused)
        """
        pass

    def update(self, engine: 'VisualEngine', audio_time: float) -> None:
        """
        Update blank background (no-op).

        Args:
            engine: VisualEngine (unused)
            audio_time: Ignored
        """
        pass

    def on_video_end(self, engine: 'VisualEngine') -> None:
        """
        Handle video end (no-op).

        Args:
            engine: VisualEngine (unused)
        """
        pass
