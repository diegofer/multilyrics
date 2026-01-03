import pytest
from unittest.mock import Mock

from core.playback_manager import PlaybackManager


class DummySignal:
    def __init__(self):
        self._connected = None
    def connect(self, fn):
        self._connected = fn


class DummySync:
    def __init__(self):
        self.set_audio_time_called_with = None
        self.audioTimeUpdated = DummySignal()

    def set_audio_time(self, seconds: float):
        self.set_audio_time_called_with = seconds


@pytest.fixture
def sync():
    return DummySync()


@pytest.fixture
def playback(sync):
    return PlaybackManager(sync)


def test_request_seek_calls_players_and_sync(playback):
    mock_audio = Mock()
    mock_video = Mock()
    mock_timeline = Mock()

    playback.set_audio_player(mock_audio)
    playback.set_video_player(mock_video)
    playback.set_timeline(mock_timeline)

    # No longer testing positionChanged signal - it was removed
    # Instead verify timeline model gets updated

    playback.request_seek(4.2)

    mock_audio.seek_seconds.assert_called_once_with(4.2)
    mock_video.seek_seconds.assert_called_once_with(4.2)
    assert playback.sync.set_audio_time_called_with == 4.2
    mock_timeline.set_playhead_time.assert_called_once_with(4.2)


def test_request_seek_clamps_to_duration(playback):
    mock_audio = Mock()
    mock_video = Mock()
    mock_timeline = Mock()

    playback.set_audio_player(mock_audio)
    playback.set_video_player(mock_video)
    playback.set_timeline(mock_timeline)
    playback.set_duration(5.0)

    # Verify timeline gets clamped value instead of signal

    playback.request_seek(12.3)  # beyond duration

    mock_audio.seek_seconds.assert_called_once_with(5.0)
    mock_video.seek_seconds.assert_called_once_with(5.0)
    assert playback.sync.set_audio_time_called_with == 5.0
    mock_timeline.set_playhead_time.assert_called_once_with(5.0)


def test_request_seek_handles_negative_values(playback):
    mock_audio = Mock()
    mock_video = Mock()
    mock_timeline = Mock()

    playback.set_audio_player(mock_audio)
    playback.set_video_player(mock_video)
    playback.set_timeline(mock_timeline)

    # Verify timeline gets clamped to 0

    playback.request_seek(-3.5)

    mock_audio.seek_seconds.assert_called_once_with(0.0)
    mock_video.seek_seconds.assert_called_once_with(0.0)
    assert playback.sync.set_audio_time_called_with == 0.0
    mock_timeline.set_playhead_time.assert_called_once_with(0.0)


def test_request_seek_tolerates_missing_players(playback):
    # No players set, no timeline set
    # Should not raise even without signal connection
    playback.request_seek(2.0)
    
    # Test passes if no exception raised
    assert True


def test_playing_changed_emitted_on_audio_state_change(playback):
    mock_audio = Mock()

    playback.set_audio_player(mock_audio)

    emit_mock = Mock()
    playback.playingChanged.connect(emit_mock)

    # The PlaybackManager should have set the audio's playStateCallback attribute
    assert hasattr(mock_audio, 'playStateCallback')

    # Simulate audio player reporting state changes
    mock_audio.playStateCallback(True)
    emit_mock.assert_called_with(True)

    mock_audio.playStateCallback(False)
    assert emit_mock.call_count == 2
    assert emit_mock.call_args_list[-1][0][0] is False


def test_play_without_arg_resumes_not_restart(monkeypatch):
    # Avoid opening a real sounddevice stream by mocking OutputStream
    class DummyStream:
        def __init__(self, *a, **k):
            self.active = False
        def start(self):
            self.active = True
        def stop(self):
            self.active = False
        def close(self):
            self.active = False

    monkeypatch.setattr('sounddevice.OutputStream', DummyStream)

    from audio.multitrack_player import MultiTrackPlayer

    player = MultiTrackPlayer()
    # pretend we have one track loaded
    player._n_tracks = 1
    player._n_frames = 44100 * 5

    # move position to mid-track
    player._pos = 44100 * 1

    # Calling play() without arg should resume (not reset to 0)
    player.play()
    assert player.get_position_seconds() == pytest.approx(1.0)
    assert player.is_playing()

    # Calling play(0) explicitly should restart from beginning
    player.stop()
    player._pos = 44100 * 2
    player.play(0)
    assert player.get_position_seconds() == pytest.approx(0.0)
