#!/usr/bin/env python3
"""
Script de prueba para verificar que la ventana de video aparece correctamente en Linux.

Uso:
    python scripts/test_video_display.py

Esto mostrará:
1. Las pantallas detectadas en el sistema
2. Si es posible adjuntar VLC a la ventana X11
3. El comportamiento de show/hide de la ventana
"""

import sys
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QApplication, QLabel, QMainWindow, QPushButton,
                               QVBoxLayout, QWidget)

# Agregar raíz del proyecto al path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils.logger import get_logger
from video.video import VideoLyrics

logger = get_logger(__name__)

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Test Video Display")
        self.setGeometry(100, 100, 800, 300)

        central = QWidget()
        layout = QVBoxLayout(central)
        self.setCentralWidget(central)

        # Información
        info_label = QLabel(
            "Test de Ventana de Video\n\n"
            "Presiona 'Mostrar Video' para verificar que aparece en pantalla secundaria\n"
            "Presiona 'Ocultar Video' para cerrarla\n"
            "Verifica los logs para más información"
        )
        layout.addWidget(info_label)

        # Botones de control
        show_btn = QPushButton("Mostrar Video")
        show_btn.clicked.connect(self.show_video)
        layout.addWidget(show_btn)

        hide_btn = QPushButton("Ocultar Video")
        hide_btn.clicked.connect(self.hide_video)
        layout.addWidget(hide_btn)

        close_btn = QPushButton("Cerrar (salir)")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

        # Crear video player
        logger.info("=" * 60)
        logger.info("INICIALIZANDO VIDEO PLAYER")
        logger.info("=" * 60)
        self.video_player = VideoLyrics(screen_index=1)
        logger.info("=" * 60)

    def show_video(self):
        logger.info("\n>>> Usuario presionó 'Mostrar Video'")
        self.video_player.show_window()

    def hide_video(self):
        logger.info("\n>>> Usuario presionó 'Ocultar Video'")
        self.video_player.hide_window()

    def closeEvent(self, event):
        logger.info("\n>>> Cerrando aplicación")
        self.video_player.closeEvent(event)
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())
