"""
VlcEngine - VLC backend implementation for video playback.

Extracts all VLC-specific logic from VideoLyrics into a reusable engine.
This allows VideoLyrics to be backend-agnostic and prepares for mpv migration.
"""

import platform
from typing import Optional

import vlc
from PySide6.QtCore import QTimer
from PySide6.QtGui import QScreen

from utils.logger import get_logger
from video.engines.base import VisualEngine

logger = get_logger(__name__)


class VlcEngine(VisualEngine):
    """
    VLC-based video playback engine.

    Responsibilities:
    - Initialize VLC instance with optimized args
    - Attach to OS window handles (Windows/Linux/macOS)
    - Control playback: play, pause, stop, seek, rate
    - Report playback state and position

    Extracted from VideoLyrics (video.py L56-70, L396-456).
    """

    def __init__(self, is_legacy_hardware: bool = False):
        """
        Initialize VLC engine with hardware-specific optimizations.

        Args:
            is_legacy_hardware: Enable optimizations for old CPUs (pre-2013)
        """
        self.is_legacy_hardware = is_legacy_hardware
        self.system = platform.system()

        # VLC args - CRITICAL: '--no-audio' to prevent VLC from emitting sound
        # AudioEngine is the sole owner of audio output
        vlc_args = ['--quiet', '--no-video-title-show', '--log-verbose=2', '--no-audio']

        if is_legacy_hardware:
            # Optimizations for legacy CPUs (Sandy Bridge, Core 2 Duo, etc.)
            vlc_args.extend([
                '--avcodec-hurry-up',         # Skip frames if CPU slow
                '--avcodec-skiploopfilter=4', # Skip deblocking (less CPU)
                '--avcodec-threads=2',        # Limit threads (leave for audio)
                '--file-caching=1000',        # Larger buffer (reduce spikes)
            ])
            logger.info("🔧 VlcEngine: Legacy hardware optimizations enabled")

        # Initialize VLC instance and player
        self.instance = vlc.Instance(vlc_args)
        self.player = self.instance.media_player_new()
        self.player.audio_set_mute(True)  # Ensure audio is muted

        logger.info(f"🎬 VlcEngine initialized (system={self.system}, legacy={is_legacy_hardware})")

        # Event callback for video end (set by VisualController)
        self._end_callback = None

    def set_end_callback(self, callback) -> None:
        """
        Set callback for video end event.

        Args:
            callback: Function to call when video ends (no arguments)
        """
        self._end_callback = callback

        # Attach VLC event
        event_manager = self.player.event_manager()
        event_manager.event_attach(vlc.EventType.MediaPlayerEndReached, self._on_vlc_end)

    def _on_vlc_end(self, event) -> None:
        """VLC event callback when video reaches end."""
        if self._end_callback:
            # Schedule callback on Qt event loop to avoid VLC thread issues
            QTimer.singleShot(0, self._end_callback)

    def load(self, path: str) -> None:
        """
        Load video file for playback.

        Args:
            path: Absolute path to video file
        """
        if self.player.is_playing():
            self.player.stop()

        media = self.instance.media_new(str(path))
        media.add_option("--no-audio")  # Ensure no audio from video

        self.player.set_media(media)
        media.release()

        logger.debug(f"📹 VlcEngine: Loaded video: {path}")

    def play(self) -> None:
        """Start or resume playback."""
        self.player.play()

    def pause(self) -> None:
        """Pause playback."""
        self.player.pause()

    def stop(self) -> None:
        """Stop playback and reset position."""
        self.player.stop()

    def seek(self, milliseconds: int) -> None:
        """
        Seek to specific time position.

        Args:
            milliseconds: Target position in milliseconds
        """
        self.player.set_time(int(milliseconds))

    def set_rate(self, rate: float) -> None:
        """
        Set playback rate.

        Args:
            rate: Playback speed multiplier (1.0 = normal)
        """
        self.player.set_rate(float(rate))

    def get_time(self) -> int:
        """
        Get current playback position.

        Returns:
            Position in milliseconds (-1 if unavailable)
        """
        return self.player.get_time()

    def get_length(self) -> int:
        """
        Get video duration.

        Returns:
            Duration in milliseconds (-1 if unavailable)
        """
        return self.player.get_length()

    def is_playing(self) -> bool:
        """
        Check if video is playing.

        Returns:
            True if playing, False otherwise
        """
        return self.player.is_playing()

    def attach_to_window(self, win_id: int, screen: Optional[QScreen], system: str) -> None:
        """
        Attach VLC output to OS window handle.

        Args:
            win_id: Native window ID (HWND/XID/NSView)
            screen: Target QScreen (optional, for logging)
            system: OS identifier ("Windows", "Linux", "Darwin")

        Raises:
            RuntimeError: If attachment failed

        Note:
            Extracted from VideoLyrics._attach_vlc_to_window() (L396-456)
        """
        try:
            if system == "Windows":
                hwnd = int(win_id)
                logger.info(f"✓ VlcEngine: HWND obtained: {hwnd}")
                self.player.set_hwnd(hwnd)

            elif system == "Linux":
                xid = int(win_id)
                if xid == 0:
                    raise RuntimeError("winId() returned 0 - window not initialized")

                logger.info(f"✓ VlcEngine: XWindow ID obtained: {xid}")
                self.player.set_xwindow(xid)
                logger.info("✓ VlcEngine: Attached to X11 window")

            elif system == "Darwin":  # macOS
                logger.info("🍎 VlcEngine: macOS detected - using set_nsobject()")
                try:
                    self.player.set_nsobject(win_id)
                    logger.info("✓ VlcEngine: Attached to macOS window")
                except Exception as e:
                    logger.warning(f"⚠ set_nsobject failed: {e}, using default config")
            else:
                logger.warning(f"⚠ Unknown OS: {system}, VLC using default config")

            screen_name = screen.name() if screen else "unknown"
            logger.info(f"✓ VlcEngine: Attached to window (screen={screen_name})")

        except Exception as e:
            logger.error(f"❌ VlcEngine: Failed to attach to window: {e}", exc_info=True)
            raise RuntimeError(f"VLC attachment failed: {e}")

    def set_mute(self, muted: bool) -> None:
        """
        Mute/unmute video audio.

        Args:
            muted: True to mute, False to unmute
        """
        self.player.audio_set_mute(muted)

    def release(self) -> None:
        """Release VLC resources."""
        try:
            if self.player:
                self.player.stop()
                self.player.release()
            if self.instance:
                self.instance.release()
            logger.debug("🔧 VlcEngine: Resources released")
        except Exception as e:
            logger.warning(f"⚠ VlcEngine: Error releasing resources: {e}")
