#!/usr/bin/env python3
"""
Test script for RAM validation and latency measurement.

Tests:
1. RAM validation with synthetic large tracks
2. Latency measurement during playback
3. get_latency_stats() output format

Usage:
    python scripts/test_audio_optimizations.py [test_audio.wav]
"""

import sys
import time
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.engine import MultiTrackPlayer
from utils.logger import get_logger

logger = get_logger(__name__)


def _default_temp_path(name: str) -> Path:
    """Return a cross-platform temp path for test audio files."""
    return Path(tempfile.gettempdir()) / name


def create_test_audio(path: str, duration_sec: float = 5.0, samplerate: int = 48000):
    """Create a test audio file with sine wave."""
    t = np.linspace(0, duration_sec, int(samplerate * duration_sec))
    # 440 Hz sine wave (A4 note)
    audio = np.sin(2 * np.pi * 440 * t).astype('float32')
    # Make stereo
    audio = np.column_stack([audio, audio])
    path_obj = Path(path)
    try:
        path_obj.unlink(missing_ok=True)
    except Exception:
        pass
    sf.write(path_obj, audio, samplerate)
    logger.info(f"✅ Created test audio: {path_obj} ({duration_sec}s @ {samplerate}Hz)")


def test_ram_validation():
    """Test RAM validation with synthetic large tracks."""
    logger.info("\n" + "="*60)
    logger.info("TEST 1: RAM Validation")
    logger.info("="*60)

    # Create a temporary test file
    test_file = _default_temp_path("multilyrics_test_track.wav")
    create_test_audio(test_file, duration_sec=10.0, samplerate=48000)

    player = MultiTrackPlayer(samplerate=48000, blocksize=2048)

    try:
        # Load single track (should succeed)
        logger.info("\n📝 Loading 1 track (should succeed)...")
        player.load_tracks([test_file])
        logger.info("✅ PASS: Single track loaded successfully")

        # Get some stats
        import psutil
        mem = psutil.virtual_memory()
        logger.info(f"💾 System RAM: {mem.total / (1024**3):.2f} GB total, "
                   f"{mem.available / (1024**3):.2f} GB available")

        # Calculate track size
        if player._tracks:
            track_size_mb = player._tracks[0].nbytes / (1024**2)
            logger.info(f"📊 Single track size: {track_size_mb:.2f} MB")

    except MemoryError as e:
        logger.error(f"❌ FAIL: {e}")
    except Exception as e:
        logger.error(f"❌ FAIL: Unexpected error: {e}")
    finally:
        player.close()
        Path(test_file).unlink(missing_ok=True)


def test_latency_measurement(audio_file: str = None):
    """Test latency measurement during playback."""
    logger.info("\n" + "="*60)
    logger.info("TEST 2: Latency Measurement")
    logger.info("="*60)

    if audio_file and Path(audio_file).exists():
        test_file = audio_file
        cleanup = False
    else:
        # Create test audio
        test_file = _default_temp_path("multilyrics_test_latency.wav")
        create_test_audio(test_file, duration_sec=3.0, samplerate=48000)
        cleanup = True

    player = MultiTrackPlayer(samplerate=None, blocksize=2048, gc_policy='disable_during_playback')

    try:
        # Load track
        logger.info(f"\n📝 Loading audio: {test_file}")
        player.load_tracks([test_file])
        logger.info(f"✅ Loaded: {player.get_duration_seconds():.2f}s @ {player.samplerate}Hz")

        # Initial stats (should be empty)
        stats = player.get_latency_stats()
        logger.info(f"\n📊 Initial stats (before playback):")
        logger.info(f"   Total callbacks: {stats['total_callbacks']}")
        logger.info(f"   Mean: {stats['mean_ms']:.2f}ms | Max: {stats['max_ms']:.2f}ms | Budget: {stats['budget_ms']:.2f}ms")

        # Start playback
        logger.info(f"\n▶️  Starting playback for 2 seconds...")
        player.play()
        time.sleep(2.0)

        # Check stats during playback
        stats = player.get_latency_stats()
        logger.info(f"\n📊 Stats during playback:")
        logger.info(f"   Total callbacks: {stats['total_callbacks']}")
        logger.info(f"   Mean: {stats['mean_ms']:.2f}ms | Max: {stats['max_ms']:.2f}ms | Min: {stats['min_ms']:.2f}ms")
        logger.info(f"   Budget: {stats['budget_ms']:.2f}ms")
        logger.info(f"   Usage: {stats['usage_pct']:.1f}%")
        logger.info(f"   Xruns: {stats['xruns']}")

        # Evaluate performance
        if stats['usage_pct'] < 50:
            logger.info(f"✅ PASS: Healthy performance (usage < 50%)")
        elif stats['usage_pct'] < 80:
            logger.info(f"⚠️  PASS: Acceptable performance (usage < 80%)")
        else:
            logger.warning(f"❌ WARNING: High CPU usage (usage > 80%) - xruns likely")

        if stats['xruns'] == 0:
            logger.info(f"✅ PASS: No xruns detected")
        else:
            logger.warning(f"⚠️  WARNING: {stats['xruns']} xruns detected (callback exceeded 80% of budget)")

        # Stop playback
        player.stop()
        time.sleep(0.5)

        # Final stats
        final_stats = player.get_latency_stats()
        logger.info(f"\n📊 Final stats (after stop):")
        logger.info(f"   Total callbacks processed: {final_stats['total_callbacks']}")
        logger.info(f"   Average latency: {final_stats['mean_ms']:.2f}ms")
        logger.info(f"   Peak latency: {final_stats['max_ms']:.2f}ms")

    except Exception as e:
        logger.error(f"❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
    finally:
        player.close()
        if cleanup:
            Path(test_file).unlink(missing_ok=True)


def test_gc_policy():
    """Test GC policy functionality."""
    logger.info("\n" + "="*60)
    logger.info("TEST 3: GC Policy")
    logger.info("="*60)

    import gc

    # Test with GC disabled during playback
    logger.info("\n📝 Testing gc_policy='disable_during_playback'")
    initial_state = gc.isenabled()
    logger.info(f"   Initial GC state: {'enabled' if initial_state else 'disabled'}")

    player = MultiTrackPlayer(samplerate=48000, gc_policy='disable_during_playback')

    # Simulate playback start
    player._disable_gc_if_needed()
    gc_during_playback = gc.isenabled()
    logger.info(f"   GC during playback: {'enabled' if gc_during_playback else 'disabled'}")

    if not gc_during_playback:
        logger.info("✅ PASS: GC correctly disabled during playback")
    else:
        logger.error("❌ FAIL: GC should be disabled during playback")

    # Simulate playback stop
    player._restore_gc_if_needed()
    gc_after_stop = gc.isenabled()
    logger.info(f"   GC after stop: {'enabled' if gc_after_stop else 'disabled'}")

    if gc_after_stop == player._gc_was_enabled:
        logger.info("✅ PASS: GC correctly restored after stop")
    else:
        logger.error("❌ FAIL: GC should be restored to initial state")

    player.close()


def main():
    """Run all tests."""
    logger.info("🧪 MultiLyrics Audio Optimization Test Suite")
    logger.info("="*60)

    # Test 1: RAM Validation
    test_ram_validation()

    # Test 2: Latency Measurement
    audio_file = sys.argv[1] if len(sys.argv) > 1 else None
    test_latency_measurement(audio_file)

    # Test 3: GC Policy
    test_gc_policy()

    logger.info("\n" + "="*60)
    logger.info("✅ All tests completed")
    logger.info("="*60)


if __name__ == "__main__":
    main()
