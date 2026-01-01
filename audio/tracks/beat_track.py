from dataclasses import dataclass
from typing import Optional

from PySide6.QtGui import QPen, QColor

from core.timeline_model import TimelineModel


@dataclass
class ViewContext:
    """Lightweight, UI-independent context describing the current view.

    This object intentionally avoids UI concepts beyond width/height and the
    TimelineModel reference. It is serializable-friendly and easy to test.
    """
    start_sample: int
    end_sample: int
    total_samples: int
    sample_rate: int
    width: int
    height: int
    timeline_model: Optional[TimelineModel]


class BeatTrack:
    """Responsible for painting beats/downbeats given a ViewContext.

    The visual output is kept identical to previous widget behavior: same
    colors, widths, and ordering. This class isolates beat-drawing so the
    WaveformWidget can delegate and focus on waveform rendering.
    """

    def paint(self, painter, ctx: ViewContext) -> None:
        if ctx.end_sample <= ctx.start_sample:
            return

        w = max(1, ctx.width)
        h = max(2, ctx.height)

        # Pens match previous WaveformWidget styling
        beat_pen = QPen(QColor(0, 150, 255, 150))  # cyan, semi-transparent
        beat_pen.setWidth(1)
        down_pen = QPen(QColor(255, 200, 0, 120))  # yellow/orange, less opaque
        down_pen.setWidth(2)

        beats_samples = []
        downbeat_samples = []

        # Query TimelineModel (if any) for beats and downbeats in the visible time window
        if ctx.timeline_model is not None:
            try:
                start_s = ctx.start_sample / float(ctx.sample_rate)
                end_s = ctx.end_sample / float(ctx.sample_rate)

                beats_seconds = ctx.timeline_model.beats_in_range(start_s, end_s)
                beats_samples = [int(max(0, min(int(b * ctx.sample_rate), ctx.total_samples - 1))) for b in beats_seconds]

                if hasattr(ctx.timeline_model, 'downbeats_in_range'):
                    downbeats = ctx.timeline_model.downbeats_in_range(start_s, end_s)
                    downbeat_samples = [int(max(0, min(int(d * ctx.sample_rate), ctx.total_samples - 1))) for d in downbeats]
            except Exception:
                beats_samples = []
                downbeat_samples = []

        # Draw beats (thin, subtle)
        painter.setPen(beat_pen)
        for b in beats_samples:
            if ctx.start_sample <= b <= ctx.end_sample:
                rel_b = (b - ctx.start_sample) / (ctx.end_sample - ctx.start_sample)
                x_b = int(rel_b * w)
                painter.drawLine(x_b, 0, x_b, h)

        # Draw downbeats on top (also thin and translucent)
        painter.setPen(down_pen)
        for d in downbeat_samples:
            if ctx.start_sample <= d <= ctx.end_sample:
                rel_d = (d - ctx.start_sample) / (ctx.end_sample - ctx.start_sample)
                x_d = int(rel_d * w)
                painter.drawLine(x_d, 0, x_d, h)
