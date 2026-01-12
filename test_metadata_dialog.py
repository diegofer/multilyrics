"""
Test standalone para MetadataEditorDialog
Ejecutar: python test_metadata_dialog.py
"""

import sys
from pathlib import Path

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget, QLabel
from ui.widgets.metadata_editor_dialog import MetadataEditorDialog


class TestWindow(QWidget):
    """Ventana de prueba para lanzar el diálogo con diferentes casos"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Test: MetadataEditorDialog")
        self.resize(400, 300)
        
        layout = QVBoxLayout(self)
        
        # Instrucciones
        label = QLabel(
            "Haz clic en un botón para probar el diálogo\n"
            "con diferentes metadatos extraídos."
        )
        label.setWordWrap(True)
        layout.addWidget(label)
        
        # Caso 1: Metadatos limpios
        btn1 = QPushButton("Caso 1: Metadatos limpios")
        btn1.clicked.connect(self.test_clean_metadata)
        layout.addWidget(btn1)
        
        # Caso 2: Metadatos con basura (típico de YouTube)
        btn2 = QPushButton("Caso 2: Metadatos sucios (YouTube)")
        btn2.clicked.connect(self.test_dirty_metadata)
        layout.addWidget(btn2)
        
        # Caso 3: Metadatos incompletos
        btn3 = QPushButton("Caso 3: Metadatos incompletos")
        btn3.clicked.connect(self.test_incomplete_metadata)
        layout.addWidget(btn3)
        
        # Label para mostrar resultados
        self.result_label = QLabel("")
        self.result_label.setWordWrap(True)
        self.result_label.setStyleSheet("padding: 10px; background: #2a2a2a;")
        layout.addWidget(self.result_label)
        
    def test_clean_metadata(self):
        """Caso con metadatos bien extraídos"""
        metadata = {
            'track_name': 'Bajo Tu Control',
            'artist_name': 'ROJO',
            'duration_seconds': 243.5
        }
        self._show_dialog(metadata)
        
    def test_dirty_metadata(self):
        """Caso típico de extracción de YouTube con título largo"""
        metadata = {
            'track_name': 'ROJO | Bajo Tu Control (Video de Letras | Lyric Video)',
            'artist_name': 'ROJO OFICIAL (REAL)',
            'duration_seconds': 243.5
        }
        self._show_dialog(metadata)
        
    def test_incomplete_metadata(self):
        """Caso con metadatos vacíos o incompletos"""
        metadata = {
            'track_name': '',
            'artist_name': 'Artista Desconocido',
            'duration_seconds': 180.0
        }
        self._show_dialog(metadata)
        
    def _show_dialog(self, metadata: dict):
        """Mostrar diálogo y capturar resultado"""
        dialog = MetadataEditorDialog(metadata, parent=self)
        
        # Conectar señales para ver qué ocurre
        dialog.metadata_confirmed.connect(
            lambda m: self._on_metadata_confirmed(m)
        )
        dialog.search_skipped.connect(
            lambda: self._on_search_skipped()
        )
        
        dialog.exec()
        
    def _on_metadata_confirmed(self, metadata: dict):
        """Callback cuando usuario confirma búsqueda"""
        self.result_label.setText(
            f"✅ Búsqueda confirmada:\n"
            f"  Título: {metadata['track_name']}\n"
            f"  Artista: {metadata['artist_name']}\n"
            f"  Duración: {metadata['duration_seconds']}s"
        )
        self.result_label.setStyleSheet(
            "padding: 10px; background: #1a4d2e; color: #4ade80;"
        )
        
    def _on_search_skipped(self):
        """Callback cuando usuario omite búsqueda"""
        self.result_label.setText("⏭ Búsqueda omitida por el usuario")
        self.result_label.setStyleSheet(
            "padding: 10px; background: #4d3a1a; color: #fbbf24;"
        )


def main():
    app = QApplication(sys.argv)
    
    # Aplicar tema oscuro básico
    app.setStyle("Fusion")
    from PySide6.QtGui import QPalette, QColor
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(20, 32, 74))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(208, 214, 232))
    palette.setColor(QPalette.ColorRole.Base, QColor(14, 22, 48))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(20, 32, 74))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(208, 214, 232))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(208, 214, 232))
    palette.setColor(QPalette.ColorRole.Text, QColor(208, 214, 232))
    palette.setColor(QPalette.ColorRole.Button, QColor(20, 32, 74))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(208, 214, 232))
    app.setPalette(palette)
    
    window = TestWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
