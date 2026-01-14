"""Timeline-based lyrics model for audio applications.

Provides interface for querying, editing, loading and saving lyric lines
at specific playback positions. Supports .lrc file format.
"""

import re
from dataclasses import dataclass
from typing import Optional, Callable
from bisect import bisect_right, insort
from pathlib import Path


@dataclass
class LyricLine:
    """A single lyric line with its timestamp.
    
    Attributes:
        time_s: Time in seconds when this line becomes active (clamped to >= 0)
        text: The lyric text content
    """
    time_s: float
    text: str
    
    def __post_init__(self):
        """Clamp negative times to zero."""
        if self.time_s < 0:
            self.time_s = 0.0


class LyricsModel:
    """Manages an ordered sequence of timed lyric lines.
    
    Lines are kept sorted by time. Provides efficient lookup of active,
    previous, and next lines for a given playback position.
    Supports editing operations and .lrc file I/O.
    Safe for frequent calls during playback.
    """
    
    def __init__(self, lines: Optional[list[LyricLine]] = None):
        """Initialize the lyrics model.
        
        Args:
            lines: Optional list of LyricLine objects, will be sorted by time
        """
        self._lines = lines or []
        self._lines.sort(key=lambda l: l.time_s)
        self._callbacks: list[Callable[[], None]] = []
    
    def line_index_at_time(self, t: float) -> Optional[int]:
        """Find the index of the active lyric line at the given time.
        
        A line is active if its time <= t < next line time.
        Returns None if no line is active (before first line or empty).
        
        Args:
            t: Time in seconds
            
        Returns:
            Index of the active line, or None if no line is active
        """
        if not self._lines:
            return None
        
        # bisect_right finds insertion point: all lines before have time_s <= t
        idx = bisect_right([line.time_s for line in self._lines], t)
        
        # If idx is 0, we're before the first line
        if idx == 0:
            return None
        
        # The active line is at idx - 1
        return idx - 1
    
    def get_active_line(self, t: float) -> Optional[LyricLine]:
        """Get the active lyric line at the given time.
        
        Args:
            t: Time in seconds
            
        Returns:
            The active LyricLine, or None if no line is active
        """
        idx = self.line_index_at_time(t)
        return self._lines[idx] if idx is not None else None
    
    def get_previous_line(self, t: float) -> Optional[LyricLine]:
        """Get the lyric line before the active line at the given time.
        
        Args:
            t: Time in seconds
            
        Returns:
            The previous LyricLine, or None if no previous line exists
        """
        idx = self.line_index_at_time(t)
        if idx is not None and idx > 0:
            return self._lines[idx - 1]
        return None
    
    def get_next_line(self, t: float) -> Optional[LyricLine]:
        """Get the lyric line after the active line at the given time.
        
        Args:
            t: Time in seconds
            
        Returns:
            The next LyricLine, or None if no next line exists
        """
        idx = self.line_index_at_time(t)
        if idx is not None and idx < len(self._lines) - 1:
            return self._lines[idx + 1]
        return None
    
    def line_at_time(self, t: float) -> Optional[LyricLine]:
        """Alias for get_active_line for API compatibility.
        
        Args:
            t: Time in seconds
            
        Returns:
            The active LyricLine, or None if no line is active
        """
        return self.get_active_line(t)
    
    # === Editing Operations ===
    
    def insert_line(self, time_s: float, text: str) -> None:
        """Insert a new lyric line at the specified time.
        
        Maintains sorted order. Clamps negative times to zero.
        
        Args:
            time_s: Time in seconds when the line becomes active
            text: The lyric text content
        """
        line = LyricLine(time_s=time_s, text=text)
        # insort maintains sorted order efficiently
        insort(self._lines, line, key=lambda l: l.time_s)
        self._notify_change()
    
    def update_line_time(self, index: int, new_time_s: float) -> None:
        """Update the time of a lyric line at the given index.
        
        Maintains sorted order by removing and re-inserting the line.
        Clamps negative times to zero.
        
        Args:
            index: Index of the line to update
            new_time_s: New time in seconds
            
        Raises:
            IndexError: If index is out of bounds
        """
        if not 0 <= index < len(self._lines):
            raise IndexError(f"Index {index} out of bounds for {len(self._lines)} lines")
        
        line = self._lines.pop(index)
        line.time_s = max(0.0, new_time_s)
        insort(self._lines, line, key=lambda l: l.time_s)
        self._notify_change()
    
    def update_line_text(self, index: int, new_text: str) -> None:
        """Update the text of a lyric line at the given index.
        
        Args:
            index: Index of the line to update
            new_text: New text content
            
        Raises:
            IndexError: If index is out of bounds
        """
        if not 0 <= index < len(self._lines):
            raise IndexError(f"Index {index} out of bounds for {len(self._lines)} lines")
        
        self._lines[index].text = new_text
        self._notify_change()
    
    def delete_line(self, index: int) -> None:
        """Delete a lyric line at the given index.
        
        Args:
            index: Index of the line to delete
            
        Raises:
            IndexError: If index is out of bounds
        """
        if not 0 <= index < len(self._lines):
            raise IndexError(f"Index {index} out of bounds for {len(self._lines)} lines")
        
        self._lines.pop(index)
        self._notify_change()
    
    # === File I/O Operations ===
    
    def load_from_lrc(self, path: Path) -> None:
        """Load lyrics from an .lrc file.
        
        Replaces current lyrics with the loaded content.
        Supports multiple timestamps per line and ignores metadata tags.
        
        Args:
            path: Path to the .lrc file
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the file cannot be parsed
        """
        if not path.exists():
            raise FileNotFoundError(f"LRC file not found: {path}")
        
        try:
            text = path.read_text(encoding='utf-8')
            lines = self._parse_lrc_text(text)
            self._lines = lines
            self._notify_change()
        except Exception as e:
            raise ValueError(f"Failed to parse LRC file: {e}")
    
    def export_to_lrc(self, path: Path) -> None:
        """Export lyrics to an .lrc file.
        
        Saves the current lyrics in standard .lrc format.
        Creates parent directories if they don't exist.
        
        Args:
            path: Path where the .lrc file will be saved
            
        Raises:
            IOError: If the file cannot be written
        """
        try:
            # Ensure parent directory exists
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Generate LRC content
            lrc_lines = []
            for line in self._lines:
                timestamp = self._format_timestamp(line.time_s)
                lrc_lines.append(f"{timestamp}{line.text}")
            
            # Write to file
            path.write_text('\n'.join(lrc_lines), encoding='utf-8')
        except Exception as e:
            raise IOError(f"Failed to export LRC file: {e}")
    
    # === Callback Management ===
    
    def register_callback(self, callback: Callable[[], None]) -> None:
        """Register a callback to be notified when the model changes.
        
        Callbacks are called after any editing or loading operation.
        
        Args:
            callback: Function to call when the model changes
        """
        if callback not in self._callbacks:
            self._callbacks.append(callback)
    
    def unregister_callback(self, callback: Callable[[], None]) -> None:
        """Unregister a previously registered callback.
        
        Args:
            callback: Function to remove from callbacks
        """
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    # === Private Helper Methods ===
    
    def _notify_change(self) -> None:
        """Notify all registered callbacks of a change."""
        for callback in self._callbacks:
            try:
                callback()
            except Exception:
                # Don't let callback failures break the model
                pass
    
    def _parse_lrc_text(self, text: str) -> list[LyricLine]:
        """Parse LRC format text into a list of LyricLine objects.
        
        Supports:
        - Multiple timestamps per line: [00:12.00][00:17.20]Repeated line
        - Metadata tags (ignored): [ar:], [ti:], [al:], etc.
        - Standard format: [mm:ss.xx]Lyric text
        
        Args:
            text: LRC format text content
            
        Returns:
            List of LyricLine objects, sorted by time
        """
        lines = []
        timestamp_pattern = re.compile(r'\[(\d+):(\d+(?:\.\d+)?)\]')
        
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            
            timestamps = timestamp_pattern.findall(line)
            if not timestamps:
                continue
            
            lyric_text = timestamp_pattern.sub('', line).strip()
            
            # Skip metadata tags like [ar:Artist]
            if lyric_text.startswith('[') and ':' in lyric_text and lyric_text.endswith(']'):
                continue
            
            # Create a LyricLine for each timestamp
            for minutes, seconds in timestamps:
                time_s = int(minutes) * 60 + float(seconds)
                lines.append(LyricLine(time_s=time_s, text=lyric_text))
        
        lines.sort(key=lambda l: l.time_s)
        return lines
    
    def _format_timestamp(self, time_s: float) -> str:
        """Format a time in seconds as an LRC timestamp.
        
        Args:
            time_s: Time in seconds
            
        Returns:
            Formatted timestamp like [02:34.56]
        """
        minutes = int(time_s // 60)
        seconds = time_s % 60
        return f"[{minutes:02d}:{seconds:05.2f}]"
    
    # === Properties and Special Methods ===
    
    @property
    def lines(self) -> list[LyricLine]:
        """Access to the underlying list of lyric lines (read-only view)."""
        return self._lines.copy()
    
    def __len__(self) -> int:
        """Return the number of lyric lines."""
        return len(self._lines)
    
    def __bool__(self) -> bool:
        """Return True if the model contains any lines."""
        return bool(self._lines)
