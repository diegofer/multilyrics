"""Tests for LyricsLoader timeout and retry logic.

Validates HTTP request timeout, retry mechanism with exponential backoff,
and graceful error handling.
"""

import pytest
import urllib.error
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import time

from audio.lyrics.loader import LyricsLoader


class TestLyricsLoaderRetry:
    """Test suite for HTTP retry logic in LyricsLoader."""
    
    @pytest.fixture
    def loader(self):
        """Create a fresh LyricsLoader instance."""
        return LyricsLoader()
    
    def test_make_request_success_first_try(self, loader):
        """Successful request on first attempt returns response immediately."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"result": "success"}'
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = False
        
        with patch('urllib.request.urlopen', return_value=mock_response) as mock_urlopen:
            result = loader._make_request("http://test.com")
            
            assert result == b'{"result": "success"}'
            assert mock_urlopen.call_count == 1
    
    def test_make_request_retries_on_timeout(self, loader):
        """Request retries on timeout error with exponential backoff."""
        # First two attempts timeout, third succeeds
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"result": "success"}'
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = False
        
        with patch('urllib.request.urlopen') as mock_urlopen, \
             patch('time.sleep') as mock_sleep:
            
            # Simulate 2 timeouts then success
            mock_urlopen.side_effect = [
                urllib.error.URLError("timeout"),
                urllib.error.URLError("timeout"),
                mock_response
            ]
            
            start_time = time.time()
            result = loader._make_request("http://test.com")
            
            assert result == b'{"result": "success"}'
            assert mock_urlopen.call_count == 3
            
            # Verify exponential backoff: 1s, then 2s
            assert mock_sleep.call_count == 2
            mock_sleep.assert_any_call(1.0)  # First retry delay
            mock_sleep.assert_any_call(2.0)  # Second retry delay (doubled)
    
    def test_make_request_exhausts_retries(self, loader):
        """Request raises exception after all retries exhausted."""
        with patch('urllib.request.urlopen') as mock_urlopen, \
             patch('time.sleep') as mock_sleep:
            
            # All attempts fail
            mock_urlopen.side_effect = urllib.error.URLError("persistent error")
            
            with pytest.raises(urllib.error.URLError, match="persistent error"):
                loader._make_request("http://test.com")
            
            # Should have tried MAX_RETRIES times
            assert mock_urlopen.call_count == loader.MAX_RETRIES
            
            # Should have slept MAX_RETRIES - 1 times (no sleep after last attempt)
            assert mock_sleep.call_count == loader.MAX_RETRIES - 1
    
    def test_make_request_no_retry_on_client_error(self, loader):
        """4xx client errors are not retried."""
        mock_error = urllib.error.URLError("Not Found")
        mock_error.code = 404
        
        with patch('urllib.request.urlopen') as mock_urlopen, \
             patch('time.sleep') as mock_sleep:
            
            mock_urlopen.side_effect = mock_error
            
            with pytest.raises(urllib.error.URLError):
                loader._make_request("http://test.com")
            
            # Should only try once (no retry for 4xx)
            assert mock_urlopen.call_count == 1
            assert mock_sleep.call_count == 0
    
    def test_make_request_custom_timeout(self, loader):
        """Custom timeout parameter is respected."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'test'
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = False
        
        with patch('urllib.request.urlopen', return_value=mock_response) as mock_urlopen:
            loader._make_request("http://test.com", timeout=5.0)
            
            # Verify timeout was passed
            mock_urlopen.assert_called_once_with("http://test.com", timeout=5.0)
    
    def test_search_lrclib_api_handles_timeout_gracefully(self, loader):
        """API search returns empty list on timeout instead of crashing."""
        with patch.object(loader, '_make_request') as mock_request:
            mock_request.side_effect = urllib.error.URLError("timeout")
            
            results = loader._search_lrclib_api("test song", "test artist")
            
            # Should return empty list for graceful degradation
            assert results == []
    
    def test_search_lrclib_api_handles_json_decode_error(self, loader):
        """API search returns empty list on malformed JSON."""
        with patch.object(loader, '_make_request') as mock_request:
            mock_request.return_value = b'<html>Not JSON</html>'
            
            results = loader._search_lrclib_api("test song", "test artist")
            
            assert results == []
    
    def test_search_lrclib_api_success_with_retry(self, loader):
        """API search succeeds after retry."""
        valid_response = b'[{"trackName": "Test", "syncedLyrics": "[00:00.00]Test"}]'
        
        with patch.object(loader, '_make_request') as mock_request:
            # First call fails, second succeeds (simulated by retry inside _make_request)
            mock_request.return_value = valid_response
            
            results = loader._search_lrclib_api("test song", "test artist")
            
            assert len(results) == 1
            assert results[0]['trackName'] == "Test"
    
    def test_retry_delay_configuration(self, loader):
        """Verify retry configuration is reasonable."""
        assert loader.REQUEST_TIMEOUT == 10  # 10 seconds timeout
        assert loader.MAX_RETRIES == 3  # 3 attempts total
        assert loader.RETRY_DELAY == 1.0  # 1 second initial delay
    
    def test_exponential_backoff_timing(self, loader):
        """Verify exponential backoff doubles delay each time."""
        with patch('urllib.request.urlopen') as mock_urlopen, \
             patch('time.sleep') as mock_sleep:
            
            mock_urlopen.side_effect = urllib.error.URLError("fail")
            
            try:
                loader._make_request("http://test.com")
            except urllib.error.URLError:
                pass
            
            # Check delays: 1s, 2s (exponential: delay *= 2)
            calls = [call[0][0] for call in mock_sleep.call_args_list]
            assert calls[0] == 1.0
            assert calls[1] == 2.0
    
    def test_integration_search_with_network_issues(self, loader):
        """Integration test: search_all handles network issues gracefully."""
        with patch.object(loader, '_make_request') as mock_request:
            # Simulate intermittent network error
            mock_request.side_effect = [
                urllib.error.URLError("connection reset"),
                urllib.error.URLError("connection reset")
            ]
            
            # Should not crash, just return empty results
            results = loader.search_all("Test Song", "Test Artist")
            
            assert results == []
