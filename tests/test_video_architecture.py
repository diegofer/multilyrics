"""
Test for refactored video architecture (VisualEngine + VisualBackground).

Tests the decoupled architecture without requiring actual video files or VLC.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch

from video.engines.base import VisualEngine
from video.engines.vlc_engine import VlcEngine
from video.engines.mpv_engine import MpvEngine
from video.backgrounds.base import VisualBackground
from video.backgrounds.video_lyrics_background import VideoLyricsBackground
from video.backgrounds.loop_background import VideoLoopBackground
from video.backgrounds.static_background import StaticFrameBackground
from video.backgrounds.blank_background import BlankBackground


class TestVisualEngineInterface:
    """Test that VisualEngine interface is properly defined."""

    def test_visual_engine_is_abstract(self):
        """VisualEngine should be abstract and not instantiable."""
        with pytest.raises(TypeError):
            VisualEngine()

    def test_vlc_engine_implements_interface(self):
        """VlcEngine should implement all VisualEngine methods."""
        # Mock VLC to avoid actual VLC dependency
        with patch('video.engines.vlc_engine.vlc'):
            engine = VlcEngine(is_legacy_hardware=False)

            # Check all required methods exist
            assert hasattr(engine, 'load')
            assert hasattr(engine, 'play')
            assert hasattr(engine, 'pause')
            assert hasattr(engine, 'stop')
            assert hasattr(engine, 'seek')
            assert hasattr(engine, 'set_rate')
            assert hasattr(engine, 'get_time')
            assert hasattr(engine, 'get_length')
            assert hasattr(engine, 'is_playing')
            assert hasattr(engine, 'attach_to_window')
            assert hasattr(engine, 'set_mute')
            assert hasattr(engine, 'release')

    def test_mpv_engine_raises_not_implemented(self):
        """MpvEngine should raise NotImplementedError (stub)."""
        with pytest.raises(NotImplementedError):
            MpvEngine(is_legacy_hardware=False)


class TestVisualBackgroundInterface:
    """Test that VisualBackground interface is properly defined."""

    def test_visual_background_is_abstract(self):
        """VisualBackground should be abstract and not instantiable."""
        with pytest.raises(TypeError):
            VisualBackground()

    def test_video_lyrics_background_implements_interface(self):
        """VideoLyricsBackground should implement all VisualBackground methods."""
        background = VideoLyricsBackground(sync_controller=None)

        # Check all required methods exist
        assert hasattr(background, 'start')
        assert hasattr(background, 'stop')
        assert hasattr(background, 'pause')
        assert hasattr(background, 'update')
        assert hasattr(background, 'on_video_end')
        assert hasattr(background, 'apply_correction')

    def test_loop_background_implements_interface(self):
        """VideoLoopBackground should implement all VisualBackground methods."""
        background = VideoLoopBackground()

        assert hasattr(background, 'start')
        assert hasattr(background, 'stop')
        assert hasattr(background, 'pause')
        assert hasattr(background, 'update')
        assert hasattr(background, 'on_video_end')

    def test_static_background_implements_interface(self):
        """StaticFrameBackground should implement all VisualBackground methods."""
        background = StaticFrameBackground(static_frame_seconds=0.0)

        assert hasattr(background, 'start')
        assert hasattr(background, 'stop')
        assert hasattr(background, 'pause')
        assert hasattr(background, 'update')
        assert hasattr(background, 'on_video_end')

    def test_blank_background_implements_interface(self):
        """BlankBackground should implement all VisualBackground methods."""
        background = BlankBackground()

        assert hasattr(background, 'start')
        assert hasattr(background, 'stop')
        assert hasattr(background, 'pause')
        assert hasattr(background, 'update')
        assert hasattr(background, 'on_video_end')


class TestBackgroundBehavior:
    """Test background behavior with mocked engine."""

    def create_mock_engine(self):
        """Create a mock VisualEngine for testing."""
        engine = Mock(spec=VisualEngine)
        engine.is_playing.return_value = True
        engine.get_time.return_value = 1000  # 1 second
        engine.get_length.return_value = 10000  # 10 seconds
        return engine

    def test_video_lyrics_background_start_with_offset(self):
        """VideoLyricsBackground should calculate offset correctly."""
        engine = self.create_mock_engine()
        background = VideoLyricsBackground(sync_controller=None)

        # Start with audio at 2s, offset +0.5s
        # Expected: video seeks to 2.5s = 2500ms
        background.start(engine, audio_time=2.0, offset=0.5)

        engine.seek.assert_called_once_with(2500)
        engine.play.assert_called_once()

    def test_loop_background_always_starts_at_zero(self):
        """VideoLoopBackground should always start from 0."""
        engine = self.create_mock_engine()
        background = VideoLoopBackground()

        # Start with any audio time/offset - should ignore and seek to 0
        background.start(engine, audio_time=5.0, offset=1.0)

        engine.seek.assert_called_once_with(0)
        engine.play.assert_called_once()

    def test_static_background_seeks_and_pauses(self):
        """StaticFrameBackground should seek to frame and pause."""
        engine = self.create_mock_engine()
        background = StaticFrameBackground(static_frame_seconds=2.5)

        # Start should seek to 2.5s = 2500ms and play (pause happens async)
        background.start(engine, audio_time=0.0, offset=0.0)

        engine.seek.assert_called_once_with(2500)
        engine.play.assert_called_once()

    def test_blank_background_does_nothing(self):
        """BlankBackground should be no-op."""
        engine = self.create_mock_engine()
        background = BlankBackground()

        # All methods should be no-op
        background.start(engine, audio_time=0.0, offset=0.0)
        background.stop(engine)
        background.pause(engine)
        background.update(engine, audio_time=0.0)
        background.on_video_end(engine)

        # Engine should not be called at all
        engine.seek.assert_not_called()
        engine.play.assert_not_called()
        engine.stop.assert_not_called()
        engine.pause.assert_not_called()

    def test_video_lyrics_background_apply_elastic_correction(self):
        """VideoLyricsBackground should apply elastic rate correction."""
        engine = self.create_mock_engine()
        background = VideoLyricsBackground(sync_controller=None)

        correction = {
            'type': 'elastic',
            'new_rate': 1.05,
            'current_rate': 1.0,
            'drift_ms': 50
        }

        background.apply_correction(engine, correction)

        engine.set_rate.assert_called_once_with(1.05)

    def test_video_lyrics_background_apply_hard_correction(self):
        """VideoLyricsBackground should apply hard seek correction."""
        engine = self.create_mock_engine()
        background = VideoLyricsBackground(sync_controller=None)

        correction = {
            'type': 'hard',
            'new_time_ms': 3000,
            'drift_ms': 100,
            'reset_rate': True
        }

        background.apply_correction(engine, correction)

        engine.seek.assert_called_once_with(3000)
        engine.set_rate.assert_called_once_with(1.0)


class TestVlcEngineInitialization:
    """Test VlcEngine initialization with different configurations."""

    @patch('video.engines.vlc_engine.vlc')
    def test_vlc_engine_normal_hardware(self, mock_vlc):
        """VlcEngine should initialize with standard args for normal hardware."""
        mock_instance = MagicMock()
        mock_player = MagicMock()
        mock_vlc.Instance.return_value = mock_instance
        mock_instance.media_player_new.return_value = mock_player

        engine = VlcEngine(is_legacy_hardware=False)

        # Check VLC instance was created
        mock_vlc.Instance.assert_called_once()
        args = mock_vlc.Instance.call_args[0][0]

        # Should have basic args but NOT legacy optimizations
        assert '--quiet' in args
        assert '--no-audio' in args
        assert '--avcodec-hurry-up' not in args  # Legacy optimization

    @patch('video.engines.vlc_engine.vlc')
    def test_vlc_engine_legacy_hardware(self, mock_vlc):
        """VlcEngine should add optimization args for legacy hardware."""
        mock_instance = MagicMock()
        mock_player = MagicMock()
        mock_vlc.Instance.return_value = mock_instance
        mock_instance.media_player_new.return_value = mock_player

        engine = VlcEngine(is_legacy_hardware=True)

        # Check VLC instance was created with legacy args
        args = mock_vlc.Instance.call_args[0][0]

        assert '--quiet' in args
        assert '--no-audio' in args
        assert '--avcodec-hurry-up' in args  # Legacy optimization
        assert '--avcodec-skiploopfilter=4' in args
        assert '--avcodec-threads=2' in args


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
