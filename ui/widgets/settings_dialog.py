"""
Multi Lyrics - Settings Dialog
Copyright (C) 2026 Diego Fernando

Application settings and preferences dialog.
Includes audio configuration and debug options.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import json
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QGroupBox,
                               QHBoxLayout, QLabel, QPushButton, QVBoxLayout)

from core.config_manager import ConfigManager
from ui.styles import StyleManager
from utils.logger import get_logger

logger = get_logger(__name__)


class SettingsDialog(QDialog):
    """Settings dialog for application preferences."""

    def __init__(self, parent=None):
        """
        Initialize settings dialog.

        Args:
            parent: Parent widget (MainWindow)
        """
        super().__init__(parent)
        self.parent_window = parent
        self.config = ConfigManager.get_instance()  # Use ConfigManager singleton

        self.setWindowTitle("Settings - Multi Lyrics")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setMinimumHeight(300)

        self.init_ui()
        self.load_current_settings()

    def _load_settings(self) -> dict:
        """Load settings from ConfigManager (deprecated - use ConfigManager directly)."""
        # For backwards compatibility, but ConfigManager is the source of truth
        return self.config.get_all()

    def _save_settings(self):
        """Save settings via ConfigManager (deprecated - use ConfigManager directly)."""
        # For backwards compatibility, but ConfigManager handles persistence
        self.config.save()

    def init_ui(self):
        """Initialize UI layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)

        # ===== Audio Settings Group =====
        audio_group = QGroupBox("Audio Settings")
        audio_layout = QVBoxLayout()

        # Profile info (read-only display)
        if hasattr(self.parent_window, 'current_audio_profile'):
            profile = self.parent_window.current_audio_profile
            profile_label = QLabel(
                f"🎛️ Active Profile: <b>{profile.name}</b><br>"
                f"<span style='color: {StyleManager.get_color('text_dim').name()}; font-size: 10px;'>"
                f"{profile.description}</span>"
            )
            profile_label.setWordWrap(True)
            audio_layout.addWidget(profile_label)

        # Latency Monitor checkbox (controls enable_latency_monitor: STEP 2 audio callback data collection)
        self.latency_monitor_checkbox = QCheckBox("Enable Latency Monitoring")
        self.latency_monitor_checkbox.setToolTip(
            "Enable real-time latency stats collection in audio callback (debug mode). When enabled, shows statistics in the monitor widget."
        )
        self.latency_monitor_checkbox.stateChanged.connect(self._on_latency_monitor_changed)
        audio_layout.addWidget(self.latency_monitor_checkbox)

        audio_group.setLayout(audio_layout)
        main_layout.addWidget(audio_group)

        # ===== Video Settings Group =====
        video_group = QGroupBox("Video Settings (Global)")
        video_layout = QVBoxLayout()

        # Display recommended mode with hardware info
        recommended_mode = self.config.get("video.recommended_mode", "full")
        mode_display_names = {
            "full": "Full Video",
            "loop": "Loop Background",
            "static": "Static Frame",
            "none": "None (Audio Only)"
        }
        recommended_display = mode_display_names.get(recommended_mode, "Full Video")

        recommended_label = QLabel(
            f"👍 Recommended for your hardware: <b>{recommended_display}</b>"
        )
        recommended_label.setStyleSheet(f"color: {StyleManager.get_color('text_dim').name()}; font-size: 10px;")
        video_layout.addWidget(recommended_label)

        # Video mode selector
        mode_label = QLabel("Video Mode:")
        self.video_mode_combo = QComboBox()
        self.video_mode_combo.addItems(["Full Video", "Loop Background", "Static Frame", "None (Audio Only)"])
        self.video_mode_combo.currentIndexChanged.connect(self._on_video_mode_changed)
        video_layout.addWidget(mode_label)
        video_layout.addWidget(self.video_mode_combo)

        # Warning label (initially hidden)
        self.video_warning_label = QLabel(
            "⚠️ This mode may cause performance issues on your hardware. "
            "Consider using the recommended mode for best experience."
        )
        self.video_warning_label.setWordWrap(True)
        self.video_warning_label.setStyleSheet(f"""
            background-color: {StyleManager.get_color('warning_bg').name()};
            color: {StyleManager.get_color('warning_text').name()};
            padding: 8px;
            border-radius: 4px;
            border: 1px solid {StyleManager.get_color('warning_border').name()};
        """)
        self.video_warning_label.hide()  # Hidden by default
        video_layout.addWidget(self.video_warning_label)

        # Loop video info (read-only for now, preview selector coming later)
        loop_info_label = QLabel("Current Loop Background:")
        loop_info_label.setStyleSheet(f"color: {StyleManager.get_color('text_dim').name()}; font-size: 10px; margin-top: 8px;")
        video_layout.addWidget(loop_info_label)

        # Display current loop path
        current_loop = self.config.get("video.loop_video_path", "assets/loops/default.mp4")
        self.loop_path_label = QLabel(f"📹 {current_loop}")
        self.loop_path_label.setStyleSheet(f"color: {StyleManager.get_color('text_bright').name()}; font-size: 10px; padding: 4px;")
        self.loop_path_label.setWordWrap(True)
        video_layout.addWidget(self.loop_path_label)

        video_group.setLayout(video_layout)
        main_layout.addWidget(video_group)

        # ===== Spacer =====
        main_layout.addStretch()

        # ===== Bottom Buttons =====
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        # Close button
        close_btn = QPushButton("Close")
        close_btn.setMinimumWidth(80)
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)

        main_layout.addLayout(button_layout)

        # Apply styles
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {StyleManager.get_color('bg_main')};
            }}
            QGroupBox {{
                color: {StyleManager.get_color('text_bright')};
                border: 1px solid {StyleManager.get_color('border_light')};
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 4px;
            }}
            QLabel {{
                color: {StyleManager.get_color('text_primary')};
            }}
            QCheckBox {{
                color: {StyleManager.get_color('text_bright')};
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 1px solid {StyleManager.get_color('border_subtle')};
                border-radius: 3px;
                background-color: {StyleManager.get_color('surface_dark')};
            }}
            QCheckBox::indicator:checked {{
                background-color: {StyleManager.get_color('accent_cyan')};
                border: 1px solid {StyleManager.get_color('accent_cyan')};
            }}
            QPushButton {{
                background-color: {StyleManager.get_color('blue_deep_medium')};
                color: {StyleManager.get_color('text_bright')};
                border: 1px solid {StyleManager.get_color('border_light')};
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {StyleManager.get_color('surface_light')};
                border: 1px solid {StyleManager.get_color('accent_cyan')};
            }}
        """)

    def load_current_settings(self):
        """Load current settings into UI controls from ConfigManager."""
        # Load enable_latency_monitor (STEP 2: audio callback data collection)
        enable_monitoring = self.config.get("audio.enable_latency_monitor", default=False)
        self.latency_monitor_checkbox.setChecked(enable_monitoring)

        # STEP 6: Load video mode
        current_mode = self.config.get("video.mode", "full")
        mode_index = {"full": 0, "loop": 1, "static": 2, "none": 3}.get(current_mode, 0)
        self.video_mode_combo.setCurrentIndex(mode_index)

        # Check if current mode matches recommended
        self._update_video_warning()

    def _on_latency_monitor_changed(self, state):
        """Handle latency monitoring checkbox change (STEP 2: enable_latency_monitor)."""
        enable_monitoring = (state == Qt.CheckState.Checked.value)

        # Update settings via ConfigManager (handles persistence automatically)
        self.config.set("audio.enable_latency_monitor", enable_monitoring)
        # When enabled, also show the monitor widget automatically
        self.config.set("audio.show_latency_monitor", enable_monitoring)

        # Apply to main window
        if self.parent_window:
            self.parent_window.set_latency_monitor_visible(enable_monitoring)

        logger.info(f"🖥️  Latency monitoring: {'ENABLED (callback collecting data)' if enable_monitoring else 'disabled'}")

    def _on_video_mode_changed(self, index):
        """Handle video mode combo box changes."""
        mode_names = ["full", "loop", "static", "none"]
        selected_mode = mode_names[index]

        # Save to config
        self.config.set("video.mode", selected_mode)
        logger.info(f"🎬 Video mode changed to: {selected_mode}")

        # Update warning visibility
        self._update_video_warning()

    def _update_video_warning(self):
        """Show/hide warning label based on selected vs recommended mode."""
        current_index = self.video_mode_combo.currentIndex()
        mode_names = ["full", "loop", "static", "none"]
        selected_mode = mode_names[current_index]

        recommended_mode = self.config.get("video.recommended_mode", "full")

        if selected_mode != recommended_mode:
            self.video_warning_label.show()
        else:
            self.video_warning_label.hide()

    @staticmethod
    def get_setting(key_path: str, default=None):
        """
        Get a setting value from ConfigManager (static convenience method).

        Args:
            key_path: Dot-separated path (e.g., "audio.show_latency_monitor")
            default: Default value if key not found

        Returns:
            Setting value or default

        Note:
            This is a convenience method. Preferred approach is:
            config = ConfigManager.get_instance()
            value = config.get("audio.show_latency_monitor", default=None)
        """
        config = ConfigManager.get_instance()
        return config.get(key_path, default=default)
