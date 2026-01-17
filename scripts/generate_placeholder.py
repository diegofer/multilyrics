"""
Multi Lyrics - Placeholder Waveform Generator
Copyright (C) 2026 Diego Fernando

This script generates a decorative placeholder waveform for the timeline empty state.
Run once to generate assets/audio/placeholder.wav (~2.5MB uncompressed).

Usage:
    python scripts/generate_placeholder.py
"""

import numpy as np
import soundfile as sf
from pathlib import Path

def generate_placeholder_waveform():
    """Generate a realistic-looking synthetic waveform for empty timeline state."""

    # Audio parameters
    duration = 30.0  # 30 seconds (reduced for smaller file size ~2.5MB)
    sample_rate = 44100
    num_samples = int(duration * sample_rate)

    print(f"Generating {duration}s placeholder waveform...")

    # Consistent random seed for reproducible waveform
    np.random.seed(42)

    # Time array
    t = np.linspace(0, duration, num_samples)

    # Generate strong white noise as the main component (high frequency content)
    # This survives downsampling better and creates a dense visible waveform
    audio = np.random.randn(num_samples).astype(np.float32)

    # Create fade in/out envelope (crescendo at start, decrescendo at end)
    fade_duration = num_samples // 6  # 1/6 of total duration for each fade
    
    # Fade in (0 to 1 over first 1/6)
    fade_in = np.linspace(0, 1, fade_duration) ** 2  # Quadratic for smooth curve
    
    # Stable middle section with slight variations (1/6 to 5/6)
    middle_length = num_samples - 2 * fade_duration
    middle = np.ones(middle_length)
    # Add some dynamics in the middle (slight amplitude variations)
    middle *= 0.7 + 0.3 * np.abs(np.sin(2 * np.pi * 0.08 * np.linspace(0, duration * 4/6, middle_length)))
    
    # Fade out (1 to 0 over last 1/6)
    fade_out = np.linspace(1, 0, fade_duration) ** 2  # Quadratic for smooth curve
    
    # Combine all envelope sections
    envelope = np.concatenate([fade_in, middle, fade_out])
    
    # Apply envelope to create volume variations with smooth start/end
    audio *= envelope

    # Normalize to use most of the dynamic range for good visibility
    audio = audio.astype(np.float32)
    max_amp = np.max(np.abs(audio))
    if max_amp > 0:
        audio = audio / max_amp * 0.9  # Use 90% of full range

    print(f"  Generated audio range: {np.min(audio):.3f} to {np.max(audio):.3f}")
    print(f"  Audio mean: {np.mean(audio):.6f}, std: {np.std(audio):.3f}")

    return audio, sample_rate

def main():
    # Get project root (parent of scripts folder)
    project_root = Path(__file__).parent.parent

    # Try WAV first to rule out OGG encoding issues
    output_path = project_root / "assets" / "audio" / "placeholder.wav"

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Generate waveform
    audio, sample_rate = generate_placeholder_waveform()

    # Verify audio before saving
    print(f"\nPre-save verification:")
    print(f"  Audio shape: {audio.shape}")
    print(f"  Audio dtype: {audio.dtype}")
    print(f"  Non-zero samples: {np.count_nonzero(audio)} / {len(audio)}")
    print(f"  Max absolute value: {np.max(np.abs(audio)):.6f}")

    # Save to WAV (uncompressed) first to test
    print(f"\nSaving to WAV (uncompressed)...")
    sf.write(str(output_path), audio, sample_rate, format='WAV', subtype='PCM_16')

    # Verify saved file by reading it back
    print(f"\nVerifying saved file...")
    try:
        loaded_audio, loaded_sr = sf.read(str(output_path), dtype='float32')
        print(f"  Loaded shape: {loaded_audio.shape}")
        print(f"  Loaded range: {np.min(loaded_audio):.3f} to {np.max(loaded_audio):.3f}")
        print(f"  Non-zero samples after save: {np.count_nonzero(loaded_audio)} / {len(loaded_audio)}")

        if np.max(np.abs(loaded_audio)) < 0.01:
            print("  ⚠️ WARNING: Audio is nearly silent after saving!")
        else:
            print("  ✓ Audio preserved correctly")
    except Exception as e:
        print(f"  ⚠️ Could not verify saved file: {e}")

    file_size_kb = output_path.stat().st_size / 1024
    print(f"✓ Placeholder waveform saved to: {output_path}")
    print(f"✓ File size: {file_size_kb:.1f} KB")
    print(f"✓ Duration: {len(audio) / sample_rate:.1f}s @ {sample_rate}Hz")

if __name__ == "__main__":
    main()
