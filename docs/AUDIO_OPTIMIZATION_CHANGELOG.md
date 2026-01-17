# Audio Optimization Changelog

## Tarea #1: Garbage Collection Management (Implemented)

**Date**: 2024
**Status**: ✅ Implemented

### Problem
Python's garbage collector (GC) can cause unpredictable pauses of 10-100ms during execution, which introduces audio glitches (xruns, dropouts, clicks) on legacy hardware (2008-2012 era CPUs like Intel Core 2 Duo, Sandy Bridge).

### Solution
Implemented GC management policy that disables garbage collection during audio playback and restores it when playback stops or pauses.

### Implementation Details

**Changes to `core/engine.py`:**

1. **Added `gc` import** at module level
2. **Modified constructor** to accept `gc_policy` parameter:
   ```python
   def __init__(self, samplerate: Optional[int] = None, blocksize: int = 2048, 
                dtype: str = 'float32', gc_policy: str = 'disable_during_playback'):
   ```
   - `gc_policy='disable_during_playback'`: Default, recommended for legacy hardware
   - `gc_policy='normal'`: Keep GC enabled for modern systems with CPU headroom

3. **Added helper methods**:
   - `_disable_gc_if_needed()`: Disables GC when playback starts
   - `_restore_gc_if_needed()`: Re-enables GC when playback stops/pauses

4. **Integrated GC calls into playback control**:
   - `play()`: Disables GC before starting playback
   - `stop()`: Restores GC after stopping
   - `pause()`: Restores GC when paused (safe to collect during pause)
   - `resume()`: Disables GC when resuming from pause
   - `_on_stream_finished()`: Restores GC when stream completes naturally
   - `close()`: Ensures GC is restored when engine is closed

**Changes to `main.py`:**
```python
self.audio_player = MultiTrackPlayer(
    samplerate=None, 
    blocksize=2048, 
    gc_policy='disable_during_playback'
)
```

### Why This Works
1. **Playback sessions are short** (3-5 minutes) - no memory leak risk during this time
2. **All audio data pre-loaded** before playback starts (no allocation during callback)
3. **Callback does no allocation** - only reads pre-loaded NumPy arrays
4. **GC restored safely** during pauses and after stop (when it's safe to collect)

### Future Work
- Audio profile system will automatically select GC policy based on detected hardware
- Modern CPUs (2015+) can use `gc_policy='normal'` if benchmarks show sufficient headroom

---

## Tarea #3: Auto-Detect Sample Rate (Implemented)

**Date**: 2024
**Status**: ✅ Implemented

### Problem
1. Users had to manually configure sample rate (44.1 kHz vs 48 kHz)
2. Sample rate mismatches between tracks caused immediate errors
3. Error messages didn't provide actionable solutions

### Solution
Implemented auto-detection of sample rate from the first loaded track, with validation that all tracks match. No live resampling (too CPU-intensive for legacy hardware).

### Implementation Details

**Changes to `core/engine.py`:**

1. **Modified constructor** to accept `Optional[int]` for samplerate:
   ```python
   def __init__(self, samplerate: Optional[int] = None, ...):
       self.samplerate = samplerate  # None until first track loaded
   ```

2. **Refactored `load_tracks()` method**:
   - Loads first track separately to detect sample rate
   - If `samplerate` is `None`, auto-detects from first track
   - Validates all remaining tracks have matching sample rate
   - Provides helpful error messages with ffmpeg commands to fix mismatches

   ```python
   first_data, first_sr = sf.read(paths[0], dtype='float32', always_2d=True)
   
   if self.samplerate is None:
       self.samplerate = first_sr
       logger.info(f"🎵 Auto-detected sample rate: {self.samplerate} Hz")
   elif first_sr != self.samplerate:
       raise ValueError(
           f"❌ Sample rate mismatch: expected {self.samplerate} Hz, "
           f"got {first_sr} Hz from {paths[0]}\n"
           f"💡 Fix with: ffmpeg -i '{paths[0]}' -ar {self.samplerate} output.wav"
       )
   ```

3. **Enhanced error messages**:
   - Clear identification of mismatched file
   - Exact ffmpeg command to fix the issue
   - Emoji indicators for visual clarity

**Changes to `main.py`:**
```python
self.audio_player = MultiTrackPlayer(samplerate=None, ...)  # Auto-detect
```

### Benefits
1. **Zero configuration**: Users don't need to know their audio file sample rates
2. **Clear error messages**: If mismatches occur, users get exact command to fix it
3. **Multi-platform support**: Works with both 44.1 kHz (CD quality) and 48 kHz (video standard)
4. **No live resampling**: Maintains audio engine simplicity and CPU efficiency
5. **Offline validation**: All sample rate checks happen at load time, not during playback

### Design Decisions
- **No live resampling**: Too CPU-intensive for legacy hardware (2008-2012 CPUs)
- **Offline validation**: All tracks validated at `load_tracks()` time
- **Explicit errors**: Better to fail fast at load time with clear fix than to degrade playback
- **Support both rates**: 44.1 kHz (CD/music) and 48 kHz (video/broadcast) are most common

---

## Documentation Updates

**Updated `.github/copilot-instructions.md`:**
- Added "Garbage Collection Management (GC)" section with implementation pattern
- Added "Sample Rate Handling" section with auto-detection pattern
- Documented when to use each GC policy (legacy vs modern hardware)
- Explained why pre-load + GC disable works for short playback sessions

---

## Testing

**Manual Testing:**
- ✅ Application starts successfully (`python3 main.py`)
- ✅ Syntax checks pass for `core/engine.py` and `main.py`
- ✅ No runtime errors during initialization

**Remaining Test Coverage:**
- Test GC state transitions (enable → disable → restore)
- Test sample rate auto-detection with 44.1 kHz files
- Test sample rate auto-detection with 48 kHz files
- Test sample rate mismatch error handling
- Test error message format and ffmpeg command generation

---

## Next Steps (High Priority)

### Tarea #2: RAM Validation
- Add `psutil` to `requirements.txt`
- Calculate total bytes needed for all tracks in `load_tracks()`
- Check `psutil.virtual_memory().available`
- Raise `MemoryError` if insufficient RAM (use <70% of available)
- Log pre-load size in GB for user awareness

### Tarea #4: Internal Latency Measurement
- Add `time.perf_counter()` at start/end of `_callback()`
- Track last 100 callback durations in circular buffer
- Add `get_latency_stats()` method returning:
  - `mean_ms`: Average callback duration
  - `max_ms`: Peak callback duration
  - `xruns`: Count of callbacks exceeding budget
  - `budget_ms`: Time budget for blocksize
  - `usage_pct`: Percentage of budget used
- Log warning if callback exceeds 80% of time budget

### Tarea #5: Audio Profile System
- Create `config/profiles/linux/legacy.json`, `modern.json`
- Create `config/profiles/windows/legacy.json`, `modern.json`
- Create `config/profiles/macos/legacy.json`, `modern.json`
- Create `core/audio_profiles.py` with `AudioProfile` dataclass
- Add OS/CPU detection logic (year, cores, architecture)
- Load appropriate profile at startup based on hardware
- Allow manual override in Settings GUI

---

## References

- Blueprint: `.github/PROJECT_BLUEPRINT.md` sections 4.1, 8.5, 17
- Copilot Instructions: `.github/copilot-instructions.md` sections on GC, Sample Rate, Anti-Patterns
- Audio Engineering Best Practices: Pre-load strategy, no allocation in callback, GC disable during playback
