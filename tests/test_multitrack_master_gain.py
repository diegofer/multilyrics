import numpy as np
import pytest

from core.engine import MultiTrackPlayer


def make_mono_track(value, length=8):
    # shape (frames, channels=1)
    return np.full((length, 1), float(value), dtype='float32')


def test_master_gain_applies_to_mix():
    p = MultiTrackPlayer(samplerate=44100, blocksize=4)
    # two mono tracks of 0.5 each -> mix should be 1.0
    p._tracks = [make_mono_track(0.5, 8), make_mono_track(0.5, 8)]
    p._n_tracks = 2
    p._n_frames = 8
    p.target_gains = np.ones(2, dtype='float32')
    p.current_gains = p.target_gains.copy()

    # default master_gain == 1.0
    out = p._mix_block(0, 4)
    # left channel first frame should be ~1.0
    assert out[0, 0] == pytest.approx(1.0)

    p.set_master_gain(0.5)
    out2 = p._mix_block(0, 4)
    assert out2[0, 0] == pytest.approx(0.5)


def test_set_master_gain_clamps():
    p = MultiTrackPlayer()
    p.set_master_gain(2.0)
    assert p.get_master_gain() == pytest.approx(1.0)
    p.set_master_gain(-1.0)
    assert p.get_master_gain() == pytest.approx(0.0)
