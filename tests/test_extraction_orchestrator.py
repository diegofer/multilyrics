"""Tests for ExtractionOrchestrator class.

Validates the pipeline coordination of audio extraction, beat detection,
and chord recognition with proper signal routing and error handling.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call
from PySide6.QtCore import QThread, Signal

from core.extraction_orchestrator import ExtractionOrchestrator


class TestExtractionOrchestrator:
    """Test suite for ExtractionOrchestrator."""
    
    @pytest.fixture
    def orchestrator(self, qapp):
        """Create orchestrator instance with mock status callback."""
        status_callback = Mock()
        orch = ExtractionOrchestrator(status_callback=status_callback)
        yield orch
        # Cleanup
        if orch.is_running():
            orch.stop_extraction()
    
    def test_initialization(self, orchestrator):
        """Orchestrator initializes with None workers and thread."""
        assert orchestrator.thread is None
        assert orchestrator.extract_worker is None
        assert orchestrator.beats_worker is None
        assert orchestrator.chords_worker is None
        assert not orchestrator.is_running()
    
    def test_start_extraction_creates_workers(self, orchestrator):
        """Starting extraction creates thread and all workers."""
        with patch('core.extraction_orchestrator.AudioExtractWorker'), \
             patch('core.extraction_orchestrator.BeatsExtractorWorker'), \
             patch('core.extraction_orchestrator.ChordExtractorWorker'), \
             patch('core.extraction_orchestrator.QThread'):
            
            orchestrator.start_extraction("/path/to/video.mp4")
            
            assert orchestrator.thread is not None
            assert orchestrator.extract_worker is not None
            assert orchestrator.beats_worker is not None
            assert orchestrator.chords_worker is not None
            assert orchestrator.is_running()
    
    def test_start_extraction_emits_started_signal(self, orchestrator, qtbot):
        """Starting extraction emits extraction_started signal."""
        with patch('core.extraction_orchestrator.AudioExtractWorker'), \
             patch('core.extraction_orchestrator.BeatsExtractorWorker'), \
             patch('core.extraction_orchestrator.ChordExtractorWorker'), \
             patch('core.extraction_orchestrator.QThread'):
            
            with qtbot.waitSignal(orchestrator.extraction_started, timeout=1000):
                orchestrator.start_extraction("/path/to/video.mp4")
    
    def test_start_extraction_empty_path_raises(self, orchestrator):
        """Starting with empty path raises ValueError."""
        with pytest.raises(ValueError, match="video_path cannot be empty"):
            orchestrator.start_extraction("")
    
    def test_start_extraction_updates_status(self, orchestrator):
        """Starting extraction calls status_callback."""
        with patch('core.extraction_orchestrator.AudioExtractWorker'), \
             patch('core.extraction_orchestrator.BeatsExtractorWorker'), \
             patch('core.extraction_orchestrator.ChordExtractorWorker'), \
             patch('core.extraction_orchestrator.QThread'):
            
            orchestrator.start_extraction("/path/to/video.mp4")
            
            # Should have called status callback with initial message
            orchestrator.status_callback.assert_called()
            args = orchestrator.status_callback.call_args[0]
            assert "extrayendo audio" in args[0].lower()
    
    def test_stop_extraction_when_not_running(self, orchestrator):
        """Stopping extraction when not running is safe (no-op)."""
        # Should not raise
        orchestrator.stop_extraction()
        assert not orchestrator.is_running()
    
    def test_stop_extraction_quits_thread(self, orchestrator):
        """Stopping extraction quits the thread."""
        with patch('core.extraction_orchestrator.AudioExtractWorker'), \
             patch('core.extraction_orchestrator.BeatsExtractorWorker'), \
             patch('core.extraction_orchestrator.ChordExtractorWorker'), \
             patch('core.extraction_orchestrator.QThread') as mock_thread_class:
            
            mock_thread = Mock()
            mock_thread.isRunning.return_value = True
            mock_thread_class.return_value = mock_thread
            
            orchestrator.start_extraction("/path/to/video.mp4")
            orchestrator.stop_extraction()
            
            mock_thread.quit.assert_called_once()
            mock_thread.wait.assert_called_once()
            assert not orchestrator.is_running()
    
    def test_audio_extracted_triggers_beats(self, orchestrator):
        """Audio extraction completion triggers beat detection via direct signal connection."""
        with patch('core.extraction_orchestrator.AudioExtractWorker') as mock_extract, \
             patch('core.extraction_orchestrator.BeatsExtractorWorker') as mock_beats, \
             patch('core.extraction_orchestrator.ChordExtractorWorker'), \
             patch('core.extraction_orchestrator.QThread'):
            
            mock_extract_instance = Mock()
            mock_beats_instance = Mock()
            mock_extract.return_value = mock_extract_instance
            mock_beats.return_value = mock_beats_instance
            
            orchestrator.start_extraction("/path/to/video.mp4")
            
            # Verify direct signal connection exists (workers chain themselves)
            # The result signal from extract_worker connects to beats_worker.run
            mock_extract_instance.signals.result.connect.assert_any_call(mock_beats_instance.run)
    
    def test_beats_extracted_triggers_chords(self, orchestrator):
        """Beat detection completion triggers chord recognition via direct signal connection."""
        with patch('core.extraction_orchestrator.AudioExtractWorker'), \
             patch('core.extraction_orchestrator.BeatsExtractorWorker') as mock_beats, \
             patch('core.extraction_orchestrator.ChordExtractorWorker') as mock_chords, \
             patch('core.extraction_orchestrator.QThread'):
            
            mock_beats_instance = Mock()
            mock_chords_instance = Mock()
            mock_beats.return_value = mock_beats_instance
            mock_chords.return_value = mock_chords_instance
            
            orchestrator.start_extraction("/path/to/video.mp4")
            
            # Verify direct signal connection exists (workers chain themselves)
            # The result signal from beats_worker connects to chords_worker.run
            mock_beats_instance.signals.result.connect.assert_any_call(mock_chords_instance.run)
    
    def test_chords_extracted_emits_completed(self, orchestrator, qtbot):
        """Chord recognition completion emits extraction_completed."""
        with patch('core.extraction_orchestrator.AudioExtractWorker'), \
             patch('core.extraction_orchestrator.BeatsExtractorWorker'), \
             patch('core.extraction_orchestrator.ChordExtractorWorker'), \
             patch('core.extraction_orchestrator.QThread'):
            
            orchestrator.start_extraction("/path/to/video.mp4")
            
            # Simulate chords extraction completing
            with qtbot.waitSignal(orchestrator.extraction_completed, timeout=1000) as blocker:
                orchestrator._on_chords_extracted("/path/to/audio.wav")
            
            # Should have emitted signal with audio path
            assert blocker.args == ["/path/to/audio.wav"]
    
    def test_stage_changed_signals(self, orchestrator, qtbot):
        """Stage transitions emit stage_changed signals."""
        with patch('core.extraction_orchestrator.AudioExtractWorker'), \
             patch('core.extraction_orchestrator.BeatsExtractorWorker'), \
             patch('core.extraction_orchestrator.ChordExtractorWorker'), \
             patch('core.extraction_orchestrator.QThread'):
            
            orchestrator.start_extraction("/path/to/video.mp4")
            
            # Check each stage transition
            with qtbot.waitSignal(orchestrator.stage_changed, timeout=1000) as blocker:
                orchestrator._on_audio_extracted("/path/to/audio.wav")
            assert blocker.args == ["beats"]
            
            with qtbot.waitSignal(orchestrator.stage_changed, timeout=1000) as blocker:
                orchestrator._on_beats_extracted("/path/to/audio.wav")
            assert blocker.args == ["chords"]
            
            with qtbot.waitSignal(orchestrator.stage_changed, timeout=1000) as blocker:
                orchestrator._on_chords_extracted("/path/to/audio.wav")
            assert blocker.args == ["lyrics"]
    
    def test_worker_error_emits_error_signal(self, orchestrator, qtbot):
        """Worker error emits extraction_error signal."""
        with patch('core.extraction_orchestrator.AudioExtractWorker'), \
             patch('core.extraction_orchestrator.BeatsExtractorWorker'), \
             patch('core.extraction_orchestrator.ChordExtractorWorker'), \
             patch('core.extraction_orchestrator.QThread'):
            
            orchestrator.start_extraction("/path/to/video.mp4")
            
            with qtbot.waitSignal(orchestrator.extraction_error, timeout=1000) as blocker:
                orchestrator._on_worker_error("FFmpeg extraction failed")
            
            assert blocker.args == ["FFmpeg extraction failed"]
            assert not orchestrator.is_running()
    
    def test_multiple_start_stops_previous(self, orchestrator):
        """Starting extraction while running stops previous extraction."""
        with patch('core.extraction_orchestrator.AudioExtractWorker'), \
             patch('core.extraction_orchestrator.BeatsExtractorWorker'), \
             patch('core.extraction_orchestrator.ChordExtractorWorker'), \
             patch('core.extraction_orchestrator.QThread') as mock_thread_class:
            
            mock_thread = Mock()
            mock_thread.isRunning.return_value = True
            mock_thread_class.return_value = mock_thread
            
            # Start first extraction
            orchestrator.start_extraction("/path/to/video1.mp4")
            first_thread = orchestrator.thread
            
            # Start second extraction (should stop first)
            orchestrator.start_extraction("/path/to/video2.mp4")
            
            # First thread should have been quit
            first_thread.quit.assert_called()
    
    def test_status_callback_called_at_each_stage(self, orchestrator):
        """Status callback is called at each pipeline stage."""
        with patch('core.extraction_orchestrator.AudioExtractWorker'), \
             patch('core.extraction_orchestrator.BeatsExtractorWorker'), \
             patch('core.extraction_orchestrator.ChordExtractorWorker'), \
             patch('core.extraction_orchestrator.QThread'):
            
            orchestrator.start_extraction("/path/to/video.mp4")
            initial_calls = orchestrator.status_callback.call_count
            
            # Each stage should update status
            orchestrator._on_audio_extracted("/path/to/audio.wav")
            assert orchestrator.status_callback.call_count > initial_calls
            
            orchestrator._on_beats_extracted("/path/to/audio.wav")
            assert orchestrator.status_callback.call_count > initial_calls + 1
            
            orchestrator._on_chords_extracted("/path/to/audio.wav")
            assert orchestrator.status_callback.call_count > initial_calls + 2
