from core.playback_manager import PlaybackManager
from models.timeline_model import TimelineModel


class FakeSignal:
    def __init__(self):
        self._cb = None

    def connect(self, cb):
        self._cb = cb

    def emit(self, *args, **kwargs):
        if self._cb is not None:
            self._cb(*args, **kwargs)


class FakeSync:
    def __init__(self):
        self.audioTimeUpdated = FakeSignal()
        self._last_set_audio_time = None

    def set_audio_time(self, t: float):
        self._last_set_audio_time = t


def test_audio_time_updates_timeline():
    sync = FakeSync()
    timeline = TimelineModel()
    # Ensure timeline duration allows the incoming time
    timeline.set_duration_seconds(10.0)
    pm = PlaybackManager(sync, timeline=timeline)

    # Emit an audio time update from the sync; the manager should call
    # timeline.set_playhead_time() and update the timeline playhead.
    sync.audioTimeUpdated.emit(1.5)
    assert timeline.get_playhead_time() == 1.5


def test_request_seek_updates_timeline_and_clamps():
    sync = FakeSync()
    timeline = TimelineModel()
    pm = PlaybackManager(sync, timeline=timeline)

    # Set a known duration and request a seek beyond it; timeline should be clamped
    pm.set_duration(5.0)
    pm.request_seek(10.0)
    assert timeline.get_playhead_time() == 5.0


def test_set_timeline_late_and_update():
    sync = FakeSync()
    timeline = TimelineModel()
    pm = PlaybackManager(sync, timeline=None)

    # Attach timeline after construction
    pm.set_timeline(timeline)
    # Ensure timeline duration allows the incoming time
    timeline.set_duration_seconds(10.0)
    sync.audioTimeUpdated.emit(2.25)
    assert timeline.get_playhead_time() == 2.25


def test_set_duration_updates_timeline_duration():
    sync = FakeSync()
    timeline = TimelineModel()
    pm = PlaybackManager(sync, timeline=timeline)

    pm.set_duration(7.5)
    assert timeline.duration_seconds == 7.5
