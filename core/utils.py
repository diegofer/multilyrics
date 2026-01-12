from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QLayout
from pathlib import Path
import os
import math 
from typing import List


def clear_layout(layout: QLayout):
    """Remove all widgets and child layouts from a Qt layout.

    This walks the layout and detaches any child widgets (setParent(None))
    and removes nested layouts. Safe to call on an empty layout or None.
    """
    if layout is None:
        return

    # Iterate until layout is empty; use takeAt(0) which shifts items down
    while layout.count():
        item = layout.takeAt(0)
        if item is None:
            break
        widget = item.widget()
        if widget is not None:
            widget.setParent(None)
        elif item.layout() is not None:
            clear_layout(item.layout())


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
    """
    Get list of multis with display names from metadata.
    Returns list of tuples (display_name, path).
    Uses track_name_display with fallback to track_name, then folder name.
    """
    result = []
    
    # evitar fallar si no hay carpetas
    if not os.path.exists(library_path):
        return result

    for item in os.listdir(library_path):
        item_path = os.path.join(library_path, item)

        if os.path.isdir(item_path):
            # Try to read display name from metadata
            display_name = item  # Fallback to folder name
            meta_path = Path(item_path) / "meta.json"
            
            if meta_path.exists():
                try:
                    import json
                    with open(meta_path, 'r', encoding='utf-8') as f:
                        meta_data = json.load(f)
                    # Use display name with fallback chain: display -> original -> folder name
                    display_name = (
                        meta_data.get('track_name_display') or 
                        meta_data.get('track_name') or 
                        item
                    )
                except Exception as e:
                    # If reading fails, use folder name
                    print(f"Warning: Could not read metadata for {item}: {e}")
                    
            result.append((display_name, item_path))

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


def get_tracks(
    folder_path: str | Path, 
    extensiones: List[str] = ['.wav', '.ogg', '.flac']
    ) -> List[str]:
    """
    Busca archivos de audio con extensiones específicas en un directorio dado
    y sus subdirectorios de forma recursiva.

    Args:
        folder_path: La ruta al directorio donde se buscarán los archivos.
        extensiones: Una lista de extensiones de archivo a buscar 
                     (debe incluir el punto, ej: '.wav').

    Returns:
        Una lista de strings (paths) con las rutas absolutas a los archivos de audio encontrados.
    """
    tracks_folder = Path(folder_path)

    if not tracks_folder.is_dir():
        # Puedes cambiar esto a raise FileNotFoundError si prefieres que falle
        # en lugar de devolver una lista vacía.
        print(f"⚠️ Error: La ruta '{folder_path}' no es un directorio válido o no existe.")
        return []

    extensiones_normalizadas = {
        ext.lower() if ext.startswith('.') else f'.{ext}'.lower()
        for ext in extensiones
    }

    archivos_encontrados: List[str] = []
    
    for archivo in tracks_folder.rglob('*'):
        if archivo.is_file() and archivo.suffix.lower() in extensiones_normalizadas:
            archivos_encontrados.append(str(archivo.resolve())) # resolve() da la ruta absoluta

    return archivos_encontrados


def find_file_by_name(folder_path: str, file_base_name: str) -> Path | None:
    """
    Busca un único archivo dentro de la carpeta especificada que coincida 
    con el nombre base dado, ignorando la extensión.

    Args:
        folder_path: La ruta de la carpeta a inspeccionar.
        file_base_name: El nombre del archivo a buscar (sin extensión).

    Returns:
        El objeto Path del archivo encontrado si es único, o None si hay 
        cero o más de uno, o si la carpeta no existe.
    """
    # 1. Crear un objeto Path para la carpeta
    p = Path(folder_path)

    if not p.is_dir():
        print(f"❌ Error: La carpeta '{folder_path}' no existe o no es un directorio.")
        return None
    
    # 2. Definir el patrón de búsqueda: 'nombre_base.*'
    # Esto busca cualquier archivo que comience con 'file_base_name' seguido de una extensión
    search_pattern = f"{file_base_name}.*"
    
    # 3. Usar .glob() para encontrar todos los archivos que coincidan
    matching_files = list(p.glob(search_pattern))
    
    # 4. Comprobar la cantidad de archivos encontrados
    if len(matching_files) == 1:
        # Si solo hay uno, devolver el objeto Path completo
        # Ahora devuelve el Path object, que es más útil
        return matching_files[0]
    
    elif len(matching_files) == 0:
        print(f"❌ No se encontró ningún archivo con el nombre base '{file_base_name}' en: {folder_path}")
        return None
        
    else:
        print(f"❌ Se encontraron {len(matching_files)} archivos con el nombre base '{file_base_name}'. Se esperaba solo uno.")
        # Opcionalmente, puedes imprimir la lista de conflictos
        # for file in matching_files:
        #     print(f"   - {file.name}")
        return None

# ==============================================================
# VOLUME(LOGARÍTMICO)
# ==============================================================
def get_logarithmic_volume(slider_value: int):
    """
    Establece el factor de volumen usando una curva logarítmica (dB).
    
    slider_value: Valor entero del QSlider (asumido: 0 a 100).
    0 (min) -> -60 dB (silencio)
    100 (max) -> 0 dB (volumen máximo/unidad)
    """
    volume = 0.0
    # Normalizar el valor de 0-100 a 0.0-1.0
    linear_val = max(0.0, min(1.0, slider_value / 100.0))
    
    # El volumen de 0 dB a -60 dB se usa para simular un fader de consola.
    # Rango en dB: de -60 dB a 0 dB (aprox. -60.0, 0.0)
    DB_RANGE = 60
    
    if linear_val <= 0.001: 
        # Si está cerca de cero, establecer a silencio total para evitar log(0)
        volume = 0.0
    else:
        # Mapear el valor lineal (0-1) a un valor de decibelios (-60 a 0).
        # Se usa una función exponencial (10**(dB/20)) para obtener el factor de amplitud.
        
        # El factor de decibelios (dB) varía de -DB_RANGE a 0.
        # Usamos log(linear_val) para crear la curva logarítmica
        
        # 1. Aplicar curva logarítmica:
        # Esto produce un valor que imita la posición de un fader logarítmico.
        dB = linear_val * DB_RANGE - DB_RANGE 
        
        # 2. Convertir dB a factor de amplitud (lineal):
        # Amplitud = 10^(dB/20)
        volume = math.pow(10, dB / 20.0)
        
        # Asegurar que el volumen esté entre 0.0 y 1.0 (máximo)
        volume = max(0.0, min(1.0, volume))

    # Opcional: imprimir el factor para depuración
    #print(f"Slider: {slider_value} -> dB: {dB:.2f} -> Factor: {self.volume:.4f}")
    return volume


def format_time(seconds):
    """Convierte segundos a formato MM:SS."""
    if seconds is None or seconds < 0:
        return "00:00"
    
    # Redondear al segundo más cercano para un formato simple
    total_seconds = int(round(seconds))
    
    minutes = total_seconds // 60
    secs = total_seconds % 60
    
    return f"{minutes:02d}:{secs:02d}"