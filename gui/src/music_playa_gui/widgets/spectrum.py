from PySide6.QtCore import QRectF, QTimer
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QFormLayout, QLabel, QSpinBox, QWidget

from music_playa.interfaces import Visualizer
from music_playa_gui.i18n import tr, translator
from music_playa_gui.theme import SYNTHWAVE_GRADIENT
from music_playa_gui.utils import clamp

DEFAULT_COLUMNS = 32
DEFAULT_SEGMENTS = 8
MIN_COLUMNS = 4
MAX_COLUMNS = 128
MIN_SEGMENTS = 2
MAX_SEGMENTS = 32
FRAME_MS = 33

# Colour stops as (red, green, blue), bottom to top.
_GRADIENT = [QColor(colour).getRgb()[:3] for colour in SYNTHWAVE_GRADIENT]
# The widget has no background of its own: it is drawn over the cover art, so
# lit segments are translucent and unlit ones are not drawn at all.
_LIT_ALPHA = 230


def _gradient_color(position: float) -> QColor:
    """Colour for a height in 0..1, interpolated between the gradient stops."""
    scaled = clamp(position, 0.0, 1.0) * (len(_GRADIENT) - 1)
    index = min(int(scaled), len(_GRADIENT) - 2)
    fraction = scaled - index
    start, end = _GRADIENT[index], _GRADIENT[index + 1]
    red, green, blue = (round(a + (b - a) * fraction) for a, b in zip(start, end))
    return QColor(red, green, blue)


def segment_colors(segments: int) -> list[QColor]:
    """Bottom-to-top colours for the given number of segments."""
    if segments == 1:
        return [_gradient_color(0.0)]
    return [_gradient_color(segment / (segments - 1)) for segment in range(segments)]


def column_levels(bands: list[float], columns: int = DEFAULT_COLUMNS) -> list[float]:
    """Average the visualizer bands into a fixed number of display columns."""
    if not bands:
        return [0.0] * columns
    size = len(bands) / columns
    levels = []
    for column in range(columns):
        chunk = bands[int(column * size) : max(int((column + 1) * size), int(column * size) + 1)]
        levels.append(sum(chunk) / len(chunk))
    return levels


class SpectrumWidget(QWidget):
    """Bar spectrum drawn as columns of coloured segments."""

    def __init__(
        self,
        visualizer: Visualizer,
        columns: int = DEFAULT_COLUMNS,
        segments: int = DEFAULT_SEGMENTS,
    ) -> None:
        super().__init__()
        self._visualizer = visualizer
        self._columns = clamp(columns, MIN_COLUMNS, MAX_COLUMNS)
        self._segments = clamp(segments, MIN_SEGMENTS, MAX_SEGMENTS)
        self._colors = segment_colors(self._segments)
        self._levels = [0.0] * self._columns
        self.setMinimumHeight(160)
        self._timer = QTimer(self)
        self._timer.setInterval(FRAME_MS)
        self._timer.timeout.connect(self._refresh)
        self._timer.start()

    @property
    def columns(self) -> int:
        return self._columns

    @property
    def segments(self) -> int:
        return self._segments

    def set_columns(self, columns: int) -> None:
        self._columns = clamp(columns, MIN_COLUMNS, MAX_COLUMNS)
        self._levels = column_levels(self._visualizer.bands(), self._columns)
        self.update()

    def set_segments(self, segments: int) -> None:
        self._segments = clamp(segments, MIN_SEGMENTS, MAX_SEGMENTS)
        self._colors = segment_colors(self._segments)
        self.update()

    def _refresh(self) -> None:
        self._levels = column_levels(self._visualizer.bands(), self._columns)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        columns = len(self._levels)
        segments = self._segments
        column_width = self.width() / columns
        segment_height = self.height() / segments
        gap = min(4.0, column_width * 0.25, segment_height * 0.25)
        for column, level in enumerate(self._levels):
            lit = round(clamp(level, 0.0, 1.0) * segments)
            for segment in range(lit):
                color = QColor(self._colors[segment])
                color.setAlpha(_LIT_ALPHA)
                top = self.height() - (segment + 1) * segment_height
                rect = QRectF(
                    column * column_width + gap / 2,
                    top + gap / 2,
                    column_width - gap,
                    segment_height - gap,
                )
                painter.fillRect(rect, color)
        painter.end()


class SpectrumSettings(QWidget):
    """Inputs for the spectrum width (columns) and height (segments)."""

    def __init__(self, spectrum: SpectrumWidget) -> None:
        super().__init__()
        self.setObjectName("spectrumSettings")
        self.columns = QSpinBox()
        self.columns.setRange(MIN_COLUMNS, MAX_COLUMNS)
        self.columns.setValue(spectrum.columns)
        self.columns.valueChanged.connect(spectrum.set_columns)

        self.segments = QSpinBox()
        self.segments.setRange(MIN_SEGMENTS, MAX_SEGMENTS)
        self.segments.setValue(spectrum.segments)
        self.segments.valueChanged.connect(spectrum.set_segments)

        self._columns_label = QLabel()
        self._segments_label = QLabel()

        form = QFormLayout(self)
        form.setContentsMargins(0, 0, 0, 0)
        form.setVerticalSpacing(6)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        form.addRow(self._columns_label, self.columns)
        form.addRow(self._segments_label, self.segments)

        translator.language_changed.connect(self.retranslate)
        self.retranslate()

    def retranslate(self) -> None:
        self._columns_label.setText(tr("settings.columns"))
        self._segments_label.setText(tr("settings.segments"))
