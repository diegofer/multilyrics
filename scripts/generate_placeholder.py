"""
Multi Lyrics - Placeholder Waveform Generator
Copyright (C) 2026 Diego Fernando

This script generates a decorative placeholder waveform for the timeline empty state.
Run once to generate assets/audio/placeholder.wav (~450KB).

Usage:
    python scripts/generate_placeholder.py
"""

import numpy as np
import soundfile as sf
from pathlib import Path

def generate_placeholder_waveform():
    """Generate a realistic-looking synthetic waveform for empty timeline state."""

    # Audio parameters
    duration = 120.0  # 120 seconds
    sample_rate = 44100
    num_samples = int(duration * sample_rate)

    print(f"Generating {duration}s placeholder waveform...")

    # Consistent random seed for reproducible waveform
    np.random.seed(42)

    # Time array
    t = np.linspace(0, duration, num_samples)

    # Base noise (white noise for texture)
    base_noise = np.random.randn(num_samples).astype(np.float32) * 0.3

    # Add low frequency components (like bass/drums)
    low_freq = np.sin(2 * np.pi * 2 * t) * 0.5
    low_freq += np.sin(2 * np.pi * 3.5 * t) * 0.3

    # Add mid frequency components (like melody)
    mid_freq = np.sin(2 * np.pi * 8 * t) * 0.4
    mid_freq += np.sin(2 * np.pi * 12 * t) * 0.2

    # Combine all components
    audio = base_noise + low_freq + mid_freq

    # Add random amplitude variations (like dynamics in real music)
    amplitude_variation = 0.5 + 0.5 * np.abs(np.sin(2 * np.pi * 0.5 * t))
    audio *= amplitude_variation

    # Apply envelope for natural look (fade in/out)
    envelope = np.concatenate([
        np.linspace(0, 1, num_samples // 4),
        np.ones(num_samples // 2),
        np.linspace(1, 0, num_samples // 4)
    ])
    audio *= envelope

    # Normalize to make it visible (fuller waveform)
    audio = audio.astype(np.float32)
    max_amp = np.max(np.abs(audio))
    if max_amp > 0:
        audio = audio / max_amp * 0.8  # Scale to 80% of full range

    return audio, sample_rate

def main():
    # Get project root (parent of scripts folder)
    project_root = Path(__file__).parent.parent
    output_path = project_root / "assets" / "audio" / "placeholder.wav"

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Generate waveform
    audio, sample_rate = generate_placeholder_waveform()

    # Save to file
    sf.write(str(output_path), audio, sample_rate)

    file_size_kb = output_path.stat().st_size / 1024
    print(f"✓ Placeholder waveform saved to: {output_path}")
    print(f"✓ File size: {file_size_kb:.1f} KB")
    print(f"✓ Duration: {len(audio) / sample_rate:.1f}s @ {sample_rate}Hz")

if __name__ == "__main__":
    main()
