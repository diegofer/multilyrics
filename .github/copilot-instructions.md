# Multi Lyrics - AI Agent Instructions

## Project Overview
Multi Lyrics is a professional multitrack audio/video player with synchronized lyrics display. Built with PySide6 (Qt for Python), it features advanced audio analysis (beat detection, chord recognition), waveform visualization, and audio-video synchronization.

## Architecture

### Core Data Flow Pattern: Single Source of Truth
**Critical architectural principle**: `TimelineModel` is the **canonical source** of playhead time.

```
Audio Playback (sounddevice) 
  → SyncController.audio_callback() 
  → PlaybackManager._on_audio_time() 
  → TimelineModel.set_playhead_time()
  → Observers notified (TimelineView, ControlsWidget, etc.)
```

**Never** emit redundant position signals from `PlaybackManager`. UI components observe `TimelineModel` directly via `timeline.on_playhead_changed()`.

### Component Responsibilities

- **`core/timeline_model.py`**: UI-independent state container. Stores beats, downbeats, chords, lyrics model, and **canonical playhead time**. Uses observer pattern (not Qt signals).

- **`core/playback_manager.py`**: Coordinates players and propagates time from `SyncController` to `TimelineModel`. Manages play/pause/seek operations.

- **`core/sync.py`**: Audio-video synchronization using `AudioClock` for smooth time interpolation. Emits correction signals to `VideoLyrics`.

- **`audio/multitrack_player.py`**: Real-time audio mixer using `sounddevice`. Implements per-track gain, mute/solo, master gain with smoothing to avoid clicks.

- **`audio/timeline_view.py`**: Custom `QWidget` with track-based rendering architecture (waveform, beats, chords, lyrics, playhead). Three zoom modes: GENERAL, PLAYBACK, EDIT.

### Track Rendering System
Timeline painting uses a **ViewContext** pattern. Each track is a separate renderer:

```python
# In TimelineView.paintEvent()
ctx = ViewContext(start_sample, end_sample, total_samples, sample_rate, width, height, timeline_model)
self._waveform_track.paint(painter, ctx, samples, downsample_factor)
self._beat_track.paint(painter, ctx)
self._chord_track.paint(painter, ctx)
self._lyrics_track.paint(painter, ctx)
self._playhead_track.paint(painter, ctx)
```

Tracks are in `audio/tracks/`. Each implements `.paint(painter, ctx)` method.

## Critical Patterns

### Qt Designer Workflow
UI files live in `ui/`. Generated Python files (e.g., `shell.py`) **must not be edited manually** - they're regenerated from `.ui` files.

**To regenerate UI**: Use Designer (shortcut exists) or run `pyside6-uic ui/shell.ui -o ui/shell.py`

### Custom Widget Margins
When a custom `QWidget` with `paintEvent()` draws directly, **layout margins don't restrict painting area**. The widget receives its full allocated rectangle. To respect visual margins:
- Use `self.setContentsMargins(left, top, right, bottom)` in widget's `__init__`
- Or manually offset painting in `paintEvent()` with `painter.translate()`

### Style Management
**Never hardcode colors**. Use `StyleManager.get_color("color_name")` and `StyleManager.get_font()`. Theme is deep blue with neon accents. See `ui/style_manager.py` for complete palette.

### Worker Threads
Long-running tasks (audio extraction, beat detection) use Qt's worker pattern with `QThread`:
```python
worker = BeatsExtractorWorker(audio_path)
thread = QThread()
worker.moveToThread(thread)
thread.started.connect(worker.run)
worker.signals.finished.connect(thread.quit)
```

### Audio Analysis Pipeline
When loading audio:
1. `AudioExtractWorker`: Extract WAV from video (ffmpeg)
2. `BeatsExtractorWorker`: Detect beats/downbeats (madmom library)
3. `ChordExtractorWorker`: Recognize chords (madmom)
4. Populate `TimelineModel` with results
5. Reload lyrics from `library/multis/{song}/lyrics.lrc`

## Development Workflows

### Running
```powershell
python main.py
```

### Testing
```powershell
pytest tests/
# Or specific test:
pytest tests/test_timeline_model_playhead.py -v
```

### Environment Setup
Project uses `env/` virtual environment on Windows (PowerShell):
```powershell
.\env\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Dependencies
- **PySide6**: Qt GUI framework
- **sounddevice/soundfile**: Real-time audio playback
- **madmom**: Audio analysis (beats, chords) - installed from git
- **python-vlc**: Video playback
- **numpy/scipy**: Signal processing
- **ffmpeg-python**: Audio extraction (requires system ffmpeg)

## Project Conventions

### Coordinate Systems
- Audio: **samples** (int) internally, convert to/from seconds via `timeline.seconds_to_sample()` / `timeline.sample_to_seconds()`
- UI: **pixels** for painting, convert using samples-per-pixel calculation

### File Organization
- `library/multis/{song_name}/`: Contains `*.mp4` video, extracted `*.wav`, `beats.json`, `chords.json`, `lyrics.lrc`
- `assets/`: Fonts, images, icons
- `ui/`: Qt Designer files (`.ui`) and generated Python files
- `core/`: Business logic (models, managers, utilities)
- `audio/`: Audio-specific components (player, analysis, visualization)
- `tests/`: Pytest test suite

### Signal/Slot Naming
- Qt Signals: camelCase (e.g., `playingChanged`, `durationChanged`)
- Slots/callbacks: snake_case with `_on_` prefix (e.g., `_on_audio_time`, `_on_playhead_changed`)

### Observer Unsubscription Pattern
Observer callbacks return unsubscribe functions:
```python
unsub = timeline.on_playhead_changed(callback)
# Later:
unsub()  # Remove observer
```

Store unsubscribe functions in `closeEvent()` or destructor to prevent memory leaks.

## Common Pitfalls

1. **Don't emit position from PlaybackManager** - `TimelineModel` is the canonical source
2. **Don't hardcode colors** - always use `StyleManager`
3. **Don't edit generated UI files** (`ui/shell.py`) - regenerate from `.ui` instead
4. **Don't forget painter.save()/restore()** in track paint methods
5. **Clamp playhead time** to `[0, duration]` range when setting
6. **Use downsample_factor in GENERAL zoom mode** for waveform performance

## Key Files Reference

- [`main.py`](main.py): Application entry, wires components together
- [`core/timeline_model.py`](core/timeline_model.py): Central state, observer pattern
- [`core/playback_manager.py`](core/playback_manager.py): Playback coordination
- [`audio/timeline_view.py`](audio/timeline_view.py): Main visualization widget
- [`audio/multitrack_player.py`](audio/multitrack_player.py): Real-time audio mixer
- [`ui/style_manager.py`](ui/style_manager.py): Complete color/font palette
