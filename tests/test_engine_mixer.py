"""
Multi Lyrics - Engine Mixer Unit Tests
Copyright (C) 2026 Diego Fernando

Comprehensive test coverage for mixer logic in MultiTrackPlayer:
- Solo/mute truth tables
- Gain smoothing (convergence, bounds)
- Master gain application
- Edge cases (all muted, all solo'd, empty tracks)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import numpy as np
import pytest

from core.engine import MultiTrackPlayer

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def make_mono_track(value, length=8):
    """Create a mono track with constant value."""
    return np.full((length, 1), float(value), dtype='float32')


def make_stereo_track(left_value, right_value, length=8):
    """Create a stereo track with different L/R values."""
    left = np.full((length, 1), float(left_value), dtype='float32')
    right = np.full((length, 1), float(right_value), dtype='float32')
    return np.column_stack([left, right])


def setup_player_with_tracks(n_tracks=3, track_length=8, track_value=1.0):
    """
    Setup player with N mono tracks.

    Args:
        n_tracks: Number of tracks
        track_length: Length of each track in samples
        track_value: Constant value for all tracks

    Returns:
        Configured MultiTrackPlayer instance
    """
    player = MultiTrackPlayer(samplerate=44100, blocksize=4)
    player._tracks = [make_mono_track(track_value, track_length) for _ in range(n_tracks)]
    player._n_tracks = n_tracks
    player._n_frames = track_length
    player.target_gains = np.ones(n_tracks, dtype='float32')
    player.current_gains = player.target_gains.copy()
    player.muted = np.zeros(n_tracks, dtype=bool)
    player.solo_mask = np.zeros(n_tracks, dtype=bool)
    return player


# =============================================================================
# SOLO/MUTE TRUTH TABLE TESTS
# =============================================================================

class TestSoloMuteLogic:
    """Test solo and mute logic with all combinations."""

    def test_no_solo_no_mute_all_active(self):
        """When no tracks are solo'd or muted, all should be active."""
        player = setup_player_with_tracks(n_tracks=3, track_value=1.0)

        # Mix: 3 tracks * 1.0 gain = 3.0
        out = player._mix_block(0, 4)
        assert out[0, 0] == pytest.approx(3.0)

    def test_mute_single_track(self):
        """Muting a single track should exclude it from mix."""
        player = setup_player_with_tracks(n_tracks=3, track_value=1.0)
        player.mute(1, True)  # Mute track 1

        # Mix: 2 tracks * 1.0 gain = 2.0
        out = player._mix_block(0, 4)
        assert out[0, 0] == pytest.approx(2.0)

    def test_mute_multiple_tracks(self):
        """Muting multiple tracks should exclude them from mix."""
        player = setup_player_with_tracks(n_tracks=3, track_value=1.0)
        player.mute(0, True)
        player.mute(2, True)

        # Mix: 1 track * 1.0 gain = 1.0
        out = player._mix_block(0, 4)
        assert out[0, 0] == pytest.approx(1.0)

    def test_mute_all_tracks_silence(self):
        """Muting all tracks should produce silence."""
        player = setup_player_with_tracks(n_tracks=3, track_value=1.0)
        player.mute(0, True)
        player.mute(1, True)
        player.mute(2, True)

        out = player._mix_block(0, 4)
        assert out[0, 0] == pytest.approx(0.0)

    def test_solo_single_track(self):
        """Solo'ing a single track should only play that track."""
        player = setup_player_with_tracks(n_tracks=3, track_value=1.0)
        player.solo(1, True)  # Solo track 1

        # Mix: 1 track * 1.0 gain = 1.0
        out = player._mix_block(0, 4)
        assert out[0, 0] == pytest.approx(1.0)

    def test_solo_multiple_tracks(self):
        """Solo'ing multiple tracks should play only those tracks."""
        player = setup_player_with_tracks(n_tracks=3, track_value=1.0)
        player.solo(0, True)
        player.solo(2, True)

        # Mix: 2 tracks * 1.0 gain = 2.0
        out = player._mix_block(0, 4)
        assert out[0, 0] == pytest.approx(2.0)

    def test_solo_overrides_non_solo(self):
        """When any track is solo'd, non-solo tracks are excluded."""
        player = setup_player_with_tracks(n_tracks=3, track_value=1.0)
        player.solo(1, True)  # Only track 1 should be heard

        out = player._mix_block(0, 4)
        assert out[0, 0] == pytest.approx(1.0)

    def test_solo_and_mute_same_track_muted(self):
        """Muting a solo'd track should silence it (mute takes precedence)."""
        player = setup_player_with_tracks(n_tracks=3, track_value=1.0)
        player.solo(1, True)
        player.mute(1, True)

        # Solo track 1 but also muted -> silence
        out = player._mix_block(0, 4)
        assert out[0, 0] == pytest.approx(0.0)

    def test_solo_multiple_mute_one_of_them(self):
        """Solo'ing multiple tracks but muting one of them."""
        player = setup_player_with_tracks(n_tracks=3, track_value=1.0)
        player.solo(0, True)
        player.solo(1, True)
        player.mute(1, True)  # Mute one of the solo'd tracks

        # Mix: Only track 0 plays (track 1 is solo'd but muted)
        out = player._mix_block(0, 4)
        assert out[0, 0] == pytest.approx(1.0)

    def test_clear_solo(self):
        """clear_solo() should disable all solo flags."""
        player = setup_player_with_tracks(n_tracks=3, track_value=1.0)
        player.solo(0, True)
        player.solo(2, True)

        # Before clear: 2 tracks
        out1 = player._mix_block(0, 4)
        assert out1[0, 0] == pytest.approx(2.0)

        player.clear_solo()

        # After clear: all 3 tracks
        out2 = player._mix_block(0, 4)
        assert out2[0, 0] == pytest.approx(3.0)

    def test_unmute_track(self):
        """Unmuting a previously muted track should restore it."""
        player = setup_player_with_tracks(n_tracks=3, track_value=1.0)
        player.mute(1, True)

        # Muted: 2 tracks
        out1 = player._mix_block(0, 4)
        assert out1[0, 0] == pytest.approx(2.0)

        player.mute(1, False)

        # Unmuted: 3 tracks
        out2 = player._mix_block(0, 4)
        assert out2[0, 0] == pytest.approx(3.0)

    def test_unsolo_track(self):
        """Unsolo'ing a solo'd track."""
        player = setup_player_with_tracks(n_tracks=3, track_value=1.0)
        player.solo(1, True)

        # Solo: 1 track
        out1 = player._mix_block(0, 4)
        assert out1[0, 0] == pytest.approx(1.0)

        player.solo(1, False)

        # No solo: all 3 tracks
        out2 = player._mix_block(0, 4)
        assert out2[0, 0] == pytest.approx(3.0)


# =============================================================================
# GAIN TESTS
# =============================================================================

class TestGainControl:
    """Test per-track and master gain control."""

    def test_set_gain_single_track(self):
        """Setting gain on a single track should affect only that track."""
        player = setup_player_with_tracks(n_tracks=3, track_value=1.0)
        player.set_gain(1, 0.5)

        # Force immediate gain update (skip smoothing for test)
        player.current_gains[1] = 0.5

        # Mix: track0=1.0, track1=0.5, track2=1.0 -> 2.5
        out = player._mix_block(0, 4)
        assert out[0, 0] == pytest.approx(2.5)

    def test_set_gain_zero_silences_track(self):
        """Setting gain to 0 should silence the track."""
        player = setup_player_with_tracks(n_tracks=3, track_value=1.0)
        player.set_gain(1, 0.0)
        player.current_gains[1] = 0.0

        # Mix: 2 tracks * 1.0 = 2.0
        out = player._mix_block(0, 4)
        assert out[0, 0] == pytest.approx(2.0)

    def test_set_gain_clamps_to_0_1(self):
        """Gain should be clamped to [0.0, 1.0] range."""
        player = setup_player_with_tracks(n_tracks=1)

        # Test upper clamp
        player.set_gain(0, 2.0)
        assert player.target_gains[0] == pytest.approx(1.0)

        # Test lower clamp
        player.set_gain(0, -0.5)
        assert player.target_gains[0] == pytest.approx(0.0)

    def test_get_gain(self):
        """get_gain() should return current target gain."""
        player = setup_player_with_tracks(n_tracks=2)
        player.set_gain(0, 0.7)
        player.set_gain(1, 0.3)

        assert player.get_gain(0) == pytest.approx(0.7)
        assert player.get_gain(1) == pytest.approx(0.3)

    def test_master_gain_affects_all_tracks(self):
        """Master gain should multiply the entire mix."""
        player = setup_player_with_tracks(n_tracks=3, track_value=1.0)

        # Default master gain = 1.0
        out1 = player._mix_block(0, 4)
        assert out1[0, 0] == pytest.approx(3.0)

        player.set_master_gain(0.5)
        out2 = player._mix_block(0, 4)
        assert out2[0, 0] == pytest.approx(1.5)  # 3.0 * 0.5

    def test_master_gain_zero_silences_output(self):
        """Master gain of 0 should silence all output."""
        player = setup_player_with_tracks(n_tracks=3, track_value=1.0)
        player.set_master_gain(0.0)

        out = player._mix_block(0, 4)
        assert out[0, 0] == pytest.approx(0.0)

    def test_master_gain_clamps_to_0_1(self):
        """Master gain should be clamped to [0.0, 1.0]."""
        player = setup_player_with_tracks(n_tracks=1)

        player.set_master_gain(2.0)
        assert player.get_master_gain() == pytest.approx(1.0)

        player.set_master_gain(-0.5)
        assert player.get_master_gain() == pytest.approx(0.0)

    def test_master_and_track_gain_multiply(self):
        """Master gain and track gain should multiply together."""
        player = setup_player_with_tracks(n_tracks=2, track_value=1.0)
        player.set_gain(0, 0.5)
        player.set_gain(1, 0.8)
        player.current_gains[0] = 0.5
        player.current_gains[1] = 0.8
        player.set_master_gain(0.5)

        # Mix: (0.5 + 0.8) * 0.5 = 0.65
        out = player._mix_block(0, 4)
        assert out[0, 0] == pytest.approx(0.65)


# =============================================================================
# GAIN SMOOTHING TESTS
# =============================================================================

class TestGainSmoothing:
    """Test exponential gain smoothing behavior."""

    def test_gain_smoothing_converges_to_target(self):
        """Current gain should exponentially converge to target gain."""
        player = setup_player_with_tracks(n_tracks=1, track_value=1.0)
        player.gain_smoothing = 0.15
        player.current_gains[0] = 0.0
        player.set_gain(0, 1.0)

        # Run multiple mix blocks to allow convergence
        for _ in range(50):
            player._mix_block(0, 4)

        # Should be very close to target after 50 iterations
        assert player.current_gains[0] == pytest.approx(1.0, abs=0.01)

    def test_gain_smoothing_rate(self):
        """Verify exponential smoothing formula: g = g*(1-α) + target*α"""
        player = setup_player_with_tracks(n_tracks=1, track_value=1.0)
        alpha = 0.15
        player.gain_smoothing = alpha
        player.current_gains[0] = 0.0
        player.set_gain(0, 1.0)

        # First iteration
        player._mix_block(0, 4)
        expected_1 = 0.0 * (1 - alpha) + 1.0 * alpha
        assert player.current_gains[0] == pytest.approx(expected_1)

        # Second iteration
        player._mix_block(0, 4)
        expected_2 = expected_1 * (1 - alpha) + 1.0 * alpha
        assert player.current_gains[0] == pytest.approx(expected_2)

    def test_gain_smoothing_prevents_clicks(self):
        """Rapid gain changes should be smoothed to prevent clicks."""
        player = setup_player_with_tracks(n_tracks=1, track_value=1.0)
        player.gain_smoothing = 0.15
        player.current_gains[0] = 1.0

        # Sudden gain drop
        player.set_gain(0, 0.0)

        # First block should NOT immediately be 0
        out1 = player._mix_block(0, 4)
        assert out1[0, 0] > 0.5  # Should still have significant amplitude

    def test_gain_smoothing_respects_bounds(self):
        """Smoothed gain should never exceed [0.0, 1.0] range."""
        player = setup_player_with_tracks(n_tracks=1, track_value=1.0)
        player.gain_smoothing = 0.5  # Aggressive smoothing
        player.current_gains[0] = 1.0
        player.set_gain(0, 1.0)

        # Run many iterations
        for _ in range(100):
            player._mix_block(0, 4)
            # Should never exceed bounds
            assert 0.0 <= player.current_gains[0] <= 1.0


# =============================================================================
# STEREO/MONO MIXING TESTS
# =============================================================================

class TestStereoMono:
    """Test mixing of mono and stereo tracks."""

    def test_mono_track_duplicates_to_stereo(self):
        """Mono tracks should be duplicated to both L/R channels."""
        player = setup_player_with_tracks(n_tracks=1, track_value=1.0)
        out = player._mix_block(0, 4)

        # Both channels should be identical
        assert out[0, 0] == out[0, 1]

    def test_stereo_track_averaged_to_mono_then_duplicated(self):
        """Stereo tracks should be averaged to mono, then duplicated."""
        player = MultiTrackPlayer(samplerate=44100, blocksize=4)
        # Create stereo track: L=0.8, R=0.4 -> average = 0.6
        player._tracks = [make_stereo_track(0.8, 0.4, length=8)]
        player._n_tracks = 1
        player._n_frames = 8
        player.target_gains = np.ones(1, dtype='float32')
        player.current_gains = player.target_gains.copy()

        out = player._mix_block(0, 4)
        expected = (0.8 + 0.4) / 2.0  # Average of L and R
        assert out[0, 0] == pytest.approx(expected)
        assert out[0, 1] == pytest.approx(expected)

    def test_mixed_mono_stereo_tracks(self):
        """Player should handle mix of mono and stereo tracks."""
        player = MultiTrackPlayer(samplerate=44100, blocksize=4)
        player._tracks = [
            make_mono_track(1.0, length=8),
            make_stereo_track(0.6, 0.4, length=8),  # avg = 0.5
        ]
        player._n_tracks = 2
        player._n_frames = 8
        player.target_gains = np.ones(2, dtype='float32')
        player.current_gains = player.target_gains.copy()

        out = player._mix_block(0, 4)
        # mono(1.0) + stereo_avg(0.5) = 1.5
        assert out[0, 0] == pytest.approx(1.5)


# =============================================================================
# EDGE CASES
# =============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_player_no_tracks(self):
        """Player with no tracks should produce silence."""
        player = MultiTrackPlayer(samplerate=44100, blocksize=4)
        player._tracks = []
        player._n_tracks = 0
        player._n_frames = 0

        out = player._mix_block(0, 4)
        assert np.all(out == 0.0)

    def test_mix_beyond_end_of_track(self):
        """Mixing beyond track length should pad with zeros."""
        player = setup_player_with_tracks(n_tracks=1, track_length=8, track_value=1.0)

        # Request 8 frames starting at position 4 (only 4 frames available)
        out = player._mix_block(4, 8)

        # First 4 frames should have audio
        assert out[0, 0] == pytest.approx(1.0)
        assert out[3, 0] == pytest.approx(1.0)

        # Last 4 frames should be silence (padding)
        assert out[4, 0] == pytest.approx(0.0)
        assert out[7, 0] == pytest.approx(0.0)

    def test_mix_at_exact_end_of_track(self):
        """Mixing at exactly the end of track should produce silence."""
        player = setup_player_with_tracks(n_tracks=1, track_length=8, track_value=1.0)

        out = player._mix_block(8, 4)
        assert np.all(out == 0.0)

    def test_mix_past_end_of_track(self):
        """Mixing past the end of track should produce silence."""
        player = setup_player_with_tracks(n_tracks=1, track_length=8, track_value=1.0)

        out = player._mix_block(100, 4)
        assert np.all(out == 0.0)

    def test_all_tracks_different_gains(self):
        """Mix with all tracks having different gains."""
        player = setup_player_with_tracks(n_tracks=4, track_value=1.0)
        gains = [0.2, 0.4, 0.6, 0.8]
        for i, g in enumerate(gains):
            player.set_gain(i, g)
            player.current_gains[i] = g

        out = player._mix_block(0, 4)
        expected = sum(gains)
        assert out[0, 0] == pytest.approx(expected)

    def test_solo_all_tracks(self):
        """Solo'ing all tracks should behave like no solo."""
        player = setup_player_with_tracks(n_tracks=3, track_value=1.0)

        # No solo baseline
        out1 = player._mix_block(0, 4)

        # Solo all tracks
        for i in range(3):
            player.solo(i, True)

        out2 = player._mix_block(0, 4)

        # Should be identical (all tracks active in both cases)
        assert out1[0, 0] == pytest.approx(out2[0, 0])

    def test_zero_blocksize_request(self):
        """Requesting 0 frames should return empty array."""
        player = setup_player_with_tracks(n_tracks=1, track_value=1.0)
        out = player._mix_block(0, 0)
        assert out.shape == (0, 2)

    def test_tracks_with_zero_amplitude(self):
        """Tracks with 0 amplitude should contribute nothing to mix."""
        player = setup_player_with_tracks(n_tracks=3, track_value=0.0)
        out = player._mix_block(0, 4)
        assert out[0, 0] == pytest.approx(0.0)


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestMixerIntegration:
    """Test complex scenarios combining multiple mixer features."""

    def test_complex_scenario_solo_mute_gain(self):
        """Complex scenario: Solo some tracks, mute one of them, different gains."""
        player = setup_player_with_tracks(n_tracks=4, track_value=1.0)

        # Solo tracks 0, 1, 2 (exclude track 3)
        player.solo(0, True)
        player.solo(1, True)
        player.solo(2, True)

        # Mute track 1 (solo'd but muted)
        player.mute(1, True)

        # Set different gains
        player.set_gain(0, 0.5)
        player.set_gain(2, 0.8)
        player.current_gains[0] = 0.5
        player.current_gains[2] = 0.8

        # Master gain
        player.set_master_gain(0.5)

        # Expected: (track0=0.5 + track2=0.8) * master=0.5 = 0.65
        out = player._mix_block(0, 4)
        assert out[0, 0] == pytest.approx(0.65)

    def test_dynamic_gain_changes_during_playback(self):
        """Simulate gain changes during playback with smoothing."""
        player = setup_player_with_tracks(n_tracks=1, track_value=1.0)
        player.gain_smoothing = 0.2

        # Start at full gain
        player.set_gain(0, 1.0)
        player.current_gains[0] = 1.0

        # Mix a few blocks
        out1 = player._mix_block(0, 4)
        assert out1[0, 0] == pytest.approx(1.0)

        # Change gain to 0.5
        player.set_gain(0, 0.5)

        # Next block should be somewhere between 1.0 and 0.5
        out2 = player._mix_block(0, 4)
        assert 0.5 < out2[0, 0] < 1.0

        # After many blocks, should converge to 0.5
        for _ in range(30):
            player._mix_block(0, 4)

        out3 = player._mix_block(0, 4)
        assert out3[0, 0] == pytest.approx(0.5, abs=0.05)

    def test_realistic_mixer_session(self):
        """Simulate a realistic mixing session."""
        player = setup_player_with_tracks(n_tracks=6, track_value=1.0)

        # Setup gains like a real mix
        gains = [0.7, 0.8, 0.6, 0.9, 0.5, 0.4]  # Drums, Bass, Guitar1, Guitar2, Vox, Keys
        for i, g in enumerate(gains):
            player.set_gain(i, g)
            player.current_gains[i] = g

        # Mute keys during verse
        player.mute(5, True)

        # Solo guitars to check their sound
        player.solo(2, True)
        player.solo(3, True)

        # Expected: guitar1=0.6 + guitar2=0.9 = 1.5
        out1 = player._mix_block(0, 4)
        assert out1[0, 0] == pytest.approx(1.5)

        # Clear solo for full mix
        player.clear_solo()

        # Expected: all except keys (muted)
        expected = sum(gains[:5])  # Exclude keys (index 5)
        out2 = player._mix_block(0, 4)
        assert out2[0, 0] == pytest.approx(expected)

        # Master fade-out
        player.set_master_gain(0.3)
        out3 = player._mix_block(0, 4)
        assert out3[0, 0] == pytest.approx(expected * 0.3)


# =============================================================================
# PERFORMANCE TESTS (Optional, for benchmarking)
# =============================================================================

class TestMixerPerformance:
    """Test mixer performance under stress (optional benchmarks)."""

    def test_many_tracks_performance(self):
        """Mixer should handle many tracks efficiently."""
        player = setup_player_with_tracks(n_tracks=32, track_length=1024, track_value=1.0)

        # Should complete without timeout (pytest default 60s)
        import time
        start = time.perf_counter()
        out = player._mix_block(0, 512)
        duration = time.perf_counter() - start

        # Should be very fast (< 10ms for 32 tracks)
        assert duration < 0.01
        assert out[0, 0] == pytest.approx(32.0)

    def test_long_audio_blocks(self):
        """Mixer should handle large block sizes efficiently."""
        player = setup_player_with_tracks(n_tracks=8, track_length=48000, track_value=1.0)

        # Mix 1 second of audio (48000 samples @ 48kHz)
        import time
        start = time.perf_counter()
        out = player._mix_block(0, 48000)
        duration = time.perf_counter() - start

        # Should complete in < 50ms
        assert duration < 0.05
        assert out.shape == (48000, 2)


# =============================================================================
# REGRESSION TESTS
# =============================================================================

class TestRegressions:
    """Test for known bugs and regressions."""

    def test_gain_smoothing_doesnt_overshoot(self):
        """Regression: Gain smoothing should never overshoot target."""
        player = setup_player_with_tracks(n_tracks=1, track_value=1.0)
        player.gain_smoothing = 0.99  # Very aggressive smoothing
        player.current_gains[0] = 0.0
        player.set_gain(0, 0.5)

        for _ in range(100):
            player._mix_block(0, 4)
            # Should never exceed target
            assert player.current_gains[0] <= 0.5 + 1e-6

    def test_solo_mask_persists_after_mix(self):
        """Regression: Solo mask should persist between mix calls."""
        player = setup_player_with_tracks(n_tracks=3, track_value=1.0)
        player.solo(1, True)

        out1 = player._mix_block(0, 4)
        out2 = player._mix_block(4, 4)

        # Both blocks should have same level (solo persists)
        assert out1[0, 0] == pytest.approx(out2[0, 0])

    def test_mute_doesnt_affect_gain(self):
        """Regression: Muting should not modify gain values."""
        player = setup_player_with_tracks(n_tracks=1, track_value=1.0)
        player.set_gain(0, 0.7)

        original_gain = player.get_gain(0)
        player.mute(0, True)

        # Gain should be unchanged
        assert player.get_gain(0) == pytest.approx(original_gain)

    def test_master_gain_doesnt_affect_track_gains(self):
        """Regression: Master gain should not modify track gains."""
        player = setup_player_with_tracks(n_tracks=2, track_value=1.0)
        player.set_gain(0, 0.6)
        player.set_gain(1, 0.8)

        original_gains = [player.get_gain(0), player.get_gain(1)]

        player.set_master_gain(0.5)

        # Track gains should be unchanged
        assert player.get_gain(0) == pytest.approx(original_gains[0])
        assert player.get_gain(1) == pytest.approx(original_gains[1])
