"""
Multi Lyrics - Latency Monitor Widget
Copyright (C) 2026 Diego Fernando

Optional debug widget to display real-time audio callback latency statistics.
Enable in Settings → Audio → Show Latency Monitor (debug mode).

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from ui.styles import StyleManager


class LatencyMonitor(QWidget):
    """
    Lightweight widget to display audio callback latency statistics.
    Updates every 500ms to avoid UI overhead.

    Color coding:
    - Green: Usage < 50% (healthy)
    - Orange: Usage 50-80% (acceptable)
    - Red: Usage > 80% (critical, xruns likely)
    """

    def __init__(self, engine, parent=None):
        """
        Args:
            engine: MultiTrackPlayer instance to monitor
            parent: Parent widget (optional)
        """
        super().__init__(parent)
        self.engine = engine
        self.init_ui()

        # Update timer (500ms refresh rate)
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_stats)
        self.update_timer.start(500)  # 2 Hz update rate

    def init_ui(self):
        """Initialize UI layout and labels."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(2)

        # Title label
        title_label = QLabel("🎛️ Audio Engine Stats")
        title_font = StyleManager.get_font()
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet(f"color: {StyleManager.get_color('text_primary')};")
        layout.addWidget(title_label)

        # Stats label (monospace for alignment)
        self.stats_label = QLabel("Waiting for playback...")
        stats_font = QFont("Courier New", 9)  # Monospace font
        self.stats_label.setFont(stats_font)
        self.stats_label.setWordWrap(False)
        layout.addWidget(self.stats_label)

        # Set background
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {StyleManager.get_color('surface_dark')};
                border: 1px solid {StyleManager.get_color('border_subtle')};
                border-radius: 4px;
            }}
        """)

    def update_stats(self):
        """Update displayed statistics from engine."""
        if not self.engine:
            return

        try:
            stats = self.engine.get_latency_stats()

            if stats['total_callbacks'] == 0:
                self.stats_label.setText("⏸️  No playback activity")
                self.stats_label.setStyleSheet(f"color: {StyleManager.get_color('text_secondary')};")
                return

            # Determine color based on usage percentage
            usage_pct = stats['usage_pct']
            if usage_pct < 50:
                color = "#00FF7F"  # Green (healthy)
                status = "✓"
            elif usage_pct < 80:
                color = "#FFA500"  # Orange (acceptable)
                status = "⚠"
            else:
                color = "#FF4444"  # Red (critical)
                status = "✗"

            # Format stats text
            text = (
                f"{status} Avg: {stats['mean_ms']:.2f}ms | "
                f"Peak: {stats['max_ms']:.2f}ms | "
                f"Budget: {stats['budget_ms']:.2f}ms\n"
                f"Usage: {usage_pct:.1f}% | "
                f"Xruns: {stats['xruns']} | "
                f"Callbacks: {stats['total_callbacks']}"
            )

            self.stats_label.setText(text)
            self.stats_label.setStyleSheet(f"color: {color};")

        except Exception as e:
            self.stats_label.setText(f"❌ Error reading stats: {e}")
            self.stats_label.setStyleSheet(f"color: {StyleManager.get_color('error')};")

    def closeEvent(self, event):
        """Stop timer when widget is closed."""
        self.update_timer.stop()
        super().closeEvent(event)
