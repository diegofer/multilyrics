"""Unit tests for LyricsLoader service.

Tests metadata key normalization, API search, and parsing functionality.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import json

from audio.lyrics.loader import LyricsLoader
from audio.lyrics.model import LyricsModel, LyricLine


class TestLyricsLoaderMetadataKeys:
    """Test metadata key normalization for backward compatibility."""
    
    @pytest.fixture
    def loader(self):
        return LyricsLoader()
    
    @pytest.fixture
    def song_folder(self, tmp_path):
        """Create temporary song folder."""
        folder = tmp_path / "test_song"
        folder.mkdir()
        return folder
    
    def test_load_with_new_keys(self, loader, song_folder):
        """Test loading with new normalized keys (track_name, artist_name, duration_seconds)."""
        metadata = {
            'track_name': 'Test Song',
            'artist_name': 'Test Artist',
            'duration_seconds': 180.5
        }
        
        mock_results = [{
            'trackName': 'Test Song',
            'artistName': 'Test Artist',
            'duration': 180,
            'syncedLyrics': '[00:10.00]Test line\n[00:20.00]Another line'
        }]
        
        with patch.object(loader, 'search_lrclib', return_value=mock_results):
            result = loader.load(song_folder, metadata)
        
        assert result is not None
        assert isinstance(result, LyricsModel)
        assert len(result) == 2
    
    def test_load_with_legacy_keys(self, loader, song_folder):
        """Test loading with legacy keys (title, artist, duration) for backward compatibility."""
        metadata = {
            'title': 'Test Song',
            'artist': 'Test Artist',
            'duration': 180.5
        }
        
        mock_results = [{
            'trackName': 'Test Song',
            'artistName': 'Test Artist',
            'duration': 180,
            'syncedLyrics': '[00:10.00]Test line\n[00:20.00]Another line'
        }]
        
        with patch.object(loader, 'search_lrclib', return_value=mock_results):
            result = loader.load(song_folder, metadata)
        
        assert result is not None
        assert isinstance(result, LyricsModel)
        assert len(result) == 2
    
    def test_load_with_mixed_keys(self, loader, song_folder):
        """Test loading with mixed keys (new keys take precedence)."""
        metadata = {
            'track_name': 'New Title',
            'title': 'Old Title',
            'artist_name': 'New Artist',
            'artist': 'Old Artist',
            'duration_seconds': 200.0,
            'duration': 180.0
        }
        
        mock_results = [{
            'trackName': 'New Title',
            'artistName': 'New Artist',
            'duration': 200,
            'syncedLyrics': '[00:10.00]Test line'
        }]
        
        with patch.object(loader, '_search_lrclib_api', return_value=mock_results) as mock_search:
            result = loader.load(song_folder, metadata)
        
        # Verify it used the new keys
        mock_search.assert_called_once_with('New Title', 'New Artist')
        assert result is not None
    
    def test_load_with_missing_track_name(self, loader, song_folder):
        """Test that load returns None when track name is missing."""
        metadata = {
            'artist_name': 'Test Artist',
            'duration_seconds': 180.0
        }
        
        result = loader.load(song_folder, metadata)
        assert result is None
    
    def test_load_with_missing_artist_name(self, loader, song_folder):
        """Test that load returns None when artist name is missing."""
        metadata = {
            'track_name': 'Test Song',
            'duration_seconds': 180.0
        }
        
        result = loader.load(song_folder, metadata)
        assert result is None


class TestLyricsLoaderLocalFile:
    """Test loading from local lyrics.lrc file."""
    
    @pytest.fixture
    def loader(self):
        return LyricsLoader()
    
    @pytest.fixture
    def song_folder(self, tmp_path):
        folder = tmp_path / "test_song"
        folder.mkdir()
        return folder
    
    def test_load_from_local_existing_file(self, loader, song_folder):
        """Test loading from existing lyrics.lrc file."""
        lrc_content = "[00:10.00]First line\n[00:20.50]Second line\n"
        lrc_path = song_folder / "lyrics.lrc"
        lrc_path.write_text(lrc_content, encoding='utf-8')
        
        result = loader.load_from_local(song_folder)
        
        assert result is not None
        assert len(result) == 2
        assert result._lines[0].text == "First line"
        assert result._lines[1].text == "Second line"
    
    def test_load_from_local_missing_file(self, loader, song_folder):
        """Test that load_from_local returns None when file doesn't exist."""
        result = loader.load_from_local(song_folder)
        assert result is None
    
    def test_load_prefers_local_over_api(self, loader, song_folder):
        """Test that load() prefers local file over API search."""
        lrc_content = "[00:10.00]Local lyrics\n"
        lrc_path = song_folder / "lyrics.lrc"
        lrc_path.write_text(lrc_content, encoding='utf-8')
        
        metadata = {
            'track_name': 'Test Song',
            'artist_name': 'Test Artist',
            'duration_seconds': 180.0
        }
        
        # Mock API to ensure it's NOT called
        with patch.object(loader, 'search_lrclib') as mock_search:
            result = loader.load(song_folder, metadata)
        
        # Should not have called API
        mock_search.assert_not_called()
        
        # Should have loaded local file
        assert result is not None
        assert result._lines[0].text == "Local lyrics"


class TestLyricsLoaderDurationFiltering:
    """Test duration-based filtering of search results."""
    
    @pytest.fixture
    def loader(self):
        return LyricsLoader()
    
    def test_select_best_match_within_tolerance(self, loader):
        """Test selecting result within duration tolerance."""
        results = [
            {'duration': 180.0, 'syncedLyrics': 'lyrics1'},  # 1s difference
            {'duration': 182.0, 'syncedLyrics': 'lyrics2'},  # 1s difference
            {'duration': 185.0, 'syncedLyrics': 'lyrics3'},  # 4s - outside tolerance
        ]
        
        best = loader.select_best_match(results, 181.0)
        
        assert best is not None
        # Should select 180.0 (both are 1s away, but 180.0 comes first)
        assert best['duration'] == 180.0
    
    def test_select_best_match_exact(self, loader):
        """Test selecting exact duration match."""
        results = [
            {'duration': 175.0, 'syncedLyrics': 'lyrics1'},
            {'duration': 180.0, 'syncedLyrics': 'lyrics2'},  # Exact match
            {'duration': 185.0, 'syncedLyrics': 'lyrics3'},
        ]
        
        best = loader.select_best_match(results, 180.0)
        
        assert best is not None
        assert best['duration'] == 180.0
    
    def test_select_best_match_no_synced_lyrics(self, loader):
        """Test that results without syncedLyrics are ignored."""
        results = [
            {'duration': 180.0},  # No syncedLyrics
            {'duration': 181.0, 'syncedLyrics': None},  # None syncedLyrics
            {'duration': 182.0, 'syncedLyrics': ''},  # Empty syncedLyrics
        ]
        
        best = loader.select_best_match(results, 180.0)
        
        assert best is None
    
    def test_select_best_match_outside_tolerance(self, loader):
        """Test that results outside tolerance are rejected."""
        results = [
            {'duration': 170.0, 'syncedLyrics': 'lyrics1'},  # -10s
            {'duration': 190.0, 'syncedLyrics': 'lyrics2'},  # +10s
        ]
        
        best = loader.select_best_match(results, 180.0)
        
        assert best is None


class TestLyricsLoaderParsing:
    """Test LRC format parsing."""
    
    @pytest.fixture
    def loader(self):
        return LyricsLoader()
    
    def test_parse_lrc_basic(self, loader):
        """Test parsing basic LRC format."""
        lrc_text = """
[00:10.00]First line
[00:20.50]Second line
[00:30.75]Third line
"""
        result = loader.parse_lrc(lrc_text)
        
        assert len(result) == 3
        lines = result._lines
        assert lines[0].time_s == 10.0
        assert lines[0].text == "First line"
        assert lines[1].time_s == 20.5
        assert lines[1].text == "Second line"
    
    def test_parse_lrc_multiple_timestamps(self, loader):
        """Test parsing lines with multiple timestamps (repeated lyrics)."""
        lrc_text = "[00:10.00][00:50.00]Repeated chorus"
        
        result = loader.parse_lrc(lrc_text)
        
        assert len(result) == 2
        lines = result._lines
        assert lines[0].time_s == 10.0
        assert lines[0].text == "Repeated chorus"
        assert lines[1].time_s == 50.0
        assert lines[1].text == "Repeated chorus"
    
    def test_parse_lrc_skip_metadata(self, loader):
        """Test that metadata tags are skipped."""
        lrc_text = """
[ar:Artist Name]
[ti:Track Title]
[al:Album Name]
[00:10.00]Actual lyrics
"""
        result = loader.parse_lrc(lrc_text)
        
        assert len(result) == 1
        assert result._lines[0].text == "Actual lyrics"
    
    def test_parse_lrc_empty_lines(self, loader):
        """Test that empty lines are ignored."""
        lrc_text = """

[00:10.00]First line

[00:20.00]Second line

"""
        result = loader.parse_lrc(lrc_text)
        
        assert len(result) == 2
    
    def test_parse_lrc_sorted_by_time(self, loader):
        """Test that lines are sorted by time."""
        lrc_text = """
[00:30.00]Third
[00:10.00]First
[00:20.00]Second
"""
        result = loader.parse_lrc(lrc_text)
        
        lines = result._lines
        assert lines[0].time_s == 10.0
        assert lines[0].text == "First"
        assert lines[1].time_s == 20.0
        assert lines[2].time_s == 30.0


class TestLyricsLoaderSaveLocal:
    """Test saving lyrics to local file."""
    
    @pytest.fixture
    def loader(self):
        return LyricsLoader()
    
    @pytest.fixture
    def song_folder(self, tmp_path):
        folder = tmp_path / "test_song"
        folder.mkdir()
        return folder
    
    def test_save_lrc_creates_file(self, loader, song_folder):
        """Test that save_lrc creates lyrics.lrc file."""
        lrc_text = "[00:10.00]Test lyrics"
        
        loader._save_lrc(lrc_text, song_folder)
        
        lrc_path = song_folder / "lyrics.lrc"
        assert lrc_path.exists()
        content = lrc_path.read_text(encoding='utf-8')
        assert content == lrc_text
    
    def test_save_lrc_creates_folder(self, loader, tmp_path):
        """Test that save_lrc creates parent folder if missing."""
        song_folder = tmp_path / "new_folder" / "test_song"
        lrc_text = "[00:10.00]Test lyrics"
        
        loader._save_lrc(lrc_text, song_folder)
        
        assert song_folder.exists()
        lrc_path = song_folder / "lyrics.lrc"
        assert lrc_path.exists()


class TestLyricsLoaderNewAPI:
    """Test new modular API methods (Phase 1)."""
    
    @pytest.fixture
    def loader(self):
        return LyricsLoader()
    
    @pytest.fixture
    def song_folder(self, tmp_path):
        folder = tmp_path / "test_song"
        folder.mkdir()
        return folder
    
    def test_search_all_filters_synced_only(self, loader):
        """Test that search_all returns only results with syncedLyrics."""
        mock_results = [
            {'trackName': 'Song 1', 'syncedLyrics': '[00:10]Lyrics 1'},
            {'trackName': 'Song 2', 'syncedLyrics': None},
            {'trackName': 'Song 3'},  # No syncedLyrics key
            {'trackName': 'Song 4', 'syncedLyrics': '[00:20]Lyrics 4'},
        ]
        
        with patch.object(loader, '_search_lrclib_api', return_value=mock_results):
            results = loader.search_all('Test', 'Artist')
        
        assert len(results) == 2
        assert all(r.get('syncedLyrics') for r in results)
    
    def test_search_all_empty_when_no_synced(self, loader):
        """Test that search_all returns empty list when no synced lyrics."""
        mock_results = [
            {'trackName': 'Song 1', 'syncedLyrics': None},
            {'trackName': 'Song 2'},
        ]
        
        with patch.object(loader, '_search_lrclib_api', return_value=mock_results):
            results = loader.search_all('Test', 'Artist')
        
        assert results == []
    
    def test_auto_download_with_duration_filters(self, loader, song_folder):
        """Test auto_download filters by duration when provided."""
        mock_results = [
            {'duration': 170.0, 'syncedLyrics': '[00:10]Too short'},
            {'duration': 180.0, 'syncedLyrics': '[00:10]Perfect match'},
            {'duration': 200.0, 'syncedLyrics': '[00:10]Too long'},
        ]
        
        with patch.object(loader, '_search_lrclib_api', return_value=mock_results):
            result = loader.auto_download(song_folder, 'Test', 'Artist', 181.0)
        
        assert result is not None
        # Should select 180.0 (1s difference, within tolerance)
        assert len(result) == 1
        assert result._lines[0].text == "Perfect match"
    
    def test_auto_download_without_duration_takes_first(self, loader, song_folder):
        """Test auto_download takes first synced result when no duration provided."""
        mock_results = [
            {'trackName': 'Song 1', 'syncedLyrics': '[00:10]First'},
            {'trackName': 'Song 2', 'syncedLyrics': '[00:20]Second'},
        ]
        
        with patch.object(loader, '_search_lrclib_api', return_value=mock_results):
            result = loader.auto_download(song_folder, 'Test', 'Artist')
        
        assert result is not None
        assert result._lines[0].text == "First"
    
    def test_auto_download_returns_none_on_no_results(self, loader, song_folder):
        """Test auto_download returns None when API returns no results."""
        with patch.object(loader, '_search_lrclib_api', return_value=[]):
            result = loader.auto_download(song_folder, 'Test', 'Artist', 180.0)
        
        assert result is None
    
    def test_auto_download_requires_track_and_artist(self, loader, song_folder):
        """Test auto_download returns None when track or artist missing."""
        result1 = loader.auto_download(song_folder, None, 'Artist', 180.0)
        result2 = loader.auto_download(song_folder, 'Track', None, 180.0)
        result3 = loader.auto_download(song_folder, '', 'Artist', 180.0)
        
        assert result1 is None
        assert result2 is None
        assert result3 is None
    
    def test_download_and_save_creates_model(self, loader, song_folder):
        """Test download_and_save creates LyricsModel and saves file."""
        result_dict = {
            'trackName': 'Test Song',
            'syncedLyrics': '[00:10.00]Line 1\n[00:20.00]Line 2'
        }
        
        model = loader.download_and_save(result_dict, song_folder)
        
        assert model is not None
        assert len(model) == 2
        assert model._lines[0].text == "Line 1"
        
        # Verify file was saved
        lrc_path = song_folder / "lyrics.lrc"
        assert lrc_path.exists()
    
    def test_download_and_save_returns_none_without_synced(self, loader, song_folder):
        """Test download_and_save returns None when no syncedLyrics."""
        result_dict = {'trackName': 'Test Song'}
        
        model = loader.download_and_save(result_dict, song_folder)
        
        assert model is None
    
    def test_load_uses_auto_download_internally(self, loader, song_folder):
        """Test that load() uses auto_download() internally when no local file."""
        metadata = {
            'track_name': 'Test Song',
            'artist_name': 'Test Artist',
            'duration_seconds': 180.0
        }
        
        mock_results = [{
            'duration': 180.0,
            'syncedLyrics': '[00:10]Auto downloaded'
        }]
        
        with patch.object(loader, '_search_lrclib_api', return_value=mock_results):
            result = loader.load(song_folder, metadata)
        
        assert result is not None
        assert result._lines[0].text == "Auto downloaded"


class TestLyricsLoaderBackwardCompatibility:
    """Test that legacy API methods still work (deprecated but functional)."""
    
    @pytest.fixture
    def loader(self):
        return LyricsLoader()
    
    def test_search_lrclib_still_works(self, loader):
        """Test deprecated search_lrclib() still functions."""
        with patch.object(loader, '_search_lrclib_api', return_value=[{'test': 'data'}]) as mock:
            result = loader.search_lrclib('Track', 'Artist')
        
        mock.assert_called_once_with('Track', 'Artist')
        assert result == [{'test': 'data'}]
    
    def test_select_best_match_still_works(self, loader):
        """Test deprecated select_best_match() still functions."""
        results = [{'duration': 180.0, 'syncedLyrics': 'lyrics'}]
        
        with patch.object(loader, '_select_best_match', return_value=results[0]) as mock:
            result = loader.select_best_match(results, 180.0)
        
        mock.assert_called_once_with(results, 180.0)
        assert result == results[0]


class TestLyricsLoaderSaveLocal:
    """Test saving lyrics to local file."""
    
    @pytest.fixture
    def loader(self):
        return LyricsLoader()
    
    @pytest.fixture
    def song_folder(self, tmp_path):
        folder = tmp_path / "test_song"
        folder.mkdir()
        return folder
    
    def test_save_lrc_creates_file(self, loader, song_folder):
        """Test that _save_lrc creates lyrics.lrc file."""
        lrc_text = "[00:10.00]Test lyrics"
        
        loader._save_lrc(lrc_text, song_folder)
        
        lrc_path = song_folder / "lyrics.lrc"
        assert lrc_path.exists()
        content = lrc_path.read_text(encoding='utf-8')
        assert content == lrc_text
    
    def test_save_lrc_creates_folder(self, loader, tmp_path):
        """Test that _save_lrc creates parent folder if missing."""
        song_folder = tmp_path / "new_folder" / "test_song"
        lrc_text = "[00:10.00]Test lyrics"
        
        loader._save_lrc(lrc_text, song_folder)
        
        assert song_folder.exists()
        lrc_path = song_folder / "lyrics.lrc"
        assert lrc_path.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
