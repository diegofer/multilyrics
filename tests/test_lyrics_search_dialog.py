"""
Tests for LyricsSearchDialog - unified lyrics search interface.
"""

import pytest
from unittest.mock import MagicMock, patch
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from ui.widgets.lyrics_search_dialog import LyricsSearchDialog


@pytest.fixture
def qapp():
    """Create QApplication instance"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def mock_lyrics_loader():
    """Mock LyricsLoader"""
    loader = MagicMock()
    loader.search_all.return_value = []
    return loader


@pytest.fixture
def sample_metadata():
    """Sample metadata dict"""
    return {
        'track_name': 'Test Song',
        'artist_name': 'Test Artist',
        'duration_seconds': 180.5
    }


@pytest.fixture
def sample_results():
    """Sample search results"""
    return [
        {
            'id': 1,
            'trackName': 'Test Song',
            'artistName': 'Test Artist',
            'duration': 180.0,  # Exact match (≤1s)
            'syncedLyrics': '[00:00.00] Test lyrics'
        },
        {
            'id': 2,
            'trackName': 'Test Song (Live)',
            'artistName': 'Test Artist',
            'duration': 185.0,  # Not exact match (>1s)
            'syncedLyrics': '[00:00.00] Test lyrics live'
        }
    ]


class TestLyricsSearchDialog:
    """Test suite for LyricsSearchDialog"""
    
    def test_dialog_creation(self, qapp, sample_metadata, sample_results, mock_lyrics_loader):
        """Test dialog can be created with initial results"""
        dialog = LyricsSearchDialog(
            sample_metadata,
            sample_results,
            mock_lyrics_loader
        )
        
        assert dialog.windowTitle() == "Buscar Letras"
        assert dialog.metadata == sample_metadata
        assert dialog.results == sample_results
        # selected_result is auto-set to first exact match
        assert dialog.selected_result is not None
    
    def test_metadata_fields_populated(self, qapp, sample_metadata, sample_results, mock_lyrics_loader):
        """Test metadata fields are pre-populated"""
        dialog = LyricsSearchDialog(
            sample_metadata,
            sample_results,
            mock_lyrics_loader
        )
        
        assert dialog.track_input.text() == 'Test Song'
        assert dialog.artist_input.text() == 'Test Artist'
    
    def test_results_list_populated(self, qapp, sample_metadata, sample_results, mock_lyrics_loader):
        """Test results list is populated with initial results"""
        dialog = LyricsSearchDialog(
            sample_metadata,
            sample_results,
            mock_lyrics_loader
        )
        
        assert dialog.results_list.count() == 2
        assert "Resultados (2)" in dialog.results_label.text()
    
    def test_exact_match_highlighting(self, qapp, sample_metadata, sample_results, mock_lyrics_loader):
        """Test exact matches (≤1s) are highlighted in green"""
        dialog = LyricsSearchDialog(
            sample_metadata,
            sample_results,
            mock_lyrics_loader
        )
        
        # First item should be green (exact match)
        first_item = dialog.results_list.item(0)
        first_color = first_item.foreground().color()
        
        # Second item should not be green (not exact match)
        second_item = dialog.results_list.item(1)
        second_color = second_item.foreground().color()
        
        # Green highlighting check (StyleManager returns rgb string)
        assert first_color.green() > first_color.red()  # More green than red
        assert second_color != first_color  # Different colors
    
    def test_auto_selection_exact_match(self, qapp, sample_metadata, sample_results, mock_lyrics_loader):
        """Test first exact match is auto-selected"""
        dialog = LyricsSearchDialog(
            sample_metadata,
            sample_results,
            mock_lyrics_loader
        )
        
        # First item (exact match) should be selected via currentItem
        assert dialog.results_list.currentItem() is not None
        assert dialog.download_btn.isEnabled()
        assert dialog.selected_result == sample_results[0]
    
    def test_empty_results(self, qapp, sample_metadata, mock_lyrics_loader):
        """Test dialog with no results shows info message"""
        dialog = LyricsSearchDialog(
            sample_metadata,
            [],
            mock_lyrics_loader
        )
        
        assert dialog.results_list.count() == 0
        assert "No se encontraron letras sincronizadas" in dialog.info_label.text()
        assert not dialog.download_btn.isEnabled()
    
    def test_manual_search(self, qapp, sample_metadata, sample_results, mock_lyrics_loader):
        """Test manual search button triggers search with updated metadata"""
        mock_lyrics_loader.search_all.return_value = sample_results
        
        dialog = LyricsSearchDialog(
            sample_metadata,
            [],
            mock_lyrics_loader
        )
        
        # Change metadata
        dialog.track_input.setText("New Track")
        dialog.artist_input.setText("New Artist")
        
        # Click search
        dialog.search_btn.click()
        
        # Verify search was called with new metadata
        mock_lyrics_loader.search_all.assert_called_once_with("New Track", "New Artist")
        
        # Results should be updated
        assert dialog.results_list.count() == 2
    
    def test_result_selection_enables_download(self, qapp, sample_metadata, sample_results, mock_lyrics_loader):
        """Test selecting a result enables download button"""
        dialog = LyricsSearchDialog(
            sample_metadata,
            sample_results,
            mock_lyrics_loader
        )
        
        # Initially auto-selected, button enabled
        assert dialog.download_btn.isEnabled()
        
        # Click different item
        dialog.results_list.setCurrentRow(1)
        dialog._on_result_clicked(dialog.results_list.item(1))
        
        assert dialog.selected_result == sample_results[1]
        assert dialog.download_btn.isEnabled()
    
    def test_download_button_emits_signal(self, qapp, sample_metadata, sample_results, mock_lyrics_loader):
        """Test download button emits lyrics_selected signal"""
        dialog = LyricsSearchDialog(
            sample_metadata,
            sample_results,
            mock_lyrics_loader
        )
        
        # Connect signal spy
        emitted_result = None
        def capture_result(result):
            nonlocal emitted_result
            emitted_result = result
        
        dialog.lyrics_selected.connect(capture_result)
        
        # Select first result and download
        dialog.results_list.setCurrentRow(0)
        dialog._on_result_clicked(dialog.results_list.item(0))
        dialog.download_btn.click()
        
        assert emitted_result == sample_results[0]
    
    def test_skip_button_emits_signal(self, qapp, sample_metadata, sample_results, mock_lyrics_loader):
        """Test skip button emits search_skipped signal"""
        dialog = LyricsSearchDialog(
            sample_metadata,
            sample_results,
            mock_lyrics_loader
        )
        
        # Connect signal spy
        skipped = False
        def capture_skip():
            nonlocal skipped
            skipped = True
        
        dialog.search_skipped.connect(capture_skip)
        
        # Click skip
        dialog.skip_btn.click()
        
        assert skipped is True
    
    def test_double_click_emits_signal(self, qapp, sample_metadata, sample_results, mock_lyrics_loader):
        """Test double-clicking a result downloads immediately"""
        dialog = LyricsSearchDialog(
            sample_metadata,
            sample_results,
            mock_lyrics_loader
        )
        
        # Connect signal spy
        emitted_result = None
        def capture_result(result):
            nonlocal emitted_result
            emitted_result = result
        
        dialog.lyrics_selected.connect(capture_result)
        
        # Double-click first result
        dialog._on_result_double_clicked(dialog.results_list.item(0))
        
        assert emitted_result == sample_results[0]
    
    def test_duration_display_format(self, qapp, sample_metadata, mock_lyrics_loader):
        """Test duration is displayed in MM:SS format"""
        from PySide6.QtWidgets import QLabel
        
        dialog = LyricsSearchDialog(
            sample_metadata,
            [],
            mock_lyrics_loader
        )
        
        # Find all QLabels
        labels = dialog.findChildren(QLabel)
        duration_texts = [label.text() for label in labels]
        
        # Should contain "03:00" for 180.5 seconds
        assert any("03:00" in text for text in duration_texts)
    
    def test_search_with_empty_fields(self, qapp, sample_metadata, mock_lyrics_loader):
        """Test search with empty metadata fields shows warning"""
        mock_lyrics_loader.search_all.return_value = []
        
        dialog = LyricsSearchDialog(
            sample_metadata,
            [],
            mock_lyrics_loader
        )
        
        # Clear fields
        dialog.track_input.setText("")
        dialog.artist_input.setText("")
        
        # Click search
        dialog.search_btn.click()
        
        # Should NOT call search - shows warning instead
        mock_lyrics_loader.search_all.assert_not_called()
        assert "Por favor ingresa" in dialog.info_label.text()
