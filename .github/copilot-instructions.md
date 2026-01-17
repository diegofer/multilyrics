# Multi Lyrics - AI Agent Instructions

## Project Overview
Multi Lyrics is a professional multitrack audio/video player with synchronized lyrics display designed for churches and worship teams. Built with PySide6 (Qt for Python), it features advanced audio analysis (beat detection, chord recognition), waveform visualization, and audio-video synchronization.

**Mission**: Democratize professional multitrack usage through a free, lightweight, open-source tool (GPLv3).

## Architecture

## Rol: Actúa como un experto en audio de baja latencia con Python y sounddevice.

### Target Hardware & Platform Support

MultiLyrics is designed to support:
- **Windows 10/11** (x64, native WASAPI audio)
- **Linux** (ALSA/PulseAudio/PipeWire) including legacy systems (Mint XFCE, Ubuntu 20.04+)
- **macOS 10.13+** (CoreAudio)
- **Legacy Hardware**: Intel Core 2 Duo (2008–2009), 8GB RAM, SSD/HDD

#### Audio Specifications
- **Sample Rates**: Auto-detect 44.1 kHz or 48 kHz from first loaded track
- **Buffer Size**: 512 samples (fixed, ~10.67 ms @ 48kHz for stable playback)
- **Output**: Stereo (L/R channels)
- **Audio Format**: WAV (uncompressed, pre-extracted from MP4)

**Design Consequence**: Pre-load full WAV into RAM at song selection to avoid disk I/O during playback, critical for legacy hardware stability.

### Core Data Flow Pattern: Single Source of Truth
**Critical architectural principle**: `TimelineModel` is the **canonical source** of playhead time. The sounddevice callback is the only true clock—all timing derives from samples processed in the callback.

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

- **`ui/widgets/track_widget.py`**: Mixer strip widget using **Dependency Injection** pattern. Receives `AudioEngine` reference in constructor and connects directly to engine methods (eliminates intermediary lambdas in MainWindow).

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
- **Any NumPy allocation** (`np.zeros()`, `np.concatenate()`)

**✅ ALLOWED:**
- Vectorized operations on pre-loaded NumPy arrays
- Basic arithmetic (`+`, `-`, `*`, `/`, `np.clip()`)
- Reading atomic variables (`bool`, `int`, `float`)
- Array slicing (read-only): `audio_data[start:end]`

**Communication Patterns:**
- **UI → Callback**: Use `queue.Queue` (thread-safe, non-blocking)
- **Callback → UI**: Update atomic counters, emit signals from separate thread

### Memory Architecture: Pre-Load Strategy

All WAV files must be loaded into NumPy arrays **at song selection time**, before playback begins. This is critical for legacy hardware (2008–2009) that cannot handle real-time disk I/O during playback.

```python
# In SongModel or AudioEngine.load()
self.audio_data = {}  # {track_name: np.ndarray(dtype=float32)}

for stem_path in song_dir / "tracks":
    audio, sr = librosa.load(stem_path, sr=self.sample_rate, mono=False)
    self.audio_data[stem_name] = audio.astype(np.float32)  # Pre-load once
```

**Why pre-load?**
1. Legacy hardware (2008–2009) cannot handle real-time disk I/O + audio processing
2. Disk latency (even SSDs) introduces jitter in audio callback
3. 8GB RAM is sufficient for multi-song library (~1.5GB per 6 stems)
4. Pre-loading trades startup time (acceptable) for rock-solid playback

**UI Feedback During Pre-Load:**
- Show progress bar while loading (may take 2–3 sec on legacy disk)
- Lock playback button until 100% loaded
- Display "Loading: 45%" during pre-load phase

### Garbage Collection Management (GC)

**Critical Rule**: Python's garbage collector can cause unpredictable pauses (10-100ms) that introduce audio glitches on legacy hardware.

**Implementation Pattern:**
```python
# In AudioEngine.__init__()
self.gc_policy = 'disable_during_playback'  # Recommended for legacy hardware
self._gc_was_enabled = gc.isenabled()

# Disable GC before starting playback
def play(self):
    if self.gc_policy == 'disable_during_playback' and gc.isenabled():
        self._gc_was_enabled = True
        gc.disable()
    # ... start playback

# Restore GC after stopping/pausing
def stop(self):
    # ... stop playback
    if self.gc_policy == 'disable_during_playback' and self._gc_was_enabled:
        gc.enable()
```

**When to Use:**
- **Legacy hardware (2008-2012)**: Always disable GC during playback (`gc_policy='disable_during_playback'`)
- **Modern hardware (2015+)**: Can keep GC enabled (`gc_policy='normal'`) if CPU has headroom
- **Audio profiles**: Different profiles can set different GC policies based on detected hardware

**Why This Works:**
1. Playback sessions are short (3-5 minutes) - no memory leak risk
2. All audio data pre-loaded before playback starts
3. Callback does no allocation (only reads pre-loaded arrays)
4. GC restored during pauses and after stop (safe to collect then)

### Sample Rate Handling

**Critical Rule**: All tracks in a multi must have the same sample rate. No live resampling in audio callback (too CPU-intensive for legacy hardware).

**Auto-Detection Pattern:**
```python
# In AudioEngine.__init__()
self.samplerate = None  # Auto-detect from first track

# In load_tracks()
first_data, first_sr = sf.read(paths[0], dtype='float32', always_2d=True)

if self.samplerate is None:
    self.samplerate = first_sr  # Auto-detect
    logger.info(f"🎵 Auto-detected sample rate: {self.samplerate} Hz")
elif first_sr != self.samplerate:
    raise ValueError(f"Sample rate mismatch: expected {self.samplerate} Hz, got {first_sr} Hz")

# Validate all remaining tracks
for p in paths[1:]:
    data, sr = sf.read(p, dtype='float32', always_2d=True)
    if sr != self.samplerate:
        raise ValueError(f"Sample rate mismatch in {p}")
```

**Error Messages:**
- Always suggest ffmpeg command to fix mismatches: `ffmpeg -i 'input.wav' -ar 48000 output.wav`
- Check sample rate at load time, not during playback
- Support both 44.1 kHz and 48 kHz (most common rates)

## Critical Patterns

### Design Anti-Patterns (What NOT to Do)

#### ❌ Anti-Pattern 1: Secondary Timer for Playhead
```python
# WRONG: Qt timer independent of audio callback
QTimer().timeout.connect(self.update_playhead)  # ❌ Causes desync
```
**Why**: UI timer ≠ audio clock. Will desynchronize with actual playback.

**Correct**:
```python
# Audio callback updates atomic counter
# UI reads counter via observer callback (async)
unsub = timeline.on_playhead_changed(self.update_display)
```

#### ❌ Anti-Pattern 2: Heavy DSP in Callback
```python
def audio_callback(self, indata, frames, time_info, status):
    # WRONG: FFT, convolution, resampling in callback
    fft_result = np.fft.fft(indata)  # ❌ Too slow, will glitch
```
**Why**: Real-time constraint violated. Causes audio underruns on legacy hardware.

**Correct**: Pre-compute offline during loading, store results in SongModel.

#### ❌ Anti-Pattern 3: Direct UI Updates from Callback
```python
def audio_callback(self, indata, frames, time_info, status):
    self.waveform_widget.update_position(self.playback_frame)  # ❌ DEADLOCK
```
**Why**: Qt is not thread-safe from audio thread context.

**Correct**: Update atomic variable, emit signal from separate thread.

#### ❌ Anti-Pattern 4: Over-Engineering on Legacy Hardware
```python
# WRONG: Excessive abstraction on 2008 CPU
observer_manager = ObserverRegistry()
factory = AudioEngineFactory()
bridge = StrategyBridge()
# ❌ Memory overhead, CPU wasted on meta-logic
```
**Why**: Legacy hardware has limited CPU. Prefer simple, direct calls.

**Correct**: Direct method calls, minimal OOP overhead.

### Dependency Injection for Widgets
UI widgets that interact with business logic receive dependencies via constructor (not Qt signals to parent):

```python
# ✅ CORRECT: Dependency Injection (Individual Track)
track_widget = TrackWidget(
    track_name="Drums",
    track_index=0,
    engine=self.audio_player,  # Engine injected
    is_master=False
)
# Widget connects directly to engine methods internally

# ✅ CORRECT: Dependency Injection (Master Track with dual control)
master_track = TrackWidget(
    track_name="Master",
    track_index=0,
    engine=self.audio_player,      # For master gain
    is_master=True,
    timeline_view=self.timeline_view  # For preview volume
)
# Widget handles both audio gain and preview volume internally
# Includes get_logarithmic_volume conversion inside widget

# ❌ INCORRECT: Mediator pattern (deprecated)
track_widget = TrackWidget("Drums", False)
track_widget.volume_changed.connect(lambda g, i=0: self.set_gain(i, g))  # Lambda closure
```

**Benefits**: Reduces repetitive lambda code, improves testability (easy to mock engine), clearer widget responsibilities.

**Volume Control Pattern**: Widgets handle logarithmic conversion internally using `get_logarithmic_volume()` from `utils.helpers`. Master track coordinates both audio gain and waveform preview volume in a single `_on_master_volume_changed()` method.

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

This prevents slow startup times and protects audio/UI stability on legacy hardware.

### Multi-Platform Audio Implementation

#### Windows (PySide6 + WASAPI)
```python
# sounddevice will auto-select WASAPI automatically
device = sd.default.device  # Native Windows audio
```

#### Linux (ALSA/PulseAudio/PipeWire)
```python
# User may need to select device from dropdown
# Provide device selection in settings for flexibility
import sounddevice as sd
print(sd.query_devices())  # Let user choose if needed
```

#### macOS (CoreAudio)
```python
# CoreAudio is default via sounddevice
# Test on macOS 10.13+ for compatibility
```

#### Linux Legacy (XFCE on 2008 Hardware)
- Test on **Linux Mint 21 XFCE** (lightweight desktop)
- Verify with ALSA (minimal overhead)
- May need to build `libportaudio2` from source if unavailable
- Use `installer.py` to verify `libportaudio2` presence at startup

### Performance Budgets

**Callback Budget** (512 samples @ 48 kHz = 10.67 ms):
- Audio mixing: **< 5 ms** (headroom for system jitter)
- Gain application: **< 1 ms**
- Output copy: **< 2 ms**

**UI Update Budget** (30 FPS = 33 ms per frame):
- Waveform redraw: **< 10 ms** (use downsample factor in GENERAL zoom)
- Playhead position update: **< 5 ms** (async observer callback)

**Memory Budget** (8 GB system):
- OS + Python runtime: ~500 MB
- PySide6 GUI: ~200 MB
- Audio library (6 songs × 3 min @ 48kHz stereo): ~1.5 GB
- **Headroom**: ~5.8 GB (safe for typical usage)

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
