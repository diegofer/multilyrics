from PySide6.QtCore import QPoint
from pathlib import Path
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


def get_mp4(folder_path: str) -> str:
    """
    Busca un único archivo .mp4 dentro de la carpeta especificada.

    Args:
        folder_path: La ruta de la carpeta a inspeccionar.

    Returns:
        El nombre del archivo .mp4 si es único, o una cadena vacía si 
        hay cero o más de uno.
    """
    # 1. Crear un objeto Path para la carpeta
    p = Path(folder_path)
    
    # 2. Usar .glob() para encontrar todos los archivos que terminen en .mp4
    # La búsqueda es sensible a mayúsculas/minúsculas. Si necesitas ignorar eso, 
    # usa '*.MP4' y combínalos. Aquí asumiremos minúsculas.
    mp4_files = list(p.glob('*.mp4'))
    
    # 3. Comprobar la cantidad de archivos encontrados
    if len(mp4_files) == 1:
        # Si solo hay uno, devolver su nombre (el Path object)
        # Convertimos a str para devolver la ruta completa o .name si solo quieres el nombre
        return str(mp4_files[0].name)
    elif len(mp4_files) == 0:
        print(f"❌ No se encontró ningún archivo .mp4 en: {folder_path}")
        return ""
    else:
        print(f"❌ Se encontraron {len(mp4_files)} archivos .mp4. Se esperaba solo uno.")
        # Opcionalmente, puedes devolver la lista para inspección
        return ""
