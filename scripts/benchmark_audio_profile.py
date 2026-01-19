#!/usr/bin/env python3
"""
Multi Lyrics - Audio Profile Benchmark Script
Copyright (C) 2026 Diego Fernando

Benchmarks all available audio profiles by playing test audio and measuring performance.
Compares with auto-selected profile and recommends optimal configuration.

Usage:
    python scripts/benchmark_audio_profile.py
    python scripts/benchmark_audio_profile.py --test-file path/to/audio.wav
    python scripts/benchmark_audio_profile.py --duration 30
    python scripts/benchmark_audio_profile.py --profile-only balanced

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

try:
    import numpy as np
except ImportError:
    print("❌ Error: numpy not installed")
    print("💡 Install with: pip install numpy")
    sys.exit(1)

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("⚠️  Warning: psutil not installed - CPU monitoring limited")
    print("💡 Install with: pip install psutil")

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.audio_profiles import AudioProfile, AudioProfileManager
from core.engine import MultiTrackPlayer
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class BenchmarkResult:
    """Results from benchmarking a single profile."""

    profile_name: str
    blocksize: int
    gc_policy: str

    # Performance metrics
    avg_latency_ms: float
    peak_latency_ms: float
    xruns: int
    total_callbacks: int
    avg_cpu_percent: float
    peak_cpu_percent: float

    # Test parameters
    duration_seconds: float
    test_passed: bool
    error_message: Optional[str] = None

    def score(self) -> float:
        """
        Calculate overall score (0-100).
        Higher is better. Considers latency, xruns, and CPU usage.
        """
        if not self.test_passed:
            return 0.0

        # Latency score (inverse, lower is better)
        # 10ms = 100 points, 100ms = 10 points
        latency_score = max(0, 100 - self.avg_latency_ms)

        # Xrun score (0 xruns = 100, 10+ xruns = 0)
        xrun_score = max(0, 100 - (self.xruns * 10))

        # CPU score (20% = 100 points, 80% = 20 points)
        cpu_score = max(0, 100 - self.avg_cpu_percent)

        # Weighted average
        return (latency_score * 0.3 + xrun_score * 0.5 + cpu_score * 0.2)

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'profile_name': self.profile_name,
            'blocksize': self.blocksize,
            'gc_policy': self.gc_policy,
            'avg_latency_ms': round(self.avg_latency_ms, 2),
            'peak_latency_ms': round(self.peak_latency_ms, 2),
            'xruns': self.xruns,
            'total_callbacks': self.total_callbacks,
            'avg_cpu_percent': round(self.avg_cpu_percent, 1),
            'peak_cpu_percent': round(self.peak_cpu_percent, 1),
            'duration_seconds': round(self.duration_seconds, 1),
            'test_passed': self.test_passed,
            'score': round(self.score(), 1),
            'error_message': self.error_message
        }


class AudioBenchmark:
    """Benchmarks audio profiles with real playback."""

    def __init__(self, profile_manager: AudioProfileManager):
        """
        Initialize benchmark.

        Args:
            profile_manager: AudioProfileManager instance
        """
        self.profile_manager = profile_manager
        self.results: List[BenchmarkResult] = []
        self.auto_selected_profile: Optional[AudioProfile] = None

    def generate_test_audio(self, duration_seconds: float = 10.0, samplerate: int = 48000) -> np.ndarray:
        """
        Generate test audio (sine sweep + pink noise).

        Args:
            duration_seconds: Duration of test audio
            samplerate: Sample rate

        Returns:
            Audio array of shape (n_samples, 2) for stereo
        """
        n_samples = int(duration_seconds * samplerate)
        t = np.linspace(0, duration_seconds, n_samples, dtype=np.float32)

        # Sine sweep from 200 Hz to 2000 Hz
        freq_start = 200.0
        freq_end = 2000.0
        sweep = np.sin(2 * np.pi * (freq_start + (freq_end - freq_start) * t / duration_seconds) * t)

        # Pink noise (random with 1/f spectrum approximation)
        noise = np.random.randn(n_samples).astype(np.float32)

        # Mix 70% sweep + 30% noise
        audio_mono = 0.7 * sweep + 0.3 * noise * 0.1

        # Normalize to avoid clipping
        audio_mono = audio_mono / np.max(np.abs(audio_mono)) * 0.8

        # Convert to stereo
        audio_stereo = np.column_stack([audio_mono, audio_mono])

        return audio_stereo

    def benchmark_profile(
        self,
        profile: AudioProfile,
        test_audio: np.ndarray,
        samplerate: int = 48000,
        duration_seconds: Optional[float] = None
    ) -> BenchmarkResult:
        """
        Benchmark a single profile.

        Args:
            profile: AudioProfile to test
            test_audio: Test audio array (n_samples, 2)
            samplerate: Sample rate
            duration_seconds: Test duration (if None, uses full audio length)

        Returns:
            BenchmarkResult with performance metrics
        """
        logger.info(f"🧪 Benchmarking profile: {profile.name}")
        logger.info(f"   Blocksize: {profile.blocksize}, GC: {profile.gc_policy}")

        if duration_seconds is None:
            duration_seconds = len(test_audio) / samplerate

        # Initialize engine with profile settings
        try:
            engine = MultiTrackPlayer(
                samplerate=samplerate,
                blocksize=profile.blocksize,
                gc_policy=profile.gc_policy
            )
        except Exception as e:
            logger.error(f"❌ Failed to initialize engine: {e}")
            return BenchmarkResult(
                profile_name=profile.name,
                blocksize=profile.blocksize,
                gc_policy=profile.gc_policy,
                avg_latency_ms=0.0,
                peak_latency_ms=0.0,
                xruns=0,
                total_callbacks=0,
                avg_cpu_percent=0.0,
                peak_cpu_percent=0.0,
                duration_seconds=duration_seconds,
                test_passed=False,
                error_message=str(e)
            )

        # Load test audio as a single track
        try:
            engine.load_tracks([test_audio], names=['test'], samplerate=samplerate)
        except Exception as e:
            logger.error(f"❌ Failed to load test audio: {e}")
            return BenchmarkResult(
                profile_name=profile.name,
                blocksize=profile.blocksize,
                gc_policy=profile.gc_policy,
                avg_latency_ms=0.0,
                peak_latency_ms=0.0,
                xruns=0,
                total_callbacks=0,
                avg_cpu_percent=0.0,
                peak_cpu_percent=0.0,
                duration_seconds=duration_seconds,
                test_passed=False,
                error_message=str(e)
            )

        # Monitor CPU usage during playback
        cpu_samples = []
        start_time = time.time()

        # Start playback
        try:
            engine.play()
            logger.info(f"▶️  Playing for {duration_seconds:.1f} seconds...")

            # Sample CPU usage every 0.5 seconds
            while engine.is_playing() and (time.time() - start_time) < duration_seconds:
                if PSUTIL_AVAILABLE:
                    cpu_samples.append(psutil.cpu_percent(interval=0.1))
                else:
                    time.sleep(0.1)

            # Stop playback
            engine.stop()

        except Exception as e:
            logger.error(f"❌ Playback error: {e}")
            engine.stop()
            return BenchmarkResult(
                profile_name=profile.name,
                blocksize=profile.blocksize,
                gc_policy=profile.gc_policy,
                avg_latency_ms=0.0,
                peak_latency_ms=0.0,
                xruns=0,
                total_callbacks=0,
                avg_cpu_percent=0.0,
                peak_cpu_percent=0.0,
                duration_seconds=time.time() - start_time,
                test_passed=False,
                error_message=str(e)
            )

        # Collect latency stats
        stats = engine.get_latency_stats()

        # Calculate CPU stats
        avg_cpu = np.mean(cpu_samples) if cpu_samples else 0.0
        peak_cpu = np.max(cpu_samples) if cpu_samples else 0.0

        # Determine if test passed
        test_passed = (
            stats['xruns'] <= profile.xrun_tolerance and
            stats['mean_ms'] <= profile.target_latency_ms * 1.2  # Allow 20% margin
        )

        result = BenchmarkResult(
            profile_name=profile.name,
            blocksize=profile.blocksize,
            gc_policy=profile.gc_policy,
            avg_latency_ms=stats['mean_ms'],
            peak_latency_ms=stats['max_ms'],
            xruns=stats['xruns'],
            total_callbacks=stats['total_callbacks'],
            avg_cpu_percent=avg_cpu,
            peak_cpu_percent=peak_cpu,
            duration_seconds=time.time() - start_time,
            test_passed=test_passed
        )

        # Log results
        status = "✅ PASS" if test_passed else "❌ FAIL"
        logger.info(f"{status} {profile.name}:")
        logger.info(f"   Latency: {result.avg_latency_ms:.2f} ms avg, {result.peak_latency_ms:.2f} ms peak")
        logger.info(f"   Xruns: {result.xruns}")
        logger.info(f"   CPU: {result.avg_cpu_percent:.1f}% avg, {result.peak_cpu_percent:.1f}% peak")
        logger.info(f"   Score: {result.score():.1f}/100")

        return result

    def run_all_profiles(
        self,
        duration_seconds: float = 10.0,
        profile_filter: Optional[str] = None
    ) -> List[BenchmarkResult]:
        """
        Benchmark all available profiles.

        Args:
            duration_seconds: Test duration per profile
            profile_filter: If set, only test profiles containing this substring

        Returns:
            List of BenchmarkResult objects sorted by score
        """
        logger.info("=" * 70)
        logger.info("🎯 Starting Audio Profile Benchmark")
        logger.info("=" * 70)

        # Detect auto-selected profile
        self.auto_selected_profile = self.profile_manager.auto_select_profile()
        logger.info(f"🤖 Auto-selected profile: {self.auto_selected_profile.name}")
        logger.info("")

        # Generate test audio
        logger.info(f"🎵 Generating test audio ({duration_seconds:.1f} seconds)...")
        test_audio = self.generate_test_audio(duration_seconds)
        logger.info(f"✅ Test audio ready: {len(test_audio)} samples @ 48000 Hz")
        logger.info("")

        # Get all available profiles
        os_name = self.profile_manager._detected_os
        profiles_path = self.profile_manager.profiles_dir / os_name

        if not profiles_path.exists():
            logger.error(f"❌ Profiles directory not found: {profiles_path}")
            return []

        profile_files = sorted(profiles_path.glob('*.json'))
        if profile_filter:
            profile_files = [p for p in profile_files if profile_filter.lower() in p.stem.lower()]

        logger.info(f"📋 Found {len(profile_files)} profiles to test")
        logger.info("")

        # Benchmark each profile
        self.results = []
        for i, profile_file in enumerate(profile_files, 1):
            logger.info(f"[{i}/{len(profile_files)}] Testing profile: {profile_file.stem}")

            try:
                profile = AudioProfile.from_json(profile_file)
                result = self.benchmark_profile(profile, test_audio, duration_seconds=duration_seconds)
                self.results.append(result)
            except Exception as e:
                logger.error(f"❌ Failed to benchmark {profile_file.stem}: {e}")

            logger.info("")

        # Sort by score (descending)
        self.results.sort(key=lambda r: r.score(), reverse=True)

        return self.results

    def generate_report(self) -> str:
        """
        Generate a comprehensive benchmark report.

        Returns:
            Report as formatted string
        """
        if not self.results:
            return "⚠️  No benchmark results available"

        lines = []
        lines.append("=" * 70)
        lines.append("📊 BENCHMARK REPORT")
        lines.append("=" * 70)
        lines.append("")

        # Auto-selected profile info
        if self.auto_selected_profile:
            lines.append(f"🤖 Auto-Selected Profile: {self.auto_selected_profile.name}")
            lines.append(f"   Blocksize: {self.auto_selected_profile.blocksize}")
            lines.append(f"   GC Policy: {self.auto_selected_profile.gc_policy}")
            lines.append("")

        # Rankings
        lines.append("🏆 RANKINGS (by score):")
        lines.append("")
        lines.append(f"{'Rank':<6} {'Profile':<20} {'Score':<8} {'Latency':<12} {'Xruns':<8} {'CPU':<10} {'Status':<8}")
        lines.append("-" * 70)

        for i, result in enumerate(self.results, 1):
            status = "✅ PASS" if result.test_passed else "❌ FAIL"
            lines.append(
                f"#{i:<5} {result.profile_name:<20} "
                f"{result.score():<7.1f} "
                f"{result.avg_latency_ms:<11.2f} "
                f"{result.xruns:<8} "
                f"{result.avg_cpu_percent:<9.1f}% "
                f"{status:<8}"
            )

        lines.append("")
        lines.append("=" * 70)
        lines.append("💡 RECOMMENDATIONS:")
        lines.append("=" * 70)
        lines.append("")

        # Find best profile
        best_result = self.results[0] if self.results else None

        if best_result and best_result.test_passed:
            lines.append(f"✅ Recommended Profile: {best_result.profile_name}")
            lines.append(f"   Score: {best_result.score():.1f}/100")
            lines.append(f"   Latency: {best_result.avg_latency_ms:.2f} ms average")
            lines.append(f"   Xruns: {best_result.xruns}")
            lines.append(f"   CPU Usage: {best_result.avg_cpu_percent:.1f}%")
            lines.append("")

            # Compare with auto-selected
            if self.auto_selected_profile:
                auto_result = next((r for r in self.results if r.profile_name == self.auto_selected_profile.name), None)
                if auto_result and auto_result.profile_name != best_result.profile_name:
                    lines.append(f"⚠️  Note: Auto-selected '{auto_result.profile_name}' ranked #{self.results.index(auto_result) + 1}")
                    lines.append(f"   Consider manually selecting '{best_result.profile_name}' for better performance")
                elif auto_result:
                    lines.append(f"✅ Auto-selection is optimal! '{best_result.profile_name}' is the best choice.")
        else:
            lines.append("❌ No profiles passed the benchmark")
            lines.append("💡 Suggestions:")
            lines.append("   - Check audio device configuration")
            lines.append("   - Close other CPU-intensive applications")
            lines.append("   - Try a higher blocksize (e.g., 2048 or 4096)")

        lines.append("")
        lines.append("=" * 70)

        return "\n".join(lines)

    def export_json(self, output_path: Path):
        """
        Export benchmark results to JSON file.

        Args:
            output_path: Path to output JSON file
        """
        data = {
            'auto_selected_profile': self.auto_selected_profile.name if self.auto_selected_profile else None,
            'results': [r.to_dict() for r in self.results],
            'recommended_profile': self.results[0].profile_name if self.results and self.results[0].test_passed else None
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

        logger.info(f"📄 Results exported to: {output_path}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Benchmark audio profiles and recommend optimal configuration',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--duration',
        type=float,
        default=10.0,
        help='Test duration per profile in seconds (default: 10)'
    )

    parser.add_argument(
        '--profile-only',
        type=str,
        help='Only test profiles containing this substring (e.g., "balanced")'
    )

    parser.add_argument(
        '--export',
        type=Path,
        help='Export results to JSON file'
    )

    args = parser.parse_args()

    # Initialize profile manager
    profile_manager = AudioProfileManager()

    # Create benchmark
    benchmark = AudioBenchmark(profile_manager)

    # Run benchmarks
    results = benchmark.run_all_profiles(
        duration_seconds=args.duration,
        profile_filter=args.profile_only
    )

    if not results:
        logger.error("❌ No results to report")
        return 1

    # Print report
    print()
    print(benchmark.generate_report())

    # Export if requested
    if args.export:
        benchmark.export_json(args.export)

    return 0


if __name__ == '__main__':
    sys.exit(main())
