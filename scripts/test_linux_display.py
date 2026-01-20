#!/usr/bin/env python3
"""
Test script for Linux Display Detection System

Tests different scenarios:
1. X11 with libxcb-cursor0
2. X11 without libxcb-cursor0
3. Wayland with libxcb-cursor0
4. Wayland without libxcb-cursor0

Usage:
    python scripts/test_linux_display.py
"""

import os
import sys
from pathlib import Path
import pytest

# Skip entirely on Windows where Linux display detection is not applicable
pytestmark = pytest.mark.skipif(sys.platform.startswith("win"), reason="Linux-only display test")

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.linux_display import LinuxDisplayManager


def test_scenario(name: str, session_type: str, xcb_available: bool):
    """Test a specific display configuration scenario."""
    print(f"\n{'='*60}")
    print(f"Scenario: {name}")
    print('='*60)

    # Setup environment
    os.environ['XDG_SESSION_TYPE'] = session_type

    # Clear Qt platform to allow reconfiguration
    if 'QT_QPA_PLATFORM' in os.environ:
        del os.environ['QT_QPA_PLATFORM']
    if 'MULTILYRICS_WAYLAND_NATIVE' in os.environ:
        del os.environ['MULTILYRICS_WAYLAND_NATIVE']

    # Mock libxcb-cursor0 check
    original_check = LinuxDisplayManager.check_xcb_cursor_available
    LinuxDisplayManager.check_xcb_cursor_available = lambda: xcb_available

    try:
        # Run detection
        display = LinuxDisplayManager.detect_display_server()
        xcb_present = LinuxDisplayManager.check_xcb_cursor_available()

        print(f"Display Server: {display}")
        print(f"libxcb-cursor0: {xcb_present}")

        # Configure platform
        LinuxDisplayManager.configure_qt_platform()

        # Check results
        qt_platform = os.environ.get('QT_QPA_PLATFORM', 'default')
        wayland_native = os.environ.get('MULTILYRICS_WAYLAND_NATIVE', '0')

        print(f"Qt Platform: {qt_platform}")
        print(f"Wayland Native Flag: {wayland_native}")

        # Verify expected behavior
        if session_type == 'x11' and xcb_available:
            assert qt_platform == 'xcb', "Should use XCB on X11 with libxcb"
            print("✅ PASS: Correctly using XCB on X11")

        elif session_type == 'wayland' and xcb_available:
            assert qt_platform == 'xcb', "Should use XCB via XWayland"
            print("✅ PASS: Correctly using XCB via XWayland")

        elif session_type == 'wayland' and not xcb_available:
            assert qt_platform == 'wayland', "Should use Wayland native"
            assert wayland_native == '1', "Should set workaround flag"
            print("✅ PASS: Correctly using Wayland native + workaround")

        else:
            print(f"⚠️  WARNING: Unexpected configuration")

    finally:
        # Restore original check
        LinuxDisplayManager.check_xcb_cursor_available = original_check


def main():
    """Run all test scenarios."""
    print("Linux Display Detection System - Test Suite")
    print("=" * 60)

    scenarios = [
        ("X11 + libxcb-cursor0 (Ubuntu/Mint default)", "x11", True),
        ("X11 without libxcb-cursor0 (edge case)", "x11", False),
        ("Wayland + libxcb-cursor0 (optimal)", "wayland", True),
        ("Wayland without libxcb-cursor0 (workaround)", "wayland", False),
    ]

    for name, session, xcb in scenarios:
        test_scenario(name, session, xcb)

    print("\n" + "="*60)
    print("✅ All scenarios tested successfully!")
    print("="*60)


if __name__ == '__main__':
    main()
