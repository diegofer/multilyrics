"""
Tests for optimized lyrics flow in multi creation workflow.

Tests the silent auto-attempt + fallback to search dialog pattern.
"""

import pytest
from unittest.mock import MagicMock, patch, call
from pathlib import Path


class TestOptimizedLyricsFlow:
    """Test suite for optimized lyrics download flow"""
    
    @pytest.fixture
    def mock_main_window(self):
        """Create mock MainWindow with necessary components"""
        from main import MainWindow
        
        with patch('main.Ui_MainWindow'), \
             patch('main.TimelineView'), \
             patch('main.MultiTrackPlayer'), \
             patch('main.VideoLyrics'), \
             patch('main.SyncController'), \
             patch('main.PlaybackManager'), \
             patch('main.ControlsWidget'), \
             patch('main.AddDialog'), \
             patch('main.SpinnerDialog'):
            
            window = MainWindow()
            
            # Mock loader
            window.loader = MagicMock()
            window.loader.show = MagicMock()
            window.loader.hide = MagicMock()
            
            # Mock lyrics loader
            window.lyrics_loader = MagicMock()
            
            # Mock timeline
            window.timeline_model = MagicMock()
            window.timeline_view = MagicMock()
            window.add_dialog = MagicMock()
            
            # Mock methods
            window.set_active_song = MagicMock()
            
            return window
    
    @pytest.fixture
    def sample_metadata(self):
        """Sample metadata with normalized LRCLIB fields"""
        return {
            'title': 'Test Song',
            'artist': 'Test Artist',
            'duration': 210.5,
            'track_name': 'Test Song',
            'artist_name': 'Test Artist',
            'duration_seconds': 210.5
        }
    
    @pytest.fixture
    def sample_audio_path(self, tmp_path):
        """Create temporary audio path"""
        multi_dir = tmp_path / "Test Song - Test Artist"
        multi_dir.mkdir()
        
        audio_file = multi_dir / "audio.wav"
        audio_file.write_text("mock audio")
        
        # Create meta.json
        import json
        meta_file = multi_dir / "meta.json"
        meta_file.write_text(json.dumps({
            'track_name': 'Test Song',
            'artist_name': 'Test Artist',
            'duration_seconds': 210.5
        }))
        
        return str(audio_file)
    
    def test_single_exact_match_auto_downloads(self, mock_main_window, sample_audio_path, sample_metadata):
        """Test Case 1: Single exact match triggers silent auto-download"""
        # Setup: One exact match result
        exact_result = {
            'id': 1,
            'trackName': 'Test Song',
            'artistName': 'Test Artist',
            'duration': 210.0,  # Within 1s tolerance
            'syncedLyrics': '[00:00.00] Test'
        }
        
        mock_main_window.lyrics_loader.search_all.return_value = [exact_result]
        mock_lyrics_model = MagicMock()
        mock_main_window.lyrics_loader.download_and_save.return_value = mock_lyrics_model
        
        # Mock MetaJson
        with patch('main.MetaJson') as mock_meta:
            mock_meta_instance = MagicMock()
            mock_meta_instance.read_meta.return_value = sample_metadata
            mock_meta.return_value = mock_meta_instance
            
            # Execute
            mock_main_window.on_extraction_process(sample_audio_path)
        
        # Verify: Auto-downloaded without showing dialog
        mock_main_window.lyrics_loader.search_all.assert_called_once_with('Test Song', 'Test Artist')
        mock_main_window.lyrics_loader.download_and_save.assert_called_once()
        
        # Verify: Timeline and player updated
        mock_main_window.timeline_model.set_lyrics_model.assert_called_once_with(mock_lyrics_model)
        mock_main_window.set_active_song.assert_called_once()
    
    def test_no_results_shows_dialog(self, mock_main_window, sample_audio_path, sample_metadata):
        """Test Case 2: No results shows search dialog"""
        # Setup: No results
        mock_main_window.lyrics_loader.search_all.return_value = []
        
        # Mock MetaJson
        with patch('main.MetaJson') as mock_meta:
            mock_meta_instance = MagicMock()
            mock_meta_instance.read_meta.return_value = sample_metadata
            mock_meta.return_value = mock_meta_instance
            
            # Mock dialog
            with patch.object(mock_main_window, '_show_lyrics_search_dialog') as mock_dialog:
                # Execute
                mock_main_window.on_extraction_process(sample_audio_path)
        
        # Verify: Dialog shown with empty results
        mock_dialog.assert_called_once()
        call_args = mock_dialog.call_args
        assert call_args[0][0] == sample_metadata  # metadata
        assert call_args[0][1] == []  # empty results
    
    def test_multiple_matches_shows_dialog(self, mock_main_window, sample_audio_path, sample_metadata):
        """Test Case 3: Multiple exact matches shows dialog"""
        # Setup: Two exact matches
        results = [
            {'id': 1, 'trackName': 'Test Song', 'duration': 210.0, 'syncedLyrics': 'v1'},
            {'id': 2, 'trackName': 'Test Song', 'duration': 210.5, 'syncedLyrics': 'v2'}
        ]
        
        mock_main_window.lyrics_loader.search_all.return_value = results
        
        # Mock MetaJson
        with patch('main.MetaJson') as mock_meta:
            mock_meta_instance = MagicMock()
            mock_meta_instance.read_meta.return_value = sample_metadata
            mock_meta.return_value = mock_meta_instance
            
            # Mock dialog
            with patch.object(mock_main_window, '_show_lyrics_search_dialog') as mock_dialog:
                # Execute
                mock_main_window.on_extraction_process(sample_audio_path)
        
        # Verify: Dialog shown with all results
        mock_dialog.assert_called_once()
        call_args = mock_dialog.call_args
        assert call_args[0][1] == results  # All results passed
    
    def test_inexact_match_shows_dialog(self, mock_main_window, sample_audio_path, sample_metadata):
        """Test Case 4: Results with >1s duration difference shows dialog"""
        # Setup: One result but duration >1s off
        results = [
            {'id': 1, 'trackName': 'Test Song', 'duration': 220.0, 'syncedLyrics': 'v1'}  # 9.5s diff
        ]
        
        mock_main_window.lyrics_loader.search_all.return_value = results
        
        # Mock MetaJson
        with patch('main.MetaJson') as mock_meta:
            mock_meta_instance = MagicMock()
            mock_meta_instance.read_meta.return_value = sample_metadata
            mock_meta.return_value = mock_meta_instance
            
            # Mock dialog
            with patch.object(mock_main_window, '_show_lyrics_search_dialog') as mock_dialog:
                # Execute
                mock_main_window.on_extraction_process(sample_audio_path)
        
        # Verify: Dialog shown because no exact match
        mock_dialog.assert_called_once()
    
    def test_duration_tolerance_boundary(self, mock_main_window, sample_audio_path, sample_metadata):
        """Test duration tolerance is exactly 1.0 seconds"""
        # Setup: Result exactly 1.0s different (should auto-download)
        results = [
            {'id': 1, 'trackName': 'Test Song', 'duration': 211.5, 'syncedLyrics': 'v1'}  # Exactly 1.0s
        ]
        
        mock_main_window.lyrics_loader.search_all.return_value = results
        mock_lyrics_model = MagicMock()
        mock_main_window.lyrics_loader.download_and_save.return_value = mock_lyrics_model
        
        # Mock MetaJson
        with patch('main.MetaJson') as mock_meta:
            mock_meta_instance = MagicMock()
            mock_meta_instance.read_meta.return_value = sample_metadata
            mock_meta.return_value = mock_meta_instance
            
            # Execute
            mock_main_window.on_extraction_process(sample_audio_path)
        
        # Verify: Auto-downloaded (≤1s tolerance)
        mock_main_window.lyrics_loader.download_and_save.assert_called_once()
    
    def test_user_skip_loads_multi_without_lyrics(self, mock_main_window, sample_metadata):
        """Test user skip in dialog loads multi with None lyrics"""
        # Import dialog class locally (matches main.py's lazy import)
        from ui.widgets.lyrics_search_dialog import LyricsSearchDialog
        
        # Setup dialog with skip callback
        with patch('ui.widgets.lyrics_search_dialog.LyricsSearchDialog') as mock_dialog_class:
            mock_dialog = MagicMock()
            mock_dialog_class.return_value = mock_dialog
            
            # Store the multi path
            mock_main_window._current_multi_path = Path("/tmp/test_multi")
            mock_main_window._current_meta_data = sample_metadata
            
            # Trigger dialog show
            mock_main_window._show_lyrics_search_dialog(sample_metadata, [])
            
            # Get the connected skip handler
            skip_handler = mock_dialog.search_skipped.connect.call_args[0][0]
            
            # Execute skip
            skip_handler()
        
        # Verify: Multi finalized with None lyrics
        mock_main_window.timeline_model.set_lyrics_model.assert_called_once_with(None)
        mock_main_window.set_active_song.assert_called_once()
    
    def test_user_selection_downloads_chosen_lyrics(self, mock_main_window, sample_metadata):
        """Test user manual selection downloads chosen lyrics"""
        chosen_result = {
            'id': 2,
            'trackName': 'Test Song (Live)',
            'duration': 215.0,
            'syncedLyrics': '[00:00.00] Live version'
        }
        
        # Import dialog class locally (matches main.py's lazy import)
        from ui.widgets.lyrics_search_dialog import LyricsSearchDialog
        
        # Setup dialog with selection callback
        with patch('ui.widgets.lyrics_search_dialog.LyricsSearchDialog') as mock_dialog_class:
            mock_dialog = MagicMock()
            mock_dialog_class.return_value = mock_dialog
            
            mock_lyrics_model = MagicMock()
            mock_main_window.lyrics_loader.download_and_save.return_value = mock_lyrics_model
            
            # Store the multi path
            mock_main_window._current_multi_path = Path("/tmp/test_multi")
            mock_main_window._current_meta_data = sample_metadata
            
            # Trigger dialog show
            mock_main_window._show_lyrics_search_dialog(sample_metadata, [])
            
            # Get the connected selection handler
            selection_handler = mock_dialog.lyrics_selected.connect.call_args[0][0]
            
            # Execute selection
            selection_handler(chosen_result)
        
        # Verify: Chosen lyrics downloaded
        mock_main_window.lyrics_loader.download_and_save.assert_called_once_with(
            chosen_result,
            Path("/tmp/test_multi")
        )
        
        # Verify: Multi finalized with downloaded lyrics
        mock_main_window.timeline_model.set_lyrics_model.assert_called_once_with(mock_lyrics_model)
    
    def test_results_without_duration_ignored(self, mock_main_window, sample_audio_path, sample_metadata):
        """Test results without duration field are filtered out"""
        # Setup: One with duration, one without
        results = [
            {'id': 1, 'trackName': 'Test Song', 'duration': 210.0, 'syncedLyrics': 'v1'},
            {'id': 2, 'trackName': 'Test Song', 'syncedLyrics': 'v2'}  # No duration
        ]
        
        mock_main_window.lyrics_loader.search_all.return_value = results
        mock_lyrics_model = MagicMock()
        mock_main_window.lyrics_loader.download_and_save.return_value = mock_lyrics_model
        
        # Mock MetaJson
        with patch('main.MetaJson') as mock_meta:
            mock_meta_instance = MagicMock()
            mock_meta_instance.read_meta.return_value = sample_metadata
            mock_meta.return_value = mock_meta_instance
            
            # Execute
            mock_main_window.on_extraction_process(sample_audio_path)
        
        # Verify: Auto-downloaded the one with duration
        mock_main_window.lyrics_loader.download_and_save.assert_called_once()
        call_args = mock_main_window.lyrics_loader.download_and_save.call_args[0]
        assert call_args[0]['id'] == 1  # First result (with duration)
