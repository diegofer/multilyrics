"""
VisualBackground - Abstract base class for video playback strategies.

This interface defines the contract for different playback modes (full sync, loop, static).
Backgrounds control HOW the video plays, while engines control the low-level playback.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from video.engines.base import VisualEngine


class VisualBackground(ABC):
    """
    Abstract interface for video playback strategies.

    Responsibilities:
    - Define playback behavior (sync with audio, loop, static frame)
    - Coordinate with VisualEngine for playback control
    - Handle video end events (loop restart, stop, etc.)
    - Report position for sync (if applicable)

    Implementations:
    - VideoLyricsBackground: Full video with elastic sync to audio
    - VideoLoopBackground: Continuous loop without audio sync
    - StaticFrameBackground: Single frozen frame
    - BlankBackground: No video (black screen)
    """

    @abstractmethod
    def start(self, engine: 'VisualEngine', audio_time: float, offset: float) -> None:
        """
        Start playback with this background strategy.

        Args:
            engine: VisualEngine instance to control
            audio_time: Current audio position in seconds (for sync modes)
            offset: Video offset from metadata (video_offset_seconds)
                    Positive = video starts after audio
                    Negative = video starts before audio

        Note:
            Implementation should:
            1. Calculate initial video position (if sync mode)
            2. Call engine.seek() if needed
            3. Call engine.play()
            4. Start any timers/monitoring needed
        """
        pass

    @abstractmethod
    def stop(self, engine: 'VisualEngine') -> None:
        """
        Stop playback and cleanup.

        Args:
            engine: VisualEngine instance to control

        Note:
            Implementation should:
            1. Stop any timers/monitoring
            2. Call engine.stop()
            3. Cleanup any state
        """
        pass

    @abstractmethod
    def pause(self, engine: 'VisualEngine') -> None:
        """
        Pause playback.

        Args:
            engine: VisualEngine instance to control

        Note:
            Implementation should:
            1. Stop any timers/monitoring
            2. Call engine.pause()
        """
        pass

    @abstractmethod
    def update(self, engine: 'VisualEngine', audio_time: float) -> None:
        """
        Update background state (called periodically by timer).

        Args:
            engine: VisualEngine instance to query/control
            audio_time: Current audio position in seconds

        Note:
            Called every 50ms by VisualController's position timer.
            Implementations can use this for:
            - Reporting position to SyncController (full mode)
            - Checking loop boundaries (loop mode)
            - No-op for static/blank modes
        """
        pass

    @abstractmethod
    def on_video_end(self, engine: 'VisualEngine') -> None:
        """
        Handle video end event from engine.

        Args:
            engine: VisualEngine instance that reached end

        Note:
            Called when engine detects end of media.
            Implementations can:
            - Restart loop (loop mode)
            - Stop playback (full mode)
            - Ignore (static mode)
        """
        pass

    def apply_correction(self, engine: 'VisualEngine', correction: dict) -> None:
        """
        Apply sync correction (optional, only for sync modes).

        Args:
            engine: VisualEngine instance to control
            correction: Correction dict from SyncController with:
                - 'type': 'elastic' | 'hard' | 'rate_reset'
                - 'new_rate': Playback rate (for elastic)
                - 'new_time_ms': Seek target (for hard)
                - 'drift_ms': Current drift value

        Note:
            Default implementation does nothing (non-sync modes).
            Override in VideoLyricsBackground for elastic sync.
        """
        pass
