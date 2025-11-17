from typing import Type
from PySide6.QtWidgets import QWidget, QFrame, QLayout


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
