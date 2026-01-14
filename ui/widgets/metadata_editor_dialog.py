"""
MetadataEditorDialog - Editor de metadatos antes de búsqueda de lyrics
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QGroupBox, QFormLayout
)
from ui.styles import StyleManager


class MetadataEditorDialog(QDialog):
    """
    Diálogo para editar título y artista antes de buscar lyrics en LRCLIB.
    
    Caso de uso típico:
    - Extracción automática puede dar metadatos incorrectos:
      Original: "ROJO | Bajo Tu Control (Video de Letras)"
      Editado: "Bajo Tu Control"
    
    Signals:
        metadata_confirmed(dict): Emitido cuando usuario confirma búsqueda.
            dict contiene: track_name, artist_name, duration_seconds
        search_skipped(): Emitido cuando usuario decide omitir búsqueda
    """
    
    metadata_confirmed = Signal(dict)
    search_skipped = Signal()
    
    def __init__(self, metadata: dict, parent=None):
        """
        Args:
            metadata: Dict con track_name, artist_name, duration_seconds
        """
        super().__init__(parent)
        
        # Almacenar datos originales
        self._track_name = metadata.get('track_name', '')
        self._artist_name = metadata.get('artist_name', '')
        self._duration_seconds = metadata.get('duration_seconds', 0.0)
        
        self._setup_ui()
        self._apply_styles()
        self._connect_signals()
        
    def _setup_ui(self):
        """Construir interfaz"""
        self.setWindowTitle("Editar Metadatos")
        self.setModal(True)
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header con instrucciones
        header_label = QLabel(
            "Edita los metadatos para mejorar la búsqueda de lyrics.\n"
            "Los datos extraídos pueden contener información extra."
        )
        header_label.setWordWrap(True)
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header_label)
        
        # Group box con campos de edición
        metadata_group = QGroupBox("Metadatos de Búsqueda")
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        # Campo: Título
        self._track_input = QLineEdit()
        self._track_input.setText(self._track_name)
        self._track_input.setPlaceholderText("Ej: Bajo Tu Control")
        form_layout.addRow("Título:", self._track_input)
        
        # Campo: Artista
        self._artist_input = QLineEdit()
        self._artist_input.setText(self._artist_name)
        self._artist_input.setPlaceholderText("Ej: ROJO")
        form_layout.addRow("Artista:", self._artist_input)
        
        # Campo: Duración (solo lectura)
        duration_label = QLabel(self._format_duration(self._duration_seconds))
        duration_label.setEnabled(False)
        form_layout.addRow("Duración:", duration_label)
        
        metadata_group.setLayout(form_layout)
        layout.addWidget(metadata_group)
        
        layout.addStretch()
        
        # Botones de acción
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        self._skip_btn = QPushButton("⏭ Omitir Búsqueda")
        self._skip_btn.setToolTip("Crear multitrack sin descargar lyrics")
        self._skip_btn.setMinimumHeight(36)
        
        self._search_btn = QPushButton("🔍 Buscar Lyrics")
        self._search_btn.setToolTip("Buscar lyrics con los metadatos editados")
        self._search_btn.setMinimumHeight(36)
        self._search_btn.setDefault(True)
        
        buttons_layout.addWidget(self._skip_btn)
        buttons_layout.addWidget(self._search_btn)
        
        layout.addLayout(buttons_layout)
        
    def _apply_styles(self):
        """Aplicar estilos consistentes con el tema de la aplicación"""
        # Background del diálogo
        bg = StyleManager.get_color("bg_base")
        self.setStyleSheet(f"QDialog {{ background-color: {bg.name()}; }}")
        
        # Colores principales
        text_normal = StyleManager.get_color("text_normal")
        text_dim = StyleManager.get_color("text_dim")
        bg_panel = StyleManager.get_color("bg_panel")
        border_light = StyleManager.PALETTE["border_light"]
        accent = StyleManager.get_color("accent")
        btn_normal = StyleManager.PALETTE["btn_normal"]
        btn_hover = StyleManager.PALETTE["btn_hover"]
        
        # Labels
        for label in self.findChildren(QLabel):
            label.setStyleSheet(f"color: {text_normal.name()};")
        
        # GroupBox
        self.findChild(QGroupBox).setStyleSheet(f"""
            QGroupBox {{
                color: {text_normal.name()};
                border: 1px solid {border_light};
                border-radius: 4px;
                margin-top: 8px;
                padding: 10px;
                background-color: {bg_panel.name()};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
                color: {accent.name()};
            }}
        """)
        
        # LineEdits
        for line_edit in self.findChildren(QLineEdit):
            line_edit.setStyleSheet(f"""
                QLineEdit {{
                    background-color: {bg_panel.name()};
                    color: {text_normal.name()};
                    border: 1px solid {border_light};
                    border-radius: 3px;
                    padding: 6px;
                    selection-background-color: {accent.name()};
                    selection-color: {bg_panel.name()};
                }}
                QLineEdit:focus {{
                    border: 1px solid {accent.name()};
                }}
            """)
        
        # Botones
        self._skip_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {btn_normal};
                color: {text_normal.name()};
                border: 1px solid {border_light};
                border-radius: 4px;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background-color: {btn_hover};
            }}
            QPushButton:pressed {{
                background-color: rgba(10, 16, 34, 0.85);
            }}
        """)
        
        self._search_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {btn_normal};
                color: {accent.name()};
                border: 1px solid {accent.name()};
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {btn_hover};
                border: 2px solid {accent.name()};
            }}
            QPushButton:pressed {{
                background-color: rgba(10, 16, 34, 0.85);
            }}
            QPushButton:default {{
                border: 2px solid {accent.name()};
            }}
        """)
        
    def _connect_signals(self):
        """Conectar señales de botones"""
        self._search_btn.clicked.connect(self._on_search_clicked)
        self._skip_btn.clicked.connect(self._on_skip_clicked)
        
    def _on_search_clicked(self):
        """Usuario confirma búsqueda con metadatos editados"""
        track_name = self._track_input.text().strip()
        artist_name = self._artist_input.text().strip()
        
        # Validar que no estén vacíos
        if not track_name or not artist_name:
            # TODO: Mostrar mensaje de error (en fase posterior)
            return
        
        # Emitir metadatos editados
        metadata = {
            'track_name': track_name,
            'artist_name': artist_name,
            'duration_seconds': self._duration_seconds
        }
        self.metadata_confirmed.emit(metadata)
        self.accept()
        
    def _on_skip_clicked(self):
        """Usuario decide omitir búsqueda de lyrics"""
        self.search_skipped.emit()
        self.reject()
        
    def _format_duration(self, seconds: float) -> str:
        """Formatear duración en MM:SS"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
