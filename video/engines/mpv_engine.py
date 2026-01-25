"""
MpvEngine - mpv backend implementation for video playback.

Minimal functional implementation using python-mpv library.
Supports MP4 and images, loop playback, and multi-monitor output.
"""

import platform
from pathlib import Path
from typing import Optional

from utils.logger import get_logger
from video.engines.base import VisualEngine, PlaybackState

logger = get_logger(__name__)


class MpvEngine(VisualEngine):
    """
    mpv-based video playback engine.

    Minimal implementation focusing on stability over features.
    Uses python-mpv library with safe fallback if mpv not available.

    Responsibilities:
    - Initialize mpv player with basic config
    - Attach to OS window handles (Windows/Linux/macOS)
    - Control playback: play, pause, stop, seek
    - Report playback state and position
    - Support loop playback and multi-monitor
    """

    def __init__(self, is_legacy_hardware: bool = False):
        """
        Construct mpv engine (lightweight).

        Args:
            is_legacy_hardware: Enable optimizations for old CPUs (pre-2013)

        Note:
            Does NOT initialize mpv resources. Call initialize() after construction.
        """
        self.is_legacy_hardware = is_legacy_hardware
        self.system = platform.system()
        self.player = None
        self._loop_enabled = False

        logger.debug(f"🎬 MpvEngine constructed (system={self.system}, legacy={is_legacy_hardware})")

    # --- Lifecycle ------------------------------------------------

    def initialize(self) -> None:
        """
        Initialize mpv backend resources.

        Creates mpv player with basic configuration.

        Raises:
            RuntimeError: If mpv initialization failed (mpv not installed)
        """
        try:
            # Lazy import to allow graceful fallback
            import mpv
        except ImportError as e:
            raise RuntimeError(
                "python-mpv library not installed. "
                "Install with: pip install python-mpv"
            ) from e

        try:
            # Basic mpv configuration
            # CRITICAL: no-audio to prevent mpv from emitting sound
            self.player = mpv.MPV(
                # Audio
                no_audio=True,  # AudioEngine owns audio output

                # Video output
                vo='gpu',  # Hardware-accelerated rendering
                hwdec='auto',  # Auto-detect hardware decoding

                # Window behavior
                keep_open='yes',  # Don't close after playback
                idle='yes',  # Keep player alive when no file loaded

                # Performance
                video_sync='display-resample',  # Smooth playback

                # Logging
                log_level='info',
                terminal='no',  # Suppress terminal output
                msg_level='all=error',  # Only errors in console
            )

            # Legacy hardware optimizations
            if self.is_legacy_hardware:
                self.player['profile'] = 'sw-fast'  # Software decoding profile
                self.player['scale'] = 'bilinear'  # Faster scaling
                logger.info("🔧 MpvEngine: Legacy hardware optimizations enabled")

            logger.info(f"🎬 MpvEngine initialized (system={self.system}, legacy={self.is_legacy_hardware})")

        except Exception as e:
            raise RuntimeError(f"mpv initialization failed: {e}") from e

    def shutdown(self) -> None:
        """
        Release all mpv resources.

        Stops playback and destroys player instance.
        """
        if self.player:
            try:
                self.player.terminate()
                logger.debug("✓ MpvEngine: Player terminated")
            except Exception as e:
                logger.warning(f"⚠️ MpvEngine shutdown error: {e}")
            finally:
                self.player = None

    # --- Window / Screen ------------------------------------------

    def attach_window(
        self,
        win_id: Optional[int],
        screen_index: Optional[int] = None,
        fullscreen: bool = True,
    ) -> None:
        """
        Attach mpv output to window or screen.

        Args:
            win_id: Native window ID (HWND/XID/NSView), or None for mpv-owned window
            screen_index: Preferred screen index (0=primary, 1=secondary, etc.)
            fullscreen: Request fullscreen mode

        Raises:
            RuntimeError: If attachment failed

        Note:
            If win_id is None, mpv creates its own window (not yet implemented).
            For now, requires valid win_id.
        """
        if not self.player:
            raise RuntimeError("Player not initialized. Call initialize() first.")

        if win_id is None:
            # TODO: Implement mpv-owned window for future
            raise NotImplementedError("mpv-owned window not yet supported. Provide win_id.")

        try:
            # Auto-detect OS and attach to window
            system = self.system

            if system == "Windows":
                self.player['wid'] = int(win_id)
                logger.info(f"✓ MpvEngine: Attached to Windows HWND: {win_id}")

            elif system == "Linux":
                self.player['wid'] = int(win_id)
                logger.info(f"✓ MpvEngine: Attached to X11 window: {win_id}")

            elif system == "Darwin":  # macOS
                self.player['wid'] = int(win_id)
                logger.info(f"✓ MpvEngine: Attached to macOS window: {win_id}")

            else:
                logger.warning(f"⚠️ Unknown OS: {system}, attempting wid attachment")
                self.player['wid'] = int(win_id)

            # Note: Screen positioning handled by Qt (QWidget geometry)
            # mpv will render to whatever window Qt provides

        except Exception as e:
            logger.error(f"❌ MpvEngine: Failed to attach to window: {e}", exc_info=True)
            raise RuntimeError(f"mpv attachment failed: {e}") from e

    def show(self) -> None:
        """
        Make visual output visible (no-op for embedded mpv).

        Note:
            When mpv renders to Qt window, visibility controlled by Qt.
            This method reserved for future mpv-owned window support.
        """
        pass

    def hide(self) -> None:
        """
        Hide visual output (no-op for embedded mpv).

        Note:
            When mpv renders to Qt window, visibility controlled by Qt.
            This method reserved for future mpv-owned window support.
        """
        pass

    # --- Media control --------------------------------------------

    def load(self, path: str) -> None:
        """
        Load a video file or image for playback.

        Args:
            path: Absolute path to media file (MP4, PNG, JPEG, etc.)

        Raises:
            FileNotFoundError: If file doesn't exist
            RuntimeError: If mpv failed to load file
        """
        if not self.player:
            raise RuntimeError("Player not initialized. Call initialize() first.")

        # Validate file exists
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Media file not found: {path}")

        try:
            # Load media file
            self.player.loadfile(str(file_path.absolute()))

            # Apply loop setting if enabled
            if self._loop_enabled:
                self.player['loop-file'] = 'inf'

            logger.debug(f"📹 MpvEngine: Loaded media: {file_path.name}")

        except Exception as e:
            raise RuntimeError(f"Failed to load media: {e}") from e

    def play(self) -> None:
        """Start or resume playback."""
        if not self.player:
            raise RuntimeError("Player not initialized. Call initialize() first.")

        try:
            self.player['pause'] = False
        except Exception as e:
            logger.warning(f"⚠️ MpvEngine play error: {e}")

    def pause(self) -> None:
        """Pause playback."""
        if not self.player:
            raise RuntimeError("Player not initialized. Call initialize() first.")

        try:
            self.player['pause'] = True
        except Exception as e:
            logger.warning(f"⚠️ MpvEngine pause error: {e}")

    def stop(self) -> None:
        """
        Stop playback and reset position.

        Note:
            mpv doesn't have explicit 'stop'. We pause and seek to 0.
        """
        if not self.player:
            raise RuntimeError("Player not initialized. Call initialize() first.")

        try:
            self.player['pause'] = True
            self.player.seek(0, reference='absolute')
        except Exception as e:
            logger.warning(f"⚠️ MpvEngine stop error: {e}")

    def seek(self, seconds: float) -> None:
        """
        Seek to absolute time position.

        Args:
            seconds: Target position in seconds (e.g., 45.5)
        """
        if not self.player:
            raise RuntimeError("Player not initialized. Call initialize() first.")

        try:
            self.player.seek(seconds, reference='absolute')
        except Exception as e:
            logger.warning(f"⚠️ MpvEngine seek error: {e}")

    # --- Playback parameters --------------------------------------

    def set_rate(self, rate: float) -> None:
        """
        Set playback rate (NOT IMPLEMENTED - out of scope).

        Args:
            rate: Playback speed multiplier

        Note:
            Rate control not required for basic visual playback.
            Background sync handles corrections via seek, not rate.
        """
        logger.warning("⚠️ MpvEngine: set_rate() not implemented (out of scope)")

    def set_loop(self, enabled: bool) -> None:
        """
        Enable or disable infinite looping.

        Args:
            enabled: True to loop indefinitely, False to play once
        """
        self._loop_enabled = enabled

        if self.player:
            try:
                self.player['loop-file'] = 'inf' if enabled else 'no'
                logger.debug(f"🔄 MpvEngine: Loop {'enabled' if enabled else 'disabled'}")
            except Exception as e:
                logger.warning(f"⚠️ MpvEngine set_loop error: {e}")

    # --- State / Timing -------------------------------------------

    def get_time(self) -> float:
        """
        Get current playback position.

        Returns:
            Position in seconds (e.g., 45.5), or -1.0 if unavailable
        """
        if not self.player:
            return -1.0

        try:
            time_pos = self.player['time-pos']
            return float(time_pos) if time_pos is not None else -1.0
        except Exception:
            return -1.0

    def get_length(self) -> float:
        """
        Get total media duration (NOT IMPLEMENTED - out of scope).

        Returns:
            -1.0 (not implemented)

        Note:
            Duration not required for basic loop playback.
            LoopBackground uses boundary timer instead.
        """
        return -1.0

    def is_playing(self) -> bool:
        """
        Check if media is currently playing.

        Returns:
            True if playing, False if paused/stopped
        """
        if not self.player:
            return False

        try:
            # In mpv: not paused = playing
            paused = self.player['pause']
            return not paused if paused is not None else False
        except Exception:
            return False

    def is_paused(self) -> bool:
        """
        Check if media is currently paused (NOT IMPLEMENTED - out of scope).

        Returns:
            False (stub)

        Note:
            Not required for minimal implementation.
        """
        return False

    def get_state(self) -> PlaybackState:
        """
        Get playback state (NOT IMPLEMENTED - out of scope).

        Returns:
            PlaybackState.STOPPED (stub)

        Note:
            Granular state not required for minimal implementation.
        """
        return PlaybackState.STOPPED

    def set_end_callback(self, callback) -> None:
        """
        Set callback for media end event (NOT IMPLEMENTED - out of scope).

        Args:
            callback: Function to call when media ends

        Note:
            EOF callbacks not required for minimal implementation.
            Backgrounds use polling via is_playing() instead.
        """
        logger.warning("⚠️ MpvEngine: set_end_callback() not implemented (out of scope)")
