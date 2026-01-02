import numpy as np
from PySide6.QtGui import QPainter, QColor, QPen

from audio.tracks.beat_track import ViewContext


class WaveformTrack:
    """Renders the audio waveform using a cached envelope per paint call.

    Stateless aside from an internal render cache keyed by (start, end, width).
    """

    def __init__(self) -> None:
        self._last_params = None  # (start, end, width)
        self._last_envelope = None  # (mins, maxs)

    def reset_cache(self) -> None:
        self._last_params = None
        self._last_envelope = None

    def _compute_envelope(self, samples: np.ndarray, start: int, end: int, w: int, zoom_factor=None):
        key = (start, end, w, zoom_factor)
        if self._last_params == key and self._last_envelope is not None:
            return self._last_envelope

        window = samples[start:end + 1]
        L = len(window)
        if L == 0:
            mins = np.zeros(w, dtype=np.float32)
            maxs = np.zeros(w, dtype=np.float32)
        elif L < w:
            indices = np.linspace(0, L - 1, num=w)
            interp = np.interp(indices, np.arange(L), window)
            mins = interp.astype(np.float32)
            maxs = interp.astype(np.float32)
        else:
            edges = np.linspace(0, L, num=w + 1, dtype=int)
            mins = np.empty(w, dtype=np.float32)
            maxs = np.empty(w, dtype=np.float32)
            for i in range(w):
                s = edges[i]
                e = edges[i + 1]
                if e <= s:
                    v = float(window[min(s, L - 1)])
                    mins[i] = v
                    maxs[i] = v
                else:
                    block = window[s:e]
                    mins[i] = float(np.min(block))
                    maxs[i] = float(np.max(block))

        self._last_params = key
        self._last_envelope = (mins, maxs)
        return mins, maxs

    def paint(self, painter: QPainter, ctx: ViewContext, samples: np.ndarray) -> None:
        """Draw waveform envelope for the current viewport."""
        w = max(1, ctx.width)
        h = max(2, ctx.height)
        mid = h // 2

        pen = QPen(QColor(0, 200, 255), 1)
        painter.setPen(pen)

        mins, maxs = self._compute_envelope(samples, ctx.start_sample, ctx.end_sample, w, None)
        for x in range(w):
            y1 = int(mins[x] * (h / 2 - 2))
            y2 = int(maxs[x] * (h / 2 - 2))
            painter.drawLine(x, mid - y2, x, mid - y1)
