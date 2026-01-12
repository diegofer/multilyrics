from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSlider, QPushButton
from PySide6.QtCore import Qt, Signal


class TrackWidget(QWidget):

    volume_changed = Signal(int)
    mute_toggled = Signal(bool)
    solo_toggled = Signal(bool)

    def __init__(self, track_name="Track 0", master_type=None, parent=None):
        super().__init__(parent)
        self.track_name = track_name
        self.master_type = master_type
        self.setFixedWidth(70)
        self.init_ui()
    
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
        if not self.master_type:
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
        initial_value = 70 if self.master_type else 100
        self.slider.setValue(initial_value)
        #self.slider.setStyleSheet("QSlider::handle { width: 50px; height: 20px; }")
        layout.addWidget(self.slider, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Título del instrumento
        self.label = QLabel(self.track_name)
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)
        
        self.setLayout(layout)


        #Signals
        self.mute_button.toggled.connect(self._on_mute_toggled)
        self.solo_button.toggled.connect(lambda checked: self.solo_toggled.emit(checked) if not self.master_type else None)
        self.slider.valueChanged.connect(self._emit_volume_change)
    
    def _on_mute_toggled(self, checked):
        self.mute_toggled.emit(checked)

    def _on_solo_toggled(self, checked):
        self.solo_toggled.emit(checked)

    def _emit_volume_change(self, value):
        self.volume_changed.emit(value)