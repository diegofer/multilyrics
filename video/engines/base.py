"""
VisualEngine - Abstract base class for video playback backends.

This interface defines the contract that all video engines (VLC, mpv) must implement.
Engines are responsible for low-level video playback control, independent of playback strategy.
"""

from abc import ABC, abstractmethod
from typing import Optional

from PySide6.QtGui import QScreen


class VisualEngine(ABC):
    """
    Abstract interface for video playback engines.

    Responsibilities:
    - Load and control video playback (play, pause, stop, seek)
    - Attach to OS window handles for rendering
    - Report playback state and position
    - Control playback rate for sync corrections

    Implementations:
    - VlcEngine: Uses python-vlc backend
    - MpvEngine: Uses mpv backend (future)
    """

    @abstractmethod
    def load(self, path: str) -> None:
        """
        Load a video file for playback.

        Args:
            path: Absolute path to video file

        Raises:
            FileNotFoundError: If video file doesn't exist
            RuntimeError: If engine failed to load video
        """
        pass

    @abstractmethod
    def play(self) -> None:
        """
        Start or resume video playback.

        If video is paused, resumes from current position.
        If video is stopped, starts from beginning or last seek position.
        """
        pass

    @abstractmethod
    def pause(self) -> None:
        """
        Pause video playback.

        Preserves current position for resume.
        """
        pass

    @abstractmethod
    def stop(self) -> None:
        """
        Stop video playback and reset position.

        After stop, next play() will start from beginning.
        """
        pass

    @abstractmethod
    def seek(self, milliseconds: int) -> None:
        """
        Seek to specific time position.

        Args:
            milliseconds: Target position in milliseconds

        Note:
            Seeking may not be frame-accurate depending on backend.
            Position is clamped to [0, duration].
        """
        pass

    @abstractmethod
    def set_rate(self, rate: float) -> None:
        """
        Set playback rate for sync corrections.

        Args:
            rate: Playback speed multiplier (1.0 = normal speed)
                  Typical range: 0.95 - 1.05 for elastic sync

        Note:
            Used by VideoLyricsBackground for elastic sync corrections.
        """
        pass

    @abstractmethod
    def get_time(self) -> int:
        """
        Get current playback position.

        Returns:
            Current position in milliseconds

        Note:
            Returns -1 if position unavailable (e.g., no media loaded).
        """
        pass

    @abstractmethod
    def get_length(self) -> int:
        """
        Get total video duration.

        Returns:
            Duration in milliseconds

        Note:
            Returns -1 if duration unavailable (e.g., no media loaded).
        """
        pass

    @abstractmethod
    def is_playing(self) -> bool:
        """
        Check if video is currently playing.

        Returns:
            True if playing, False if paused/stopped
        """
        pass

    @abstractmethod
    def attach_to_window(self, win_id: int, screen: Optional[QScreen], system: str) -> None:
        """
        Attach video output to OS window handle.

        Args:
            win_id: Native window ID (HWND on Windows, XID on Linux, NSView on macOS)
            screen: Target QScreen for multi-monitor setups (optional)
            system: OS identifier ("Windows", "Linux", "Darwin")

        Raises:
            RuntimeError: If attachment failed

        Note:
            Must be called after window is visible and has valid winId().
            Platform-specific implementation required.
        """
        pass

    @abstractmethod
    def set_mute(self, muted: bool) -> None:
        """
        Mute/unmute video audio track.

        Args:
            muted: True to mute, False to unmute

        Note:
            Video audio should ALWAYS be muted in MultiLyrics.
            AudioEngine is the sole owner of audio output.
        """
        pass

    @abstractmethod
    def release(self) -> None:
        """
        Release engine resources.

        Called when engine is no longer needed.
        Should stop playback and free backend resources.
        """
        pass
