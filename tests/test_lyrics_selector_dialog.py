"""
Unit tests para LyricsSelectorDialog
"""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from ui.widgets.lyrics_selector_dialog import LyricsSelectorDialog


@pytest.fixture(scope='module')
def qapp():
    """Fixture para QApplication (requerido por Qt)"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def sample_results():
    """Resultados de ejemplo para tests"""
    return [
        {
            'artistName': 'ROJO',
            'trackName': 'Bajo Tu Control',
            'duration': 243,
            'syncedLyrics': '[00:10.00]Test lyrics 1'
        },
        {
            'artistName': 'ROJO',
            'trackName': 'Bajo Tu Control (Live)',
            'duration': 250,
            'syncedLyrics': '[00:10.00]Test lyrics 2'
        },
        {
            'artistName': 'ROJO',
            'trackName': 'Bajo Tu Control (Acoustic)',
            'duration': 235,
            'syncedLyrics': '[00:10.00]Test lyrics 3'
        }
    ]


class TestLyricsSelectorDialog:
    """Tests para el diálogo de selección de lyrics"""
    
    def test_initialization_with_results(self, qapp, sample_results):
        """Debe inicializar correctamente con lista de resultados"""
        dialog = LyricsSelectorDialog(sample_results, expected_duration=243.0)
        
        assert dialog._results == sample_results
        assert dialog._expected_duration == 243.0
        assert dialog._list_widget.count() == 3
        
    def test_initialization_without_duration(self, qapp, sample_results):
        """Debe manejar ausencia de duración esperada"""
        dialog = LyricsSelectorDialog(sample_results, expected_duration=None)
        
        assert dialog._expected_duration is None
        assert dialog._list_widget.count() == 3
        
    def test_duration_formatting(self, qapp, sample_results):
        """Debe formatear duración correctamente en MM:SS"""
        dialog = LyricsSelectorDialog(sample_results, expected_duration=243.0)
        
        assert dialog._format_duration(243) == "04:03"
        assert dialog._format_duration(0) == "00:00"
        assert dialog._format_duration(59) == "00:59"
        assert dialog._format_duration(3600) == "60:00"
        
    def test_result_formatting_with_duration(self, qapp, sample_results):
        """Debe formatear resultado con diferencia de duración"""
        dialog = LyricsSelectorDialog(sample_results, expected_duration=243.0)
        
        result = sample_results[0]  # duration=243
        formatted = dialog._format_result(result)
        
        assert "ROJO - Bajo Tu Control [04:03]" in formatted
        assert "(Δ +0s)" in formatted or "(Δ -0s)" in formatted
        
    def test_result_formatting_without_duration(self, qapp, sample_results):
        """Debe formatear resultado sin mostrar diferencia cuando no hay duración esperada"""
        dialog = LyricsSelectorDialog(sample_results, expected_duration=None)
        
        result = sample_results[0]
        formatted = dialog._format_result(result)
        
        assert "ROJO - Bajo Tu Control [04:03]" in formatted
        assert "Δ" not in formatted
        
    def test_is_within_tolerance(self, qapp, sample_results):
        """Debe identificar correctamente resultados dentro de tolerancia (±2s)"""
        dialog = LyricsSelectorDialog(sample_results, expected_duration=243.0)
        
        # Exacto
        assert dialog._is_within_tolerance(sample_results[0]) is True  # 243s
        
        # Fuera de tolerancia
        assert dialog._is_within_tolerance(sample_results[1]) is False  # 250s (+7s)
        
        # En el límite (243 ± 2)
        result_edge = {'duration': 245}  # +2s
        assert dialog._is_within_tolerance(result_edge) is True
        
        result_out = {'duration': 246}  # +3s
        assert dialog._is_within_tolerance(result_out) is False
        
    def test_is_within_tolerance_no_expected_duration(self, qapp, sample_results):
        """Sin duración esperada, ninguno debe estar dentro de tolerancia"""
        dialog = LyricsSelectorDialog(sample_results, expected_duration=None)
        
        for result in sample_results:
            assert dialog._is_within_tolerance(result) is False
            
    def test_list_population(self, qapp, sample_results):
        """Debe poblar la lista con todos los resultados"""
        dialog = LyricsSelectorDialog(sample_results, expected_duration=243.0)
        
        assert dialog._list_widget.count() == len(sample_results)
        
        # Verificar que cada item tiene su resultado en UserRole
        for i in range(dialog._list_widget.count()):
            item = dialog._list_widget.item(i)
            stored_result = item.data(Qt.ItemDataRole.UserRole)
            assert stored_result == sample_results[i]
            
    def test_select_button_initially_disabled(self, qapp, sample_results):
        """Botón de selección debe estar deshabilitado inicialmente si no hay selección"""
        dialog = LyricsSelectorDialog(sample_results, expected_duration=None)
        
        # Limpiar cualquier selección automática
        dialog._list_widget.clearSelection()
        
        # Verificar estado
        assert dialog._select_btn.isEnabled() is False
        
    def test_select_button_enabled_on_selection(self, qapp, qtbot, sample_results):
        """Botón de selección debe habilitarse cuando se selecciona un item"""
        dialog = LyricsSelectorDialog(sample_results, expected_duration=243.0)
        
        # Seleccionar primer item manualmente
        dialog._list_widget.clearSelection()  # Limpiar auto-selección
        dialog._select_btn.setEnabled(False)  # Reset estado
        
        dialog._list_widget.setCurrentRow(0)
        
        # Procesar eventos para que la señal se emita
        qtbot.wait(10)
        
        assert dialog._select_btn.isEnabled() is True
        
    def test_lyrics_selected_signal_on_confirm(self, qapp, qtbot, sample_results):
        """Debe emitir lyrics_selected con resultado correcto al confirmar"""
        dialog = LyricsSelectorDialog(sample_results, expected_duration=243.0)
        
        # Seleccionar segundo resultado
        dialog._list_widget.setCurrentRow(1)
        
        # Capturar señal
        with qtbot.waitSignal(dialog.lyrics_selected) as blocker:
            dialog._select_btn.click()
        
        # Verificar resultado emitido
        emitted_result = blocker.args[0]
        assert emitted_result == sample_results[1]
        assert emitted_result['trackName'] == 'Bajo Tu Control (Live)'
        
    def test_selection_cancelled_signal(self, qapp, qtbot, sample_results):
        """Debe emitir selection_cancelled al cancelar"""
        dialog = LyricsSelectorDialog(sample_results, expected_duration=243.0)
        
        with qtbot.waitSignal(dialog.selection_cancelled):
            dialog._cancel_btn.click()
            
    def test_double_click_selects(self, qapp, qtbot, sample_results):
        """Doble click debe confirmar selección directamente"""
        dialog = LyricsSelectorDialog(sample_results, expected_duration=243.0)
        
        item = dialog._list_widget.item(0)
        
        with qtbot.waitSignal(dialog.lyrics_selected) as blocker:
            dialog._on_item_double_clicked(item)
        
        # Verificar resultado
        emitted_result = blocker.args[0]
        assert emitted_result == sample_results[0]
        
    def test_cannot_select_without_selection(self, qapp, sample_results):
        """No debe hacer nada al confirmar sin selección"""
        dialog = LyricsSelectorDialog(sample_results, expected_duration=None)
        
        # Limpiar selección
        dialog._list_widget.clearSelection()
        
        # Intentar confirmar - no debe crashear
        dialog._on_select_clicked()
        
        # Diálogo debe seguir abierto (no accept)
        assert not dialog.result()
        
    def test_modal_property(self, qapp, sample_results):
        """Diálogo debe ser modal"""
        dialog = LyricsSelectorDialog(sample_results, expected_duration=243.0)
        assert dialog.isModal()
        
    def test_window_properties(self, qapp, sample_results):
        """Verificar propiedades básicas de la ventana"""
        dialog = LyricsSelectorDialog(sample_results, expected_duration=243.0)
        
        assert dialog.windowTitle() == "Seleccionar Lyrics"
        assert dialog.minimumWidth() == 600
        assert dialog.minimumHeight() == 400
        
    def test_empty_results_list(self, qapp):
        """Debe manejar lista vacía sin errores"""
        dialog = LyricsSelectorDialog([], expected_duration=243.0)
        
        assert dialog._list_widget.count() == 0
        assert dialog._select_btn.isEnabled() is False
        
    def test_single_result(self, qapp):
        """Debe manejar correctamente un solo resultado"""
        results = [
            {
                'artistName': 'Artist',
                'trackName': 'Track',
                'duration': 180,
                'syncedLyrics': '[00:10.00]Lyrics'
            }
        ]
        
        dialog = LyricsSelectorDialog(results, expected_duration=180.0)
        
        assert dialog._list_widget.count() == 1
        # Primer resultado dentro de tolerancia debe estar auto-seleccionado
        assert dialog._list_widget.currentRow() == 0
