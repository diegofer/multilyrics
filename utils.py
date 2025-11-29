from typing import Type
from PySide6.QtWidgets import QWidget, QFrame, QLayout
from PySide6.QtCore import QPoint
import os


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

def get_multis_list(library_path):
    result = []
    
    for item in os.listdir(library_path):
        item_path = os.path.join(library_path, item)

        if os.path.isdir(item_path):
            result.append((item, item_path))

    return result

