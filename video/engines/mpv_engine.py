"""
MpvEngine - mpv backend implementation (STUB - Not implemented yet).

This is a placeholder for future mpv backend migration.
All methods raise NotImplementedError.
"""

from typing import Optional

from PySide6.QtGui import QScreen

from utils.logger import get_logger
from video.engines.base import VisualEngine, PlaybackState

logger = get_logger(__name__)


class MpvEngine(VisualEngine):
    """
    mpv-based video playback engine (STUB).

    Future implementation will use python-mpv library.
    This stub ensures the architecture is ready for mpv migration.
    """

    def __init__(self, is_legacy_hardware: bool = False):
        """
        Initialize mpv engine (NOT IMPLEMENTED).

        Args:
            is_legacy_hardware: Hardware optimization flag (unused)
        """
        logger.warning("⚠️ MpvEngine is not implemented yet. Use VlcEngine instead.")
        raise NotImplementedError(
            "MpvEngine is not implemented yet. "
            "Use VlcEngine for video playback."
        )

    def set_end_callback(self, callback) -> None:
        """Set callback for video end event (NOT IMPLEMENTED)."""
        raise NotImplementedError("MpvEngine not implemented")

    def load(self, path: str) -> None:
        raise NotImplementedError("MpvEngine not implemented")

    def play(self) -> None:
        raise NotImplementedError("MpvEngine not implemented")

    def pause(self) -> None:
        raise NotImplementedError("MpvEngine not implemented")

    def stop(self) -> None:
        raise NotImplementedError("MpvEngine not implemented")

    def seek(self, seconds: float) -> None:
        raise NotImplementedError("MpvEngine not implemented")

    def set_rate(self, rate: float) -> None:
        raise NotImplementedError("MpvEngine not implemented")

    def get_time(self) -> float:
        raise NotImplementedError("MpvEngine not implemented")

    def get_length(self) -> float:
        raise NotImplementedError("MpvEngine not implemented")

    def is_playing(self) -> bool:
        raise NotImplementedError("MpvEngine not implemented")

    def is_paused(self) -> bool:
        raise NotImplementedError("MpvEngine not implemented")

    def get_state(self) -> PlaybackState:
        raise NotImplementedError("MpvEngine not implemented")

    def attach_window(
        self,
        win_id: Optional[int],
        screen_index: Optional[int] = None,
        fullscreen: bool = True,
    ) -> None:
        raise NotImplementedError("MpvEngine not implemented")

    def show(self) -> None:
        raise NotImplementedError("MpvEngine not implemented")

    def hide(self) -> None:
        raise NotImplementedError("MpvEngine not implemented")

    def set_loop(self, enabled: bool) -> None:
        raise NotImplementedError("MpvEngine not implemented")

    def shutdown(self) -> None:
        raise NotImplementedError("MpvEngine not implemented")
