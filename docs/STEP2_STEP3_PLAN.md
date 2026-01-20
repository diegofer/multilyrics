# 🗺️ STEP 2 & 3: Optional Monitoring + Ring Buffer (Implementation Plan)

**Status:** READY TO START  
**Estimated Time:** 2-3 hours total  
**Dependency:** STEP 1 ✅ (already completed)  

---

## 📋 Overview

Currently, `time.perf_counter()` syscalls and `deque.append()` allocations happen **every callback** (48,000 times per second @ 48kHz). This violates real-time rules even though overhead is <0.5%. 

**Goal:** Make latency monitoring optional so production users get 0% overhead when disabled.

---

## 🎯 STEP 2: Make Monitoring Optional

### **Changes Required**

#### **2.1 core/engine.py: Constructor parameter**

```python
def __init__(self, 
             samplerate: Optional[int] = None, 
             blocksize: int = 2048, 
             dtype: str = 'float32', 
             gc_policy: str = 'disable_during_playback',
             enable_latency_monitor: bool = False):  # ← NEW PARAMETER
    """
    ...
    enable_latency_monitor: bool
        - False (default): Monitoring disabled, 0% callback overhead
        - True: Latency stats collection enabled (for debugging/benchmarking)
    """
    # ... existing code ...
    
    # NEW: Store monitoring flag
    self.enable_latency_monitor = bool(enable_latency_monitor)
```

**Action:** Add parameter to `__init__` signature (around line 66)

---

#### **2.2 core/engine.py: Conditional in callback**

**Current code (lines 292-331):**
```python
# ❌ ALWAYS happens (every callback)
callback_start = time.perf_counter()
# ... callback logic ...
callback_end = time.perf_counter()
callback_duration = callback_end - callback_start
self._callback_durations.append(callback_duration)
self._total_callbacks += 1
if callback_duration > time_budget * 0.80:
    self._xrun_count += 1
```

**New code (wrapped in optional check):**
```python
# ✅ ONLY happens if enabled
if self.enable_latency_monitor:
    callback_start = time.perf_counter()
    # ... rest of monitoring code ...
    callback_end = time.perf_counter()
    callback_duration = callback_end - callback_start
    self._callback_durations.append(callback_duration)
    self._total_callbacks += 1
    if callback_duration > time_budget * 0.80:
        self._xrun_count += 1
```

**Action:** Wrap lines 292-331 in `if self.enable_latency_monitor:` block

---

#### **2.3 main.py: Load flag from config**

```python
# In main() function, after loading settings
from core.audio_profiles import AudioProfileManager

config = AudioProfileManager.get_instance()  # or ConfigManager once ready
enable_monitoring = config.get("monitoring.enable_latency_monitor", default=False)

# Pass to engine
player = MultiTrackPlayer(
    samplerate=None,
    blocksize=blocksize,
    gc_policy=profile.gc_policy,
    enable_latency_monitor=enable_monitoring  # ← NEW
)
```

**Action:** Check config and pass flag when creating engine

---

### **Why This Works**

- **Compilation optimization:** Compiler may optimize away `if False:` blocks
- **Zero-cost when disabled:** No branch penalty (single flag check per callback)
- **Backward compatible:** Default is `False` (no monitoring)
- **Developer-friendly:** Easy to enable via config for benchmarking

---

## 🎯 STEP 3: Replace `deque.append()` with Pre-Allocated Ring Buffer

### **Problem with Current Approach**

```python
# Line 118-120
self._callback_durations = deque(maxlen=100)

# Inside callback (line 328)
self._callback_durations.append(callback_duration)  # ← Can allocate
```

**Issue:** `deque.append()` may allocate memory even with `maxlen` set. This violates "no allocation in callback" rule.

### **Solution: Pre-Allocate Fixed Array + Index Counter**

#### **3.1 core/engine.py: Constructor modification**

```python
# BEFORE:
self._callback_durations = deque(maxlen=100)

# AFTER:
self._callback_durations = np.zeros(100, dtype='float64')  # Pre-allocate
self._duration_index = 0  # Atomic counter (wraps at 100)
```

**Action:** Replace deque with numpy array in `__init__` (lines 118-120)

---

#### **3.2 core/engine.py: Callback modification**

```python
# BEFORE (inside if self.enable_latency_monitor:):
self._callback_durations.append(callback_duration)
self._total_callbacks += 1

# AFTER:
# Ring buffer: Write to array[index % 100], increment index
self._callback_durations[self._duration_index % 100] = callback_duration
self._duration_index = (self._duration_index + 1) % 10000  # Wrap at 10k

# Keep existing _total_callbacks for compatibility
self._total_callbacks += 1
```

**Action:** Replace append with ring buffer write (line ~328)

---

#### **3.3 core/engine.py: Update `get_latency_stats()` method**

```python
# BEFORE:
def get_latency_stats(self) -> Dict[str, float]:
    if not self._callback_durations:
        return {...}
    
    durations = list(self._callback_durations)  # ← Copy from deque
    mean_duration = sum(durations) / len(durations)
    # ...

# AFTER:
def get_latency_stats(self) -> Dict[str, float]:
    # Use current ring buffer content (no deque copy needed)
    durations = self._callback_durations.copy()  # NumPy copy (safe)
    
    # Filter out zeros (empty slots in ring buffer if not full yet)
    durations = durations[durations > 0]
    
    if len(durations) == 0:
        return {...}
    
    mean_duration = float(np.mean(durations))
    max_duration = float(np.max(durations))
    min_duration = float(np.min(durations))
    # ...
```

**Action:** Update `get_latency_stats()` to use numpy array (lines 440-469)

---

### **Why This Approach**

- **No allocation in callback:** Ring buffer pre-allocated, index wraps atomically
- **Memory efficient:** Fixed 100-sample array (~800 bytes)
- **Fast reads:** O(1) write, O(n) read (acceptable, only called on UI demand)
- **Simple index wrapping:** `index % 100` is a single modulo operation (~1 cycle)

---

## 🔗 Relationship Between STEP 2 & 3

```
STEP 2: Wrap in if self.enable_latency_monitor:
    ├─ When disabled: 0% overhead (no timing, no allocation)
    ├─ When enabled: Continue to STEP 3
    │
    └─→ STEP 3: Replace deque with ring buffer
        ├─ When enabled: <0.5% overhead (fast ring buffer write)
        └─ Still benefits from Step 2 guard (can disable entirely)
```

**Example scenarios:**

| Scenario | enable_latency_monitor | Overhead | Use Case |
|----------|----------------------|----------|----------|
| Production | `False` | 0% | Live performance (church) |
| Benchmarking | `True` | <0.5% | Tuning audio profiles |
| Debugging | `True` + ring buffer | <0.5% | Troubleshooting glitches |

---

## ✅ Validation Checklist (After Both Steps)

- [ ] No new imports required (already have numpy)
- [ ] Tests still pass (238/238)
- [ ] `time.perf_counter()` calls wrapped in guard
- [ ] `deque.append()` replaced with ring buffer write
- [ ] `get_latency_stats()` updated to handle numpy array
- [ ] Config flag properly loaded in main.py
- [ ] Default is `False` (production use case: no monitoring)
- [ ] Can enable monitoring via config for debugging

---

## 📝 Implementation Order

1. **2.1:** Add `enable_latency_monitor` parameter to `__init__`
2. **2.2:** Wrap monitoring code in `if self.enable_latency_monitor:` guard
3. **2.3:** Update `main.py` to load and pass flag
4. **3.1:** Replace `deque` with numpy array in `__init__`
5. **3.2:** Update callback ring buffer write logic
6. **3.3:** Update `get_latency_stats()` to use numpy array
7. **Testing:** Run full test suite (expect 238/238 passed)
8. **Verification:** Check that latency monitor toggle works in app settings

---

## 🎯 After STEP 2 & 3 Complete

**Callback will be:**
```python
def _callback(self, outdata, frames, time_info, status):
    # Only real-time safe operations:
    if not self._playing:
        outdata.fill(0)
        self._frames_processed = self._pos
        return
    
    block = self._mix_block(self._pos, frames)  # Pure mixing (safe)
    out_len = min(frames, block.shape[0])
    outdata[:out_len] = block[:out_len]
    
    self._pos += out_len  # Atomic write (safe)
    
    if self._pos >= self._n_frames:
        self._playing = False
        self._stop_requested = True  # From STEP 1
    
    self._frames_processed = self._pos  # From STEP 1
    
    # OPTIONAL monitoring (STEP 2 & 3):
    if self.enable_latency_monitor:  # Guard added in STEP 2
        callback_start = time.perf_counter()
        # ... measurement code ...
        callback_end = time.perf_counter()
        callback_duration = callback_end - callback_start
        self._callback_durations[self._duration_index % 100] = callback_duration  # Ring buffer from STEP 3
        self._duration_index = (self._duration_index + 1) % 10000
        self._total_callbacks += 1
        if callback_duration > time_budget * 0.80:
            self._xrun_count += 1
    
    # ✅ Zero allocation, zero locks, zero driver calls
    # ✅ Compliant with all real-time safety rules
```

**Status:** Ready to implement ✅

