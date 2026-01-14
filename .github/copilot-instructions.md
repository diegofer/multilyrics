# Multi Lyrics - AI Agent Instructions

## Project Overview
Multi Lyrics is a professional multitrack audio/video player with synchronized lyrics display designed for churches and worship teams. Built with PySide6 (Qt for Python), it features advanced audio analysis (beat detection, chord recognition), waveform visualization, and audio-video synchronization.

**Mission**: Democratize professional multitrack usage through a free, lightweight, open-source tool (GPLv3).

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

- **`models/timeline_model.py`**: UI-independent state container. Stores beats, downbeats, chords, lyrics model, and **canonical playhead time**. Uses observer pattern (not Qt signals).

- **`core/playback_manager.py`**: Coordinates players and propagates time from `SyncController` to `TimelineModel`. Manages play/pause/seek operations.

- **`core/sync.py`**: Audio-video synchronization using `AudioClock` for smooth time interpolation. Emits correction signals to `VideoLyrics`.

- **`core/engine.py`** (formerly multitrack_player): Real-time audio mixer using `sounddevice`. Implements per-track gain, mute/solo, master gain with smoothing to avoid clicks.

- **`ui/widgets/timeline_view.py`**: Custom `QWidget` with track-based rendering architecture (waveform, beats, chords, lyrics, playhead). Three zoom modes: GENERAL, PLAYBACK, EDIT.

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

Tracks are in `ui/widgets/tracks/`. Each implements `.paint(painter, ctx)` method.

## Audio Engine Callback Rules (CRITICAL)

The audio callback runs in a high-priority thread. **NEVER** do these inside the callback:

**❌ PROHIBITED:**
- Locks, mutexes, semaphores (`threading.Lock`)
- File I/O (`open()`, `read()`, `write()`)
- Prints or logging (`print()`, `logging.info()`)
- Qt Signal emissions (`Signal.emit()` can cause deadlocks)
- Memory allocation (`list.append()`, `dict[key] = value`)

**✅ ALLOWED:**
- Operations on pre-loaded NumPy arrays
- Basic arithmetic (`+`, `-`, `*`, `/`, `np.clip()`)
- Reading atomic variables (`bool`, `int`, `float`)

**Communication Patterns:**
- **UI → Callback**: Use `queue.Queue` (thread-safe, non-blocking)
- **Callback → UI**: Update atomic counters, emit signals from separate thread

## Critical Patterns

### Qt Designer Workflow
UI files live in `ui/`. Generated Python files (e.g., `main_window.py`) **must not be edited manually** - they're regenerated from `.ui` files.

**To regenerate UI**: Use Designer (shortcut exists) or run `pyside6-uic ui/main_window.ui -o ui/main_window.py`

### Custom Widget Margins
When a custom `QWidget` with `paintEvent()` draws directly, **layout margins don't restrict painting area**. The widget receives its full allocated rectangle. To respect visual margins:
- Use `self.setContentsMargins(left, top, right, bottom)` in widget's `__init__`
- Or manually offset painting in `paintEvent()` with `painter.translate()`

### Style Management
**Never hardcode colors**. Use `StyleManager.get_color("color_name")` and `StyleManager.get_font()`. See `ui/styles.py` for complete palette.

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
1. `AudioExtractWorker`: Extract WAV from video (ffmpeg) - `core/extract.py`
2. `BeatsExtractorWorker`: Detect beats/downbeats (madmom library) - `core/beats.py`
3. `ChordExtractorWorker`: Recognize chords (madmom) - `core/chords.py`
4. Populate `TimelineModel` with results
5. Reload lyrics from `library/multis/{song}/lyrics.lrc`

### Lazy Loading and Heavy Libraries
**Critical Rule**: Heavy libraries (`torch`, `demucs`, `madmom`) must **never** be imported at module level.

**❌ PROHIBITED:**
```python
# At top of file
import torch
import demucs
```

**✅ CORRECT:**
```python
def separate_stems(audio_path):
    import torch  # Local import
    import demucs
    # ... processing
```

This prevents slow startup times and protects audio/UI stability.

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

### File Structure
```
multilyrics/
├── main.py
├── CREDITS.md             # Third-party licenses and attributions
├── README.md
├── requirements.txt
│
├── library/               # Song storage
│   └── multis/
│       └── {song_name}/
│           ├── meta.json        # BPM, key, compass, duration
│           ├── master.wav       # Audio for waveform
│           ├── video.mp4        # Optional video lyrics
│           ├── lyrics.lrc       # Synchronized lyrics (UTF-8)
│           ├── beats.json       # Beat timestamps
│           ├── chords.json      # Chord progressions
│           └── tracks/          # Individual stems
│
├── core/                  # Business logic and engine
│   ├── engine.py                # Audio engine (sounddevice)
│   ├── beats.py                 # Beat detection processor
│   ├── chords.py                # Chord recognition processor
│   ├── extract.py               # Audio extraction from video
│   ├── constants.py             # SCREAMING_SNAKE_CASE constants
│   ├── playback_manager.py      # Playback coordination
│   ├── sync.py                  # Audio-video sync
│   ├── extraction_orchestrator.py
│   ├── clock.py
│   └── workers.py
│
├── models/                # Data models
│   ├── timeline_model.py        # Central state (Single Source of Truth)
│   ├── lyrics_model.py          # LyricsModel, LyricLine
│   └── meta.py                  # Song metadata (MetaJson)
│
├── ui/                    # Interface
│   ├── main_window.py           # Generated from .ui (DO NOT EDIT)
│   ├── main_window.ui           # Qt Designer file
│   ├── styles.py                # StyleManager (Deep Tech Blue theme)
│   └── widgets/
│       ├── timeline_view.py     # Main visualization
│       ├── tracks/              # Track renderers
│       │   ├── beat_track.py
│       │   ├── chord_track.py
│       │   ├── lyrics_track.py
│       │   ├── playhead_track.py
│       │   └── waveform_track.py
│       └── (dialogs, controls, etc.)
│
├── utils/                 # Utilities
│   ├── logger.py                # Centralized logging
│   ├── error_handler.py         # safe_operation decorator
│   ├── helpers.py               # Common utilities
│   └── lyrics_loader.py         # LRC parser/downloader
│
├── video/                 # Video playback
│   └── video.py
│
├── docs/                  # Documentation
│   ├── architecture.md
│   └── development.md
│
├── tests/                 # Test suite
└── assets/                # Fonts, images, icons
```

### Coordinate Systems
- Audio: **samples** (int) internally, convert to/from seconds via `timeline.seconds_to_sample()` / `timeline.sample_to_seconds()`
- UI: **pixels** for painting, convert using samples-per-pixel calculation

### File Organization
- `library/multis/{song_name}/`: Contains `*.mp4` video, extracted `*.wav`, `beats.json`, `chords.json`, `lyrics.lrc`
- `assets/`: Fonts, images, icons
- `ui/`: Qt Designer files (`.ui`) and generated Python files
- `core/`: Business logic (engine, processors, managers)
- `models/`: Data models (timeline, lyrics, metadata)
- `utils/`: Cross-cutting utilities (logging, error handling, helpers)
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
3. **Don't edit generated UI files** (`ui/main_window.py`) - regenerate from `.ui` instead
4. **Don't forget painter.save()/restore()** in track paint methods
5. **Clamp playhead time** to `[0, duration]` range when setting
6. **Use downsample_factor in GENERAL zoom mode** for waveform performance
7. **Never import heavy libraries at module level** - use local imports for torch, demucs, madmom

## Key Files Reference

- [`main.py`](main.py): Application entry, wires components together
- [`models/timeline_model.py`](models/timeline_model.py): Central state, observer pattern
- [`core/playback_manager.py`](core/playback_manager.py): Playback coordination
- [`ui/widgets/timeline_view.py`](ui/widgets/timeline_view.py): Main visualization widget
- [`core/engine.py`](core/engine.py): Real-time audio mixer
- [`ui/styles.py`](ui/styles.py): Complete color/font palette
- [`CREDITS.md`](CREDITS.md): Third-party licenses and attributions

## Blueprint Implementation Status

See [PROJECT_BLUEPRINT.md](PROJECT_BLUEPRINT.md) for the complete architectural vision. Current implementation status:

### ✅ Implemented
- **Project Structure**: Clean separation of concerns (core/, models/, ui/, utils/)
- **Audio Engine**: Real-time mixer with per-track gain, mute/solo, master gain smoothing
- **Timeline Visualization**: Track-based rendering with three zoom modes
- **Audio Analysis**: Beat detection, chord recognition, audio extraction (madmom + ffmpeg)
- **Lazy Loading**: Heavy libraries loaded on-demand to protect startup time
- **Callback Safety**: Audio callback follows strict rules (no I/O, no locks, no Qt signals)
- **Single Source of Truth**: TimelineModel as canonical playhead time source
- **Observer Pattern**: Non-Qt components use callbacks for loose coupling
- **Style System**: Centralized StyleManager
- **Credits System**: CREDITS.md with proper academic attributions
- **Documentation**: Architecture and development guides in docs/
- **Cross-platform**: LF line endings configured for Windows/Linux development

### 🔄 In Progress
- **Data Models**: Using MetaJson for metadata, planned refactor to Song/Track DTOs
- **Lyrics Sync**: LRC parser implemented, lyrics as "slaves" to audio time planned
- **Worker Threads**: Qt worker pattern used for long-running tasks

### ⏳ Planned (from Blueprint)
- **Split Mode Routing**: L/R channel separation for stage monitoring (instrumental + click/cues)
- **Cues System**: Auto-trigger voice cues 4 beats before sections
- **Pitch Shifting**: Offline processing with pyrubberband
- **Remote Control**: FastAPI + WebSockets for mobile control
- **Dual Display**: Projector output with frameless window
- **Config Manager**: Singleton for settings.json (audio device, paths, volumes)
- **Beat Grid**: Visual downbeat markers for metronome sync
- **DTO Refactor**: Immutable @dataclass models (Song, Track, LyricLine)
- **Testing Strategy**: Dependency injection for better mocking
