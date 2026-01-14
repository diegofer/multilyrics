"""
Tests for edit mode button handlers in MainWindow
Tests Phase 6: Edit Mode Button Handlers
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from PySide6.QtWidgets import QApplication

from main import MainWindow
from models.lyrics_model import LyricsModel


@pytest.fixture
def window(qapp):
    """Create MainWindow instance for testing"""
    return MainWindow()


@pytest.fixture
def mock_multi_path(tmp_path):
    """Create mock multi directory structure"""
    multi_path = tmp_path / "test_multi"
    multi_path.mkdir()
    
    # Create meta.json file
    meta_file = multi_path / "meta.json"
    meta_file.write_text('{"track_name": "Test Song", "artist_name": "Test Artist", "duration_seconds": 180.5}')
    
    return multi_path


class TestEditModeHandlers:
    """Test suite for edit mode button handlers"""
    
    def test_edit_metadata_clicked_with_no_active_multi(self, window, caplog):
        """Should return early if no active multi is loaded"""
        window.active_multi_path = None
        
        window._on_edit_metadata_clicked()
        
        assert "No hay multi activo para editar metadata" in caplog.text
    
    def test_edit_metadata_clicked_with_missing_meta_file(self, window, tmp_path, caplog):
        """Should return early if meta.json doesn't exist"""
        window.active_multi_path = tmp_path / "nonexistent"
        
        window._on_edit_metadata_clicked()
        
        assert "Archivo de metadata no encontrado" in caplog.text
    
    def test_reload_lyrics_clicked_with_no_active_multi(self, window, caplog):
        """Should return early if no active multi is loaded"""
        window.active_multi_path = None
        
        window._on_reload_lyrics_clicked()
        
        assert "No hay multi activo para recargar letras" in caplog.text
    
    def test_reload_lyrics_clicked_with_missing_meta_file(self, window, tmp_path, caplog):
        """Should return early if meta.json doesn't exist"""
        window.active_multi_path = tmp_path / "nonexistent"
        
        window._on_reload_lyrics_clicked()
        
        assert "Archivo de metadata no encontrado" in caplog.text
    
    # NOTE: Old tests removed - obsolete methods deleted in Phase 10:
    # - test_reload_lyrics_clicked_success_auto_download (auto_download removed)
    # - test_reload_lyrics_clicked_fallback_to_manual (_show_lyrics_selector_for_reload removed)
    # - test_edit_mode_metadata_confirmed_success (_on_edit_mode_metadata_confirmed removed)
    # - test_edit_mode_search_skipped (_on_edit_mode_search_skipped removed)
    # - test_show_lyrics_selector_no_results (_show_lyrics_selector_for_reload removed)
    # - test_show_lyrics_selector_single_result (_show_lyrics_selector_for_reload removed)
    # - test_edit_mode_lyrics_selected (_on_edit_mode_lyrics_selected removed)
    #
    # Phase 10 uses:
    # - _on_edit_metadata_clicked -> MultiMetadataEditorDialog (edit display metadata)
    # - _on_reload_lyrics_clicked -> LyricsSearchDialog (reuse with original metadata)
    
    def test_reload_lyrics_track(self, window, caplog):
        """Should set model and reload timeline view"""
        import logging
        caplog.set_level(logging.DEBUG)
        
        mock_lyrics = Mock(spec=LyricsModel)
        mock_lyrics.lines = ['line1', 'line2', 'line3']
        
        with patch.object(window.timeline_model, 'set_lyrics_model'):
            with patch.object(window.timeline_view, 'reload_lyrics_track'):
                window._reload_lyrics_track(mock_lyrics)
                
                window.timeline_model.set_lyrics_model.assert_called_once_with(mock_lyrics)
                window.timeline_view.reload_lyrics_track.assert_called_once()
                
                assert "3 líneas" in caplog.text
    
    def test_active_multi_path_updated_in_set_active_song(self, window, mock_multi_path, monkeypatch):
        """Should update active_multi_path when loading a multi"""
        # Mock all dependencies to prevent actual loading
        monkeypatch.setattr('main.get_tracks', lambda x: [])
        monkeypatch.setattr('main.get_mp4', lambda x: 'test.mp4')
        
        # Create video file
        (mock_multi_path / 'test.mp4').touch()
        
        with patch.object(window.audio_player, 'load_tracks'):
            with patch.object(window.audio_player, 'get_duration_seconds', return_value=180):
                with patch.object(window.playback, 'set_duration'):
                    with patch.object(window.timeline_view, 'load_audio_from_master'):
                        with patch.object(window.timeline_view, 'load_metadata'):
                            with patch.object(window.lyrics_loader, 'load', return_value=None):
                                with patch.object(window.timeline_model, 'set_lyrics_model'):
                                    with patch.object(window.timeline_view, 'reload_lyrics_track'):
                                        with patch.object(window.video_player, 'set_media'):
                                            with patch.object(window.controls, 'set_edit_mode_enabled'):
                                                window.set_active_song(mock_multi_path)
                                                
                                                assert window.active_multi_path == mock_multi_path
