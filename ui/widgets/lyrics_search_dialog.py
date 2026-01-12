"""
LyricsSearchDialog - Unified dialog for metadata editing and lyrics selection.

Combines functionality of MetadataEditorDialog and LyricsSelectorDialog.
Shows initial results and allows user to refine search by editing metadata.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QListWidget, QListWidgetItem, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from ui.style_manager import StyleManager


class LyricsSearchDialog(QDialog):
    """Unified dialog for searching and selecting lyrics.
    
    Features:
    - Editable metadata fields (track_name, artist_name)
    - Manual search button (no auto-search/debounce)
    - Results list with duration highlighting (green if ≤1s)
    - Download selected or skip
    """
    
    # Signals
    lyrics_selected = Signal(dict)  # Emits selected result
    search_skipped = Signal()       # User skipped lyrics search
    
    def __init__(self, metadata: dict, initial_results: list, lyrics_loader, parent=None, skip_initial_search: bool = False):
        """
        Args:
            metadata: Dict with 'track_name', 'artist_name', 'duration_seconds'
            initial_results: List of initial search results (may be empty)
            lyrics_loader: LyricsLoader instance for manual searches
            parent: Parent widget
            skip_initial_search: If True, ignore initial_results and show empty dialog
        """
        super().__init__(parent)
        
        self.metadata = metadata
        self.lyrics_loader = lyrics_loader
        # If skip_initial_search is True, start with empty results
        self.results = [] if skip_initial_search else initial_results
        self.selected_result = None
        
        self.setWindowTitle("Buscar Letras")
        self.setModal(True)
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        
        self._setup_ui()
        self._populate_results()
        
        # Apply styling
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {StyleManager.get_color('background')};
            }}
            QLabel {{
                color: {StyleManager.get_color('text')};
                font-size: 12px;
            }}
            QLabel#dim_label {{
                color: {StyleManager.get_color('text_dim')};
                font-size: 11px;
            }}
            QLineEdit {{
                background-color: {StyleManager.get_color('surface')};
                color: {StyleManager.get_color('text')};
                border: 1px solid {StyleManager.get_color('border')};
                border-radius: 4px;
                padding: 8px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border: 1px solid {StyleManager.get_color('accent')};
            }}
            QPushButton {{
                background-color: {StyleManager.get_color('surface')};
                color: {StyleManager.get_color('text')};
                border: 1px solid {StyleManager.get_color('border')};
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {StyleManager.get_color('surface_hover')};
                border: 1px solid {StyleManager.get_color('accent')};
            }}
            QPushButton#primary {{
                background-color: {StyleManager.get_color('accent')};
                color: {StyleManager.get_color('background')};
                border: none;
            }}
            QPushButton#primary:hover {{
                background-color: {StyleManager.get_color('accent_hover')};
            }}
            QPushButton:disabled {{
                background-color: {StyleManager.get_color('surface')};
                color: {StyleManager.get_color('text_dim')};
                border: 1px solid {StyleManager.get_color('border')};
            }}
            QListWidget {{
                background-color: {StyleManager.get_color('surface')};
                color: {StyleManager.get_color('text')};
                border: 1px solid {StyleManager.get_color('border')};
                border-radius: 4px;
                font-size: 13px;
            }}
            QListWidget::item {{
                padding: 8px;
                border-bottom: 1px solid {StyleManager.get_color('border')};
            }}
            QListWidget::item:selected {{
                background-color: {StyleManager.get_color('accent')};
                color: {StyleManager.get_color('background')};
            }}
            QListWidget::item:hover {{
                background-color: {StyleManager.get_color('surface_hover')};
            }}
        """)
    
    def _setup_ui(self):
        """Setup dialog UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("Buscar Letras Sincronizadas")
        title_font = StyleManager.get_font()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # Metadata fields
        fields_frame = QFrame()
        fields_layout = QVBoxLayout(fields_frame)
        fields_layout.setSpacing(8)
        
        # Track Name
        track_label = QLabel("Nombre de la Canción:")
        fields_layout.addWidget(track_label)
        
        self.track_input = QLineEdit()
        self.track_input.setText(self.metadata.get('track_name', ''))
        self.track_input.setPlaceholderText("Ingresa el nombre de la canción...")
        fields_layout.addWidget(self.track_input)
        
        # Artist Name
        artist_label = QLabel("Artista:")
        fields_layout.addWidget(artist_label)
        
        self.artist_input = QLineEdit()
        self.artist_input.setText(self.metadata.get('artist_name', ''))
        self.artist_input.setPlaceholderText("Ingresa el nombre del artista...")
        fields_layout.addWidget(self.artist_input)
        
        # Duration info (read-only)
        duration = self.metadata.get('duration_seconds', 0)
        duration_text = f"Duración: {int(duration // 60):02d}:{int(duration % 60):02d}"
        duration_label = QLabel(duration_text)
        duration_label.setObjectName("dim_label")
        fields_layout.addWidget(duration_label)
        
        layout.addWidget(fields_frame)
        
        # Search button
        self.search_btn = QPushButton("🔍 Buscar Letras")
        self.search_btn.setObjectName("primary")
        self.search_btn.clicked.connect(self._on_search_clicked)
        layout.addWidget(self.search_btn)
        
        # Results label
        results_header = QHBoxLayout()
        self.results_label = QLabel(f"Resultados ({len(self.results)}):")
        results_header.addWidget(self.results_label)
        results_header.addStretch()
        layout.addLayout(results_header)
        
        # Results list
        self.results_list = QListWidget()
        self.results_list.itemClicked.connect(self._on_result_clicked)
        self.results_list.itemDoubleClicked.connect(self._on_result_double_clicked)
        layout.addWidget(self.results_list, 1)  # Stretch factor 1
        
        # Info label
        self.info_label = QLabel("")
        self.info_label.setObjectName("dim_label")
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        self.skip_btn = QPushButton("Omitir")
        self.skip_btn.clicked.connect(self._on_skip_clicked)
        buttons_layout.addWidget(self.skip_btn)
        
        self.download_btn = QPushButton("Descargar Seleccionada")
        self.download_btn.setObjectName("primary")
        self.download_btn.setEnabled(False)
        self.download_btn.clicked.connect(self._on_download_clicked)
        buttons_layout.addWidget(self.download_btn)
        
        layout.addLayout(buttons_layout)
    
    def _populate_results(self):
        """Populate results list with highlighting for exact matches"""
        self.results_list.clear()
        self.results_label.setText(f"Resultados ({len(self.results)}):")
        
        if not self.results:
            self.info_label.setText("No se encontraron letras sincronizadas. Intenta editar los metadatos y buscar nuevamente.")
            return
        
        duration = self.metadata.get('duration_seconds', 0)
        exact_match_found = False
        
        for result in self.results:
            track_name = result.get('trackName', 'Desconocido')
            artist_name = result.get('artistName', 'Desconocido')
            result_duration = result.get('duration', 0)
            
            # Calculate duration difference
            duration_diff = abs(result_duration - duration) if result_duration else 999
            
            # Format item text
            duration_str = f"{int(result_duration // 60):02d}:{int(result_duration % 60):02d}"
            diff_str = f"Δ {duration_diff:+.1f}s" if duration_diff < 999 else ""
            
            item_text = f"{track_name} - {artist_name} ({duration_str}) {diff_str}"
            
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, result)  # Store result data
            
            # Add item to list first
            self.results_list.addItem(item)
            
            # Highlight exact matches (≤1s) in green
            if duration_diff <= 1.0:
                exact_match_found = True
                item.setForeground(StyleManager.get_color('success'))
                # Auto-select first exact match
                if not self.selected_result:
                    self.results_list.setCurrentItem(item)
                    self.selected_result = result
                    self.download_btn.setEnabled(True)
        
        # Update info label
        if exact_match_found:
            self.info_label.setText("✓ Los elementos en verde son coincidencias exactas (≤1s de diferencia)")
        else:
            self.info_label.setText("No se encontraron coincidencias exactas de duración. Aún puedes seleccionar cualquier resultado.")
    
    def _on_search_clicked(self):
        """User clicked search button - perform new search"""
        track_name = self.track_input.text().strip()
        artist_name = self.artist_input.text().strip()
        
        if not track_name or not artist_name:
            self.info_label.setText("⚠ Por favor ingresa el nombre de la canción y el artista")
            return
        
        # Show loading state
        self.search_btn.setEnabled(False)
        self.search_btn.setText("Buscando...")
        self.info_label.setText("Buscando en LRCLIB...")
        
        # Perform search
        try:
            results = self.lyrics_loader.search_all(track_name, artist_name)
            self.results = results
            self._populate_results()
        except Exception as e:
            self.info_label.setText(f"⚠ Error en la búsqueda: {str(e)}")
        finally:
            self.search_btn.setEnabled(True)
            self.search_btn.setText("🔍 Buscar Letras")
    
    def _on_result_clicked(self, item: QListWidgetItem):
        """User clicked a result item"""
        self.selected_result = item.data(Qt.UserRole)
        self.download_btn.setEnabled(True)
    
    def _on_result_double_clicked(self, item: QListWidgetItem):
        """User double-clicked a result - download immediately"""
        self.selected_result = item.data(Qt.UserRole)
        self._on_download_clicked()
    
    def _on_download_clicked(self):
        """User confirmed download"""
        if self.selected_result:
            self.lyrics_selected.emit(self.selected_result)
            self.accept()
    
    def _on_skip_clicked(self):
        """User skipped lyrics search"""
        self.search_skipped.emit()
        self.reject()
