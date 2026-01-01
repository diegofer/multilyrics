from PySide6.QtGui import QPen, QColor, QFont
from PySide6.QtCore import Qt

from audio.tracks.beat_track import ViewContext
from core.utils import format_time


class PlayheadTrack:
    """Renders the playhead (vertical red line) and elapsed time text.

    Reads canonical playhead time from TimelineModel to avoid duplicating state.
    Visual appearance intentionally mirrors the previous in-widget logic.
    """

    def paint(self, painter, ctx: ViewContext) -> None:
        if ctx.end_sample <= ctx.start_sample:
            return
        if ctx.timeline_model is None:
            return

        w = max(1, ctx.width)
        h = max(2, ctx.height)

        # Read canonical playhead time from TimelineModel
        try:
            playhead_time = ctx.timeline_model.get_playhead_time()
            playhead_sample = int(max(0, min(int(playhead_time * ctx.sample_rate), ctx.total_samples - 1)))
        except Exception:
            return

        # Only draw if playhead is in the visible range
        if not (ctx.start_sample <= playhead_sample <= ctx.end_sample):
            return

        # Compute playhead position in pixels
        rel = (playhead_sample - ctx.start_sample) / (ctx.end_sample - ctx.start_sample)
        x_pos = int(rel * w)

        # Draw vertical red line
        play_pen = QPen(QColor(255, 50, 50), 2)
        painter.setPen(play_pen)
        painter.drawLine(x_pos, 0, x_pos, h)

        # Draw elapsed time text next to the playhead
        current_time_str = format_time(playhead_time)
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Arial", 9, QFont.Bold))

        # Position text to the right of playhead; move left if not enough space
        text_x = x_pos + 5
        if text_x + 100 > w:
            text_x = x_pos - 105

        painter.drawText(text_x, 20, 100, 20, Qt.AlignLeft, current_time_str)
