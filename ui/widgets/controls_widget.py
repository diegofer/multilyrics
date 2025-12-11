from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QFrame, QLabel,QPushButton, QMenu
from PySide6.QtCore import Qt, QSize, Signal, Slot, QPoint
from PySide6.QtGui import QIcon
from core.utils import clamp_menu_to_window, format_time

class ControlsWidget(QWidget):

    play_clicked = Signal() 
    pause_clicked = Signal()
    action_1_clicked = Signal()


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
        self.frame_1.setLayout(QVBoxLayout())
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
        self.current_time_label_style = "QLabel { color: white; font-size: 20px; font-weight: bold; background: transparent; padding: 5px; }"
        self.total_duration_label_style = "QLabel { color: white; font-size: 30px; font-weight: bold; background: transparent; padding: 5px; }"
        self.total_duration_label = QLabel("00:00") 
        self.current_time_label = QLabel("00:00")
        self.total_duration_label.setStyleSheet(self.total_duration_label_style)
        self.total_duration_label.setAlignment(Qt.AlignCenter) 
        self.current_time_label.setStyleSheet(self.current_time_label_style)
        self.current_time_label.setAlignment(Qt.AlignCenter) 

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

        self.menu_btn = QPushButton()
        self.menu_btn.setIcon(QIcon("assets/img/settings.svg"))
        self.menu_btn.setIconSize(QSize(50, 50))
        self.menu_btn.setStyleSheet(button_style)

        self.menu = QMenu()
        action_1 = self.menu.addAction("Crear")
        accion2 = self.menu.addAction("Opción 2")
        accion3 = self.menu.addAction("Opción 3")

        action_1.triggered.connect(self._emit_action_1)

        self.menu_btn.clicked.connect(self.show_settings_menu)

        # agregar botones a frames
        self.frame_1.layout().addWidget(self.total_duration_label)
        self.frame_1.layout().addWidget(self.current_time_label)
        self.frame_3.layout().addWidget(self.play_btn)
        self.frame_4.layout().addWidget(self.stop_btn)
        self.frame_6.layout().addWidget(self.menu_btn)

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

    def _emit_action_1(self):
        self.action_1_clicked.emit()

    @Slot(float)
    def update_time_position_label(self, current_time_sec: float):
        """Actualiza solo el tiempo transcurrido."""
        current_time_str = format_time(current_time_sec)
        self.current_time_label.setText(f"{current_time_str}")

    @Slot(float)
    def update_total_duration_label(self, total_duration_sec: float):
        """Actualiza solo la duración total."""
        total_duration_str = format_time(total_duration_sec)
        self.total_duration_label.setText(f"{total_duration_str}")

    def show_settings_menu(self):
        # Sacamos la esquina superior derecha del botón
        global_top_right = self.menu_btn.mapToGlobal(self.menu_btn.rect().topRight())
        menu_size = self.menu.sizeHint()

        # Queremos mostrarlo ARRIBA y pegado a la derecha
        desired_pos = QPoint(
            global_top_right.x() - menu_size.width(),
            global_top_right.y() - menu_size.height()
        )

        # Ajustar para que no se salga de la ventana principal
        final_pos = clamp_menu_to_window(self.menu, desired_pos, self.window())

        self.menu.popup(final_pos)