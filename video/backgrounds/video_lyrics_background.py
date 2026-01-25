"""
VideoLyricsBackground - Full video playback with elastic sync to audio.

This background implements the "full" video mode where video is synchronized
with audio using elastic corrections from SyncController.
"""

from typing import TYPE_CHECKING, Optional

from utils.logger import get_logger
from video.backgrounds.base import VisualBackground

if TYPE_CHECKING:
    from video.engines.base import VisualEngine
    from core.sync_controller import SyncController

logger = get_logger(__name__)


class VideoLyricsBackground(VisualBackground):
    """
    Full video playback with audio synchronization.

    Responsibilities:
    - Start video with offset calculation (audio_time + offset)
    - Report position to SyncController for drift detection
    - Apply elastic/hard corrections from SyncController

    Extracted from VideoLyrics (video.py L480-491, L703-772).
    """

    def __init__(self, sync_controller: Optional['SyncController'] = None):
        """
        Initialize full sync background.

        Args:
            sync_controller: SyncController instance for sync corrections
        """
        self.sync_controller = sync_controller
        logger.debug("🎬 VideoLyricsBackground initialized (full sync mode)")

    def start(self, engine: 'VisualEngine', audio_time: float, offset: float) -> None:
        """
        Start video playback with sync offset.

        Args:
            engine: VisualEngine to control
            audio_time: Current audio position in seconds
            offset: Video offset from metadata (video_offset_seconds)
                    Positive = video starts after audio
                    Negative = video starts before audio

        Extracted from VideoLyrics.start_playback() L480-491
        """
        # Calculate video start time with offset
        video_start_time = audio_time + offset

        if abs(video_start_time) > 0.001:
            video_seconds = max(0.0, video_start_time)
            engine.seek(video_seconds)
            logger.info(
                f"[FULL] audio={audio_time:.3f}s "
                f"offset={offset:+.3f}s → video_start={video_start_time:.3f}s"
            )

        engine.play()

        # Enable sync monitoring
        if self.sync_controller:
            self.sync_controller.start_sync()
            logger.debug("[FULL] Sync monitoring enabled")

    def stop(self, engine: 'VisualEngine') -> None:
        """
        Stop playback and sync monitoring.

        Args:
            engine: VisualEngine to control
        """
        engine.stop()

        if self.sync_controller:
            self.sync_controller.stop_sync()
            logger.debug("[FULL] Sync monitoring stopped")

    def pause(self, engine: 'VisualEngine') -> None:
        """
        Pause playback and sync monitoring.

        Args:
            engine: VisualEngine to control
        """
        engine.pause()

        if self.sync_controller:
            self.sync_controller.stop_sync()
            logger.debug("[FULL] Sync monitoring paused")

    def update(self, engine: 'VisualEngine', audio_time: float) -> None:
        """
        Report video position to SyncController for drift detection.

        Args:
            engine: VisualEngine to query
            audio_time: Current audio position (unused, sync uses video position)

        Extracted from VideoLyrics._report_position() L703-717
        """
        if not engine.is_playing():
            return

        if self.sync_controller:
            video_seconds = engine.get_time()
            self.sync_controller.on_video_position_updated(video_seconds)

    def on_video_end(self, engine: 'VisualEngine') -> None:
        """
        Handle video end event (stop playback).

        Args:
            engine: VisualEngine that reached end

        Note:
            In full mode, video ending is natural - just stop.
        """
        logger.info("[FULL] Video ended naturally")
        self.stop(engine)

    def apply_correction(self, engine: 'VisualEngine', correction: dict) -> None:
        """
        Apply sync correction from SyncController.

        Args:
            engine: VisualEngine to control
            correction: Correction dict with:
                - 'type': 'elastic' | 'hard' | 'rate_reset' | 'soft'
                - 'new_rate': Playback rate (for elastic)
                - 'new_time_ms': Seek target (for hard)
                - 'drift_ms': Current drift value

        Extracted from VideoLyrics.apply_correction() L719-772
        """
        if not engine.is_playing():
            return

        corr_type = correction.get('type')
        drift_ms = correction.get('drift_ms', 0)

        if corr_type == 'elastic':
            # Elastic correction: Adjust playback rate
            new_rate = correction.get('new_rate', 1.0)
            current_rate = correction.get('current_rate', 1.0)
            engine.set_rate(new_rate)
            logger.debug(
                f"[ELASTIC] drift={drift_ms:+d}ms "
                f"rate: {current_rate:.3f} → {new_rate:.3f}"
            )

        elif corr_type == 'rate_reset':
            # Reset rate to normal
            engine.set_rate(1.0)
            logger.debug(f"[RATE_RESET] drift={drift_ms:+d}ms → rate=1.0")

        elif corr_type == 'hard':
            # Hard correction: Seek directly
            new_time_ms = correction.get('new_time_ms')
            new_time_seconds = new_time_ms / 1000.0
            engine.seek(new_time_seconds)

            # Reset rate after hard seek
            if correction.get('reset_rate', False):
                engine.set_rate(1.0)

            logger.debug(f"[HARD] drift={drift_ms:+d}ms → seek to {new_time_seconds:.3f}s")

        elif corr_type == 'soft':
            # Legacy soft correction (deprecated, kept for compatibility)
            new_time_ms = correction.get('new_time_ms')
            adjustment_ms = correction.get('adjustment_ms', 0)
            new_time_seconds = new_time_ms / 1000.0
            engine.seek(new_time_seconds)
            logger.debug(f"[SOFT] diff={drift_ms}ms adj={adjustment_ms}ms → {new_time_seconds:.3f}s")
