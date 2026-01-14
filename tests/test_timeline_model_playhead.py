import pytest

from models.timeline_model import TimelineModel


def test_observer_called_on_playhead_change():
    m = TimelineModel(duration_seconds=10.0)
    calls = []

    def cb(t):
        calls.append(t)

    m.on_playhead_changed(cb)
    m.set_playhead_time(1.23)

    assert calls == [1.23]


def test_observer_not_called_when_same_time():
    m = TimelineModel(duration_seconds=10.0)
    m.set_playhead_time(2.0)

    calls = []
    m.on_playhead_changed(lambda t: calls.append(t))
    # Setting same time should NOT trigger the observer
    m.set_playhead_time(2.0)

    assert calls == []


def test_multiple_observers_notified_in_order():
    m = TimelineModel(duration_seconds=10.0)
    calls = []

    def a(t):
        calls.append(("a", t))

    def b(t):
        calls.append(("b", t))

    m.on_playhead_changed(a)
    m.on_playhead_changed(b)
    m.set_playhead_time(3.0)

    assert calls == [("a", 3.0), ("b", 3.0)]


def test_exception_in_one_observer_does_not_stop_others():
    m = TimelineModel(duration_seconds=10.0)
    calls = []

    def bad(t):
        raise RuntimeError("boom")

    def good(t):
        calls.append(t)

    m.on_playhead_changed(bad)
    m.on_playhead_changed(good)
    # Even though first observer raises, second should run
    m.set_playhead_time(4.0)

    assert calls == [4.0]


def test_unsubscribe_removes_observer():
    m = TimelineModel(duration_seconds=10.0)
    calls = []

    def cb(t):
        calls.append(t)

    unsub = m.on_playhead_changed(cb)
    # Remove the observer
    unsub()

    m.set_playhead_time(5.0)
    assert calls == []


def test_set_playhead_sample_triggers_observer():
    m = TimelineModel(sample_rate=44100, duration_seconds=10.0)
    calls = []

    m.on_playhead_changed(lambda t: calls.append(t))
    # 44100 samples at 44100 Hz -> 1.0 seconds
    m.set_playhead_sample(44100)

    assert calls == [1.0]
