"""
VisualEngine - Abstract base class for video playback backends.

This interface defines the contract that all video engines (VLC, mpv) must implement.
Engines are responsible for low-level video playback control, independent of playback strategy.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional

from PySide6.QtGui import QScreen


# ================= CONSTANTS =================

class PlaybackState(Enum):
    """Playback state enumeration."""
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
    ENDED = "ended"
    ERROR = "error"


class VisualEngine(ABC):
    """
    Low-level visual output engine.

    Responsible ONLY for rendering visual media to a screen.
    Follows 4 core rules:
    1. Does not decide what to show (only executes commands)
    2. Does not know about songs, lyrics, or modes
    3. Time is external (exposes position, accepts seek, does not govern clock)
    4. Allows clean degradation (fallback window, optional secondary screen, swappable backend)

    Implementations:
    - VlcEngine: Uses python-vlc backend
    - MpvEngine: Uses mpv backend (future)
    """


    # --- Lifecycle ------------------------------------------------

    @abstractmethod
    def initialize(self) -> None:
        """
        Initialize backend resources (processes, instances, windows).

        Called once after construction to allocate heavy resources.
        Separates object construction from resource allocation.

        Raises:
            RuntimeError: If initialization failed (e.g., VLC not installed)

        Note:
            Must be called before any playback operations.
            Allows lazy initialization pattern for performance.
        """
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """
        Release all backend resources.

        Called when engine is no longer needed.
        Should stop playback, free players/processes, destroy windows.
        """
        pass

    # --- Window / Screen ------------------------------------------

    @abstractmethod
    def attach_window(
        self,
        win_id: Optional[int],
        screen_index: Optional[int] = None,
        fullscreen: bool = True,
    ) -> None:
        """
        Attach rendering output to window or screen.

        Args:
            win_id: Native window ID (HWND/XID/NSView), or None if backend creates own
            screen_index: Preferred screen index (0=primary, 1=secondary, etc.)
            fullscreen: Request fullscreen mode when possible

        Raises:
            RuntimeError: If attachment failed

        Note:
            Backend auto-detects OS (Windows/Linux/Darwin) internally.
            Must be called after window is visible and has valid winId().
        """
        pass


    @abstractmethod
    def show(self) -> None:
        """
        Make visual output visible.

        Note:
            For VLC, this is no-op (Qt controls window visibility).
            For mpv with own window, this shows the window.
        """
        pass

    @abstractmethod
    def hide(self) -> None:
        """
        Hide visual output without destroying resources.

        Note:
            For VLC, this is no-op (Qt controls window visibility).
            For mpv with own window, this hides the window.
        """
        pass


    # --- Media control --------------------------------------------

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
    def seek(self, seconds: float) -> None:
        """
        Seek to absolute time position.

        Args:
            seconds: Target position in seconds (e.g., 45.5)

        Note:
            Seeking may not be frame-accurate depending on backend.
            Position is clamped to [0, duration].
        """
        pass


    # --- Playback parameters --------------------------------------

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
    def set_loop(self, enabled: bool) -> None:
        """
        Enable or disable infinite looping.

        Args:
            enabled: True to loop indefinitely, False to play once

        Note:
            Backend-specific. VLC uses --repeat, mpv uses --loop-file=inf.
            Some backgrounds (LoopBackground) may handle restart manually.
        """
        pass


    # --- State / Timing -------------------------------------------

    @abstractmethod
    def get_time(self) -> float:
        """
        Get current playback position.

        Returns:
            Current position in seconds (e.g., 45.5)

        Note:
            Returns -1.0 if position unavailable (e.g., no media loaded).
        """
        pass

    @abstractmethod
    def get_length(self) -> float:
        """
        Get total video duration.

        Returns:
            Duration in seconds (e.g., 180.5)

        Note:
            Returns -1.0 if duration unavailable (e.g., no media loaded).
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
    def is_paused(self) -> bool:
        """
        Check if video is currently paused.

        Returns:
            True if paused, False otherwise

        Note:
            A paused video can be resumed from its current position.
            This is different from stopped (which resets position).
        """
        pass

    @abstractmethod
    def get_state(self) -> PlaybackState:
        """
        Get current playback state.

        Returns:
            PlaybackState enum value (STOPPED, PLAYING, PAUSED, ENDED, ERROR)

        Note:
            Provides more granular state than is_playing()/is_paused() booleans.
            Useful for debugging and logging.
        """
        pass

    @abstractmethod
    def set_end_callback(self, callback) -> None:
        """
        Set callback for video end event (TECHNICAL DETAIL).

        Args:
            callback: Function to call when video reaches end (no arguments)

        Note:
            This is backend-specific optimization (e.g., VLC EventType.MediaPlayerEndReached).
            Backgrounds should NOT rely on this - use polling via is_playing() instead.
            Callback invoked on Qt event loop (thread-safe).
            May be deprecated if polling proves sufficient.
        """
        pass


