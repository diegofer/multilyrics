"""
Test TimelineView empty state initialization and transitions.

Verifies that the timeline can start without audio and properly
transitions to loaded state when audio is provided.
"""

import tempfile
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf
from PySide6.QtWidgets import QApplication

from models.timeline_model import TimelineModel
from ui.widgets.timeline_view import TimelineView


@pytest.fixture
def qapp():
    """Fixture to provide QApplication instance"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def temp_audio_file():
    """Create a temporary audio file for testing"""
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        # Generate 1 second of sine wave at 440 Hz
        sample_rate = 44100
        duration = 1.0
        samples = int(sample_rate * duration)
        t = np.linspace(0, duration, samples)
        audio_data = np.sin(2 * np.pi * 440 * t).astype(np.float32)

        sf.write(f.name, audio_data, sample_rate)
        yield Path(f.name)

        # Cleanup
        Path(f.name).unlink(missing_ok=True)


def test_timeline_starts_empty(qapp):
    """Test that TimelineView initializes in empty state"""
    timeline_view = TimelineView()

    # Verify empty state
    assert not timeline_view.has_audio_loaded()
    assert timeline_view.audio_data is None
    assert timeline_view.audio_path is None
    assert timeline_view.total_samples == 0
    assert timeline_view.duration_seconds == 0.0

    # Verify get_audio_info returns None
    assert timeline_view.get_audio_info() is None


def test_timeline_no_audio_path_parameter(qapp):
    """Test that TimelineView constructor doesn't require audio_path parameter"""
    # Should not raise any exception
    timeline_view = TimelineView()
    assert timeline_view is not None


def test_timeline_loads_audio_from_empty_state(qapp, temp_audio_file):
    """Test transition from empty state to loaded state"""
    timeline_view = TimelineView()
    timeline_model = TimelineModel()
    timeline_view.set_timeline(timeline_model)

    # Verify starts empty
    assert not timeline_view.has_audio_loaded()

    # Load audio
    timeline_view.load_audio_from_master(temp_audio_file)

    # Verify audio is loaded
    assert timeline_view.has_audio_loaded()
    assert timeline_view.audio_data is not None
    assert len(timeline_view.audio_data) > 0
    assert timeline_view.audio_path == str(temp_audio_file)
    assert timeline_view.sample_rate == 44100
    assert timeline_view.total_samples > 0
    assert timeline_view.duration_seconds > 0

    # Verify get_audio_info returns data
    info = timeline_view.get_audio_info()
    assert info is not None
    assert info['path'] == str(temp_audio_file)
    assert info['samples'] > 0
    assert info['sample_rate'] == 44100
    assert info['duration'] > 0


def test_timeline_height_changes_on_load(qapp, temp_audio_file):
    """Test that minimum height changes from empty to loaded state"""
    timeline_view = TimelineView()

    # Empty state has smaller height
    empty_height = timeline_view.minimumHeight()
    assert empty_height == 100

    # Load audio
    timeline_view.load_audio_from_master(temp_audio_file)

    # Loaded state has larger height
    loaded_height = timeline_view.minimumHeight()
    assert loaded_height == 200


def test_timeline_handles_missing_file(qapp):
    """Test that loading non-existent file doesn't crash"""
    timeline_view = TimelineView()

    # Try to load non-existent file
    timeline_view.load_audio_from_master("/nonexistent/path/audio.wav")

    # Should remain in empty state
    assert not timeline_view.has_audio_loaded()
    assert timeline_view.audio_data is None


def test_timeline_resets_to_empty_on_error(qapp):
    """Test that _reset_to_empty_state properly clears all state"""
    timeline_view = TimelineView()

    # Manually set some state
    timeline_view.audio_data = np.array([1, 2, 3])
    timeline_view.audio_path = "some_path.wav"
    timeline_view.sample_rate = 48000
    timeline_view.total_samples = 100

    # Reset to empty
    timeline_view._reset_to_empty_state()

    # Verify all state is cleared
    assert timeline_view.audio_data is None
    assert timeline_view.audio_path is None
    assert timeline_view.sample_rate == 44100
    assert timeline_view.total_samples == 0
    assert timeline_view.minimumHeight() == 100


def test_timeline_view_state_reset(qapp, temp_audio_file):
    """Test that reset_view_state works after loading audio"""
    timeline_view = TimelineView()
    timeline_model = TimelineModel()
    timeline_view.set_timeline(timeline_model)

    # Load audio
    timeline_view.load_audio_from_master(temp_audio_file)

    # Modify view state
    timeline_view.zoom_factor = 10.0
    timeline_view._user_zoom_override = True
    timeline_view._lyrics_edit_mode = True

    # Reset view state
    timeline_view.reset_view_state()

    # Verify view state is reset (but audio remains loaded)
    assert timeline_view.zoom_factor == 1.0
    assert timeline_view._user_zoom_override == False
    assert timeline_view._lyrics_edit_mode == False
    assert timeline_view.has_audio_loaded()  # Audio should still be loaded
