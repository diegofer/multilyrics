"""
Sistema de notificaciones toast no-modales.

Proporciona notificaciones temporales que aparecen en la parte superior
de la ventana y desaparecen automáticamente.
"""

from enum import Enum
from PySide6.QtWidgets import QWidget, QLabel, QGraphicsOpacityEffect
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QPainter, QColor, QPen
from ui.style_manager import StyleManager


class ToastType(Enum):
    """Tipos de notificación toast"""
    SUCCESS = "success"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ToastNotification(QWidget):
    """
    Widget de notificación toast no-modal.
    
    Aparece en la parte superior central de la ventana padre,
    se desvanece automáticamente después de la duración especificada.
    """
    
    # Configuración de estilo por tipo
    TOAST_STYLES = {
        ToastType.SUCCESS: {
            "bg_color": "#2ECC71",  # Verde
            "text_color": "#FFFFFF",
            "icon": "✓"
        },
        ToastType.INFO: {
            "bg_color": "#3498DB",  # Azul
            "text_color": "#FFFFFF",
            "icon": "ℹ"
        },
        ToastType.WARNING: {
            "bg_color": "#F39C12",  # Naranja
            "text_color": "#FFFFFF",
            "icon": "⚠"
        },
        ToastType.ERROR: {
            "bg_color": "#E74C3C",  # Rojo
            "text_color": "#FFFFFF",
            "icon": "✖"
        }
    }
    
    def __init__(self, parent: QWidget, message: str, toast_type: ToastType, duration_ms: int):
        super().__init__(parent)
        
        self.message = message
        self.toast_type = toast_type
        self.duration_ms = duration_ms
        
        # Configuración del widget
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        
        # Crear label con el mensaje
        self.label = QLabel(self)
        style = self.TOAST_STYLES[toast_type]
        icon = style["icon"]
        
        self.label.setText(f"{icon}  {message}")
        self.label.setStyleSheet(f"""
            QLabel {{
                background-color: {style['bg_color']};
                color: {style['text_color']};
                padding: 12px 24px;
                border-radius: 8px;
                font-size: 13px;
                font-weight: bold;
            }}
        """)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.adjustSize()
        
        # Ajustar tamaño del widget al label
        self.setFixedSize(self.label.size())
        
        # Efecto de opacidad para fade in/out
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(0.0)
        
        # Animación de fade in
        self.fade_in_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_in_animation.setDuration(300)
        self.fade_in_animation.setStartValue(0.0)
        self.fade_in_animation.setEndValue(0.95)
        self.fade_in_animation.setEasingCurve(QEasingCurve.OutCubic)
        
        # Animación de fade out
        self.fade_out_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_out_animation.setDuration(300)
        self.fade_out_animation.setStartValue(0.95)
        self.fade_out_animation.setEndValue(0.0)
        self.fade_out_animation.setEasingCurve(QEasingCurve.InCubic)
        self.fade_out_animation.finished.connect(self.deleteLater)
        
        # Timer para iniciar fade out
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self._start_fade_out)
        
    def show_toast(self) -> None:
        """Muestra el toast con animación"""
        # Posicionar en el centro superior del padre
        if self.parent():
            parent_rect = self.parent().rect()
            x = (parent_rect.width() - self.width()) // 2
            y = 20  # 20px desde el borde superior
            self.move(x, y)
        
        # Mostrar y animar
        self.show()
        self.raise_()
        self.fade_in_animation.start()
        
        # Programar fade out
        self.hide_timer.start(self.duration_ms)
    
    def _start_fade_out(self) -> None:
        """Inicia la animación de fade out"""
        self.fade_out_animation.start()
    
    @classmethod
    def show_success(cls, parent: QWidget, message: str, duration_ms: int = 3000) -> 'ToastNotification':
        """Muestra un toast de éxito"""
        toast = cls(parent, message, ToastType.SUCCESS, duration_ms)
        toast.show_toast()
        return toast
    
    @classmethod
    def show_info(cls, parent: QWidget, message: str, duration_ms: int = 3000) -> 'ToastNotification':
        """Muestra un toast informativo"""
        toast = cls(parent, message, ToastType.INFO, duration_ms)
        toast.show_toast()
        return toast
    
    @classmethod
    def show_warning(cls, parent: QWidget, message: str, duration_ms: int = 4000) -> 'ToastNotification':
        """Muestra un toast de advertencia"""
        toast = cls(parent, message, ToastType.WARNING, duration_ms)
        toast.show_toast()
        return toast
    
    @classmethod
    def show_error(cls, parent: QWidget, message: str, duration_ms: int = 5000) -> 'ToastNotification':
        """Muestra un toast de error"""
        toast = cls(parent, message, ToastType.ERROR, duration_ms)
        toast.show_toast()
        return toast
