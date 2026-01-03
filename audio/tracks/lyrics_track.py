"""LyricsTrack for rendering time-synchronized lyrics in a timeline view.

This track is read-only and displays lyrics aligned horizontally to the timeline,
with visual emphasis on the currently active line during playback.
"""

from typing import Optional
from PySide6.QtGui import QPainter, QFont, QColor, QPen
from PySide6.QtCore import Qt

from audio.tracks.beat_track import ViewContext
from audio.lyrics.model import LyricsModel, LyricLine


class LyricsTrack:
    """Renders timed lyrics aligned to the timeline.
    
    Read-only track that displays lyric lines horizontally positioned by time.
    The active line (at current playhead) is highlighted, with previous and
    next lines shown above and below for context.
    """
    
    def __init__(self):
        # Default colors and styling for lyrics rendering
        self.active_color = QColor(255, 255, 255, 255)      # White, full opacity
        self.active_font_size = 15
        self.active_font_weight = QFont.Bold
        
        self.inactive_color = QColor(255, 255, 255, 255)    # White, full opacity
        self.inactive_font_size = 13
        self.inactive_font_weight = QFont.Normal
        
        self.y_offset = 30  # Pixels from bottom of track
    
    def paint(self, painter: QPainter, ctx: ViewContext) -> None:
        """Paint the lyrics track.
        
        Args:
            painter: QPainter to draw with
            ctx: ViewContext containing visible range and timeline info
        """
        
        timeline = ctx.timeline_model
        
        # Defensive checks
        if ctx.end_sample <= ctx.start_sample:
            return
        
        if timeline is None:
            return
        
        lyrics_model = getattr(timeline, 'lyrics_model', None)
        if not lyrics_model or len(lyrics_model) == 0:
            return
        
        if ctx.timeline_model is None:
            return
        
        painter.save()  # Save painter state
        try:
            # Convert visible range to seconds
            start_time_s = ctx.start_sample / float(ctx.sample_rate)
            end_time_s = ctx.end_sample / float(ctx.sample_rate)
            time_range_s = end_time_s - start_time_s
            
            if time_range_s <= 0:
                return
            
            # Get current playhead time
            playhead_time_s = ctx.timeline_model.get_playhead_time()
            
            # Get the active line for highlighting
            active_line = lyrics_model.get_active_line(playhead_time_s)
            
            # Draw ALL lyric lines that are in the visible time range
            # Similar to how ChordTrack draws all chords in range
            for line in lyrics_model.lines:
                # Check if this line's time is in the visible range
                if start_time_s <= line.time_s <= end_time_s:
                    # Determine if this is the active line
                    is_active = (active_line is not None and 
                                line.time_s == active_line.time_s and 
                                line.text == active_line.text)
                    
                    self._draw_line(
                        painter, line, ctx,
                        start_time_s, time_range_s,
                        is_active
                    )
            
        except Exception as e:
            # For debugging - print the error but don't crash
            print(f"[LyricsTrack] Error in paint: {e}")
        finally:
            painter.restore()  # Always restore painter state
    
    def _draw_line(
        self,
        painter: QPainter,
        line: LyricLine,
        ctx: ViewContext,
        start_time_s: float,
        time_range_s: float,
        is_active: bool
    ) -> None:
        """Draw a single lyric line.
        
        Args:
            painter: QPainter to draw with
            line: The lyric line to draw
            ctx: ViewContext for dimensions
            start_time_s: Start time of visible range in seconds
            time_range_s: Duration of visible range in seconds
            is_active: Whether this is the active line
        """
        # Calculate horizontal position based on time (like ChordTrack does)
        rel_time = (line.time_s - start_time_s) / time_range_s
        
        # Skip if outside visible range
        if rel_time < 0 or rel_time > 1.0:
            return
        
        x_position = int(rel_time * ctx.width)
        
        # Clamp to visible area
        x_position = max(0, min(x_position, ctx.width - 1))
        
        # Configure styling based on active state
        if is_active:
            # Active line: use configured active styling
            font = QFont("Arial", self.active_font_size, self.active_font_weight)
            color = self.active_color
        else:
            # Inactive line: use configured inactive styling
            font = QFont("Arial", self.inactive_font_size, self.inactive_font_weight)
            color = self.inactive_color
        
        painter.setFont(font)
        painter.setPen(QPen(color))
        
        # Draw text
        text = line.text
        if not text:
            return
        
        # Position text using configured offset
        y_position = ctx.height - self.y_offset
        
        # Get text metrics for positioning
        fm = painter.fontMetrics()
        text_width = fm.horizontalAdvance(text)
        
        # Draw text left-aligned at the x position (like timestamps)
        text_x = x_position + 5  # Small offset to the right
        
        # Ensure text doesn't go off screen
        if text_x + text_width > ctx.width:
            text_x = max(0, ctx.width - text_width - 5)
        
        # Draw the text
        painter.drawText(text_x, y_position, text)
