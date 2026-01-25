"""
VisualController (VideoLyrics) - Orchestrates video playback with decoupled architecture.

REFACTORED: This file has been refactored to separate concerns:
- VisualEngine: Low-level video backend (VLC, mpv)
- VisualBackground: Playback strategy (full sync, loop, static, none)
- VisualController: Orchestration + UI management

Original responsibilities (794 lines) split into:
- video/engines/vlc_engine.py (~200 lines) - VLC backend
- video/backgrounds/*.py (~400 lines) - Playback strategies
- video/video.py (~300 lines) - UI + orchestration
"""

import platform
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget

from core.config_manager import ConfigManager
from core.constants import app_state
from utils.error_handler import safe_operation
from utils.logger import get_logger

# Import new architecture components
from video.engines.base import VisualEngine
from video.engines.vlc_engine import VlcEngine
from video.backgrounds.base import VisualBackground
from video.backgrounds.video_lyrics_background import VideoLyricsBackground
from video.backgrounds.loop_background import VideoLoopBackground
from video.backgrounds.static_background import StaticFrameBackground
from video.backgrounds.blank_background import BlankBackground

logger = get_logger(__name__)


class VideoLyrics(QWidget):
    """
    VisualController - Orchestrates video playback with decoupled architecture.

    Responsibilities (REFACTORED):
    - UI management: window positioning, screens, show/hide
    - Engine selection and initialization (VLC/mpv)
    - Background selection based on video mode
    - Coordination between engine, background, and SyncController

    Delegated to VisualEngine (VlcEngine):
    - VLC initialization and configuration
    - Window attachment (platform-specific)
    - Low-level playback control (play, pause, stop, seek, rate)

    Delegated to VisualBackground (VideoLyricsBackground, etc.):
    - Playback strategy (sync, loop, static)
    - Position reporting for sync
    - Sync correction application
    - Loop boundary detection
    """

    # Signal emitted when window is closed with X button
    window_closed = Signal()

    def __init__(self, screen_index: int = 1):
        """
        Initialize VisualController.

        Args:
            screen_index: Target screen index for video display (default: 1 = secondary)
        """
        super().__init__()

        self.screen_index = screen_index
        self.setWindowTitle("VideoLyrics")
        self.resize(800, 600)

        # Detect OS
        self.system = platform.system()
        logger.debug(f"SO detectado: {self.system}")

        # Initialize with video mode from ConfigManager
        config = ConfigManager.get_instance()
        self._video_mode = config.get("video.mode", "full")  # "full" | "loop" | "static" | "none"
        logger.info(f"🎬 VisualController initialized with mode: {self._video_mode}")

        # Legacy hardware detection
        self._is_legacy_hardware = self._detect_legacy_hardware()
        if self._is_legacy_hardware:
            logger.warning(
                "⚠️ Hardware antiguo detectado. "
                "Modo de video configurado en Settings puede afectar rendimiento."
            )

        # Reference to SyncController (assigned from main.py)
        # CRITICAL FIX: Must be assigned BEFORE _update_background() is called
        self.sync_controller = None

        # REFACTORED: Initialize VisualEngine (VLC backend)
        # Replaces direct VLC initialization (old L56-74)
        self.engine: VisualEngine = VlcEngine(is_legacy_hardware=self._is_legacy_hardware)
        self.engine.set_end_callback(self._on_video_end)
        logger.info("✅ VlcEngine initialized and attached")

        # REFACTORED: Initialize VisualBackground (will be set based on mode)
        self.background: Optional[VisualBackground] = None
        self._update_background()  # Create background for current mode

        # Layout required for QWidget
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        # Don't show by default - will be shown when user clicks show_video_btn
        self.hide()

        # Window initialization state
        self._window_initialized = False
        self._target_screen = None
        self._is_fallback_mode = False

        # Timer for reporting position periodically
        self.position_timer = QTimer()
        self.position_timer.setInterval(50)  # 50ms
        self.position_timer.timeout.connect(self._report_position)

    def _detect_legacy_hardware(self) -> bool:
        """
        Detect if system is legacy hardware with potential video performance issues.

        Criteria (conservative):
        - Intel Sandy Bridge or older CPUs (2011 and earlier)
        - AMD pre-2013 CPUs
        - RAM < 6GB

        Returns:
            True if legacy hardware detected, False otherwise
        """
        try:
            if self.system == "Linux":
                # Read CPU info from /proc/cpuinfo
                try:
                    with open("/proc/cpuinfo", "r") as f:
                        cpuinfo = f.read().lower()

                        # Known legacy CPU markers
                        legacy_cpu_markers = [
                            "i5-2410m",  # Sandy Bridge (2011)
                            "i3-2",      # Sandy Bridge i3
                            "i5-2",      # Sandy Bridge i5
                            "i7-2",      # Sandy Bridge i7
                            "core(tm)2 duo",  # Core 2 Duo (2006-2009)
                            "core(tm)2 quad", # Core 2 Quad (2007-2009)
                            "pentium(r) dual", # Pentium Dual Core
                        ]

                        for marker in legacy_cpu_markers:
                            if marker in cpuinfo:
                                logger.info(f"🔍 CPU Legacy detectada: {marker}")
                                return True

                except FileNotFoundError:
                    logger.debug("/proc/cpuinfo no encontrado - asumiendo hardware moderno")
                except Exception as e:
                    logger.debug(f"Error leyendo cpuinfo: {e}")

            # RAM detection (cross-platform with psutil)
            try:
                import psutil
                ram_gb = psutil.virtual_memory().total / (1024**3)
                if ram_gb < 6:
                    logger.info(f"🔍 RAM limitada detectada: {ram_gb:.1f}GB < 6GB")
                    return True
            except ImportError:
                logger.debug("psutil no disponible - saltando detección de RAM")
            except Exception as e:
                logger.debug(f"Error detectando RAM: {e}")

        except Exception as e:
            logger.warning(f"Error en detección de hardware: {e}")

        # Default: assume modern hardware (conservative approach)
        logger.info("✅ Hardware moderno detectado o no pudo determinarse - video habilitado")
        return False

    def _update_background(self) -> None:
        """
        Update VisualBackground based on current video mode.

        Creates appropriate background instance for current mode:
        - "full" → VideoLyricsBackground (sync with audio)
        - "loop" → VideoLoopBackground (continuous loop)
        - "static" → StaticFrameBackground (frozen frame)
        - "none" → BlankBackground (no video)
        """
        # Stop current background if exists
        if self.background and self.engine:
            try:
                self.background.stop(self.engine)
            except Exception as e:
                logger.warning(f"Error stopping old background: {e}")

        # Create new background based on mode
        if self._video_mode == "full":
            self.background = VideoLyricsBackground(sync_controller=self.sync_controller)
            logger.debug("📹 Background: VideoLyricsBackground (full sync)")

        elif self._video_mode == "loop":
            self.background = VideoLoopBackground()
            logger.debug("🔄 Background: VideoLoopBackground (continuous loop)")

        elif self._video_mode == "static":
            self.background = StaticFrameBackground(static_frame_seconds=0.0)
            logger.debug("🖼️ Background: StaticFrameBackground (frozen frame)")

        elif self._video_mode == "none":
            self.background = BlankBackground()
            logger.debug("⬛ Background: BlankBackground (no video)")

        else:
            logger.error(f"❌ Unknown video mode: {self._video_mode}, using BlankBackground")
            self.background = BlankBackground()

    def is_video_enabled(self) -> bool:
        """
        Check if video is enabled (backward compatibility).

        Returns:
            True if video can be played (mode != 'none')
        """
        return self._video_mode != "none"

    def get_video_mode(self) -> str:
        """
        Get current video mode.

        Returns:
            Current mode: "full" | "loop" | "static" | "none"
        """
        return self._video_mode

    def set_video_mode(self, mode: str) -> None:
        """
        Set video playback mode.

        Args:
            mode: Video mode ("full" | "loop" | "static" | "none")
        """
        if mode not in ["full", "loop", "static", "none"]:
            logger.error(f"❌ Invalid video mode: {mode}. Using 'full' as fallback.")
            mode = "full"

        old_mode = self._video_mode
        self._video_mode = mode
        logger.info(f"🎬 Video mode changed: {old_mode} → {mode}")

        # Update background to match new mode
        self._update_background()

        # Stop playback if switching to 'none'
        if mode == "none" and self.engine.is_playing():
            self.stop()

    def enable_video(self, enable: bool = True) -> None:
        """
        DEPRECATED: Use set_video_mode() or ConfigManager instead.

        Kept for backward compatibility.

        Args:
            enable: True to enable video, False to disable
        """
        import warnings
        warnings.warn(
            "enable_video() is deprecated. Use set_video_mode() or ConfigManager instead.",
            DeprecationWarning,
            stacklevel=2
        )

        # Map to video modes for backward compatibility
        if enable:
            if self._video_mode == "none":
                config = ConfigManager.get_instance()
                restored_mode = config.get("video.mode", "full")
                self.set_video_mode(restored_mode)
        else:
            self.set_video_mode("none")

    def set_media(self, video_path: Optional[str]) -> None:
        """
        Load video file respecting configured mode.

        Args:
            video_path: Path to video file (or None)
        """
        # Sync mode from config before loading media
        current_mode = ConfigManager.get_instance().get("video.mode", "full")
        if current_mode and current_mode != self._video_mode:
            logger.info(f"📹 Updating video mode from settings: {self._video_mode} → {current_mode}")
            self.set_video_mode(current_mode)

        # If mode is 'none', skip loading
        if self._video_mode == "none":
            logger.info("📹 Video mode is 'none' - skipping video load")
            return

        # If mode is 'loop', always use loop video
        if self._video_mode == "loop":
            config = ConfigManager.get_instance()
            loop_path = config.get("video.loop_video_path", "assets/loops/default.mp4")
            video_path = loop_path
            logger.info(f"📹 Loop mode active - using loop video: {video_path}")

        # If mode is 'static', use video from multi or fallback to loop
        elif self._video_mode == "static":
            if video_path is None or not Path(video_path).exists():
                logger.warning(f"📹 No video file for static mode: {video_path}")
                config = ConfigManager.get_instance()
                loop_path = config.get("video.loop_video_path", "assets/loops/default.mp4")
                video_path = loop_path
                logger.info(f"📹 Fallback to loop for static frame: {video_path}")

        # If mode is 'full', use video from multi or fallback to loop
        elif self._video_mode == "full":
            if video_path is None or not Path(video_path).exists():
                logger.warning(f"📹 Multi has no video file: {video_path}")
                logger.info("🔄 Switching to 'loop' mode and loading default loop")
                self.set_video_mode("loop")
                config = ConfigManager.get_instance()
                loop_path = config.get("video.loop_video_path", "assets/loops/default.mp4")
                video_path = loop_path
                logger.info(f"📹 Using loop video: {video_path}")

        # REFACTORED: Delegate to engine
        if self.engine.is_playing():
            self.engine.stop()
            app_state.video_is_playing = False
            logger.debug("Engine stopped before loading new media")

        self.engine.load(str(video_path))
        logger.debug(f"📹 Video loaded: {video_path} (mode: {self._video_mode})")

    def show_window(self) -> None:
        """
        Show video window on secondary screen.

        Initializes window on correct screen first time,
        then simply shows/hides as needed.
        """
        if not self._window_initialized:
            # First time: initialize window and attach engine
            logger.debug("Initializing video window for first time")
            self.show()  # Create windowHandle
            QTimer.singleShot(50, self._initialize_window)
        else:
            # Already initialized: just show
            logger.debug("Showing video window")
            if self._is_fallback_mode:
                # Windowed mode: show normal (not fullscreen)
                self.showNormal()
            else:
                # Secondary screen: fullscreen
                self.showFullScreen()

    def hide_window(self) -> None:
        """
        Hide video window without destroying engine.

        Window remains hidden but engine maintains attachment,
        avoiding reinitialization bugs.
        """
        logger.debug("Hiding video window")
        self.hide()

    def _initialize_window(self) -> None:
        """
        Initialize window on correct screen and attach engine.

        Called only first time window is shown.
        """
        self.move_to_screen()
        self._window_initialized = True
        logger.debug("Video window initialized")

    def move_to_screen(self) -> None:
        """
        Move window to secondary screen and attach engine.

        If secondary screen doesn't exist, fallback to 16:9 windowed mode
        on primary screen.
        """
        screens = QApplication.screens()
        logger.info(f"📺 Pantallas detectadas: {len(screens)}")
        for i, screen in enumerate(screens):
            dpi = screen.logicalDotsPerInch()
            size = screen.geometry()
            logger.info(f"  [{i}] {screen.name()} - Resolución: {size.width()}x{size.height()} @ {dpi} DPI")

        # FALLBACK: If secondary screen doesn't exist, use primary in windowed mode
        if self.screen_index >= len(screens):
            logger.warning(
                f"⚠️ Pantalla {self.screen_index} no disponible (solo hay {len(screens)}). "
                f"Usando modo ventana 16:9 en pantalla primaria."
            )
            self._is_fallback_mode = True
            target_screen = screens[0]  # Primary screen

            # Calculate 16:9 geometry centered (80% of screen width)
            primary_geo = target_screen.geometry()
            video_width = int(primary_geo.width() * 0.8)
            video_height = int(video_width * 9 / 16)  # 16:9 ratio

            # Center on primary screen
            x = primary_geo.x() + (primary_geo.width() - video_width) // 2
            y = primary_geo.y() + (primary_geo.height() - video_height) // 2

            logger.info(
                f"📐 Modo ventana: {video_width}x{video_height} @ ({x},{y}) "
                f"en {target_screen.name()}"
            )

            self._target_screen = target_screen

            # Configure window in normal mode (not fullscreen)
            if self.windowHandle() is None:
                self.setAttribute(Qt.WA_NativeWindow, True)
            handle = self.windowHandle()
            if handle is not None:
                try:
                    handle.setScreen(target_screen)
                    logger.info(f"✓ Screen assigned via windowHandle: {target_screen.name()}")
                except Exception as e:
                    logger.warning(f"⚠ Could not assign screen via windowHandle: {e}")

            self.setGeometry(x, y, video_width, video_height)
            self.show()
            QTimer.singleShot(100, self._attach_engine_to_window)
            return

        # NORMAL: Secondary screen exists, use fullscreen
        self._is_fallback_mode = False
        target_screen = screens[self.screen_index]
        self._target_screen = target_screen
        geo = target_screen.geometry()
        logger.info(f"✓ Moving window to screen {self.screen_index}: {geo.x()},{geo.y()} {geo.width()}x{geo.height()}")

        # Ensure window moves BEFORE attaching engine
        if self.windowHandle() is None:
            self.setAttribute(Qt.WA_NativeWindow, True)
        handle = self.windowHandle()
        if handle is not None:
            try:
                handle.setScreen(target_screen)
                logger.info(f"✓ Screen assigned via windowHandle: {target_screen.name()}")
            except Exception as e:
                logger.warning(f"⚠ Could not assign screen via windowHandle: {e}")
        else:
            logger.warning("⚠ windowHandle() not available; continuing with setGeometry")

        self.setGeometry(geo)
        self.show()  # Call show() before showFullScreen() to ensure valid winId()
        QTimer.singleShot(100, self._attach_engine_to_window)

    def _attach_engine_to_window(self) -> None:
        """
        Attach engine to window after it's fully initialized.

        REFACTORED: Delegates to engine.attach_to_window()
        """
        try:
            # Reaffirm target screen before attaching/entering fullscreen
            handle = self.windowHandle()
            if handle is not None and self._target_screen is not None:
                try:
                    handle.setScreen(self._target_screen)
                    logger.info(f"✓ Screen reaffirmed: {self._target_screen.name()}")
                except Exception as e:
                    logger.warning(f"⚠ Could not reaffirm screen: {e}")

            # Ensure window is visible before attachment
            if not self.isVisible():
                logger.warning("⚠ Window not visible before engine attachment")
                self.show()

            # REFACTORED: Delegate to engine
            win_id = int(self.winId())
            screen_index = self.screen_index if self._target_screen else None
            fullscreen = not self._is_fallback_mode
            self.engine.attach_window(win_id, screen_index, fullscreen)

            # Finally, show window (fullscreen only if NOT fallback mode)
            handle = self.windowHandle()
            if handle is not None and self._target_screen is not None:
                try:
                    handle.setScreen(self._target_screen)
                except Exception:
                    pass

            if self._is_fallback_mode:
                # Windowed mode: NO fullscreen
                self.showNormal()
                logger.info("✓ Window in normal 16:9 mode (fallback)")
            else:
                # Secondary screen: fullscreen
                self.showFullScreen()
                logger.info("✓ Window in fullscreen")

        except Exception as e:
            logger.error(f"❌ Error attaching engine: {e}", exc_info=True)

    def start_playback(self, audio_time_seconds: float = 0.0, offset_seconds: float = 0.0) -> None:
        """
        Start playback with initial offset.

        Args:
            audio_time_seconds: Current audio time (for seeks/resume)
            offset_seconds: Offset from metadata (video_offset_seconds)
                           Positive = video starts after audio
                           Negative = video starts before audio

        REFACTORED: Delegates to background.start()
        """
        # Handle 'none' mode
        if self._video_mode == "none":
            logger.debug("📹 Video mode is 'none' - skipping playback")
            return

        # Only play if window is visible (user activated show_video_btn)
        if not self.isVisible():
            logger.debug("📹 Video window hidden - skipping video playback (audio continues)")
            return

        logger.debug(f"⏯ Starting video playback in '{self._video_mode}' mode...")
        # Audio muted via engine's --no-audio flag (no need for set_mute)

        # REFACTORED: Delegate to background
        if self.background:
            self.background.start(self.engine, audio_time_seconds, offset_seconds)
            app_state.video_is_playing = True

            # Start position reporting timer
            self.position_timer.start()
        else:
            logger.error("❌ No background set - cannot start playback")

    def stop(self) -> None:
        """
        Stop playback and sync.

        REFACTORED: Delegates to background.stop()
        """
        app_state.video_is_playing = False

        # REFACTORED: Delegate to background
        if self.background:
            self.background.stop(self.engine)

        self.position_timer.stop()

    def pause(self) -> None:
        """
        Pause playback.

        REFACTORED: Delegates to background.pause()
        """
        app_state.video_is_playing = False

        # REFACTORED: Delegate to background
        if self.background:
            self.background.pause(self.engine)

        self.position_timer.stop()

    def seek_seconds(self, seconds: float) -> None:
        """
        Seek video to specified time in seconds.

        Handles edge cases like seeking after video ended.
        Preserves pause state.

        Args:
            seconds: Target position in seconds
        """
        if not self.engine:
            return

        current_time_seconds = self.engine.get_time()

        with safe_operation(f"Seeking video to {seconds:.2f}s", silent=True):
            logger.info(f"[VIDEO_SEEK] from={current_time_seconds:.3f}s to={seconds:.3f}s delta={seconds - current_time_seconds:+.3f}s")

            # Check playback state BEFORE seek
            was_playing = self.engine.is_playing()

            # Simple seek (engine handles state management)
            self.engine.seek(seconds)

            # Preserve pause state after seek
            if not was_playing:
                # VLC sometimes auto-resumes after set_time() - force pause
                QTimer.singleShot(50, lambda: self._ensure_paused())
                logger.debug("Video was paused - preserving pause state after seek")

    def _ensure_paused(self) -> None:
        """
        Ensure engine remains paused after seek.

        VLC sometimes auto-resumes after set_time() on certain platforms.
        """
        if self.engine and self.engine.is_playing():
            self.engine.pause()
            logger.debug("Enforced pause state after seek (engine auto-resumed)")

    def _report_position(self) -> None:
        """
        Report position to background for updates.

        Called periodically by position_timer (50ms).

        REFACTORED: Delegates to background.update()
        """
        if self.background and self.engine:
            # Get current audio time from PlaybackManager (if available)
            # FIXED: No longer hardcoded to 0.0
            audio_time = 0.0
            if self.sync_controller:
                # SyncController tracks audio time internally via AudioClock
                # Backgrounds can use sync_controller.audio_clock if they need precise timing
                pass  # Background implementations use sync_controller directly

            self.background.update(self.engine, audio_time)

    @Slot(dict)
    def apply_correction(self, correction: dict) -> None:
        """
        Apply sync correction from SyncController.

        Args:
            correction: Correction dict with type and parameters

        REFACTORED: Delegates to background.apply_correction()
        """
        if self.background and self.engine:
            self.background.apply_correction(self.engine, correction)

    def _on_video_end(self) -> None:
        """
        Handle video end event from engine.

        REFACTORED: Delegates to background.on_video_end()
        """
        logger.info(f"[VLC_EVENT] Video ended (mode: {self._video_mode})")

        if self.background and self.engine:
            self.background.on_video_end(self.engine)

    def closeEvent(self, event) -> None:
        """
        Intercept window close to prevent resource destruction.

        Instead of closing, hide window and notify main.py to sync
        show_video_btn state.

        IMPORTANT: Don't pause or stop video because audio engine
        continues running and timeline needs position updates.
        """
        logger.debug("🚪 Intercepting window close (X button) - hiding without stopping")

        # Emit signal to sync button
        self.window_closed.emit()

        # Simply hide window without touching playback
        # Video continues playing in background
        # position_timer remains active to update timeline
        self.hide()

        # IMPORTANT: Ignore close event to prevent destruction
        event.ignore()
