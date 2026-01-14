import os
import sys
import numpy as np
import pytest

# Ensure project root is on sys.path so top-level packages (e.g., `audio`) can be imported
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from ui.widgets.timeline_view import TimelineView, MIN_SAMPLES_PER_PIXEL, MAX_ZOOM_LEVEL
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def make_widget_with_samples(length=1000, sr=44100):
    w = TimelineView(None)
    w.samples = np.linspace(-1.0, 1.0, num=length).astype(np.float32)
    w.sr = sr
    w.total_samples = len(w.samples)
    w.duration_seconds = w.total_samples / float(w.sr)
    return w


def test_clamp_zoom_for_width_limits(qapp):
    w = make_widget_with_samples(length=441000)  # 10 seconds at 44.1kHz
    width = 1000

    # If we request a huge zoom, it should be clamped so that spp >= MIN_SAMPLES_PER_PIXEL
    requested = 10000.0
    clamped = w._clamp_zoom_for_width(requested, width)

    # compute expected max factor by samples-per-pixel constraint
    expected_max = w.total_samples / (MIN_SAMPLES_PER_PIXEL * width)
    expected_max = max(1.0, min(MAX_ZOOM_LEVEL, expected_max))

    assert clamped <= requested
    assert clamped == pytest.approx(expected_max)


def test_zoom_invalidation_and_load_clears_cache(qapp):
    w = make_widget_with_samples(length=10000)

    # ensure track exists
    from ui.widgets.tracks.waveform_track import WaveformTrack
    if getattr(w, '_waveform_track', None) is None:
        w._waveform_track = WaveformTrack()

    # create fake cache
    w._waveform_track._last_params = (0, 100, 200, w.zoom_factor)
    w._waveform_track._last_envelope = (np.ones(200), np.ones(200))

    # set_zoom should invalidate cache
    w.set_zoom(2.0)
    assert w._waveform_track._last_params is None
    assert w._waveform_track._last_envelope is None

    # set cache again and call zoom_by
    w._waveform_track._last_params = (0, 100, 200, w.zoom_factor)
    w._waveform_track._last_envelope = (np.ones(200), np.ones(200))
    w.zoom_by(1.5)
    assert w._waveform_track._last_params is None
    assert w._waveform_track._last_envelope is None

    # load_audio(None) triggers empty state and also clears cache
    w._waveform_track._last_params = (1,)
    w._waveform_track._last_envelope = (np.array([1.0]), np.array([1.0]))
    w.load_audio(None)
    assert w._waveform_track._last_params is None
    assert w._waveform_track._last_envelope is None


def test_compute_envelope_matches_direct_reduction_for_large_window(qapp):
    # Create a repeating pattern so min/max are predictable
    pattern = np.array([0.0, 1.0, -1.0, 0.5], dtype=np.float32)
    samples = np.tile(pattern, 25)  # length 100
    w = make_widget_with_samples(length=0)
    w.samples = samples
    w.total_samples = len(samples)

    start = 0
    end = len(samples) - 1
    pixel_width = 10

    from ui.widgets.tracks.waveform_track import WaveformTrack
    if getattr(w, '_waveform_track', None) is None:
        w._waveform_track = WaveformTrack()
    mins, maxs = w._waveform_track._compute_envelope(w.samples, start, end, pixel_width, w.zoom_factor)

    # Compute expected by manual binning
    L = len(samples)
    edges = np.linspace(0, L, num=pixel_width+1, dtype=int)
    expected_mins = []
    expected_maxs = []
    for i in range(pixel_width):
        s = edges[i]
        e = edges[i+1]
        block = samples[s:e] if e > s else samples[s:s+1]
        expected_mins.append(float(np.min(block)))
        expected_maxs.append(float(np.max(block)))

    assert np.allclose(mins, expected_mins)
    assert np.allclose(maxs, expected_maxs)


def test_compute_envelope_interpolation_when_L_lt_w(qapp):
    # Small window (L < w) should use interpolation path
    samples = np.array([0.0, 0.5, -0.5, 1.0, 0.0], dtype=np.float32)  # L=5
    w = make_widget_with_samples(length=0)
    w.samples = samples
    w.total_samples = len(samples)

    start = 0
    end = len(samples) - 1
    pixel_width = 10  # w > L

    from ui.widgets.tracks.waveform_track import WaveformTrack
    if getattr(w, '_waveform_track', None) is None:
        w._waveform_track = WaveformTrack()
    mins, maxs = w._waveform_track._compute_envelope(w.samples, start, end, pixel_width, w.zoom_factor)

    # Expected interpolation equals numpy.interp used in implementation
    indices = np.linspace(0, len(samples) - 1, num=pixel_width)
    interp = np.interp(indices, np.arange(len(samples)), samples)

    assert np.allclose(mins, interp)
    assert np.allclose(maxs, interp)


def test_compute_envelope_empty_returns_zeros(qapp):
    w = make_widget_with_samples(length=0)
    w.samples = np.array([], dtype=np.float32)
    w.total_samples = 0

    from ui.widgets.tracks.waveform_track import WaveformTrack
    if getattr(w, '_waveform_track', None) is None:
        w._waveform_track = WaveformTrack()
    mins, maxs = w._waveform_track._compute_envelope(w.samples, 0, 0, 50, w.zoom_factor)
    assert mins.shape == (50,)
    assert maxs.shape == (50,)
    assert np.all(mins == 0)
    assert np.all(maxs == 0)


def test_compute_envelope_cache_hits(qapp):
    samples = np.linspace(-1.0, 1.0, num=200).astype(np.float32)
    w = make_widget_with_samples(length=0)
    w.samples = samples
    w.total_samples = len(samples)

    from ui.widgets.tracks.waveform_track import WaveformTrack
    if getattr(w, '_waveform_track', None) is None:
        w._waveform_track = WaveformTrack()

    a1, b1 = w._waveform_track._compute_envelope(w.samples, 0, len(samples)-1, 100, w.zoom_factor, downsample_factor=None)
    # After call, cache should be populated
    assert w._waveform_track._last_params is not None
    assert w._waveform_track._last_envelope is not None

    a2, b2 = w._waveform_track._compute_envelope(w.samples, 0, len(samples)-1, 100, w.zoom_factor, downsample_factor=None)
    # second call should hit cache and return same values
    assert np.array_equal(a1, a2)
    assert np.array_equal(b1, b2)
    assert w._waveform_track._last_params == (0, len(samples)-1, 100, w.zoom_factor, None)

