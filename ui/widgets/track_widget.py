from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSlider, QPushButton
from PySide6.QtCore import Qt, Signal
from typing import Optional
from utils.helpers import get_logarithmic_volume


class TrackWidget(QWidget):
    """Track mixer strip widget with dependency injection pattern.

    Receives AudioEngine reference directly to eliminate intermediary code.
    For master track, engine is optional (volume handled by parent).
    """

    # Master track still emits signal (handled by MainWindow for preview volume)
    volume_changed = Signal(int)

    def __init__(self, track_name: str = "Track 0", track_index: int = 0,
                 engine: Optional[object] = None, is_master: bool = False, parent=None):
        super().__init__(parent)
        self.track_name = track_name
        self.track_index = track_index
        self.engine = engine
        self.is_master = is_master
        self.setFixedWidth(70)
        self.init_ui()
        self._connect_signals()

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
        # Master track starts at 70% for headroom (like professional mixers)
        # Individual tracks start at 100% (unity gain)
        initial_value = 70 if self.is_master else 100
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
            # Master track: emit signal for MainWindow to handle preview volume + master gain
            self.slider.valueChanged.connect(lambda value: self.volume_changed.emit(value))
        else:
            # Individual tracks: connect directly to engine
            if self.engine:
                self.mute_button.toggled.connect(self._on_mute_toggled)
                self.solo_button.toggled.connect(self._on_solo_toggled)
                self.slider.valueChanged.connect(self._on_volume_changed)

    def _on_mute_toggled(self, checked: bool):
        """Handle mute button toggle."""
        if self.engine:
            self.engine.mute(self.track_index, checked)

    def _on_solo_toggled(self, checked: bool):
        """Handle solo button toggle."""
        if self.engine:
            self.engine.solo(self.track_index, checked)

    def _on_volume_changed(self, value: int):
        """Handle volume slider change (converts to logarithmic gain)."""
        if self.engine:
            gain_log = get_logarithmic_volume(value)
            self.engine.set_gain(self.track_index, gain_log)
