"""
Multi Lyrics - Track Widget
Copyright (C) 2026 Diego Fernando

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QLabel, QPushButton, QSlider, QVBoxLayout,
                               QWidget)

from utils.helpers import get_logarithmic_volume


class TrackWidget(QWidget):
    """Track mixer strip widget with dependency injection pattern.

    Receives AudioEngine reference directly to eliminate intermediary code.
    Master track receives both engine and timeline_view for dual control:
    - AudioEngine.set_master_gain() for audio output
    - TimelineView.set_volume() for waveform preview
    """

    def __init__(self, track_name: str = "Track 0", track_index: int = 0,
                 engine: Optional[object] = None, is_master: bool = False,
                 timeline_view: Optional[object] = None, parent=None):
        super().__init__(parent)
        self.track_name = track_name
        self.track_index = track_index
        self.engine = engine
        self.is_master = is_master
        self.timeline_view = timeline_view  # For master track preview volume
        self.setFixedWidth(70)
        self.init_ui()
        self._connect_signals()
        self._initialize_volumes()  # Initialize engine/timeline with slider's initial value

    def _initialize_volumes(self):
        """Initialize audio engine and timeline with slider's initial value."""
        if self.is_master:
            # Master track: initialize both engine and timeline with slider value (70%)
            self._on_master_volume_changed(self.slider.value())
        else:
            # Individual tracks: apply logarithmic volume to engine (90% → -6 dB → 0.5 gain)
            # This ensures tracks start at the intended level, not at engine's default unity (1.0)
            # Only initialize if engine has tracks loaded (gain arrays exist)
            if self.engine and hasattr(self.engine, 'target_gains') and len(self.engine.target_gains) > self.track_index:
                self._on_volume_changed(self.slider.value())

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Centrar horizontalmente
        layout.setContentsMargins(0, 0, 0, 0)

        # Botón de mute
        self.mute_button = QPushButton("Mute")
        self.mute_button.setCheckable(True)
        layout.addWidget(self.mute_button)

        # Botón de solo
        self.solo_button = QPushButton("Solo")
        self.solo_button.setCheckable(True)
        if not self.is_master:
            layout.addWidget(self.solo_button)

        # Slider vertical
        self.slider = QSlider(Qt.Vertical)
        self.slider.setStyleSheet("""
            QSlider::groove:vertical {
                background: #444;
                width: 6px;
                border-radius: 3px;
            }

            QSlider::handle:vertical {
                image: url(assets/img/cash-solid.svg);
                height: 32px;
                width: 32px;
                margin: -14px;  /* centra el knob sobre el groove */
            }

        """)

        self.slider.setRange(0, 100)
        # Master track: 70% (-18 dB) for headroom (professional mixer standard)
        # Individual tracks: 90% (-6 dB) for live worship context
        # - Leaves +6 dB headroom upward for emphasizing bass/drums during service
        # - Pre-balanced stems remain clear while allowing dynamic adjustments
        # - Matches behavior of live playback tools (WorshipSongBand, etc.)
        initial_value = 70 if self.is_master else 90
        self.slider.setValue(initial_value)
        #self.slider.setStyleSheet("QSlider::handle { width: 50px; height: 20px; }")
        layout.addWidget(self.slider, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Título del instrumento
        self.label = QLabel(self.track_name)
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)

        self.setLayout(layout)

    def _connect_signals(self):
        """Connect internal signals to engine methods (Dependency Injection pattern)."""
        if self.is_master:
            # Master track: connect slider to dual control (preview + audio gain)
            self.slider.valueChanged.connect(self._on_master_volume_changed)
            # Master track also needs mute button (mute master uses track_index=0)
            if self.engine:
                self.mute_button.toggled.connect(lambda checked: self._on_mute_toggled_master(checked))
        else:
            # Individual tracks: connect directly to engine
            if self.engine:
                self.mute_button.toggled.connect(self._on_mute_toggled)
                self.solo_button.toggled.connect(self._on_solo_toggled)
                self.slider.valueChanged.connect(self._on_volume_changed)

    def _on_master_volume_changed(self, value: int):
        """Handle master volume slider (controls both preview and audio gain)."""
        gain = get_logarithmic_volume(value)

        # Update waveform preview volume (expects slider int)
        if self.timeline_view:
            self.timeline_view.set_volume(value)

        # Set global master gain on audio player
        if self.engine:
            self.engine.set_master_gain(gain)

    def _on_mute_toggled(self, checked: bool):
        """Handle mute button toggle."""
        if self.engine:
            self.engine.mute(self.track_index, checked)

    def _on_mute_toggled_master(self, checked: bool):
        """Handle master track mute button toggle (always uses track_index=0)."""
        if self.engine:
            self.engine.mute(0, checked)  # Master track is always at index 0

    def _on_solo_toggled(self, checked: bool):
        """Handle solo button toggle."""
        if self.engine:
            self.engine.solo(self.track_index, checked)

    def _on_volume_changed(self, value: int):
        """Handle volume slider change (converts to logarithmic gain)."""
        if self.engine:
            gain_log = get_logarithmic_volume(value)
            self.engine.set_gain(self.track_index, gain_log)
