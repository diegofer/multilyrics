# Audio Format Support

Multi Lyrics is designed to work with standard audio formats used in professional multitrack productions while also supporting compressed formats for efficient storage.

## Supported Formats

### WAV (Waveform Audio File Format)

**Recommended for:** Master tracks, waveform timeline rendering

- **Pros:**
  - Uncompressed PCM audio (bit-perfect quality)
  - Fast to read/write (no decompression overhead)
  - Universal compatibility
  - Best performance for real-time waveform rendering

- **Cons:**
  - Large file sizes (~50MB per 5-minute stereo track)
  - Not ideal for projects with many stems

- **Use cases:**
  - `master.wav`: Required for timeline waveform visualization
  - Individual stems when disk space is not a concern
  - Original recordings before compression

### OGG Vorbis

**Recommended for:** Individual stems (drums, bass, vocals, guitar, etc.)

- **Pros:**
  - Excellent compression (~10:1 ratio without perceptible loss)
  - Open-source and royalty-free
  - Fully supported by `soundfile` library
  - Reduces multitrack project size dramatically (500MB → 50MB)

- **Cons:**
  - Slight CPU overhead for real-time decompression (negligible on modern hardware)
  - Not suitable for master track waveform rendering (performance)

- **Quality settings:**
  - Quality 3-5: Recommended for worship/live use (~5-8MB per 5-minute track)
  - Quality 6-8: Near-transparent quality (~8-12MB)
  - Quality 9-10: Maximum quality (~15-20MB)

- **Use cases:**
  - Individual stems from Demucs stem separation
  - Imported multitracks from external sources
  - Archiving projects with many stems

## Format Compatibility Matrix

| Format | Stems | Master | Timeline | Notes |
|--------|-------|--------|----------|-------|
| WAV    | ✅    | ✅     | ✅       | Best for master track |
| OGG    | ✅    | ⚠️     | ❌       | Not for timeline rendering |
| MP3    | ❌    | ❌     | ❌       | Not recommended (patent issues) |
| FLAC   | ⏳    | ⏳     | ❌       | Future support planned |

## Technical Implementation

Multi Lyrics uses `soundfile` library (based on libsndfile) for audio I/O:

```python
import soundfile as sf

# Reading audio (supports WAV, OGG, FLAC, etc.)
audio_data, sample_rate = sf.read('bass.ogg', dtype='float32')

# Writing audio
sf.write('output.ogg', audio_data, sample_rate, format='OGG', subtype='VORBIS')
```

### Real-time Mixing

The audio engine (`core/engine.py`) mixes all stem formats in real-time:

1. Stems are loaded once at track initialization
2. Audio data stored in memory as NumPy float32 arrays
3. Mixing happens in the audio callback (all formats treated equally)
4. No runtime format conversion needed

### Waveform Rendering

The timeline view (`ui/widgets/timeline_view.py`) requires WAV for the master track due to:

- Heavy downsampling for GENERAL zoom mode (1024:1 ratio)
- Frequent repaints during playback
- Envelope computation for waveform drawing

OGG decompression overhead would cause stuttering in the UI.

## Best Practices

### For New Projects
1. Keep `master.wav` as WAV (uncompressed)
2. Use OGG Vorbis for all individual stems
3. Store metadata in `meta.json` (no audio needed)

### Converting Existing Projects
```bash
# Convert stems to OGG (requires ffmpeg)
ffmpeg -i bass.wav -c:a libvorbis -q:a 5 bass.ogg
ffmpeg -i drums.wav -c:a libvorbis -q:a 5 drums.ogg
# Keep master.wav as-is
```

### Disk Space Comparison

Example 5-minute song with 8 stems + master:

| Format Mix | Total Size | Notes |
|-----------|------------|-------|
| All WAV | ~450 MB | Original quality, large |
| Stems OGG + Master WAV | ~100 MB | **Recommended** |
| All OGG | ~50 MB | Not supported (master must be WAV) |

## Future Enhancements

Planned format support:
- **FLAC**: Lossless compression for stems
- **M4A/AAC**: Apple ecosystem compatibility
- **Auto-conversion**: Convert OGG stems to WAV on import (optional)

## Troubleshooting

### "Could not open file" errors
- Ensure `libsndfile1` is installed (Ubuntu: `sudo apt install libsndfile1`)
- Verify file is not corrupted (`ffprobe filename.ogg`)

### OGG playback issues on Windows
- Check that `soundfile` version is >= 0.12.0
- Verify codec support: `python -c "import soundfile; print(soundfile.available_formats())"`

### Waveform not rendering
- Confirm `master.wav` exists and is in WAV format
- Check file permissions (must be readable)
- Verify sample rate matches other stems (44.1kHz or 48kHz)

## References

- libsndfile: http://www.mega-nerd.com/libsndfile/
- OGG Vorbis: https://xiph.org/vorbis/
- soundfile Python library: https://python-soundfile.readthedocs.io/
