"""
Test standalone para TimelineView edit mode buttons
Ejecutar: python test_timeline_buttons.py
"""

import sys
from pathlib import Path

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel
from PySide6.QtCore import Qt
from audio.timeline_view import TimelineView
from core.timeline_model import TimelineModel


class TestWindow(QMainWindow):
    """Ventana de prueba para verificar botones de edición en TimelineView"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Test: Timeline Edit Mode Buttons")
        self.resize(1000, 600)
        
        # Widget central
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # TimelineModel
        self.timeline = TimelineModel(sample_rate=44100)
        self.timeline.set_duration_seconds(180.0)  # 3 minutos de audio dummy
        
        # TimelineView
        self.timeline_view = TimelineView(timeline=self.timeline)
        
        # Cargar audio de prueba (puedes usar cualquier archivo de audio)
        # Para demo, vamos a usar datos sintéticos
        import numpy as np
        self.timeline_view.samples = np.random.randn(44100 * 180).astype(np.float32) * 0.3
        self.timeline_view.sr = 44100
        self.timeline_view.total_samples = len(self.timeline_view.samples)
        self.timeline_view.duration_seconds = 180.0
        self.timeline_view.center_sample = self.timeline_view.total_samples // 2
        
        layout.addWidget(self.timeline_view)
        
        # Controles
        controls_layout = QVBoxLayout()
        
        # Toggle edit mode
        self.toggle_btn = QPushButton("Toggle Edit Mode (Currently: OFF)")
        self.toggle_btn.clicked.connect(self.toggle_edit_mode)
        controls_layout.addWidget(self.toggle_btn)
        
        # Label para mostrar eventos
        self.event_label = QLabel("Eventos:")
        self.event_label.setStyleSheet("padding: 10px; background: #2a2a2a; color: #fff;")
        self.event_label.setMinimumHeight(80)
        controls_layout.addWidget(self.event_label)
        
        layout.addLayout(controls_layout)
        
        # Conectar señales de los botones
        self.timeline_view.edit_metadata_clicked.connect(self.on_edit_metadata)
        self.timeline_view.reload_lyrics_clicked.connect(self.on_reload_lyrics)
        
        # Estado
        self.edit_mode = False
        
    def toggle_edit_mode(self):
        """Alternar modo de edición"""
        self.edit_mode = not self.edit_mode
        self.timeline_view.set_lyrics_edit_mode(self.edit_mode)
        
        status = "ON" if self.edit_mode else "OFF"
        self.toggle_btn.setText(f"Toggle Edit Mode (Currently: {status})")
        
        if self.edit_mode:
            self.event_label.setText("✅ Edit mode ENABLED\nBotones visibles en el borde derecho →")
            self.event_label.setStyleSheet("padding: 10px; background: #1a4d2e; color: #4ade80;")
        else:
            self.event_label.setText("⏹ Edit mode DISABLED\nBotones ocultos")
            self.event_label.setStyleSheet("padding: 10px; background: #2a2a2a; color: #fff;")
    
    def on_edit_metadata(self):
        """Callback cuando se hace click en Edit Metadata"""
        self.event_label.setText("📝 EDIT METADATA clicked!\n\n(Aquí se abriría MetadataEditorDialog)")
        self.event_label.setStyleSheet("padding: 10px; background: #4d3a1a; color: #fbbf24;")
        
    def on_reload_lyrics(self):
        """Callback cuando se hace click en Reload Lyrics"""
        self.event_label.setText("🔄 RELOAD LYRICS clicked!\n\n(Aquí se re-descargarían los lyrics)")
        self.event_label.setStyleSheet("padding: 10px; background: #1a3a4d; color: #60a5fa;")


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
