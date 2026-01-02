from typing import Optional
from PySide6.QtGui import QFont, QColor

from audio.tracks.beat_track import ViewContext


class ChordTrack:
    """Paints chord rectangles and labels using a ViewContext.

    Visual appearance intentionally mirrors the previous in-widget logic:
    same fonts, colors and layout.
    """

    def paint(self, painter, ctx: ViewContext) -> None:
        if ctx.end_sample <= ctx.start_sample:
            return

        w = max(1, ctx.width)
        h = max(2, ctx.height)
        total_samples = ctx.total_samples

        if ctx.timeline_model is None:
            return

        try:
            start_s = ctx.start_sample / float(ctx.sample_rate)
            end_s = ctx.end_sample / float(ctx.sample_rate)
            chords = ctx.timeline_model.chords_in_range(start_s, end_s)
        except Exception:
            chords = []

        if not chords:
            return

        painter.save()  # Save painter state
        try:
            font = QFont("Arial", 8, QFont.Bold)
            painter.setFont(font)
            box_h = min(18, max(12, h // 10))
            box_y = h - box_h - 2  # Position at bottom instead of top

            for s0_t, s1_t, name in chords:
                # convert times back to sample indices to reuse existing layout logic
                s0 = int(max(0, min(int(s0_t * ctx.sample_rate), total_samples - 1)))
                s1 = int(max(0, min(int(s1_t * ctx.sample_rate), total_samples - 1)))

                # skip if chord outside visible range
                if s1 < ctx.start_sample or s0 > ctx.end_sample:
                    continue
                # clip chord to visible window
                vis_s0 = max(s0, ctx.start_sample)
                vis_s1 = min(s1, ctx.end_sample)
                rel0 = (vis_s0 - ctx.start_sample) / (ctx.end_sample - ctx.start_sample)
                rel1 = (vis_s1 - ctx.start_sample) / (ctx.end_sample - ctx.start_sample)
                x0 = int(rel0 * w)
                x1 = int(rel1 * w)
                if x1 <= x0:
                    x1 = x0 + 1

                # color: empty chord 'N' shown grey; others greenish
                if str(name).strip().upper() == 'N':
                    fill = QColor(80, 80, 80, 120)
                    text_col = QColor(200, 200, 200)
                else:
                    fill = QColor(0, 120, 80, 150)
                    text_col = QColor(255, 255, 255)

                painter.fillRect(x0, box_y, x1 - x0, box_h, fill)
                painter.setPen(QColor(0, 0, 0, 100))
                painter.drawRect(x0, box_y, x1 - x0, box_h)
                painter.setPen(text_col)
                # Draw chord name left-aligned at chord start with a small padding
                text_padding = 4
                text_w = max(1, x1 - x0 - text_padding)
                painter.drawText(x0 + text_padding, box_y, text_w, box_h, 1 | 0x0040, str(name))
        finally:
            painter.restore()  # Always restore painter state
