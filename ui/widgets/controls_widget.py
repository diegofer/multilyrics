from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QFrame, QLabel,QPushButton, QMenu, QButtonGroup, QSizePolicy
from PySide6.QtCore import Qt, QSize, Signal, Slot, QPoint
from PySide6.QtGui import QIcon
from utils.helpers import clamp_menu_to_window, format_time

class ControlsWidget(QWidget):

    play_clicked = Signal() 
    pause_clicked = Signal()
    action_1_clicked = Signal()
    edit_mode_toggled = Signal(bool)  # Signal for edit mode state
    zoom_mode_changed = Signal(str)  # Signal for zoom mode change: "GENERAL", "PLAYBACK", "EDIT"


    def __init__(self,  control_name="ControlsWidget", parent=None):
        super().__init__(parent)

        self.controls_name = control_name
        self.initUi()

    def initUi(self):
        self.setObjectName(u"controls_widget")
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.setSpacing(10)
        self.main_layout.setContentsMargins(10, 10, 10, 20)

        self.frame_1 = QFrame(self)
        self.frame_1.setLayout(QVBoxLayout())
        self.frame_1.setObjectName(u"controls_frame_1")
        self.frame_1.layout().setContentsMargins(0, 0, 0, 0)

        self.frame_2 = QFrame(self)
        self.frame_2.setLayout(QVBoxLayout())
        self.frame_2.setObjectName(u"controls_frame_2")
        self.frame_2.layout().setContentsMargins(0, 0, 0, 0)

        self.frame_3 = QFrame(self)
        self.frame_3.setLayout(QHBoxLayout())
        self.frame_3.setObjectName(u"controls_frame_3")

        self.frame_4 = QFrame(self)
        self.frame_4.setLayout(QHBoxLayout())
        self.frame_4.setObjectName(u"controls_frame_4")
        self.frame_4.layout().setContentsMargins(0, 0, 0, 0)

        self.frame_5 = QFrame(self)
        self.frame_5.setLayout(QHBoxLayout())
        self.frame_5.setObjectName(u"controls_frame_5")
        
        self.frame_6 = QFrame(self)
        self.frame_6.setLayout(QHBoxLayout())
        self.frame_6.setObjectName(u"controls_frame_6")
        self.frame_6.layout().setContentsMargins(0, 0, 0, 0)

        self.frame_7 = QFrame(self)
        self.frame_7.setLayout(QHBoxLayout())
        self.frame_7.setObjectName(u"controls_frame_7")
        self.frame_7.layout().setContentsMargins(0, 0, 0, 0)

        # Etiqueta para mostrar el tiempo transcurrido y duración total
        self.total_duration_label = QLabel("00:00") 
        self.total_duration_label.setObjectName("label_time")
        self.current_time_label = QLabel("00:00")
        self.current_time_label.setObjectName("label_time")

        self.tempo_compass_label = QLabel("120\n4/4")
        self.tempo_compass_label.setObjectName("tempo_compass_label")

        # Single toggle button for play/pause/resume
        self.play_toggle_btn = QPushButton()
        self.play_toggle_btn.setObjectName("play_mode")
        self.play_toggle_btn.setCheckable(True)
        self.play_toggle_btn.setIcon(QIcon("assets/img/play.svg"))
        self.play_toggle_btn.setIconSize(QSize(50, 50))
        self.play_toggle_btn.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self.play_toggle_btn.toggled.connect(self._on_play_toggle)

        
        # Toggle button for editing mode
        self.edit_toggle_btn = QPushButton("Editar")
        self.edit_toggle_btn.setObjectName("edit_mode")
        self.edit_toggle_btn.setCheckable(True)
        #self.edit_toggle_btn.setFixedSize(80, 50)
        self.edit_toggle_btn.setEnabled(False)  # Disabled by default
        self.edit_toggle_btn.toggled.connect(self._on_edit_toggle)
        self.edit_toggle_btn.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        
        # Botones para cambiar modo de zoom
        #self.zoom_general_btn = QPushButton("Z1")
        #self.zoom_general_btn.setCheckable(True)
        #self.zoom_general_btn.setChecked(True)  # Modo por defecto
        #self.zoom_general_btn.setFixedSize(100, 40)
        #self.zoom_general_btn.setToolTip("Modo General: Ver toda la forma de onda")
        
        #self.zoom_playback_btn = QPushButton("Z2")
        #self.zoom_playback_btn.setCheckable(True)
        #self.zoom_playback_btn.setFixedSize(100, 40)
        #self.zoom_playback_btn.setToolTip("Modo Reproducción: Zoom adaptado para ver letras")
        
        #self.zoom_edit_btn = QPushButton("Z3")
        #self.zoom_edit_btn.setCheckable(True)
        #self.zoom_edit_btn.setFixedSize(100, 40)
        #self.zoom_edit_btn.setToolTip("Modo Edición: Zoom libre para edición precisa")
        
        # Agrupar botones de zoom para que sean mutuamente exclusivos
        #self.zoom_button_group = QButtonGroup(self)
        #self.zoom_button_group.addButton(self.zoom_general_btn, 0)
        #self.zoom_button_group.addButton(self.zoom_playback_btn, 1)
        #self.zoom_button_group.addButton(self.zoom_edit_btn, 2)
        #self.zoom_button_group.setExclusive(True)
        
        # Conectar señales
        #self.zoom_general_btn.clicked.connect(lambda: self._on_zoom_mode_changed("GENERAL"))
        #self.zoom_playback_btn.clicked.connect(lambda: self._on_zoom_mode_changed("PLAYBACK"))
        #self.zoom_edit_btn.clicked.connect(lambda: self._on_zoom_mode_changed("EDIT"))

        # button for settings menu
        self.menu_btn = QPushButton()
        self.menu_btn.setIcon(QIcon("assets/img/settings.svg"))
        self.menu_btn.setIconSize(QSize(50, 50))
        self.menu_btn.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

        self.menu = QMenu()
        action_1 = self.menu.addAction("Crear")
        accion2 = self.menu.addAction("Opción 2")
        accion3 = self.menu.addAction("Opción 3")

        action_1.triggered.connect(self._emit_action_1)

        self.menu_btn.clicked.connect(self.show_settings_menu)

        # agregar botones a frames
        self.frame_1.layout().addWidget(self.total_duration_label)
        self.frame_1.layout().addWidget(self.current_time_label)
        self.frame_2.layout().addWidget(self.tempo_compass_label)
        self.frame_4.layout().addWidget(self.play_toggle_btn)
        self.frame_6.layout().addWidget(self.edit_toggle_btn)
        self.frame_7.layout().addWidget(self.menu_btn)
        
        # Agregar botones de zoom a su frame
        #self.frame_zoom.layout().addWidget(self.zoom_general_btn)
        #self.frame_zoom.layout().addWidget(self.zoom_playback_btn)
        #self.frame_zoom.layout().addWidget(self.zoom_edit_btn)

        self.main_layout.addWidget(self.frame_1)
        self.main_layout.addWidget(self.frame_2)
        self.main_layout.addWidget(self.frame_3)
        self.main_layout.addWidget(self.frame_4)
        self.main_layout.addWidget(self.frame_5)
        #self.main_layout.addWidget(self.frame_zoom)
        self.main_layout.addWidget(self.frame_6)
        self.main_layout.addWidget(self.frame_7)

        self.main_layout.setStretch(0, 1)
        self.main_layout.setStretch(1, 1)
        self.main_layout.setStretch(2, 2)
        self.main_layout.setStretch(3, 2)
        self.main_layout.setStretch(4, 2)
        self.main_layout.setStretch(5, 1)
        self.main_layout.setStretch(6, 1)

    def _emit_play(self):
        self.play_clicked.emit()

    def _emit_pause(self):
        self.pause_clicked.emit()

    def _on_play_toggle(self, checked: bool):
        """Handler for the toggle button state.

        When checked -> play/resume, when unchecked -> pause.
        """
        if checked:
            # Switch icon to pause
            self.play_toggle_btn.setIcon(QIcon("assets/img/pause.svg"))
            self._emit_play()
        else:
            # Switch icon to play
            self.play_toggle_btn.setIcon(QIcon("assets/img/play.svg"))
            self._emit_pause()

    def _on_edit_toggle(self, checked: bool):
        """Handler for edit mode toggle.
        
        When checked -> activate edit mode, when unchecked -> deactivate.
        """
        self.edit_toggle_btn.setProperty("editing", checked)
        self.edit_toggle_btn.style().unpolish(self.edit_toggle_btn)
        self.edit_toggle_btn.style().polish(self.edit_toggle_btn)
        #self.edit_toggle_btn.update()

        # cambia el texto del botón según el estado
        if checked:
            self.edit_toggle_btn.setText("Hecho")
        else:
            self.edit_toggle_btn.setText("Editar") 

        self.edit_mode_toggled.emit(checked)

    def set_playing_state(self, playing: bool):
        """Externally set the playing state: update toggle and icon."""
        self.play_toggle_btn.setChecked(bool(playing))
        if playing:
            self.play_toggle_btn.setIcon(QIcon("assets/img/pause.svg"))
        else:
            self.play_toggle_btn.setIcon(QIcon("assets/img/play.svg"))

    def set_edit_mode_enabled(self, enabled: bool):
        """Enable or disable the edit mode button.
        
        Call this when a multitrack song is selected/deselected.
        """
        self.edit_toggle_btn.setEnabled(enabled)
        if not enabled:
            # Reset to unchecked when disabled
            self.edit_toggle_btn.setChecked(False)

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
    
    def _on_zoom_mode_changed(self, mode: str):
        """Handler para cambios de modo de zoom."""
        self.zoom_mode_changed.emit(mode)
    
    def set_zoom_mode(self, mode: str):
        """Actualiza visualmente el botón de zoom activo.
        
        Args:
            mode: "GENERAL", "PLAYBACK", o "EDIT"
        """
        if mode == "GENERAL":
            #self.zoom_general_btn.setChecked(True)
            pass
        elif mode == "PLAYBACK":
            #self.zoom_playback_btn.setChecked(True)
            pass
        elif mode == "EDIT":
            #self.zoom_edit_btn.setChecked(True)
            pass 