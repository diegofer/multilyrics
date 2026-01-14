import pytest

from models.timeline_model import TimelineModel


def test_downbeats_in_range_returns_correct_downbeats():
    m = TimelineModel()
    # Set beats with downbeat flags (1 indicates downbeat)
    m.set_beats([0.5, 1.0, 1.5, 2.0], downbeat_flags=[0, 1, 0, 1])

    res = m.downbeats_in_range(0.0, 2.0)
    assert res == [1.0, 2.0]


def test_downbeats_in_range_empty_when_no_downbeats():
    m = TimelineModel()
    m.set_beats([0.5, 1.0], downbeat_flags=None)
    assert m.downbeats_in_range(0.0, 2.0) == []


def test_downbeats_in_range_excludes_outside_range():
    m = TimelineModel()
    m.set_beats([0.5, 1.0, 2.0], downbeat_flags=[1, 0, 1])
    # Query a range that excludes the downbeats
    assert m.downbeats_in_range(1.1, 1.9) == []


def test_downbeats_in_range_invalid_range_raises():
    m = TimelineModel()
    with pytest.raises(ValueError):
        m.downbeats_in_range(2.0, 1.0)
