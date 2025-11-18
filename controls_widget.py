from PySide6.QtWidgets import QWidget, QHBoxLayout, QFrame, QLabel,QPushButton
from PySide6.QtCore import Qt, QSize, Signal, Slot
from PySide6.QtGui import QIcon

class ControlsWidget(QWidget):

    play_clicked = Signal() 
    pause_clicked = Signal()

    def __init__(self,  control_name="ControlsWidget", parent=None):
        super().__init__(parent)

        self.controls_name = control_name
        self.initUi()

    def initUi(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.setSpacing(5)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setObjectName(u"horizontallLayout")

        self.frame_1 = QFrame(self)
        self.frame_1.setLayout(QHBoxLayout())
        self.frame_1.setObjectName(u"frame_1")

        self.frame_2 = QFrame(self)
        self.frame_2.setLayout(QHBoxLayout())
        self.frame_2.setObjectName(u"frame_2")

        self.frame_3 = QFrame(self)
        self.frame_3.setLayout(QHBoxLayout())
        self.frame_3.setObjectName(u"frame_3")

        self.frame_4 = QFrame(self)
        self.frame_4.setLayout(QHBoxLayout())
        self.frame_4.setObjectName(u"frame_4")

        self.frame_5 = QFrame(self)
        self.frame_5.setLayout(QHBoxLayout())
        self.frame_5.setObjectName(u"frame_5")
        
        self.frame_6 = QFrame(self)
        self.frame_6.setLayout(QHBoxLayout())
        self.frame_6.setObjectName(u"frame_6")


        # Etiqueta para mostrar el tiempo
        self.time_label_style = "QLabel { color: white; font-size: 14px; font-weight: bold; background: transparent; padding: 5px; }"
        self.time_label = QLabel("00:00 / 00:00") # Etiqueta inicial simplificada
        self.time_label.setStyleSheet(self.time_label_style)
        self.time_label.setAlignment(Qt.AlignCenter)  

        button_style = """
                QPushButton { margin:0px; border-radius: 5px; background-color: rgb(29,35,67); color: white; } 
                QPushButton:hover { background-color: rgb(50, 60, 100); } """
        
        self.play_btn = QPushButton()
        self.play_btn.setIcon(QIcon("assets/img/play.svg"))
        self.play_btn.setIconSize(QSize(50, 50))
        self.play_btn.setStyleSheet(button_style)
        self.play_btn.clicked.connect(self._emit_play)

        self.stop_btn = QPushButton()
        self.stop_btn.setIcon(QIcon("assets/img/pause.svg"))
        self.stop_btn.setIconSize(QSize(50, 50))
        self.stop_btn.setStyleSheet(button_style)
        self.stop_btn.clicked.connect(self._emit_pause)

        # agregar botones a frames
        self.frame_1.layout().addWidget(self.time_label)
        self.frame_3.layout().addWidget(self.play_btn)
        self.frame_4.layout().addWidget(self.stop_btn)

        self.main_layout.addWidget(self.frame_1)
        self.main_layout.addWidget(self.frame_2)
        self.main_layout.addWidget(self.frame_3)
        self.main_layout.addWidget(self.frame_4)
        self.main_layout.addWidget(self.frame_5)
        self.main_layout.addWidget(self.frame_6)

        self.main_layout.setStretch(0, 1)
        self.main_layout.setStretch(1, 1)
        self.main_layout.setStretch(2, 2)
        self.main_layout.setStretch(3, 2)
        self.main_layout.setStretch(4, 1)
        self.main_layout.setStretch(5, 1)

    def _emit_play(self):
        self.play_clicked.emit()

    def _emit_pause(self):
        self.pause_clicked.emit()
    
    @Slot(str)
    def update_time_label(self, current_time_sec: float, total_duration_sec: float):
        """Actualiza el QLabel con el tiempo transcurrido y la duración total."""
        current_time_str = self._format_time(current_time_sec)
        total_duration_str = self._format_time(total_duration_sec)
        self.time_label.setText(f"{current_time_str} / {total_duration_str}")

    def _format_time(self, seconds):
        """Convierte segundos a formato MM:SS."""
        if seconds is None or seconds < 0:
            return "00:00"
            
        # Redondear al segundo más cercano
        total_seconds = int(round(seconds))
        
        minutes = total_seconds // 60
        secs = total_seconds % 60
        
        return f"{minutes:02d}:{secs:02d}"