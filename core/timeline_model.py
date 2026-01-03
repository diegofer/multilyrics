"""TimelineModel

A UI-independent model that centralizes timeline-related logic for the application.

Responsibilities:
- Maintain timeline state: sample rate, duration (seconds), canonical playhead time
- Store simple timeline metadata: beats (seconds), downbeats (seconds), chords (start,end,name)
- Store lyrics model for time-synced lyrics
- Provide conversions seconds <-> samples
- Provide query helpers for beats/chords within an arbitrary time range

Non-responsibilities (explicit):
- This class does NOT load or store raw audio sample buffers.
- This class does NOT perform any painting or UI logic.
- This class does NOT depend on Qt/PySide (no signals/slots here).

This module is intentionally minimal for the first refactor step; advanced helpers
(e.g., snapping, next/prev beat, lyric events, observer hooks, thread-safety) are
left as TODO items to be implemented later.
"""
from typing import List, Tuple, Optional, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from audio.lyrics.model import LyricsModel

# Type alias for chords stored as plain tuples (start_seconds, end_seconds, name)
Chord = Tuple[float, float, str]


class TimelineModel:
    """A minimal timeline model for the project.

    Public API is intentionally small for the first step. All times are in seconds
    (floats). Chords are plain tuples (start_seconds, end_seconds, name). Beats and
    downbeats are plain lists of seconds.
    """

    def __init__(self, sample_rate: int = 44100, duration_seconds: float = 0.0) -> None:
        if sample_rate <= 0:
            raise ValueError("sample_rate must be a positive integer")

        self._sample_rate: int = int(sample_rate)
        self._duration_seconds: float = max(0.0, float(duration_seconds))

        # Canonical playhead time in seconds (0.0 <= playhead <= duration)
        self._playhead_time: float = 0.0

        # Plain-data storage (minimal):
        self._beats: List[float] = []
        self._downbeats: List[float] = []
        self._chords: List[Chord] = []
        
        # Lyrics model (optional, set via set_lyrics_model)
        self.lyrics_model: Optional['LyricsModel'] = None

        # Observers for playhead changes (callable: new_time_seconds -> None)
        # This is a simple synchronous callback list; callers are responsible for
        # threading and marshaling to GUI threads if needed.
        self._playhead_observers: List[Callable[[float], None]] = []

    # ---------------------- Basic properties ----------------------
    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    def set_sample_rate(self, sr: int) -> None:
        if sr <= 0:
            raise ValueError("sample_rate must be a positive integer")
        self._sample_rate = int(sr)

    @property
    def duration_seconds(self) -> float:
        return self._duration_seconds

    def set_duration_seconds(self, seconds: float) -> None:
        # Emit playheadChanged signal when playhead time changes
        if seconds < 0:
            raise ValueError("duration_seconds must be non-negative")
        self._duration_seconds = float(seconds)
        # Ensure playhead remains in valid range
        if self._playhead_time > self._duration_seconds:
            self._playhead_time = self._duration_seconds
        self._notify_playhead_changed()
        if seconds < 0:
            raise ValueError("duration_seconds must be non-negative")
        self._duration_seconds = float(seconds)
        # Ensure playhead remains in valid range
        if self._playhead_time > self._duration_seconds:
            self._playhead_time = self._duration_seconds

    @property
    def total_samples(self) -> int:
        return int(self._duration_seconds * self._sample_rate)

    # ---------------------- Time <-> Sample conversions ----------------------
    def seconds_to_samples(self, seconds: float) -> int:
        """Convert seconds to integer sample index (clamped to valid range).

        If there are zero samples (duration==0), this returns 0.
        """
        if seconds < 0:
            seconds = 0.0
        if self.total_samples <= 0:
            return 0
        samples = int(seconds * self._sample_rate)
        return int(max(0, min(samples, self.total_samples - 1)))

    def samples_to_seconds(self, samples: int) -> float:
        """Convert sample index to seconds.

        Negative inputs are clamped to 0. Returns float seconds.
        """
        if samples <= 0:
            return 0.0
        # Allow samples beyond total_samples; callers can clamp if desired
        return float(samples) / float(self._sample_rate)

    # ---------------------- Playhead API ----------------------
    def set_playhead_time(self, seconds: float) -> None:
        """Set canonical playhead time in seconds (clamped to [0, duration]).

        Observers registered via ``on_playhead_changed`` are synchronously notified
        (in registration order) when the playhead value actually changes. Callbacks
        receive the new playhead time (seconds).

        Threading: callbacks are invoked on the same thread that calls this method.
        Callers are responsible for marshaling to the GUI thread if necessary.
        """
        if seconds != seconds:  # NaN check
            raise ValueError("playhead time must be a number")
        if seconds < 0.0:
            seconds = 0.0
        if seconds > self._duration_seconds:
            seconds = self._duration_seconds
        new_time = float(seconds)
        #print(f"[TimelineModel] set_playhead_time: {new_time:.3f}s (id: {id(self)})")
        # Notify only if the value actually changed
        if new_time == self._playhead_time:
            return
        self._playhead_time = new_time
        self._notify_playhead_changed()

    def _notify_playhead_changed(self) -> None:
        """Internal method to notify all observers of playhead change."""
        # Call observers synchronously in registration order. Ensure one failing
        # observer does not prevent others from running.
        for cb in list(self._playhead_observers):
            try:
                cb(self._playhead_time)
            except Exception:
                # Keep implementation lightweight: do not raise; continue to next
                # observer. Caller may replace this with logging as needed.
                try:
                    import warnings
                    warnings.warn("A playhead observer raised an exception and was ignored")
                except Exception:
                    pass

    def get_playhead_time(self) -> float:
        return self._playhead_time

    def set_playhead_sample(self, sample: int) -> None:
        if sample < 0:
            sample = 0
        if self.total_samples > 0 and sample >= self.total_samples:
            sample = max(0, self.total_samples - 1)
        seconds = self.samples_to_seconds(sample)
        # Delegate to set_playhead_time to ensure validation and observer notification
        self.set_playhead_time(seconds)

    def get_playhead_sample(self) -> int:
        return self.seconds_to_samples(self._playhead_time)

    def on_playhead_changed(self, callback: Callable[[float], None]) -> Callable[[], None]:
        """Register a synchronous callback for playhead changes.

        The callback will be invoked with a single argument: the new playhead time
        in seconds. Callbacks are called synchronously in registration order from
        the same thread that updates the playhead. The caller is responsible for
        thread-safety and for marshaling to the UI thread when necessary.

        Returns:
            unsubscribe: a callable that, when invoked, removes the registered callback.

        Raises:
            ValueError: if `callback` is not callable.
        """
        if not callable(callback):
            raise ValueError("callback must be callable")
        self._playhead_observers.append(callback)

        def unsubscribe() -> None:
            try:
                self._playhead_observers.remove(callback)
            except ValueError:
                pass

        return unsubscribe

    # ---------------------- Metadata management (minimal) ----------------------
    def set_beats(self, beats_seconds: List[float], downbeat_flags: Optional[List[int]] = None) -> None:
        """Set beats. Optionally pass corresponding downbeat flags (1==downbeat).

        Input lists are copied; no sorting or deduplication is performed here.
        """
        self._beats = [float(b) for b in beats_seconds]
        self._downbeats = []
        if downbeat_flags is not None:
            for b, flag in zip(self._beats, downbeat_flags):
                try:
                    if int(flag) == 1:
                        self._downbeats.append(b)
                except Exception:
                    continue

    def set_chords(self, chords: List[Chord]) -> None:
        """Set chords as plain tuples (start_seconds, end_seconds, name).

        Basic validation: start and end are converted to floats and clipped so
        start <= end. Invalid items are skipped.
        """
        out: List[Chord] = []
        for item in chords:
            try:
                s0 = float(item[0])
                s1 = float(item[1])
                name = str(item[2])
                if s1 < s0:
                    s0, s1 = s1, s0
                out.append((s0, s1, name))
            except Exception:
                continue
        self._chords = out

    def set_lyrics_model(self, lyrics_model: Optional['LyricsModel']) -> None:
        """Set the lyrics model for this timeline.
        
        Args:
            lyrics_model: LyricsModel instance or None to clear
        """
        self.lyrics_model = lyrics_model

    # ---------------------- Query helpers ----------------------
    def beats_in_range(self, start_s: float, end_s: float) -> List[float]:
        """Return beats whose times are within [start_s, end_s]."""
        if end_s < start_s:
            raise ValueError("end_s must be >= start_s")
        return [b for b in self._beats if start_s <= b <= end_s]

    def downbeats_in_range(self, start_s: float, end_s: float) -> List[float]:
        """Return downbeat times that fall within the closed interval [start_s, end_s].

        Args:
            start_s: start time in seconds (inclusive)
            end_s: end time in seconds (inclusive)

        Returns a list of downbeat times (floats). If the timeline has no
        downbeats, an empty list is returned.

        Raises:
            ValueError: if end_s < start_s
        """
        if end_s < start_s:
            raise ValueError("end_s must be >= start_s")
        # Use the model's canonical downbeat storage; do not expose private
        # attributes to callers. This method does not modify state.
        return [d for d in self._downbeats if start_s <= d <= end_s]

    def chords_in_range(self, start_s: float, end_s: float) -> List[Chord]:
        """Return chords that overlap the time interval [start_s, end_s]."""
        if end_s < start_s:
            raise ValueError("end_s must be >= start_s")
        result: List[Chord] = []
        for s0, s1, name in self._chords:
            # overlap test
            if s1 >= start_s and s0 <= end_s:
                result.append((s0, s1, name))
        return result

    # ---------------------- TODOs (to be implemented later) ----------------------
    # - next_beat(after_s: float) -> Optional[float]
    # - prev_beat(before_s: float) -> Optional[float]
    # - snap_time_to_beat(time_s: float, mode: str = 'nearest', max_dist: Optional[float] = None)
    # - lyric events / LRC parsing
    # - lightweight observer/callback API (or switch to event bus)

    def __repr__(self) -> str:  # pragma: no cover - small convenience
        return (
            f"<TimelineModel sr={self._sample_rate} dur={self._duration_seconds:.3f}s "
            f"playhead={self._playhead_time:.3f}s beats={len(self._beats)} chords={len(self._chords)}>"
        )
