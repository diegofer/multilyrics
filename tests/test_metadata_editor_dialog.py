"""
Unit tests para MetadataEditorDialog
"""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from ui.widgets.metadata_editor_dialog import MetadataEditorDialog


@pytest.fixture(scope='module')
def qapp():
    """Fixture para QApplication (requerido por Qt)"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestMetadataEditorDialog:
    """Tests para el diálogo de edición de metadatos"""
    
    def test_initialization_with_valid_metadata(self, qapp):
        """Debe inicializar correctamente con metadatos válidos"""
        metadata = {
            'track_name': 'Bajo Tu Control',
            'artist_name': 'ROJO',
            'duration_seconds': 243.5
        }
        
        dialog = MetadataEditorDialog(metadata)
        
        assert dialog._track_name == 'Bajo Tu Control'
        assert dialog._artist_name == 'ROJO'
        assert dialog._duration_seconds == 243.5
        assert dialog._track_input.text() == 'Bajo Tu Control'
        assert dialog._artist_input.text() == 'ROJO'
        
    def test_initialization_with_empty_metadata(self, qapp):
        """Debe manejar metadatos vacíos sin errores"""
        metadata = {
            'track_name': '',
            'artist_name': '',
            'duration_seconds': 0.0
        }
        
        dialog = MetadataEditorDialog(metadata)
        
        assert dialog._track_name == ''
        assert dialog._artist_name == ''
        assert dialog._duration_seconds == 0.0
        
    def test_duration_formatting(self, qapp):
        """Debe formatear duración correctamente en MM:SS"""
        metadata = {
            'track_name': 'Test',
            'artist_name': 'Artist',
            'duration_seconds': 243.5
        }
        
        dialog = MetadataEditorDialog(metadata)
        formatted = dialog._format_duration(243.5)
        
        assert formatted == "04:03"
        
    def test_duration_formatting_edge_cases(self, qapp):
        """Debe formatear duraciones extremas correctamente"""
        dialog = MetadataEditorDialog({
            'track_name': 'Test',
            'artist_name': 'Artist',
            'duration_seconds': 0
        })
        
        assert dialog._format_duration(0) == "00:00"
        assert dialog._format_duration(59) == "00:59"
        assert dialog._format_duration(60) == "01:00"
        assert dialog._format_duration(3599) == "59:59"
        
    def test_metadata_confirmed_signal(self, qapp, qtbot):
        """Debe emitir metadata_confirmed con datos editados al confirmar"""
        metadata = {
            'track_name': 'Original Title',
            'artist_name': 'Original Artist',
            'duration_seconds': 180.0
        }
        
        dialog = MetadataEditorDialog(metadata)
        
        # Editar campos
        dialog._track_input.setText('Edited Title')
        dialog._artist_input.setText('Edited Artist')
        
        # Capturar señal
        with qtbot.waitSignal(dialog.metadata_confirmed) as blocker:
            dialog._search_btn.click()
        
        # Verificar datos emitidos
        emitted_metadata = blocker.args[0]
        assert emitted_metadata['track_name'] == 'Edited Title'
        assert emitted_metadata['artist_name'] == 'Edited Artist'
        assert emitted_metadata['duration_seconds'] == 180.0
        
    def test_search_skipped_signal(self, qapp, qtbot):
        """Debe emitir search_skipped al presionar omitir"""
        metadata = {
            'track_name': 'Test',
            'artist_name': 'Artist',
            'duration_seconds': 180.0
        }
        
        dialog = MetadataEditorDialog(metadata)
        
        # Capturar señal
        with qtbot.waitSignal(dialog.search_skipped):
            dialog._skip_btn.click()
            
    def test_validation_empty_track_name(self, qapp, qtbot):
        """No debe confirmar si el título está vacío"""
        metadata = {
            'track_name': 'Valid Title',
            'artist_name': 'Valid Artist',
            'duration_seconds': 180.0
        }
        
        dialog = MetadataEditorDialog(metadata)
        dialog._track_input.clear()
        
        # Intentar confirmar - no debe emitir señal
        dialog._search_btn.click()
        
        # Diálogo debe seguir abierto (no cerrado con accept)
        assert not dialog.result()
        
    def test_validation_empty_artist_name(self, qapp, qtbot):
        """No debe confirmar si el artista está vacío"""
        metadata = {
            'track_name': 'Valid Title',
            'artist_name': 'Valid Artist',
            'duration_seconds': 180.0
        }
        
        dialog = MetadataEditorDialog(metadata)
        dialog._artist_input.clear()
        
        # Intentar confirmar - no debe emitir señal
        dialog._search_btn.click()
        
        # Diálogo debe seguir abierto
        assert not dialog.result()
        
    def test_whitespace_trimming(self, qapp, qtbot):
        """Debe eliminar espacios en blanco al inicio/final"""
        metadata = {
            'track_name': 'Test',
            'artist_name': 'Artist',
            'duration_seconds': 180.0
        }
        
        dialog = MetadataEditorDialog(metadata)
        
        # Agregar espacios
        dialog._track_input.setText('  Title with spaces  ')
        dialog._artist_input.setText('  Artist with spaces  ')
        
        # Capturar señal
        with qtbot.waitSignal(dialog.metadata_confirmed) as blocker:
            dialog._search_btn.click()
        
        # Verificar trimming
        emitted_metadata = blocker.args[0]
        assert emitted_metadata['track_name'] == 'Title with spaces'
        assert emitted_metadata['artist_name'] == 'Artist with spaces'
        
    def test_modal_property(self, qapp):
        """Diálogo debe ser modal"""
        metadata = {
            'track_name': 'Test',
            'artist_name': 'Artist',
            'duration_seconds': 180.0
        }
        
        dialog = MetadataEditorDialog(metadata)
        assert dialog.isModal()
        
    def test_window_properties(self, qapp):
        """Verificar propiedades básicas de la ventana"""
        metadata = {
            'track_name': 'Test',
            'artist_name': 'Artist',
            'duration_seconds': 180.0
        }
        
        dialog = MetadataEditorDialog(metadata)
        
        assert dialog.windowTitle() == "Editar Metadatos"
        assert dialog.minimumWidth() == 500
