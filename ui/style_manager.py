from PySide6.QtGui import QPalette, QColor, QFontDatabase, QFont
from PySide6.QtCore import Qt
import os

class StyleManager:
    """
    Tema visual basado en:
    - Azules profundos dominantes
    - Botones integrados al fondo (bajo contraste)
    - Neón solo como acento y estado activo
    - Transparencias para sensación de fusión con el fondo
    """
 
    PALETTE = {
        # ==========================
        # BACKGROUND AZULES PROFUNDOS
        # ==========================
        "bg_workspace": "rgb(11, 18, 36)",  # Azul más profundo (casi negro azulado). Área de trabajo, máxima concentración y mínima fatiga visual.
        "bg_base": "rgb(14, 22, 48)",       # Azul muy oscuro. Fondo base de ventanas; ligeramente más visible que workspace.
        "bg_panel": "rgb(20, 32, 74)",      # Azul oscuro claramente perceptible. Ideal para paneles, barras y módulos diferenciados.
        "blue_deep_medium": "rgb(30, 50, 110)",  # Azul medio profundo. Excelente para botones activos, tabs, hover sin salir del tema oscuro.
        "blue_highlight_soft": "rgb(48, 78, 150)",  # Azul de mayor brillo pero controlado. Bueno para bordes, panel enfocado o secciones resaltadas.

        # ==========================
        # BOTONES FUNDIDOS CON EL FONDO
        # ==========================
        # mismos tonos que panel, pero más transparentes
        "btn_normal": "rgba(25, 40, 90, 0.55)",
        "btn_hover": "rgba(35, 55, 120, 0.65)",
        "btn_pressed": "rgba(10, 16, 34, 0.85)",
        "btn_disabled": "rgba(25, 32, 60, 0.35)",

        # ==========================
        # ACENTOS NEÓN (SOLO BORDES/TEXTO ACTIVO)
        # ==========================
        "accent": "rgb(255, 180, 0)",
        "accent_hover": "rgb(255, 200, 50)",
        "accent_edit": "rgba(255, 180, 0, 0.10);",
        "accent_play": "rgb(0, 230, 140)",
        "neon_cyan": "rgb(0, 220, 255)",
        "neon_purple": "rgb(200, 0, 255)",
        "neon_red": "rgb(255, 60, 60)",
        
        # Success/Error colors
        "success": "rgb(0, 230, 140)",
        "error": "rgb(255, 100, 100)",

        # ==========================
        # BORDES
        # ==========================
        "border_light": "rgba(255, 255, 255, 0.12)",
        "border_disabled": "rgba(255, 255, 255, 0.04)",

        # ==========================
        # OVERLAYS OSCUROS (antes estaban hardcodeados)
        # ==========================
        "overlay_light": "rgba(0, 0, 0, 0.35)",
        "overlay_mid": "rgba(0, 0, 0, 0.45)",
        "overlay_strong": "rgba(0, 0, 0, 0.55)",

        # ==========================
        # AUDIO VISUAL
        # ==========================
        "waveform": "rgb(0, 220, 255)",
        "waveform_dim": "rgba(0, 220, 255, 0.35)",
        "playhead": "rgb(255, 60, 60)",

        # ==========================
        # GRID
        # ==========================
        "beat": "rgba(200, 200, 200, 0.20)",
        "downbeat": "rgba(0, 255, 255, 0.55)",

        # ==========================
        # CAPAS
        # ==========================
        "chord_bg": "rgba(155, 89, 182, 0.25)",
        "chord_text": "rgb(200, 160, 255)",
        "lyrics_bg": "rgba(46, 204, 113, 0.15)",
        "lyrics_text": "rgb(255, 255, 255)",

        # ==========================
        # TEXTO
        # ==========================
        "text_bright": "#FFFFFF",
        "text_normal": "#D0D6E8",
        "text_dim": "#7A8298",
        "text_disabled": "rgba(255, 255, 255, 0.25)",
        
        # UI elements
        "background": "rgb(14, 22, 48)",
        "surface": "rgb(20, 32, 74)",
        "surface_hover": "rgb(30, 50, 110)",
        "text": "#D0D6E8",
        "border": "rgba(255, 255, 255, 0.12)",

        # ==========================
        # FUENTES
        # ==========================
        "font_main": "'Roboto', 'Segoe UI', 'Arial', sans-serif",
        "font_mono": "'JetBrains Mono', 'Cascadia Code', 'Consolas', monospace"
    }

    @classmethod
    def get_color(cls, color_name):
        color_str = cls.PALETTE.get(color_name, "#FFFFFF")
        if "rgba" in color_str:
            parts = color_str.replace("rgba(", "").replace(")", "").split(",")
            return QColor(
                int(parts[0]),
                int(parts[1]),
                int(parts[2]),
                int(float(parts[3]) * 255)
            )
        elif "rgb" in color_str:
            parts = color_str.replace("rgb(", "").replace(")", "").split(",")
            return QColor(int(parts[0]), int(parts[1]), int(parts[2]))
        return QColor(color_str)

    @classmethod
    def get_font(cls, mono=False, size=10, bold=False):
        family = "Roboto" if not mono else "JetBrains Mono"
        weight = QFont.Bold if bold else QFont.Normal
        font = QFont(family, size)
        font.setWeight(weight)
        return font

    @classmethod
    def load_fonts(cls):
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
        QWidget {{
            color: {cls.PALETTE['text_normal']};
            font-family: {cls.PALETTE['font_main']};
            font-size: 14px;
            background-color: transparent;
        }}
        QFrame {{
            background-color: transparent;
            border: none;
        }}

        QWidget#central_widget{{
            background-color: {cls.PALETTE['bg_base']};
        }}

        QFrame#frame_playlist, QFrame#frame_controls, QWidget#frame_mixer {{
            
        }}

        QFrame#frame_timeline {{
        }}

        QFrame#frame_mixer_tracks {{
            background-color: {cls.PALETTE['bg_panel']};
            border-radius: 4px;
        }}

        /* Botones fundidos con el fondo */
        QPushButton {{
            background-color: {cls.PALETTE['btn_normal']};
            color: {cls.PALETTE['text_bright']};
            border-radius: 6px;
            border: 1px solid {cls.PALETTE['border_light']};
            padding: 6px 14px;
        }}

        QPushButton:hover {{
            background-color: {cls.PALETTE['btn_hover']};
            border: 1px solid {cls.PALETTE['neon_cyan']};
        }}

        QPushButton:pressed {{
            background-color: {cls.PALETTE['btn_pressed']};
        }}

        QPushButton:checked {{
            background-color: {cls.PALETTE['btn_hover']};
            color: {cls.PALETTE['neon_cyan']};
            border: 2px solid {cls.PALETTE['neon_cyan']};
        }}

        QPushButton:disabled {{
            background-color: {cls.PALETTE['btn_disabled']};
            color: {cls.PALETTE['text_disabled']};
            border: 1px solid {cls.PALETTE['border_disabled']};
        }}

        QPushButton[editing="true"] {{
            border: 2px solid {cls.PALETTE['accent']};
            background-color: {cls.PALETTE['accent_edit']};
            color: {cls.PALETTE['accent']};
        }}

        QLabel#time_display, QLabel#label_time {{
            font-family: {cls.PALETTE['font_mono']};
            font-size: 15pt;
            color: {cls.PALETTE['neon_cyan']};
            background: {cls.PALETTE['bg_panel']};
            padding: 4px 6px;
            border-radius: 4px;
            qproperty-alignment: 'AlignCenter';
        }}

        QLabel#tempo_compass_label {{
            font-family: {cls.PALETTE['font_mono']};
            font-size: 15pt;
            color: {cls.PALETTE['accent_play']};
            background: {cls.PALETTE['overlay_strong']};
            padding: 4px 6px;
            border-radius: 4px;
            qproperty-alignment: 'AlignCenter';
        }}
        """



"""
Estilo temporal para depuración de la estructura de la UI:
        QFrame#frame_playlist {{ background-color: red; }}
        QFrame#frame_timeline {{ background-color: green; }}
        QFrame#frame_mixer {{ background-color: pink; }}
            QFrame#frame_mixer_tracks {{ background-color: yellow; }}
            QFrame#frame_mixer_master {{ background-color: aquamarine; }}
        QFrame#frame_controls {{ background-color: green; }}
            QWidget#controls_widget {{ background-color: pink; }}
                QWidget#controls_widget QFrame {{ background-color: red; }}
"""