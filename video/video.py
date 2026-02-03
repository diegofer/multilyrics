"""
VisualController - Minimal orchestration of visual playback.

Responsibilities (STRICT):
- Engine initialization (MPV-first, VLC fallback)
- Window management (screens, fullscreen, attachment)
- Background activation/deactivation

Does NOT handle:
- Media loading (delegated to background)
- Playback timing (delegated to background)
- Video mode selection (delegated to caller)
- Sync corrections (delegated to background)
"""

import platform
from typing import Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget

from core.constants import app_state
from utils.logger import get_logger

# Import new architecture components
from video.engines.base import VisualEngine
from video.engines.mpv_engine import MpvEngine
from video.engines.vlc_engine import VlcEngine
from video.backgrounds.base import VisualBackground

logger = get_logger(__name__)


class VisualController(QWidget):
    """
    Minimal orchestrator for visual playback.

    Responsibilities (STRICT):
    - Engine initialization (MPV-first, VLC fallback)
    - Window management: positioning, screens, show/hide, attachment
    - Background activation: set_background() for dynamic switching

    Does NOT:
    - Load media files (background responsibility)
    - Track playback timing (background responsibility)
    - Apply sync corrections (background responsibility)
    - Manage video modes (caller responsibility)
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
        self.setWindowTitle("MultiLyrics Visual")
        self.resize(800, 600)

        # CRITICAL: Prevent window from showing until explicitly requested
        # This is essential to avoid auto-showing on song load
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnBottomHint)
        self.setAttribute(Qt.WA_DontShowOnScreen, True)  # CRITICAL: Don't render until shown
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        logger.info(f"🪟 VisualController created - Flags set to prevent auto-show")

        # Detect OS
        self.system = platform.system()
        logger.debug(f"OS detected: {self.system}")

        # LAZY INITIALIZATION: Don't create engine until show_window() is called
        # Creating engine requires winId() which forces native window creation (auto-shows on Windows)
        self.engine: Optional[VisualEngine] = None
        self._engine_initialized = False
        self._pending_video_path = None  # Store video path for lazy loading
        logger.info(f"🪟 Engine will be initialized lazily (on first show_window() call)")

        # Engine badge for visual identification
        from PySide6.QtWidgets import QLabel
        from core.config_manager import ConfigManager
        from video.engines.mpv_engine import MpvEngine

        self.engine_badge = QLabel(self)
        self.engine_badge.setStyleSheet(
            "background-color: rgba(0, 0, 0, 0.7); "
            "color: #888888; "
            "padding: 4px 8px; "
            "border-radius: 4px; "
            "font-family: monospace; "
            "font-size: 11px;"
        )

        # Set engine name
        engine_name = "MPV" if isinstance(self.engine, MpvEngine) else "VLC"
        self.engine_badge.setText(engine_name)
        logger.debug(f"🏷️ Engine badge: {engine_name}")

        # Check if badge should be shown (configurable)
        config = ConfigManager.get_instance()
        show_badge = config.get("video.show_engine_badge", True)
        self.engine_badge.setVisible(show_badge)

        # Active background (set externally via set_background())
        self.background: Optional[VisualBackground] = None

        # Layout required for QWidget
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        logger.info(f"🪟 Layout set - Window visible: {self.isVisible()}")

        # Window initialization state
        self._window_initialized = False
        self._pending_show = False  # Track if show_window() was called during init
        self._target_screen = None
        self._is_fallback_mode = False

    def _initialize_engine(self) -> VisualEngine:
        """Initialize video engine based on config preference."""
        from core.config_manager import ConfigManager

        config = ConfigManager.get_instance()
        engine_pref = config.get("video.engine", "auto")  # Default to auto (MPV→VLC fallback)

        logger.info(f"🎬 Engine preference: {engine_pref}")

        if engine_pref == "vlc":
            # Force VLC
            return self._init_vlc_engine()
        elif engine_pref == "mpv":
            # Try MPV (raise if unavailable)
            return self._init_mpv_engine(force=True)
        else:  # "auto"
            # Auto: Try MPV first, fallback to VLC
            return self._init_mpv_engine(force=False)

    def _init_mpv_engine(self, force: bool = False) -> VisualEngine:
        """Initialize MPV engine with optional fallback."""
        try:
            logger.info("Attempting to initialize MpvEngine...")
            engine = MpvEngine(is_legacy_hardware=False)
            engine.initialize()
            logger.info("✅ MpvEngine initialized successfully")
            return engine
        except (RuntimeError, OSError, ImportError) as e:
            if force:
                logger.error(f"❌ MpvEngine required but unavailable: {e}")
                raise RuntimeError("MPV engine not available") from e
            else:
                logger.warning(f"⚠️ MpvEngine unavailable: {e}")
                logger.info("Falling back to VlcEngine...")
                return self._init_vlc_engine()

    def _init_vlc_engine(self) -> VisualEngine:
        """Initialize VLC engine."""
        try:
            engine = VlcEngine(is_legacy_hardware=False)
            engine.initialize()
            logger.info("✅ VlcEngine initialized successfully")
            return engine
        except Exception as e:
            logger.error(f"❌ Failed to initialize VlcEngine: {e}")
            raise RuntimeError("No video engine available") from e

    def set_background(self, background: VisualBackground) -> None:
        """
        Set active visual background.

        Stops previous background and activates new one.

        Args:
            background: VisualBackground instance to activate
        """
        # Stop previous background
        if self.background and self.engine:
            try:
                self.background.stop(self.engine)
                logger.debug(f"Stopped previous background: {type(self.background).__name__}")
            except Exception as e:
                logger.warning(f"Error stopping previous background: {e}")

        # Activate new background
        self.background = background
        logger.info(f"✅ Background set: {type(background).__name__}")

    def show_window(self) -> None:
        """
        Show video window on secondary screen.

        Initializes window on correct screen first time,
        then simply shows/hides as needed.
        """
        import traceback
        logger.info("\n" + "="*50)
        logger.info("🪟 show_window() CALLED")
        logger.info("Call stack:")
        for line in traceback.format_stack()[-4:-1]:
            logger.info(line.strip())
        logger.info("="*50 + "\n")

        # LAZY INITIALIZATION: Create engine on first show (prevents premature winId() call)
        if not self._engine_initialized:
            logger.info("🔧 Initializing engine lazily (first time)")
            self.engine = self._initialize_engine()
            self.engine.set_end_callback(self._on_video_end)
            self._engine_initialized = True
            logger.info("✅ Engine initialized")

            # Load pending video if any
            if self._pending_video_path:
                logger.info(f"📹 Loading pending video: {self._pending_video_path}")
                self.engine.load(str(self._pending_video_path))
                logger.info("✅ Video loaded (lazy)")
                self._pending_video_path = None

        if not self._window_initialized:
            # First time: initialize window and attach engine
            logger.info("🔧 First time initialization - setting _pending_show=True")
            # CRITICAL: Allow window to be shown now
            self.setAttribute(Qt.WA_DontShowOnScreen, False)
            # Mark that we want to show after init completes
            self._pending_show = True
            # Defer initialization to avoid premature window creation
            QTimer.singleShot(50, self._initialize_window)
        else:
            # Already initialized: just show
            logger.info(f"🪟 Showing initialized window - fallback_mode: {self._is_fallback_mode}")
            if self._is_fallback_mode:
                # Windowed mode: show normal (not fullscreen)
                logger.info("📐 showNormal() called")
                self.showNormal()
            else:
                # Secondary screen: fullscreen
                logger.info("🖥️ showFullScreen() called")
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
        Shows window only if show_window() was called.
        """
        logger.info("🔧 _initialize_window() called")
        logger.info(f"   - _pending_show: {getattr(self, '_pending_show', 'NOT SET')}")
        logger.info(f"   - Current visibility: {self.isVisible()}")

        self.move_to_screen()
        self._window_initialized = True
        logger.info("✅ Window initialized (geometry set, engine attached)")

        # Only show if show_window() was explicitly called
        if hasattr(self, '_pending_show') and self._pending_show:
            self._pending_show = False
            logger.info(f"🪟 SHOWING window (_pending_show was True) - fallback: {self._is_fallback_mode}")
            if self._is_fallback_mode:
                logger.info("   → Calling showNormal()")
                self.showNormal()
            else:
                logger.info("   → Calling showFullScreen()")
                self.showFullScreen()
            logger.info(f"   → Window now visible: {self.isVisible()}")
        else:
            logger.info("✋ Window initialized but NOT shown (_pending_show was False)")
            logger.info(f"   → Window visibility: {self.isVisible()}")

    def move_to_screen(self) -> None:
        """
        Move window to secondary screen and attach engine.

        If secondary screen doesn't exist, fallback to 16:9 windowed mode
        on primary screen.
        """
        logger.info("🔧 move_to_screen() starting...")
        screens = QApplication.screens()
        logger.info(f"📺 Pantallas detectadas: {len(screens)}")
        for i, screen in enumerate(screens):
            dpi = screen.logicalDotsPerInch()
            size = screen.geometry()
            logger.info(f"  [{i}] {screen.name()} - Resolución: {size.width()}x{size.height()} @ {dpi} DPI")
        logger.info(f"🎯 Requested screen_index: {self.screen_index}")

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
            # Don't show() here - window will be shown by _initialize_window() if requested
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
        # Don't show() here - window will be shown by _initialize_window() after attachment
        QTimer.singleShot(100, self._attach_engine_to_window)

    def _attach_engine_to_window(self) -> None:
        """
        Attach engine to window after it's fully initialized.

        REFACTORED: Delegates to engine.attach_to_window()
        Does NOT show the window - that's handled by _initialize_window()
        """
        try:
            # Reaffirm target screen before attaching
            handle = self.windowHandle()
            if handle is not None and self._target_screen is not None:
                try:
                    handle.setScreen(self._target_screen)
                    logger.info(f"✓ Screen reaffirmed: {self._target_screen.name()}")
                except Exception as e:
                    logger.warning(f"⚠ Could not reaffirm screen: {e}")

            # Window doesn't need to be visible for engine attachment
            # Engine attaches to winId, visibility is controlled separately
            if not self.isVisible():
                logger.debug("Window hidden during engine attachment (correct)")

            # REFACTORED: Delegate to engine
            win_id = int(self.winId())
            screen_index = self.screen_index if self._target_screen else None
            fullscreen = not self._is_fallback_mode
            self.engine.attach_window(win_id, screen_index, fullscreen)

            logger.info("✓ Engine attached to window (visibility controlled by show_window())")

        except Exception as e:
            logger.error(f"❌ Error attaching engine: {e}", exc_info=True)



    def _on_video_end(self) -> None:
        """
        Handle video end event from engine.

        Delegates to active background for mode-specific handling.
        """
        logger.info("[ENGINE_EVENT] Video ended")

        if self.background and self.engine:
            self.background.on_video_end(self.engine)
        else:
            logger.debug("No active background - video end event ignored")

    def cleanup(self) -> None:
        """
        Release all visual resources.

        Called when:
        - Application shutting down
        - Switching songs
        - Changing visual configurations

        Note:
            This is NOT called on window close (X button).
            Window close only hides window.
        """
        logger.info("🧹 VisualController cleanup - releasing resources")

        # Release engine resources
        if self.engine:
            self.engine.shutdown()
            logger.debug("Engine released")

        logger.info("✅ VisualController cleanup complete")

    def closeEvent(self, event) -> None:
        """
        Intercept window close to prevent resource destruction.

        Instead of closing, hide window and emit signal.

        Note:
            cleanup() is NOT called here. Resources released only on
            app shutdown or song change (via main.py).
        """
        logger.debug("🚪 Window close (X button) - hiding window")

        # Emit signal to notify caller
        self.window_closed.emit()

        # Hide window without touching resources
        self.hide()

        # Ignore close event to prevent destruction
        event.ignore()
    def resizeEvent(self, event) -> None:
        """Reposition badge in top-right corner on window resize."""
        super().resizeEvent(event)
        # Position badge 10px from top-right
        badge_width = self.engine_badge.sizeHint().width()
        self.engine_badge.move(self.width() - badge_width - 10, 10)
