#!/usr/bin/env python3
"""
Multi Lyrics - Multi Validation Script
Copyright (C) 2026 Diego Fernando

Validates that all tracks in a multi have matching sample rates.
Detects problems before loading in the application.

Usage:
    python scripts/validate_multi.py library/multis/Song\ Name/
    python scripts/validate_multi.py --all
    python scripts/validate_multi.py --all --fix

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import soundfile as sf
except ImportError:
    print("❌ Error: soundfile not installed")
    print("💡 Install with: pip install soundfile")
    sys.exit(1)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logger import get_logger

logger = get_logger(__name__)


class MultiValidator:
    """Validates audio tracks in a multi directory."""

    def __init__(self, multi_path: Path):
        """
        Initialize validator for a multi directory.

        Args:
            multi_path: Path to multi directory (e.g., library/multis/Song Name/)
        """
        self.multi_path = Path(multi_path)
        self.tracks_dir = self.multi_path / "tracks"
        self.issues: List[str] = []
        self.warnings: List[str] = []

    def validate(self) -> bool:
        """
        Validate all tracks in the multi.

        Returns:
            True if validation passed, False otherwise
        """
        if not self.multi_path.exists():
            logger.error(f"❌ Multi directory not found: {self.multi_path}")
            return False

        if not self.tracks_dir.exists():
            logger.error(f"❌ Tracks directory not found: {self.tracks_dir}")
            self.issues.append(f"Missing tracks/ directory in {self.multi_path.name}")
            return False

        # Find all WAV files
        wav_files = sorted(self.tracks_dir.glob("*.wav"))

        if not wav_files:
            logger.error(f"❌ No WAV files found in {self.tracks_dir}")
            self.issues.append(f"No .wav files in tracks/ directory")
            return False

        logger.info(f"\n{'='*60}")
        logger.info(f"🔍 Validating Multi: {self.multi_path.name}")
        logger.info(f"{'='*60}")
        logger.info(f"📁 Location: {self.multi_path}")
        logger.info(f"🎵 Tracks found: {len(wav_files)}")

        # Read metadata for all tracks
        tracks_info = []
        for wav_file in wav_files:
            try:
                info = sf.info(wav_file)
                tracks_info.append({
                    'path': wav_file,
                    'name': wav_file.name,
                    'samplerate': info.samplerate,
                    'channels': info.channels,
                    'frames': info.frames,
                    'duration': info.duration,
                    'format': info.format,
                    'subtype': info.subtype
                })
            except Exception as e:
                logger.error(f"❌ Failed to read {wav_file.name}: {e}")
                self.issues.append(f"Cannot read file: {wav_file.name}")

        if not tracks_info:
            logger.error(f"❌ No valid WAV files found")
            return False

        # Validate sample rates
        sample_rates = [t['samplerate'] for t in tracks_info]
        unique_rates = set(sample_rates)

        logger.info(f"\n📊 Track Details:")
        logger.info(f"{'─'*60}")

        for i, track in enumerate(tracks_info, 1):
            status = "✅" if len(unique_rates) == 1 else ("❌" if track['samplerate'] != sample_rates[0] else "✅")
            logger.info(
                f"{status} {i}. {track['name']:<25} | "
                f"{track['samplerate']:>6} Hz | "
                f"{track['channels']} ch | "
                f"{track['duration']:>6.2f}s | "
                f"{track['format']}"
            )

        # Check for sample rate mismatches
        if len(unique_rates) > 1:
            logger.error(f"\n❌ VALIDATION FAILED: Sample rate mismatch detected!")
            logger.error(f"   Found {len(unique_rates)} different sample rates: {sorted(unique_rates)}")

            # Group tracks by sample rate
            rate_groups = {}
            for track in tracks_info:
                rate = track['samplerate']
                if rate not in rate_groups:
                    rate_groups[rate] = []
                rate_groups[rate].append(track['name'])

            logger.info(f"\n🔧 Grouping by sample rate:")
            for rate, tracks in sorted(rate_groups.items()):
                logger.info(f"   {rate} Hz: {len(tracks)} tracks")
                for track_name in tracks:
                    logger.info(f"      - {track_name}")

            # Suggest fix commands
            target_rate = max(unique_rates)  # Use highest rate as target
            logger.info(f"\n💡 Fix commands (targeting {target_rate} Hz):")
            logger.info(f"{'─'*60}")

            for track in tracks_info:
                if track['samplerate'] != target_rate:
                    input_file = track['path']
                    output_file = track['path'].parent / f"{track['path'].stem}_resampled.wav"
                    logger.info(f"ffmpeg -i '{input_file}' -ar {target_rate} '{output_file}'")

            self.issues.append(f"Sample rate mismatch: {sorted(unique_rates)}")
            return False

        # Check for duration mismatches (warning only)
        durations = [t['duration'] for t in tracks_info]
        max_duration = max(durations)
        min_duration = min(durations)
        duration_diff = max_duration - min_duration

        if duration_diff > 0.5:  # More than 500ms difference
            logger.warning(f"\n⚠️  WARNING: Duration mismatch detected!")
            logger.warning(f"   Max duration: {max_duration:.2f}s")
            logger.warning(f"   Min duration: {min_duration:.2f}s")
            logger.warning(f"   Difference: {duration_diff:.2f}s")
            self.warnings.append(f"Duration difference: {duration_diff:.2f}s")

        # Check for channel mismatches (warning only)
        channels = [t['channels'] for t in tracks_info]
        unique_channels = set(channels)
        if len(unique_channels) > 1:
            logger.warning(f"\n⚠️  WARNING: Mixed channel counts detected!")
            logger.warning(f"   Channels found: {sorted(unique_channels)}")
            self.warnings.append(f"Mixed channels: {sorted(unique_channels)}")

        # Success summary
        logger.info(f"\n✅ VALIDATION PASSED!")
        logger.info(f"   Sample rate: {sample_rates[0]} Hz (all tracks match)")
        logger.info(f"   Total tracks: {len(tracks_info)}")
        logger.info(f"   Duration range: {min_duration:.2f}s - {max_duration:.2f}s")

        if self.warnings:
            logger.info(f"\n⚠️  {len(self.warnings)} warning(s):")
            for warning in self.warnings:
                logger.info(f"   - {warning}")

        return True


def validate_all_multis(library_path: Path) -> Tuple[int, int, int]:
    """
    Validate all multis in the library.

    Args:
        library_path: Path to library/multis/ directory

    Returns:
        Tuple of (total, passed, failed)
    """
    multis_dir = library_path / "multis"

    if not multis_dir.exists():
        logger.error(f"❌ Library directory not found: {multis_dir}")
        return 0, 0, 0

    # Find all multi directories (containing tracks/ subdirectory)
    multi_dirs = [d for d in multis_dir.iterdir() if d.is_dir() and (d / "tracks").exists()]

    if not multi_dirs:
        logger.error(f"❌ No multis found in {multis_dir}")
        return 0, 0, 0

    logger.info(f"\n{'='*60}")
    logger.info(f"🔍 Validating All Multis in Library")
    logger.info(f"{'='*60}")
    logger.info(f"📁 Library: {multis_dir}")
    logger.info(f"🎵 Found {len(multi_dirs)} multis")

    passed = 0
    failed = 0

    for multi_dir in sorted(multi_dirs):
        validator = MultiValidator(multi_dir)
        if validator.validate():
            passed += 1
        else:
            failed += 1

    # Final summary
    logger.info(f"\n{'='*60}")
    logger.info(f"📊 Validation Summary")
    logger.info(f"{'='*60}")
    logger.info(f"✅ Passed: {passed}/{len(multi_dirs)}")
    logger.info(f"❌ Failed: {failed}/{len(multi_dirs)}")

    if failed == 0:
        logger.info(f"\n🎉 All multis validated successfully!")
    else:
        logger.error(f"\n⚠️  {failed} multi(s) need attention")

    return len(multi_dirs), passed, failed


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate sample rates in MultiLyrics multi directories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate single multi
  python scripts/validate_multi.py library/multis/Awesome\ God/

  # Validate all multis
  python scripts/validate_multi.py --all

  # Validate from project root
  python scripts/validate_multi.py library/multis/Song\ Name/
        """
    )

    parser.add_argument(
        'multi_path',
        nargs='?',
        type=str,
        help='Path to multi directory (e.g., library/multis/Song Name/)'
    )

    parser.add_argument(
        '--all',
        action='store_true',
        help='Validate all multis in library/multis/'
    )

    parser.add_argument(
        '--library',
        type=str,
        default='library',
        help='Path to library directory (default: library/)'
    )

    args = parser.parse_args()

    # Determine project root
    project_root = Path(__file__).parent.parent

    if args.all:
        # Validate all multis
        library_path = project_root / args.library
        total, passed, failed = validate_all_multis(library_path)
        sys.exit(0 if failed == 0 else 1)

    elif args.multi_path:
        # Validate single multi
        multi_path = Path(args.multi_path)

        # If relative path, resolve from project root
        if not multi_path.is_absolute():
            multi_path = project_root / multi_path

        validator = MultiValidator(multi_path)
        success = validator.validate()

        sys.exit(0 if success else 1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
