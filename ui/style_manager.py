from PySide6.QtGui import QPalette, QColor, QFontDatabase, QFont
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

        # OTROS ACENTOS NEÓN
        "neon_purple": "rgb(191, 0, 255)",  # Electric Purple (Efectos/Marcadores)
        "neon_yellow": "rgb(238, 255, 0)",  # Lemon Neon (Alertas/Modos especiales)
        
        # AUDIO VISUALS (Nuevos colores sugeridos)
        "waveform": "rgb(0, 210, 255)",     # Electric Cyan (Onda de audio nítida)
        "waveform_dim": "rgba(0, 210, 255, 0.4)", # Onda de audio en segundo plano
        "playhead": "rgb(255, 50, 50)",     # Neon Red (Línea de tiempo/cursor)
        
        # GRID RÍTMICO (Líneas verticales)
        "beat": "rgba(200, 200, 200, 0.25)",     # Light Gray (Más opaco)
        "downbeat": "rgba(0, 255, 255, 0.6)",    # Pure Cyan Neon (Muy visible)

        # CAPAS DE DATOS (Backgrounds transparentes)
        "chord_bg": "rgba(155, 89, 182, 0.25)", # Amethyst Purple (Fondo de acordes)
        "chord_text": "rgb(200, 150, 255)",     # Soft Purple (Texto de acordes)
        
        "lyrics_bg": "rgba(46, 204, 113, 0.15)", # Emerald Trans (Fondo de letras)
        "lyrics_text": "rgb(255, 255, 255)",     # White (Texto de letras)

        # TEXTO
        "text_bright": "#FFFFFF",           # Pure White (Títulos y botones activos)
        "text_normal": "#D1D5DB",           # Cool Gray (Texto general legible)
        "text_dim": "#6B7280",              # Slate Gray (Texto secundario/ayuda)
        "text_disabled": "rgba(255, 255, 255, 0.25)", # Faded White (Texto inactivo)
        
        # FUENTES
        "font_main": "'Roboto', 'Segoe UI', 'Arial', sans-serif", 
        "font_mono": "'JetBrains Mono', 'Cascadia Code', 'Consolas', monospace"
    }

    @classmethod
    def get_color(cls, color_name):
        """Devuelve un objeto QColor basado en la PALETTE."""
        color_str = cls.PALETTE.get(color_name, "#FFFFFF")
        if "rgba" in color_str:
            parts = color_str.replace("rgba(", "").replace(")", "").split(",")
            return QColor(int(parts[0]), int(parts[1]), int(parts[2]), int(float(parts[3]) * 255))
        elif "rgb" in color_str:
            parts = color_str.replace("rgb(", "").replace(")", "").split(",")
            return QColor(int(parts[0]), int(parts[1]), int(parts[2]))
        return QColor(color_str)

    @classmethod
    def get_font(cls, mono=False, size=10, bold=False):
        """Devuelve un objeto QFont configurado con las fuentes del tema."""
        family = "Roboto" if not mono else "JetBrains Mono"
        weight = QFont.Bold if bold else QFont.Normal
        font = QFont(family, size)
        font.setWeight(weight)
        return font

    @classmethod
    def load_fonts(cls):
        """Carga los archivos TTF de la carpeta assets/fonts/"""
        font_path = os.path.join(os.path.dirname(__file__), "assets", "fonts")
        fonts = ["Roboto-Regular.ttf", "Roboto-Bold.ttf", "JetBrainsMono-Regular.ttf"]
        for font in fonts:
            full_path = os.path.join(font_path, font)
            if os.path.exists(full_path):
                QFontDatabase.addApplicationFont(full_path)

    @classmethod
    def setup_theme(cls, app):
        """Configuración integral del tema y fuentes."""
        cls.load_fonts()
        palette = QPalette()
        base_color = cls.get_color("bg_base")
        text_color = cls.get_color("text_normal")
        palette.setColor(QPalette.Window, base_color)
        palette.setColor(QPalette.WindowText, text_color)
        palette.setColor(QPalette.Base, cls.get_color("bg_workspace"))
        palette.setColor(QPalette.Text, text_color)
        palette.setColor(QPalette.Button, cls.get_color("bg_panel"))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.Highlight, cls.get_color("accent"))
        palette.setColor(QPalette.HighlightedText, Qt.black)
        app.setPalette(palette)
        app.setStyleSheet(cls.get_stylesheet())

    @classmethod
    def get_stylesheet(cls):
        return f"""
        /* Estilos base omitidos para brevedad, se mantienen iguales */
        QWidget {{
            color: {cls.PALETTE['text_normal']};
            font-family: {cls.PALETTE['font_main']};
            font-size: 12px;
            outline: none;
        }}
        QMainWindow {{ background-color: {cls.PALETTE['bg_base']}; }}
        QWidget#centralwidget {{ background-color: {cls.PALETTE['bg_base']}; }}
        QFrame {{ background-color: transparent; border: none; }}
        QFrame#frame_4, QFrame#frame_6_master {{
            background-color: {cls.PALETTE['bg_panel']};
            border-top: 1px solid {cls.PALETTE['border_light']};
        }}
        QFrame#frame_2, QFrame#frame_5_tracks {{
            background-color: {cls.PALETTE['bg_workspace']};
            border-radius: 4px;
            margin: 2px;
        }}
        QPushButton {{
            background-color: {cls.PALETTE['btn_normal']};
            color: {cls.PALETTE['text_bright']};
            border: 1px solid {cls.PALETTE['border_light']};
            border-radius: 4px;
            padding: 5px 12px;
        }}
        QPushButton:hover {{
            background-color: {cls.PALETTE['btn_hover']};
            border: 1px solid {cls.PALETTE['accent']};
        }}
        QPushButton:disabled {{
            background-color: {cls.PALETTE['btn_disabled']};
            color: {cls.PALETTE['text_disabled']};
        }}
        QPushButton[editing="true"] {{
            border: 2px solid {cls.PALETTE['accent']};
            background-color: rgba(255, 171, 0, 0.15);
            color: {cls.PALETTE['accent']};
        }}
        QLabel#time_display, QLabel#label_time {{
            font-family: {cls.PALETTE['font_mono']};
            font-size: 18px;
            color: {cls.PALETTE['waveform']};
            background: rgba(0, 0, 0, 0.2);
            padding: 4px;
            border-radius: 3px;
        }}
        """