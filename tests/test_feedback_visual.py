"""
Tests for message helpers and toast notifications.

These tests verify that feedback visual components can be created
and displayed without errors.
"""

import pytest
from PySide6.QtWidgets import QMainWindow
from ui import message_helpers
from ui.widgets.toast_notification import ToastNotification, ToastType


@pytest.fixture
def main_window(qtbot):
    """Create a simple main window for testing"""
    window = QMainWindow()
    qtbot.addWidget(window)
    window.show()
    return window


class TestMessageHelpers:
    """Test suite for message_helpers functions"""
    
    def test_show_info_toast(self, main_window, qtbot):
        """Can create and display info toast"""
        toast = message_helpers.show_info_toast(
            main_window,
            "Test info message",
            duration_ms=1000
        )
        # Toast should be created and visible
        assert toast is not None
    
    def test_show_success_toast(self, main_window, qtbot):
        """Can create and display success toast"""
        toast = message_helpers.show_success_toast(
            main_window,
            "Test success message",
            duration_ms=1000
        )
        assert toast is not None
    
    def test_show_warning_toast(self, main_window, qtbot):
        """Can create and display warning toast"""
        toast = message_helpers.show_warning_toast(
            main_window,
            "Test warning message",
            duration_ms=1000
        )
        assert toast is not None
    
    def test_show_error_toast(self, main_window, qtbot):
        """Can create and display error toast"""
        toast = message_helpers.show_error_toast(
            main_window,
            "Test error message",
            duration_ms=1000
        )
        assert toast is not None


class TestToastNotification:
    """Test suite for ToastNotification widget"""
    
    def test_toast_types_exist(self):
        """All toast types are defined"""
        assert hasattr(ToastType, 'SUCCESS')
        assert hasattr(ToastType, 'INFO')
        assert hasattr(ToastType, 'WARNING')
        assert hasattr(ToastType, 'ERROR')
    
    def test_toast_styles_configured(self):
        """Toast styles are configured for all types"""
        for toast_type in ToastType:
            assert toast_type in ToastNotification.TOAST_STYLES
            style = ToastNotification.TOAST_STYLES[toast_type]
            assert 'bg_color' in style
            assert 'text_color' in style
            assert 'icon' in style
    
    def test_create_toast_notification(self, main_window, qtbot):
        """Can create toast notification widget"""
        toast = ToastNotification(
            main_window,
            "Test message",
            ToastType.INFO,
            3000
        )
        qtbot.addWidget(toast)
        assert toast.message == "Test message"
        assert toast.toast_type == ToastType.INFO
        assert toast.duration_ms == 3000
    
    def test_toast_class_methods(self, main_window, qtbot):
        """Toast class methods work correctly"""
        # Test all class methods
        success_toast = ToastNotification.show_success(main_window, "Success", 1000)
        qtbot.addWidget(success_toast)
        
        info_toast = ToastNotification.show_info(main_window, "Info", 1000)
        qtbot.addWidget(info_toast)
        
        warning_toast = ToastNotification.show_warning(main_window, "Warning", 1000)
        qtbot.addWidget(warning_toast)
        
        error_toast = ToastNotification.show_error(main_window, "Error", 1000)
        qtbot.addWidget(error_toast)
        
        # All should be created
        assert success_toast is not None
        assert info_toast is not None
        assert warning_toast is not None
        assert error_toast is not None
