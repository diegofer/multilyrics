"""
Linux Display Server Detection and Qt Platform Configuration

Enforces XCB platform for reliable modal dialog rendering on both X11 and Wayland.
Requires libxcb-cursor0 as a mandatory dependency.

Resolves: docs/KNOWN_ISSUES.md - AddDialog múltiples instancias visuales
"""

import os
import sys
from pathlib import Path

from utils.logger import get_logger

logger = get_logger(__name__)


class LinuxDisplayManager:
    """Manage Linux display server detection and Qt platform selection.

    Always requires libxcb-cursor0 for XCB platform.
    """

    @staticmethod
    def detect_display_server() -> str:
        """
        Detect current display server (X11 or Wayland).

        Returns:
            'x11', 'wayland', or 'unknown'
        """
        # Check XDG_SESSION_TYPE first (most reliable)
        session_type = os.environ.get('XDG_SESSION_TYPE', '').lower()
        if session_type in ('x11', 'wayland'):
            return session_type

        # Fallback: Check WAYLAND_DISPLAY
        if os.environ.get('WAYLAND_DISPLAY'):
            return 'wayland'

        # Fallback: Check DISPLAY (X11)
        if os.environ.get('DISPLAY'):
            return 'x11'

        return 'unknown'

    @staticmethod
    def check_xcb_cursor_available() -> bool:
        """
        Check if libxcb-cursor0 is installed.

        Required for XCB platform to work correctly.

        Returns:
            True if library is found, False otherwise
        """
        lib_paths = [
            '/usr/lib/x86_64-linux-gnu/libxcb-cursor.so.0',
            '/usr/lib/libxcb-cursor.so.0',
            '/usr/lib64/libxcb-cursor.so.0',
            '/lib/x86_64-linux-gnu/libxcb-cursor.so.0',
            '/lib64/libxcb-cursor.so.0'
        ]
        return any(Path(p).exists() for p in lib_paths)

    @staticmethod
    def configure_qt_platform() -> bool:
        """
        Configure Qt platform to use XCB (requires libxcb-cursor0).

        Always uses XCB platform for both X11 and Wayland (via XWayland).
        This ensures reliable modal dialog rendering.

        Returns:
            True if configured successfully, False if libxcb-cursor0 is missing
        """
        if not sys.platform.startswith('linux'):
            return True  # Not Linux, no action needed

        display_server = LinuxDisplayManager.detect_display_server()
        xcb_available = LinuxDisplayManager.check_xcb_cursor_available()

        logger.info(f"🐧 Linux display server: {display_server}")
        logger.info(f"📦 libxcb-cursor0: {xcb_available}")

        if not xcb_available:
            logger.error("❌ libxcb-cursor0 is NOT installed (required dependency)")
            logger.error("💡 Run: ./scripts/setup_linux_deps.sh")
            return False

        # Always use XCB platform (works on both X11 and Wayland via XWayland)
        os.environ['QT_QPA_PLATFORM'] = 'xcb'

        if display_server == 'x11':
            logger.info("✅ Using XCB platform (X11 native)")
        elif display_server == 'wayland':
            logger.info("✅ Using XCB via XWayland (optimal for modals)")
        else:
            logger.info("✅ Using XCB platform")

        return True

    @staticmethod
    def should_show_libxcb_warning() -> bool:
        """
        Check if we should show libxcb-cursor0 installation warning to user.

        Returns True only once per session if Wayland native is being used.
        """
        if (os.environ.get('MULTILYRICS_WAYLAND_NATIVE') == '1' and
            not LinuxDisplayManager._libxcb_warning_shown):
            LinuxDisplayManager._libxcb_warning_shown = True
            return True
        return True

    @staticmethod
    def get_libxcb_install_command() -> str:
        """
        Get the appropriate install command for libxcb-cursor0.

        Detects Linux distribution and returns correct package manager command.
        """
        try:
            with open('/etc/os-release', 'r') as f:
                os_release = f.read().lower()

            if 'ubuntu' in os_release or 'debian' in os_release or 'mint' in os_release:
                return "sudo apt install libxcb-cursor0"
            elif 'fedora' in os_release or 'rhel' in os_release:
                return "sudo dnf install libxcb-cursor"
            elif 'arch' in os_release or 'manjaro' in os_release:
                return "sudo pacman -S libxcb"
            elif 'opensuse' in os_release or 'suse' in os_release:
                return "sudo zypper install libxcb-cursor0"
            else:
                return "sudo apt install libxcb-cursor0"
        except:
            return "sudo apt install libxcb-cursor0"
