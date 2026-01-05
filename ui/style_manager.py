from PySide6.QtGui import QPalette, QColor, QFontDatabase
from PySide6.QtCore import Qt
import os

class StyleManager:
    """
    Gestor de estilos centralizado para el Editor Multitrack.
    Incluye registro de fuentes externas para consistencia cross-platform.
    """
    
    PALETTE = {
        # COLORES DE FONDO (Jerarquía)
        "bg_base": "rgb(29, 35, 67)",       # Deep Midnight Blue (Fondo principal)
        "bg_panel": "rgb(43, 52, 95)",      # Royal Blue Dark (Paneles y herramientas)
        "bg_workspace": "rgb(22, 27, 51)",  # Abyss Blue (Área de edición/tracks)
        
        # INTERACCIÓN
        "btn_normal": "rgb(58, 70, 128)",   # Slate Blue (Botón estado normal)
        "btn_hover": "rgb(75, 88, 155)",    # Soft Indigo (Botón al pasar el mouse)
        "btn_pressed": "rgb(15, 20, 40)",   # Charcoal Blue (Botón al presionar)
        "btn_disabled": "rgb(45, 50, 80)",  # Muted Steel Blue (Botón desactivado)
        
        # ACENTOS Y ESTADOS
        "accent": "rgb(255, 171, 0)",       # Amber/Orange (Selección, edición, enfoque)
        "accent_play": "rgb(46, 204, 113)", # Emerald Green (Reproducción activa)
        "border_light": "rgba(255, 255, 255, 0.12)", # Crystal White (Bordes sutiles)
        "border_disabled": "rgba(255, 255, 255, 0.05)", # Ghost White (Borde desactivado)
        
        # TEXTO
        "text_bright": "#FFFFFF",           # Pure White (Títulos y botones activos)
        "text_normal": "#D1D5DB",           # Cool Gray (Texto general legible)
        "text_dim": "#6B7280",              # Slate Gray (Texto secundario/ayuda)
        "text_disabled": "rgba(255, 255, 255, 0.25)", # Faded White (Texto inactivo)
        
        # FUENTES (Nombres con Fallbacks para seguridad)
        "font_main": "'Roboto', 'Segoe UI', 'Arial', sans-serif", 
        "font_mono": "'JetBrains Mono', 'Cascadia Code', 'Consolas', monospace"
    }

    @classmethod
    def load_fonts(cls):
        """Carga los archivos TTF de la carpeta assets/fonts/"""
        # Ajusta la ruta según tu estructura de carpetas
        font_path = os.path.join(os.path.dirname(__file__), "assets", "fonts")
        
        fonts = [
            "Roboto-Regular.ttf",
            "Roboto-Bold.ttf",
            "JetBrainsMono-Regular.ttf"
        ]
        
        for font in fonts:
            full_path = os.path.join(font_path, font)
            if os.path.exists(full_path):
                QFontDatabase.addApplicationFont(full_path)

    @classmethod
    def setup_theme(cls, app):
        """Configuración integral del tema y fuentes."""
        # 1. Cargar fuentes antes de aplicar el estilo
        cls.load_fonts()
        
        # 2. Configurar Paleta
        palette = QPalette()
        base_color = QColor(29, 35, 67)
        text_color = QColor(209, 213, 219)
        
        palette.setColor(QPalette.Window, base_color)
        palette.setColor(QPalette.WindowText, text_color)
        palette.setColor(QPalette.Base, QColor(22, 27, 51))
        palette.setColor(QPalette.Text, text_color)
        palette.setColor(QPalette.Button, QColor(43, 52, 95))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.Highlight, QColor(255, 171, 0))
        palette.setColor(QPalette.HighlightedText, Qt.black)
        
        app.setPalette(palette)
        
        # 3. Aplicar Hoja de Estilos
        app.setStyleSheet(cls.get_stylesheet())

    @classmethod
    def get_stylesheet(cls):
        return f"""
        /* 1. ESTILOS BASE DEL SISTEMA */
        QWidget {{
            color: {cls.PALETTE['text_normal']};
            font-family: {cls.PALETTE['font_main']};
            font-size: 12px;
            outline: none;
        }}

        QMainWindow {{
            background-color: {cls.PALETTE['bg_base']};
        }}

        /* 2. JERARQUÍA DE CONTENEDORES (QFrame) */
        QWidget#centralwidget {{
            background-color: {cls.PALETTE['bg_base']};
        }}

        QFrame {{
            background-color: transparent;
            border: none;
        }}

        QFrame#frame_4, QFrame#frame_6_master {{
            background-color: {cls.PALETTE['bg_panel']};
            border-top: 1px solid {cls.PALETTE['border_light']};
        }}

        QFrame#frame_2, QFrame#frame_5_tracks {{
            background-color: {cls.PALETTE['bg_workspace']};
            border-radius: 4px;
            margin: 2px;
        }}

        /* 3. WIDGETS DE INTERACCIÓN */
        QPushButton {{
            background-color: {cls.PALETTE['btn_normal']};
            color: {cls.PALETTE['text_bright']};
            border: 1px solid {cls.PALETTE['border_light']};
            border-radius: 4px;
            padding: 5px 12px;
            font-weight: 500;
        }}

        QPushButton:hover {{
            background-color: {cls.PALETTE['btn_hover']};
            border: 1px solid {cls.PALETTE['accent']};
        }}

        /* ESTADO DESACTIVADO */
        QPushButton:disabled {{
            background-color: {cls.PALETTE['btn_disabled']};
            color: {cls.PALETTE['text_disabled']};
            border: 1px solid {cls.PALETTE['border_disabled']};
        }}

        /* MODO EDICIÓN ACTIVO */
        QPushButton[editing="true"] {{
            border: 2px solid {cls.PALETTE['accent']};
            background-color: rgba(255, 171, 0, 0.15);
            color: {cls.PALETTE['accent']};
        }}

        /* 4. TEXTO DIGITAL (Time Displays) */
        QLabel#time_display, QLabel#label_time {{
            font-family: {cls.PALETTE['font_mono']};
            font-size: 18px;
            color: {cls.PALETTE['accent']};
            background: rgba(0, 0, 0, 0.2);
            padding: 4px;
            border-radius: 3px;
        }}
        """