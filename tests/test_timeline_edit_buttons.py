"""
Unit tests para TimelineView edit mode buttons
"""

import pytest
import numpy as np
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QPoint
from ui.widgets.timeline_view import TimelineView
from models.timeline_model import TimelineModel


@pytest.fixture(scope='module')
def qapp():
    """Fixture para QApplication (requerido por Qt)"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def timeline_view(qapp):
    """Fixture para TimelineView con datos de prueba"""
    timeline = TimelineModel(sample_rate=44100)
    timeline.set_duration_seconds(180.0)
    
    view = TimelineView(timeline=timeline)
    
    # Cargar datos sintéticos
    view.samples = np.random.randn(44100 * 180).astype(np.float32) * 0.3
    view.sr = 44100
    view.total_samples = len(view.samples)
    view.duration_seconds = 180.0
    view.center_sample = view.total_samples // 2
    
    # Forzar tamaño para cálculos consistentes
    view.resize(800, 400)
    
    return view


class TestTimelineViewEditButtons:
    """Tests para botones de edición en TimelineView"""
    
    def test_buttons_hidden_by_default(self, timeline_view):
        """Botones deben estar ocultos por defecto"""
        assert timeline_view._lyrics_edit_mode is False
        assert timeline_view._edit_buttons_visible is False
        
    def test_set_lyrics_edit_mode_shows_buttons(self, timeline_view):
        """Activar edit mode debe mostrar botones"""
        timeline_view.set_lyrics_edit_mode(True)
        
        assert timeline_view._lyrics_edit_mode is True
        assert timeline_view._edit_buttons_visible is True
        
    def test_set_lyrics_edit_mode_hides_buttons(self, timeline_view):
        """Desactivar edit mode debe ocultar botones"""
        timeline_view.set_lyrics_edit_mode(True)
        timeline_view.set_lyrics_edit_mode(False)
        
        assert timeline_view._lyrics_edit_mode is False
        assert timeline_view._edit_buttons_visible is False
        assert timeline_view._hovered_button is None
        
    def test_button_dimensions(self, timeline_view):
        """Verificar dimensiones de botones"""
        assert timeline_view._button_width == 140
        assert timeline_view._button_height == 32
        assert timeline_view._button_spacing == 10
        assert timeline_view._button_margin == 10
        
    def test_get_button_rect_first_button(self, timeline_view):
        """Calcular rectángulo del primer botón"""
        w, h = 800, 400
        x, y, bw, bh = timeline_view._get_button_rect(0, w, h)
        
        # Debe estar en el borde derecho
        assert x == w - timeline_view._button_width - timeline_view._button_margin
        assert y == timeline_view._button_margin
        assert bw == timeline_view._button_width
        assert bh == timeline_view._button_height
        
    def test_get_button_rect_second_button(self, timeline_view):
        """Calcular rectángulo del segundo botón"""
        w, h = 800, 400
        x, y, bw, bh = timeline_view._get_button_rect(1, w, h)
        
        expected_y = timeline_view._button_margin + \
                     (timeline_view._button_height + timeline_view._button_spacing)
        
        assert x == w - timeline_view._button_width - timeline_view._button_margin
        assert y == expected_y
        assert bw == timeline_view._button_width
        assert bh == timeline_view._button_height
        
    def test_get_button_at_pos_no_buttons(self, timeline_view):
        """Sin edit mode, no debe detectar botones"""
        timeline_view.set_lyrics_edit_mode(False)
        
        result = timeline_view._get_button_at_pos(700, 20)
        assert result is None
        
    def test_get_button_at_pos_edit_metadata(self, timeline_view):
        """Detectar click en botón Edit Metadata"""
        timeline_view.set_lyrics_edit_mode(True)
        
        # Obtener posición del botón
        w, h = timeline_view.width(), timeline_view.height()
        x, y, bw, bh = timeline_view._get_button_rect(0, w, h)
        
        # Click en el centro del botón
        center_x = x + bw // 2
        center_y = y + bh // 2
        
        result = timeline_view._get_button_at_pos(center_x, center_y)
        assert result == 'edit_metadata'
        
    def test_get_button_at_pos_reload_lyrics(self, timeline_view):
        """Detectar click en botón Reload Lyrics"""
        timeline_view.set_lyrics_edit_mode(True)
        
        # Obtener posición del botón
        w, h = timeline_view.width(), timeline_view.height()
        x, y, bw, bh = timeline_view._get_button_rect(1, w, h)
        
        # Click en el centro del botón
        center_x = x + bw // 2
        center_y = y + bh // 2
        
        result = timeline_view._get_button_at_pos(center_x, center_y)
        assert result == 'reload_lyrics'
        
    def test_get_button_at_pos_outside_buttons(self, timeline_view):
        """Click fuera de botones no debe detectar nada"""
        timeline_view.set_lyrics_edit_mode(True)
        
        # Click en la esquina superior izquierda (lejos de botones)
        result = timeline_view._get_button_at_pos(10, 10)
        assert result is None
        
    def test_edit_metadata_signal_emission(self, timeline_view, qtbot):
        """Debe emitir edit_metadata_clicked al hacer click en el botón"""
        timeline_view.set_lyrics_edit_mode(True)
        
        # Obtener posición del botón
        w, h = timeline_view.width(), timeline_view.height()
        x, y, bw, bh = timeline_view._get_button_rect(0, w, h)
        center_x = x + bw // 2
        center_y = y + bh // 2
        
        # Simular click
        with qtbot.waitSignal(timeline_view.edit_metadata_clicked):
            # Crear evento de mouse
            from PySide6.QtGui import QMouseEvent
            event = QMouseEvent(
                QMouseEvent.Type.MouseButtonPress,
                QPoint(center_x, center_y),
                Qt.MouseButton.LeftButton,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier
            )
            timeline_view.mousePressEvent(event)
            
    def test_reload_lyrics_signal_emission(self, timeline_view, qtbot):
        """Debe emitir reload_lyrics_clicked al hacer click en el botón"""
        timeline_view.set_lyrics_edit_mode(True)
        
        # Obtener posición del botón
        w, h = timeline_view.width(), timeline_view.height()
        x, y, bw, bh = timeline_view._get_button_rect(1, w, h)
        center_x = x + bw // 2
        center_y = y + bh // 2
        
        # Simular click
        with qtbot.waitSignal(timeline_view.reload_lyrics_clicked):
            # Crear evento de mouse
            from PySide6.QtGui import QMouseEvent
            event = QMouseEvent(
                QMouseEvent.Type.MouseButtonPress,
                QPoint(center_x, center_y),
                Qt.MouseButton.LeftButton,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier
            )
            timeline_view.mousePressEvent(event)
            
    def test_hover_state_changes(self, timeline_view):
        """Estado de hover debe cambiar al mover el mouse"""
        timeline_view.set_lyrics_edit_mode(True)
        
        # Inicialmente sin hover
        assert timeline_view._hovered_button is None
        
        # Mover sobre primer botón
        w, h = timeline_view.width(), timeline_view.height()
        x, y, bw, bh = timeline_view._get_button_rect(0, w, h)
        center_x = x + bw // 2
        center_y = y + bh // 2
        
        from PySide6.QtGui import QMouseEvent
        move_event = QMouseEvent(
            QMouseEvent.Type.MouseMove,
            QPoint(center_x, center_y),
            Qt.MouseButton.NoButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier
        )
        timeline_view.mouseMoveEvent(move_event)
        
        assert timeline_view._hovered_button == 'edit_metadata'
        
    def test_mouse_tracking_enabled(self, timeline_view):
        """Mouse tracking debe estar habilitado para hover effects"""
        assert timeline_view.hasMouseTracking() is True
        
    def test_click_outside_buttons_does_not_emit(self, timeline_view, qtbot):
        """Click fuera de botones no debe emitir señales"""
        timeline_view.set_lyrics_edit_mode(True)
        
        # Click en área de waveform (izquierda)
        from PySide6.QtGui import QMouseEvent
        event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPoint(100, 200),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier
        )
        
        # No debe emitir ninguna señal de botones
        # (qtbot.assertNotEmitted no existe, así que verificamos manualmente)
        signal_emitted = False
        
        def on_signal():
            nonlocal signal_emitted
            signal_emitted = True
        
        timeline_view.edit_metadata_clicked.connect(on_signal)
        timeline_view.reload_lyrics_clicked.connect(on_signal)
        
        timeline_view.mousePressEvent(event)
        
        assert signal_emitted is False
