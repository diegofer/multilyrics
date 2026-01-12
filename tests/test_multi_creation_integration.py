"""
Integration test for Phase 5: Multi creation workflow with lyrics dialogs
Tests the complete flow from extraction to lyrics download
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QThread

from main import MainWindow


@pytest.fixture(scope='module')
def qapp():
    """Fixture para QApplication"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestMultiCreationIntegration:
    """Integration tests for the complete multi creation workflow"""
    
    def test_extraction_triggers_metadata_dialog(self, qapp, tmp_path, monkeypatch):
        """After extraction, MetadataEditorDialog should be shown"""
        window = MainWindow()
        
        # Mock metadata
        mock_metadata = {
            'track_name': 'Test Song',
            'artist_name': 'Test Artist',
            'duration_seconds': 180.0
        }
        
        # Mock MetaJson to return our metadata
        with patch('main.MetaJson') as mock_meta_class:
            mock_meta_instance = Mock()
            mock_meta_instance.read_meta.return_value = mock_metadata
            mock_meta_class.return_value = mock_meta_instance
            
            # Mock MetadataEditorDialog
            with patch('main.MetadataEditorDialog') as mock_dialog_class:
                mock_dialog = Mock()
                mock_dialog_class.return_value = mock_dialog
                
                # Simulate extraction completion
                audio_path = tmp_path / "test_song" / "master.wav"
                audio_path.parent.mkdir(parents=True)
                audio_path.touch()
                
                window.on_extraction_process(str(audio_path))
                
                # Verify dialog was created with correct metadata
                mock_dialog_class.assert_called_once()
                call_args = mock_dialog_class.call_args
                assert call_args[0][0] == mock_metadata
                
                # Verify dialog was shown
                mock_dialog.exec.assert_called_once()
    
    def test_metadata_confirmed_triggers_auto_download(self, qapp, tmp_path):
        """When user confirms metadata, auto_download should be called"""
        window = MainWindow()
        
        # Setup state
        window._current_multi_path = tmp_path / "test_song"
        window._current_meta_data = {
            'track_name': 'Original',
            'artist_name': 'Original Artist',
            'duration_seconds': 180.0
        }
        
        edited_metadata = {
            'track_name': 'Edited Song',
            'artist_name': 'Edited Artist',
            'duration_seconds': 180.0
        }
        
        # Mock auto_download to return a lyrics model
        mock_lyrics_model = Mock()
        with patch.object(window.lyrics_loader, 'auto_download', return_value=mock_lyrics_model):
            # Mock _finalize_multi_creation
            with patch.object(window, '_finalize_multi_creation') as mock_finalize:
                window._on_metadata_confirmed(edited_metadata)
                
                # Verify auto_download was called with edited metadata
                window.lyrics_loader.auto_download.assert_called_once_with(
                    window._current_multi_path,
                    'Edited Song',
                    'Edited Artist',
                    180.0
                )
                
                # Verify finalization was called
                mock_finalize.assert_called_once_with(mock_lyrics_model)
    
    def test_auto_download_failure_triggers_manual_selection(self, qapp, tmp_path):
        """When auto_download returns None, manual selection should be offered"""
        window = MainWindow()
        
        # Setup state
        window._current_multi_path = tmp_path / "test_song"
        window._current_meta_data = {
            'track_name': 'Test',
            'artist_name': 'Artist',
            'duration_seconds': 180.0
        }
        
        edited_metadata = {
            'track_name': 'Test Song',
            'artist_name': 'Test Artist',
            'duration_seconds': 180.0
        }
        
        # Mock auto_download to return None (no automatic match)
        with patch.object(window.lyrics_loader, 'auto_download', return_value=None):
            # Mock _try_manual_lyrics_selection
            with patch.object(window, '_try_manual_lyrics_selection') as mock_manual:
                window._on_metadata_confirmed(edited_metadata)
                
                # Verify manual selection was triggered
                mock_manual.assert_called_once_with(edited_metadata)
    
    def test_manual_selection_shows_selector_dialog(self, qapp, tmp_path):
        """When multiple results exist, LyricsSelectorDialog should be shown"""
        window = MainWindow()
        
        window._current_multi_path = tmp_path / "test_song"
        
        metadata = {
            'track_name': 'Test Song',
            'artist_name': 'Test Artist',
            'duration_seconds': 180.0
        }
        
        # Mock search_all to return multiple results
        mock_results = [
            {'artistName': 'Artist', 'trackName': 'Song 1', 'duration': 180, 'syncedLyrics': '[00:10]Test'},
            {'artistName': 'Artist', 'trackName': 'Song 2', 'duration': 185, 'syncedLyrics': '[00:10]Test'}
        ]
        
        with patch.object(window.lyrics_loader, 'search_all', return_value=mock_results):
            with patch('main.LyricsSelectorDialog') as mock_dialog_class:
                mock_dialog = Mock()
                mock_dialog_class.return_value = mock_dialog
                
                window._try_manual_lyrics_selection(metadata)
                
                # Verify dialog was created with results and duration
                mock_dialog_class.assert_called_once()
                call_args = mock_dialog_class.call_args
                assert call_args[0][0] == mock_results
                assert call_args[0][1] == 180.0
                
                # Verify dialog was shown
                mock_dialog.exec.assert_called_once()
    
    def test_single_result_downloads_directly(self, qapp, tmp_path):
        """When only one result exists, download it without showing selector"""
        window = MainWindow()
        
        window._current_multi_path = tmp_path / "test_song"
        
        metadata = {
            'track_name': 'Test Song',
            'artist_name': 'Test Artist',
            'duration_seconds': 180.0
        }
        
        # Mock search_all to return single result
        single_result = {'artistName': 'Artist', 'trackName': 'Song', 'duration': 180, 'syncedLyrics': '[00:10]Test'}
        
        mock_lyrics_model = Mock()
        with patch.object(window.lyrics_loader, 'search_all', return_value=[single_result]):
            with patch.object(window.lyrics_loader, 'download_and_save', return_value=mock_lyrics_model):
                with patch.object(window, '_finalize_multi_creation') as mock_finalize:
                    window._try_manual_lyrics_selection(metadata)
                    
                    # Verify download was called with the result
                    window.lyrics_loader.download_and_save.assert_called_once_with(
                        single_result,
                        window._current_multi_path
                    )
                    
                    # Verify finalization was called
                    mock_finalize.assert_called_once_with(mock_lyrics_model)
    
    def test_no_results_proceeds_without_lyrics(self, qapp, tmp_path):
        """When no results exist, proceed without lyrics"""
        window = MainWindow()
        
        window._current_multi_path = tmp_path / "test_song"
        
        metadata = {
            'track_name': 'Unknown Song',
            'artist_name': 'Unknown Artist',
            'duration_seconds': 180.0
        }
        
        # Mock search_all to return empty list
        with patch.object(window.lyrics_loader, 'search_all', return_value=[]):
            with patch.object(window, '_finalize_multi_creation') as mock_finalize:
                window._try_manual_lyrics_selection(metadata)
                
                # Verify finalization was called with None
                mock_finalize.assert_called_once_with(None)
    
    def test_skip_search_proceeds_without_lyrics(self, qapp, tmp_path):
        """When user skips search, proceed without lyrics"""
        window = MainWindow()
        
        window._current_multi_path = tmp_path / "test_song"
        
        with patch.object(window, '_finalize_multi_creation') as mock_finalize:
            window._on_lyrics_search_skipped()
            
            # Verify finalization was called with None
            mock_finalize.assert_called_once_with(None)
    
    def test_finalize_sets_lyrics_and_loads_multi(self, qapp, tmp_path, monkeypatch):
        """Finalization should set lyrics model and load the multi"""
        window = MainWindow()
        
        multi_path = tmp_path / "test_song"
        window._current_multi_path = multi_path
        window._current_meta_data = {}
        
        mock_lyrics_model = Mock()
        
        # Mock dependencies
        with patch.object(window.timeline_view, 'reload_lyrics_track'):
            with patch.object(window, 'set_active_song'):
                with patch.object(window.add_dialog.search_widget, 'get_fresh_multis_list'):
                    window._finalize_multi_creation(mock_lyrics_model)
                    
                    # Verify lyrics model was set
                    assert window.timeline_model.lyrics_model == mock_lyrics_model
                    
                    # Verify timeline view was reloaded
                    window.timeline_view.reload_lyrics_track.assert_called_once()
                    
                    # Verify multi was loaded with the correct path
                    window.set_active_song.assert_called_once_with(multi_path)
                    
                    # Verify multis list was refreshed
                    window.add_dialog.search_widget.get_fresh_multis_list.assert_called_once()
                    
                    # Verify state was cleaned up
                    assert window._current_multi_path is None
                    assert window._current_meta_data is None
