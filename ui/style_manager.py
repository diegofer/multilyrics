from PySide6.QtGui import QPalette, QColor
from PySide6.QtCore import Qt

class StyleManager:
    """
    Gestor de estilos centralizado para el Editor Multitrack.
    Establece una jerarquía visual profesional basada en los colores Midnight Blue.
    Evita el 'flash blanco' configurando la paleta nativa y el estilo global.
    """
    
    PALETTE = {
        # COLORES DE FONDO (Jerarquía)
        "bg_base": "rgb(29, 35, 67)",       # Nivel 0: Fondo de la ventana
        "bg_panel": "rgb(43, 52, 95)",      # Nivel 1: Paneles de control y herramientas
        "bg_workspace": "rgb(22, 27, 51)",  # Nivel -1: Área de edición (más profundo)
        
        # INTERACCIÓN
        "btn_normal": "rgb(58, 70, 128)",
        "btn_hover": "rgb(75, 88, 155)",
        "btn_pressed": "rgb(15, 20, 40)",
        "btn_disabled": "rgba(43, 52, 95, 0.6)",
        
        # ACENTOS Y ESTADOS
        "accent": "rgb(255, 171, 0)",       # Ámbar: Selección, enfoque, edición
        "accent_play": "rgb(46, 204, 113)", # Esmeralda: Reproducción activa
        "border_light": "rgba(255, 255, 255, 0.08)",
        
        # TEXTO
        "text_bright": "#FFFFFF",
        "text_normal": "#D1D5DB",
        "text_dim": "#6B7280",
        
        # FUENTES
        "font_main": "'Roboto', 'Segoe UI', sans-serif",
        "font_mono": "'JetBrains Mono', 'Cascadia Code', monospace"
    }

    @classmethod
    def setup_theme(cls, app):
        """
        Configuración integral del tema para evitar destellos blancos.
        Se debe llamar ANTES de mostrar la ventana principal.
        """
        # 1. Configurar la paleta de colores del sistema (QPalette)
        # Esto cambia el color base que usa el SO para dibujar la ventana vacía
        palette = QPalette()
        base_color = QColor(29, 35, 67)
        text_color = QColor(209, 213, 219)
        
        palette.setColor(QPalette.Window, base_color)
        palette.setColor(QPalette.WindowText, text_color)
        palette.setColor(QPalette.Base, QColor(22, 27, 51))
        palette.setColor(QPalette.AlternateBase, base_color)
        palette.setColor(QPalette.ToolTipBase, Qt.white)
        palette.setColor(QPalette.ToolTipText, Qt.white)
        palette.setColor(QPalette.Text, text_color)
        palette.setColor(QPalette.Button, QColor(43, 52, 95))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, QColor(255, 171, 0))
        palette.setColor(QPalette.Highlight, QColor(255, 171, 0))
        palette.setColor(QPalette.HighlightedText, Qt.black)
        
        app.setPalette(palette)
        
        # 2. Aplicar la hoja de estilos a nivel de aplicación (Global)
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
            border-left: 1px solid {cls.PALETTE['border_light']};
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

        QPushButton:pressed {{
            background-color: {cls.PALETTE['btn_pressed']};
        }}

        QPushButton:disabled {{
            background-color: {cls.PALETTE['btn_disabled']};
            color: {cls.PALETTE['text_dim']};
            border: 1px solid transparent;
        }}

        QPushButton[editing="true"] {{
            border: 2px solid {cls.PALETTE['accent']};
            background-color: rgba(255, 171, 0, 0.15);
            color: {cls.PALETTE['accent']};
        }}

        /* 4. ELEMENTOS DE AUDIO (Sliders / Faders) */
        
        QSlider::groove:horizontal, QSlider::groove:vertical {{
            background: {cls.PALETTE['bg_base']};
            border-radius: 2px;
        }}

        QSlider::sub-page:horizontal, QSlider::add-page:vertical {{
            background: {cls.PALETTE['btn_normal']};
            border-radius: 2px;
        }}

        QSlider::handle {{
            background: {cls.PALETTE['accent']};
            border: 1px solid {cls.PALETTE['bg_base']};
            width: 12px;
            height: 12px;
            border-radius: 6px;
        }}

        /* 5. TEXTO DIGITAL (Time Displays) */
        
        QLabel#time_display, QLabel#label_time {{
            font-family: {cls.PALETTE['font_mono']};
            font-size: 18px;
            color: {cls.PALETTE['accent']};
            background: rgba(0, 0, 0, 0.2);
            padding: 4px;
            border-radius: 3px;
        }}

        /* 6. SCROLLBARS */
        
        QScrollBar:vertical {{
            border: none;
            background: {cls.PALETTE['bg_base']};
            width: 10px;
            margin: 0px;
        }}

        QScrollBar::handle:vertical {{
            background: {cls.PALETTE['btn_normal']};
            min-height: 20px;
            border-radius: 5px;
        }}

        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        """