from typing import Type
from PySide6.QtWidgets import QWidget, QFrame, QLayout
from PySide6.QtCore import QPoint


def clamp_menu_to_window(menu, desired_pos, window):
    """
    ajusta un Qmenu para que no se salga de la ventana principal
    """
    menu_size = menu.sizeHint()
    win_geo = window.frameGeometry()

    x = desired_pos.x()
    y = desired_pos.y()

    min_x = win_geo.left()
    max_x = win_geo.right() - menu_size.width()
    min_y = win_geo.top()
    max_y = win_geo.bottom() - menu_size.height()

    x = max(min_x, min(x, max_x))
    y = max(min_y, min(y, max_y))

    return QPoint(x, y)

def add_widget_to_frame(widget_class: Type[QWidget],
                        frame: QFrame,
                        layout_class: Type[QLayout]):
    """
    Inserta la CLASE de un widget dentro de un QFrame, garantizando que el frame tenga un layout.
    
    Más documentación detallada omitida aquí para no hacer ruido, pero mantenla en tu proyecto.
    """

    # Validaciones
    if not isinstance(frame, QFrame):
        raise TypeError(f"frame debe ser QFrame, recibido: {type(frame).__name__}")

    if not isinstance(widget_class, type):
        raise ValueError("widget_class debe ser una CLASE, no una instancia — usa ControlsWidget, no ControlsWidget()")

    if not issubclass(widget_class, QWidget):
        raise TypeError(f"widget_class debe heredar de QWidget: {widget_class.__name__}")

    if not isinstance(layout_class, type):
        raise ValueError("layout_class debe ser una CLASE, no una instancia — usa QHBoxLayout, no QHBoxLayout()")

    if not issubclass(layout_class, QLayout):
        raise TypeError(f"layout_class debe heredar de QLayout: {layout_class.__name__}")

    # Crear widget
    widget_instance = widget_class()

    # Obtener o crear layout
    if frame.layout() is None:
        layout_instance = layout_class(frame)
        layout_instance.setContentsMargins(0, 0, 0, 0)
    else:
        layout_instance = frame.layout()

    # Insertar widget
    layout_instance.addWidget(widget_instance)

    return widget_instance
