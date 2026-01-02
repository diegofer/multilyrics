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
    
    def __init__(self, lyrics_model: LyricsModel):
        """Initialize the lyrics track.
        
        Args:
            lyrics_model: Model containing the timed lyric lines
        """
        self._lyrics_model = lyrics_model
    
    def paint(self, painter: QPainter, ctx: ViewContext) -> None:
        """Paint the lyrics track.
        
        Args:
            painter: QPainter to draw with
            ctx: ViewContext containing visible range and timeline info
        """
        # Defensive checks
        if ctx.end_sample <= ctx.start_sample:
            return
        
        if not self._lyrics_model or len(self._lyrics_model) == 0:
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
            playhead_time_s = ctx.timeline_model.playhead_time()
            
            # Get active, previous, and next lines
            active_line = self._lyrics_model.get_active_line(playhead_time_s)
            previous_line = self._lyrics_model.get_previous_line(playhead_time_s)
            next_line = self._lyrics_model.get_next_line(playhead_time_s)
            
            # Vertical layout configuration
            center_y = ctx.height // 2
            line_spacing = ctx.height // 6
            
            # Draw previous line (above center)
            if previous_line:
                self._draw_line(
                    painter, previous_line, ctx,
                    start_time_s, time_range_s,
                    center_y - line_spacing,
                    is_active=False
                )
            
            # Draw active line (at center)
            if active_line:
                self._draw_line(
                    painter, active_line, ctx,
                    start_time_s, time_range_s,
                    center_y,
                    is_active=True
                )
            
            # Draw next line (below center)
            if next_line:
                self._draw_line(
                    painter, next_line, ctx,
                    start_time_s, time_range_s,
                    center_y + line_spacing,
                    is_active=False
                )
            
        except Exception:
            # Fail silently - don't crash the rendering pipeline
            pass
        finally:
            painter.restore()  # Always restore painter state
    
    def _draw_line(
        self,
        painter: QPainter,
        line: LyricLine,
        ctx: ViewContext,
        start_time_s: float,
        time_range_s: float,
        y_position: int,
        is_active: bool
    ) -> None:
        """Draw a single lyric line.
        
        Args:
            painter: QPainter to draw with
            line: The lyric line to draw
            ctx: ViewContext for dimensions
            start_time_s: Start time of visible range in seconds
            time_range_s: Duration of visible range in seconds
            y_position: Vertical position to draw at
            is_active: Whether this is the active line
        """
        # Calculate horizontal position based on time
        rel_time = (line.time_s - start_time_s) / time_range_s
        
        # Skip if outside visible range (with small margin for clipping)
        if rel_time < -0.1 or rel_time > 1.1:
            return
        
        x_position = int(rel_time * ctx.width)
        
        # Clamp to visible area
        x_position = max(0, min(x_position, ctx.width))
        
        # Configure styling based on active state
        if is_active:
            # Active line: white, larger, full opacity
            font = QFont("Arial", 12, QFont.Bold)
            color = QColor(255, 255, 255, 255)
        else:
            # Inactive line: light gray, smaller, reduced opacity
            font = QFont("Arial", 10, QFont.Normal)
            color = QColor(180, 180, 180, 160)
        
        painter.setFont(font)
        painter.setPen(QPen(color))
        
        # Draw text centered at the x position
        text = line.text
        if not text:
            return
        
        # Get text metrics for centering
        fm = painter.fontMetrics()
        text_width = fm.horizontalAdvance(text)
        text_height = fm.height()
        
        # Center text horizontally around the x position
        text_x = x_position - text_width // 2
        text_y = y_position + text_height // 4  # Adjust for baseline
        
        # Ensure text doesn't go off screen
        text_x = max(0, min(text_x, ctx.width - text_width))
        
        # Draw the text
        painter.drawText(text_x, text_y, text)
