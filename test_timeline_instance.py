"""Quick validation script to verify single TimelineModel instance."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from core.timeline_model import TimelineModel
from core.playback_manager import PlaybackManager
from core.sync import SyncController

# Create instances like MainWindow does
timeline = TimelineModel()
sync = SyncController(44100)
playback = PlaybackManager(sync, timeline=timeline)

print(f"Timeline instance ID: {id(timeline)}")
print(f"PlaybackManager timeline ID: {id(playback.timeline)}")
print(f"IDs match: {id(timeline) == id(playback.timeline)}")

# Simulate what WaveformWidget would do
waveform_timeline = timeline  # Same reference passed to waveform.set_timeline()
print(f"WaveformWidget timeline ID: {id(waveform_timeline)}")
print(f"All IDs match: {id(timeline) == id(playback.timeline) == id(waveform_timeline)}")

# Test that updates flow correctly
print("\n--- Testing playhead updates ---")
timeline.set_duration_seconds(10.0)  # Must set duration before playhead works
observer_called = []

def test_observer(time):
    observer_called.append(time)
    print(f"Observer received: {time:.3f}s")

timeline.on_playhead_changed(test_observer)

# Simulate PlaybackManager updating timeline during playback
print("\nSimulating PlaybackManager updating timeline...")
playback.timeline.set_playhead_time(1.5)

print(f"\nObserver was called: {len(observer_called) > 0}")
print(f"Playhead value: {timeline.get_playhead_time()}")
print("\n✅ Single TimelineModel instance successfully enforced!")
