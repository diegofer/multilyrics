"""LyricsTrack for rendering time-synchronized lyrics in a timeline view.

This track is read-only and displays lyrics aligned horizontally to the timeline,
with visual emphasis on the currently active line during playback.
"""

from typing import Optional
from PySide6.QtGui import QPainter, QFont, QColor, QPen
from PySide6.QtCore import Qt

from ui.widgets.tracks.beat_track import ViewContext
from models.lyrics_model import LyricsModel, LyricLine
from ui.styles import StyleManager
from utils.logger import get_logger

logger = get_logger(__name__)


class LyricsTrack:
    """Renders timed lyrics aligned to the timeline.

    Read-only track that displays lyric lines horizontally positioned by time.
    The active line (at current playhead) is highlighted, with previous and
    next lines shown above and below for context.
    """

    def __init__(self):
        # Default colors and styling for lyrics rendering
        self.active_color = StyleManager.get_color("text_bright")      # White, full opacity
        self.active_font_size = 11
        self.active_font_weight = QFont.Bold

        self.inactive_color = StyleManager.get_color("text_normal")    # White, full opacity
        self.inactive_font_size = 10
        self.inactive_font_weight = QFont.Normal

        # Track height for consistent layout
        self.track_height = 22  # pixels
        # Lyrics occupy the first track from bottom (0-22px from bottom)

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
            # Calculate track position: first track from bottom
            track_y = ctx.height - self.track_height

            # Draw background for the entire lyrics track (full width)
            # Using a dark blue-gray tone that contrasts well with timeline background
            bg_color = QColor(35, 45, 65)  # Dark blue-gray for readability
            bg_color.setAlpha(200)  # More opaque for better contrast
            painter.fillRect(0, track_y, ctx.width, self.track_height, bg_color)

            # Draw border for the track with a subtle accent
            border_color = QColor(60, 80, 110)  # Slightly lighter blue-gray border
            painter.setPen(border_color)
            painter.drawLine(0, track_y, ctx.width, track_y)  # Top border
            painter.drawLine(0, track_y + self.track_height - 1, ctx.width, track_y + self.track_height - 1)  # Bottom border

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

            # Detect zoom mode to adapt rendering strategy
            zoom_mode = getattr(ctx, 'zoom_mode', 'PLAYBACK')

            if zoom_mode == 'GENERAL':
                # OVERVIEW MODE: Show only first visible line + indicator
                self._paint_overview_mode(painter, ctx, lyrics_model,
                                         start_time_s, end_time_s, time_range_s, track_y)
            else:
                # PLAYBACK/EDIT MODE: Show all lines in visible range
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
            # For debugging - log the error but don't crash
            logger.error(f"[LyricsTrack] Error in paint: {e}", exc_info=True)
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
            font = StyleManager.get_font(mono=False, size=self.active_font_size, bold=True)
            color = self.active_color
        else:
            # Inactive line: use configured inactive styling
            font = StyleManager.get_font(mono=False, size=self.inactive_font_size, bold=False)
            color = self.inactive_color

        painter.setFont(font)

        # Draw text
        text = line.text
        if not text:
            return

        # Calculate track position: first track from bottom
        track_y = ctx.height - self.track_height

        # Get text metrics for positioning
        fm = painter.fontMetrics()
        text_width = fm.horizontalAdvance(text)
        text_height = fm.height()

        # Calculate text position
        text_padding = 5
        text_x = x_position + text_padding

        # Ensure text doesn't go off screen
        if text_x + text_width > ctx.width:
            text_x = max(0, ctx.width - text_width - text_padding)

        # Center text vertically within the track band
        text_y = track_y + (self.track_height + text_height) // 2 - fm.descent()

        # Draw the text directly on the track background
        painter.setPen(QPen(color))
        painter.drawText(text_x, text_y, text)

    def _paint_overview_mode(
        self,
        painter: QPainter,
        ctx: ViewContext,
        lyrics_model,
        start_time_s: float,
        end_time_s: float,
        time_range_s: float,
        track_y: int
    ) -> None:
        """Paint simplified overview: first line + count indicator.

        In GENERAL/OVERVIEW zoom mode, showing all lyrics creates clutter.
        Instead, show only the first visible line and a count of remaining lines.
        """
        # Find first line in visible range
        first_line = None
        total_lines = len(lyrics_model.lines)
        visible_count = 0

        for line in lyrics_model.lines:
            if start_time_s <= line.time_s <= end_time_s:
                if first_line is None:
                    first_line = line
                visible_count += 1

        if first_line is None:
            # No lines in visible range - show generic indicator
            self._draw_no_lyrics_indicator(painter, ctx, track_y, total_lines)
            return

        # Draw the first visible line
        font = StyleManager.get_font(mono=False, size=10, bold=False)
        color = self.inactive_color
        painter.setFont(font)
        painter.setPen(QPen(color))

        # Calculate position for first line
        rel_time = (first_line.time_s - start_time_s) / time_range_s
        x_position = int(rel_time * ctx.width)

        fm = painter.fontMetrics()
        text_height = fm.height()
        text_y = track_y + (self.track_height + text_height) // 2 - fm.descent()

        # Draw truncated text if too long
        max_text_width = ctx.width // 3  # Use max 1/3 of screen
        text = first_line.text
        text_width = fm.horizontalAdvance(text)

        if text_width > max_text_width:
            # Truncate with ellipsis
            while text_width > max_text_width - 20 and len(text) > 3:
                text = text[:-1]
                text_width = fm.horizontalAdvance(text)
            text = text + "..."

        text_x = x_position + 5
        painter.drawText(text_x, text_y, text)

        # Draw indicator for remaining lines at the end of track
        if visible_count > 1:
            indicator_text = f"♪ +{visible_count - 1} more"
            indicator_width = fm.horizontalAdvance(indicator_text)
            indicator_x = ctx.width - indicator_width - 10
            indicator_color = QColor(self.inactive_color)
            indicator_color.setAlpha(150)  # Semi-transparent
            painter.setPen(QPen(indicator_color))
            painter.drawText(indicator_x, text_y, indicator_text)

    def _draw_no_lyrics_indicator(
        self,
        painter: QPainter,
        ctx: ViewContext,
        track_y: int,
        total_lines: int
    ) -> None:
        """Draw indicator when no lyrics are visible in current range."""
        font = StyleManager.get_font(mono=False, size=10, bold=False)
        painter.setFont(font)

        indicator_color = QColor(self.inactive_color)
        indicator_color.setAlpha(120)
        painter.setPen(QPen(indicator_color))

        fm = painter.fontMetrics()
        text_height = fm.height()
        text_y = track_y + (self.track_height + text_height) // 2 - fm.descent()

        indicator_text = f"♪ {total_lines} lyrics lines"
        text_x = 10
        painter.drawText(text_x, text_y, indicator_text)
