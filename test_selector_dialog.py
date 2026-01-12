"""
Test standalone para LyricsSelectorDialog
Ejecutar: python test_selector_dialog.py
"""

import sys
from pathlib import Path

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget, QLabel
from ui.widgets.lyrics_selector_dialog import LyricsSelectorDialog


class TestWindow(QWidget):
    """Ventana de prueba para lanzar el diálogo con diferentes casos"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Test: LyricsSelectorDialog")
        self.resize(400, 350)
        
        layout = QVBoxLayout(self)
        
        # Instrucciones
        label = QLabel(
            "Haz clic en un botón para probar el diálogo\n"
            "con diferentes conjuntos de resultados."
        )
        label.setWordWrap(True)
        layout.addWidget(label)
        
        # Caso 1: Múltiples resultados con match perfecto
        btn1 = QPushButton("Caso 1: Match perfecto (duración exacta)")
        btn1.clicked.connect(self.test_perfect_match)
        layout.addWidget(btn1)
        
        # Caso 2: Resultados con diferencias de duración
        btn2 = QPushButton("Caso 2: Varios resultados con diferencias")
        btn2.clicked.connect(self.test_multiple_results)
        layout.addWidget(btn2)
        
        # Caso 3: Ninguno dentro de tolerancia
        btn3 = QPushButton("Caso 3: Todos fuera de tolerancia")
        btn3.clicked.connect(self.test_no_tolerance)
        layout.addWidget(btn3)
        
        # Caso 4: Sin duración esperada
        btn4 = QPushButton("Caso 4: Sin duración esperada")
        btn4.clicked.connect(self.test_no_duration)
        layout.addWidget(btn4)
        
        # Caso 5: Muchos resultados
        btn5 = QPushButton("Caso 5: Lista larga (10 resultados)")
        btn5.clicked.connect(self.test_many_results)
        layout.addWidget(btn5)
        
        # Label para mostrar resultados
        self.result_label = QLabel("")
        self.result_label.setWordWrap(True)
        self.result_label.setStyleSheet("padding: 10px; background: #2a2a2a;")
        layout.addWidget(self.result_label)
        
    def test_perfect_match(self):
        """Caso con duración exacta"""
        results = [
            {
                'artistName': 'ROJO',
                'trackName': 'Bajo Tu Control',
                'duration': 243,
                'syncedLyrics': '[00:10.00]Lyrics here...'
            },
            {
                'artistName': 'ROJO',
                'trackName': 'Bajo Tu Control (Live)',
                'duration': 250,
                'syncedLyrics': '[00:10.00]Lyrics here...'
            },
            {
                'artistName': 'ROJO',
                'trackName': 'Bajo Tu Control (Acoustic)',
                'duration': 235,
                'syncedLyrics': '[00:10.00]Lyrics here...'
            }
        ]
        self._show_dialog(results, expected_duration=243.0)
        
    def test_multiple_results(self):
        """Caso con varios resultados dentro/fuera de tolerancia"""
        results = [
            {
                'artistName': 'Miel San Marcos',
                'trackName': 'Su Poder',
                'duration': 180,
                'syncedLyrics': '[00:10.00]Lyrics here...'
            },
            {
                'artistName': 'Miel San Marcos',
                'trackName': 'Su Poder (Live)',
                'duration': 182,
                'syncedLyrics': '[00:10.00]Lyrics here...'
            },
            {
                'artistName': 'Miel San Marcos',
                'trackName': 'Su Poder (Version Extendida)',
                'duration': 195,
                'syncedLyrics': '[00:10.00]Lyrics here...'
            },
            {
                'artistName': 'Miel San Marcos',
                'trackName': 'Su Poder (Acústico)',
                'duration': 178,
                'syncedLyrics': '[00:10.00]Lyrics here...'
            }
        ]
        self._show_dialog(results, expected_duration=180.5)
        
    def test_no_tolerance(self):
        """Caso donde ninguno está dentro de tolerancia"""
        results = [
            {
                'artistName': 'Hillsong',
                'trackName': 'Oceans',
                'duration': 500,
                'syncedLyrics': '[00:10.00]Lyrics here...'
            },
            {
                'artistName': 'Hillsong',
                'trackName': 'Oceans (Short)',
                'duration': 200,
                'syncedLyrics': '[00:10.00]Lyrics here...'
            }
        ]
        self._show_dialog(results, expected_duration=350.0)
        
    def test_no_duration(self):
        """Caso sin duración esperada (no resalta ninguno)"""
        results = [
            {
                'artistName': 'Elevation Worship',
                'trackName': 'Way Maker',
                'duration': 240,
                'syncedLyrics': '[00:10.00]Lyrics here...'
            },
            {
                'artistName': 'Elevation Worship',
                'trackName': 'Way Maker (Live)',
                'duration': 255,
                'syncedLyrics': '[00:10.00]Lyrics here...'
            }
        ]
        self._show_dialog(results, expected_duration=None)
        
    def test_many_results(self):
        """Caso con muchos resultados"""
        results = []
        for i in range(10):
            results.append({
                'artistName': f'Artist {i+1}',
                'trackName': f'Track {i+1}',
                'duration': 200 + (i * 5),
                'syncedLyrics': '[00:10.00]Lyrics here...'
            })
        self._show_dialog(results, expected_duration=210.0)
        
    def _show_dialog(self, results: list[dict], expected_duration: float = None):
        """Mostrar diálogo y capturar resultado"""
        dialog = LyricsSelectorDialog(results, expected_duration, parent=self)
        
        # Conectar señales
        dialog.lyrics_selected.connect(
            lambda r: self._on_lyrics_selected(r)
        )
        dialog.selection_cancelled.connect(
            lambda: self._on_selection_cancelled()
        )
        
        dialog.exec()
        
    def _on_lyrics_selected(self, result: dict):
        """Callback cuando usuario selecciona resultado"""
        self.result_label.setText(
            f"✅ Lyrics seleccionados:\n"
            f"  Artista: {result['artistName']}\n"
            f"  Track: {result['trackName']}\n"
            f"  Duración: {result['duration']}s"
        )
        self.result_label.setStyleSheet(
            "padding: 10px; background: #1a4d2e; color: #4ade80;"
        )
        
    def _on_selection_cancelled(self):
        """Callback cuando usuario cancela"""
        self.result_label.setText("✖ Selección cancelada")
        self.result_label.setStyleSheet(
            "padding: 10px; background: #4d1a1a; color: #f87171;"
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
