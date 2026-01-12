"""
Utilidades para mostrar mensajes y notificaciones al usuario.

Proporciona funciones helper para QMessageBox y notificaciones toast
con estilos consistentes de la aplicación.
"""

from PySide6.QtWidgets import QMessageBox, QWidget
from PySide6.QtCore import Qt
from ui.style_manager import StyleManager


def show_info(parent: QWidget, title: str, message: str, detailed_text: str = None) -> None:
    """
    Muestra un mensaje informativo modal.
    
    Args:
        parent: Widget padre
        title: Título del mensaje
        message: Texto principal
        detailed_text: Texto detallado opcional (expandible)
    """
    msg_box = QMessageBox(parent)
    msg_box.setIcon(QMessageBox.Information)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    
    if detailed_text:
        msg_box.setDetailedText(detailed_text)
    
    msg_box.setStandardButtons(QMessageBox.Ok)
    msg_box.setDefaultButton(QMessageBox.Ok)
    
    # Aplicar estilo
    _apply_message_style(msg_box)
    msg_box.exec()


def show_warning(parent: QWidget, title: str, message: str, detailed_text: str = None) -> None:
    """
    Muestra un mensaje de advertencia modal.
    
    Args:
        parent: Widget padre
        title: Título del mensaje
        message: Texto principal
        detailed_text: Texto detallado opcional (expandible)
    """
    msg_box = QMessageBox(parent)
    msg_box.setIcon(QMessageBox.Warning)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    
    if detailed_text:
        msg_box.setDetailedText(detailed_text)
    
    msg_box.setStandardButtons(QMessageBox.Ok)
    msg_box.setDefaultButton(QMessageBox.Ok)
    
    _apply_message_style(msg_box)
    msg_box.exec()


def show_error(parent: QWidget, title: str, message: str, detailed_text: str = None) -> None:
    """
    Muestra un mensaje de error modal.
    
    Args:
        parent: Widget padre
        title: Título del mensaje
        message: Texto principal
        detailed_text: Texto detallado opcional (expandible)
    """
    msg_box = QMessageBox(parent)
    msg_box.setIcon(QMessageBox.Critical)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    
    if detailed_text:
        msg_box.setDetailedText(detailed_text)
    
    msg_box.setStandardButtons(QMessageBox.Ok)
    msg_box.setDefaultButton(QMessageBox.Ok)
    
    _apply_message_style(msg_box)
    msg_box.exec()


def show_question(
    parent: QWidget, 
    title: str, 
    message: str,
    detailed_text: str = None,
    default_yes: bool = True
) -> bool:
    """
    Muestra un diálogo de confirmación (Sí/No).
    
    Args:
        parent: Widget padre
        title: Título del mensaje
        message: Texto principal
        detailed_text: Texto detallado opcional
        default_yes: Si True, el botón Sí es el predeterminado
    
    Returns:
        True si el usuario selecciona Sí, False si selecciona No
    """
    msg_box = QMessageBox(parent)
    msg_box.setIcon(QMessageBox.Question)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    
    if detailed_text:
        msg_box.setDetailedText(detailed_text)
    
    msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    msg_box.setDefaultButton(QMessageBox.Yes if default_yes else QMessageBox.No)
    
    # Traducir botones a español
    msg_box.button(QMessageBox.Yes).setText("Sí")
    msg_box.button(QMessageBox.No).setText("No")
    
    _apply_message_style(msg_box)
    result = msg_box.exec()
    
    return result == QMessageBox.Yes


def show_success_toast(parent: QWidget, message: str, duration_ms: int = 3000) -> 'ToastNotification':
    """
    Muestra una notificación toast de éxito (temporal, no-modal).
    
    Args:
        parent: Widget padre
        message: Mensaje a mostrar
        duration_ms: Duración en milisegundos (default 3 segundos)
    
    Returns:
        ToastNotification instance
    """
    from ui.widgets.toast_notification import ToastNotification
    return ToastNotification.show_success(parent, message, duration_ms)


def show_info_toast(parent: QWidget, message: str, duration_ms: int = 3000) -> 'ToastNotification':
    """
    Muestra una notificación toast informativa (temporal, no-modal).
    
    Args:
        parent: Widget padre
        message: Mensaje a mostrar
        duration_ms: Duración en milisegundos (default 3 segundos)
    
    Returns:
        ToastNotification instance
    """
    from ui.widgets.toast_notification import ToastNotification
    return ToastNotification.show_info(parent, message, duration_ms)


def show_warning_toast(parent: QWidget, message: str, duration_ms: int = 4000) -> 'ToastNotification':
    """
    Muestra una notificación toast de advertencia (temporal, no-modal).
    
    Args:
        parent: Widget padre
        message: Mensaje a mostrar
        duration_ms: Duración en milisegundos (default 4 segundos)
    
    Returns:
        ToastNotification instance
    """
    from ui.widgets.toast_notification import ToastNotification
    return ToastNotification.show_warning(parent, message, duration_ms)


def show_error_toast(parent: QWidget, message: str, duration_ms: int = 5000) -> 'ToastNotification':
    """
    Muestra una notificación toast de error (temporal, no-modal).
    
    Args:
        parent: Widget padre
        message: Mensaje a mostrar
        duration_ms: Duración en milisegundos (default 5 segundos)
    
    Returns:
        ToastNotification instance
    """
    from ui.widgets.toast_notification import ToastNotification
    return ToastNotification.show_error(parent, message, duration_ms)


def _apply_message_style(msg_box: QMessageBox) -> None:
    """
    Aplica estilo personalizado al QMessageBox.
    
    Args:
        msg_box: QMessageBox a estilizar
    """
    # Aplicar colores del tema
    bg_color = StyleManager.get_color("background")
    text_color = StyleManager.get_color("text")
    accent_color = StyleManager.get_color("neon_blue")
    
    msg_box.setStyleSheet(f"""
        QMessageBox {{
            background-color: {bg_color.name()};
            color: {text_color.name()};
        }}
        QMessageBox QLabel {{
            color: {text_color.name()};
            min-width: 300px;
        }}
        QPushButton {{
            background-color: {accent_color.name()};
            color: {bg_color.name()};
            border: none;
            border-radius: 4px;
            padding: 6px 20px;
            font-weight: bold;
            min-width: 80px;
        }}
        QPushButton:hover {{
            background-color: {accent_color.lighter(120).name()};
        }}
        QPushButton:pressed {{
            background-color: {accent_color.darker(120).name()};
        }}
        QPushButton:default {{
            border: 2px solid {accent_color.lighter(150).name()};
        }}
    """)
