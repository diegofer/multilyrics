"""
LyricsSelectorDialog - Selección manual de lyrics cuando hay múltiples resultados
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QListWidget, QListWidgetItem
)
from PySide6.QtGui import QFont
from ui.styles import StyleManager


class LyricsSelectorDialog(QDialog):
    """
    Diálogo para selección manual de lyrics cuando LRCLIB retorna múltiples resultados.
    
    Muestra lista de resultados con formato:
    "Artist - Track [MM:SS] (Δ +2s)"
    
    Resalta en verde los resultados dentro de 2s de tolerancia respecto a la duración esperada.
    
    Signals:
        lyrics_selected(dict): Emitido cuando usuario selecciona un resultado.
            dict es el resultado completo de LRCLIB API
        selection_cancelled(): Emitido cuando usuario cancela la selección
    """
    
    lyrics_selected = Signal(dict)
    selection_cancelled = Signal()
    
    DURATION_TOLERANCE = 2.0  # segundos
    
    def __init__(self, results: list[dict], expected_duration: float = None, parent=None):
        """
        Args:
            results: Lista de resultados de LRCLIB API (deben tener syncedLyrics)
            expected_duration: Duración esperada en segundos (opcional, para resaltar matches)
        """
        super().__init__(parent)
        
        self._results = results
        self._expected_duration = expected_duration
        self._selected_result = None
        
        self._setup_ui()
        self._populate_list()
        self._apply_styles()
        self._connect_signals()
        
    def _setup_ui(self):
        """Construir interfaz"""
        self.setWindowTitle("Seleccionar Lyrics")
        self.setModal(True)
        self.setMinimumSize(600, 400)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header con instrucciones
        header_label = QLabel(
            f"Se encontraron {len(self._results)} resultados con lyrics sincronizados.\n"
            "Selecciona el que mejor coincida con tu audio."
        )
        header_label.setWordWrap(True)
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header_label)
        
        # Info de duración esperada
        if self._expected_duration is not None:
            duration_label = QLabel(
                f"Duración esperada: {self._format_duration(self._expected_duration)} "
                f"(±{self.DURATION_TOLERANCE}s de tolerancia)"
            )
            duration_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(duration_label)
        
        # Lista de resultados
        self._list_widget = QListWidget()
        self._list_widget.setAlternatingRowColors(True)
        layout.addWidget(self._list_widget)
        
        # Leyenda
        legend_label = QLabel("🟢 = dentro de tolerancia  |  ⚪ = fuera de tolerancia")
        legend_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(legend_label)
        
        # Botones de acción
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        self._cancel_btn = QPushButton("✖ Cancelar")
        self._cancel_btn.setToolTip("No descargar lyrics")
        self._cancel_btn.setMinimumHeight(36)
        
        self._select_btn = QPushButton("✔ Seleccionar")
        self._select_btn.setToolTip("Descargar lyrics del resultado seleccionado")
        self._select_btn.setMinimumHeight(36)
        self._select_btn.setDefault(True)
        self._select_btn.setEnabled(False)  # Deshabilitado hasta seleccionar
        
        buttons_layout.addWidget(self._cancel_btn)
        buttons_layout.addWidget(self._select_btn)
        
        layout.addLayout(buttons_layout)
        
    def _populate_list(self):
        """Llenar lista con resultados formateados"""
        for idx, result in enumerate(self._results):
            item_text = self._format_result(result)
            item = QListWidgetItem(item_text)
            
            # Guardar resultado en data
            item.setData(Qt.ItemDataRole.UserRole, result)
            
            # Aplicar estilo según tolerancia
            if self._is_within_tolerance(result):
                item.setForeground(StyleManager.get_color("accent_play"))
                font = QFont()
                font.setBold(True)
                item.setFont(font)
            
            self._list_widget.addItem(item)
            
            # Auto-seleccionar el primer match dentro de tolerancia
            if idx == 0 and self._is_within_tolerance(result):
                self._list_widget.setCurrentItem(item)
        
    def _format_result(self, result: dict) -> str:
        """
        Formatear resultado para display en lista
        Formato: "Artist - Track [MM:SS] (Δ +2s)"
        """
        artist = result.get('artistName', 'Unknown')
        track = result.get('trackName', 'Unknown')
        duration = result.get('duration', 0)
        
        formatted = f"{artist} - {track} [{self._format_duration(duration)}]"
        
        # Agregar diferencia si hay duración esperada
        if self._expected_duration is not None:
            diff = duration - self._expected_duration
            sign = '+' if diff >= 0 else ''
            formatted += f" (Δ {sign}{diff:.0f}s)"
        
        return formatted
    
    def _is_within_tolerance(self, result: dict) -> bool:
        """Verificar si el resultado está dentro de la tolerancia de duración"""
        if self._expected_duration is None:
            return False
        
        duration = result.get('duration', 0)
        diff = abs(duration - self._expected_duration)
        return diff <= self.DURATION_TOLERANCE
    
    def _format_duration(self, seconds: float) -> str:
        """Formatear duración en MM:SS"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
    
    def _apply_styles(self):
        """Aplicar estilos consistentes con el tema"""
        # Background del diálogo
        bg = StyleManager.get_color("bg_base")
        self.setStyleSheet(f"QDialog {{ background-color: {bg.name()}; }}")
        
        # Colores principales
        text_normal = StyleManager.get_color("text_normal")
        text_dim = StyleManager.get_color("text_dim")
        bg_panel = StyleManager.get_color("bg_panel")
        bg_workspace = StyleManager.get_color("bg_workspace")
        border_light = StyleManager.PALETTE["border_light"]
        accent = StyleManager.get_color("accent")
        btn_normal = StyleManager.PALETTE["btn_normal"]
        btn_hover = StyleManager.PALETTE["btn_hover"]
        
        # Labels
        for label in self.findChildren(QLabel):
            label.setStyleSheet(f"color: {text_normal.name()};")
        
        # ListWidget
        self._list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: {bg_workspace.name()};
                color: {text_normal.name()};
                border: 1px solid {border_light};
                border-radius: 4px;
                padding: 5px;
                outline: none;
            }}
            QListWidget::item {{
                padding: 8px;
                border-radius: 3px;
            }}
            QListWidget::item:hover {{
                background-color: {bg_panel.name()};
            }}
            QListWidget::item:selected {{
                background-color: {bg_panel.name()};
                border: 1px solid {accent.name()};
            }}
            QListWidget::item:selected:hover {{
                background-color: rgba(30, 50, 110, 0.8);
            }}
        """)
        
        # Botones
        self._cancel_btn.setStyleSheet(f"""
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
        
        self._select_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {btn_normal};
                color: {accent.name()};
                border: 1px solid {accent.name()};
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover:enabled {{
                background-color: {btn_hover};
                border: 2px solid {accent.name()};
            }}
            QPushButton:pressed:enabled {{
                background-color: rgba(10, 16, 34, 0.85);
            }}
            QPushButton:disabled {{
                color: {text_dim.name()};
                border: 1px solid {border_light};
            }}
            QPushButton:default {{
                border: 2px solid {accent.name()};
            }}
        """)
        
    def _connect_signals(self):
        """Conectar señales"""
        self._list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        self._list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        self._select_btn.clicked.connect(self._on_select_clicked)
        self._cancel_btn.clicked.connect(self._on_cancel_clicked)
        
    def _on_selection_changed(self):
        """Habilitar botón de selección cuando hay item seleccionado"""
        has_selection = len(self._list_widget.selectedItems()) > 0
        self._select_btn.setEnabled(has_selection)
        
    def _on_item_double_clicked(self, item: QListWidgetItem):
        """Doble click confirma selección directamente"""
        result = item.data(Qt.ItemDataRole.UserRole)
        self.lyrics_selected.emit(result)
        self.accept()
        
    def _on_select_clicked(self):
        """Usuario confirma selección"""
        selected_items = self._list_widget.selectedItems()
        if not selected_items:
            return
        
        result = selected_items[0].data(Qt.ItemDataRole.UserRole)
        self.lyrics_selected.emit(result)
        self.accept()
        
    def _on_cancel_clicked(self):
        """Usuario cancela selección"""
        self.selection_cancelled.emit()
        self.reject()
