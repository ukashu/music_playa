from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QComboBox, QFormLayout, QLabel, QSpinBox, QWidget

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
# Bars show the band levels; the wave draws the raw samples as one line.
MODE_BARS = "bars"
MODE_WAVE = "wave"
SPECTRUM_MODES = (MODE_BARS, MODE_WAVE)
# (width, alpha) of the glow layers under the wave, widest first, and the width of the core.
WAVE_GLOW = ((10.0, 35), (5.0, 80))
WAVE_CORE_WIDTH = 2.0
_MODE_LABEL_KEYS = {MODE_BARS: "settings.mode_bars", MODE_WAVE: "settings.mode_wave"}

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
    """Spectrum drawn either as columns of coloured segments or as a wave line."""

    def __init__(
        self,
        visualizer: Visualizer,
        columns: int = DEFAULT_COLUMNS,
        segments: int = DEFAULT_SEGMENTS,
        mode: str = MODE_BARS,
    ) -> None:
        super().__init__()
        self._visualizer = visualizer
        self._columns = clamp(columns, MIN_COLUMNS, MAX_COLUMNS)
        self._segments = clamp(segments, MIN_SEGMENTS, MAX_SEGMENTS)
        self._colors = segment_colors(self._segments)
        self._mode = mode
        self._levels = [0.0] * self._columns
        self._samples: list[float] = []
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

    @property
    def mode(self) -> str:
        return self._mode

    def set_columns(self, columns: int) -> None:
        self._columns = clamp(columns, MIN_COLUMNS, MAX_COLUMNS)
        self._refresh()

    def set_segments(self, segments: int) -> None:
        self._segments = clamp(segments, MIN_SEGMENTS, MAX_SEGMENTS)
        self._colors = segment_colors(self._segments)
        self.update()

    def set_mode(self, mode: str) -> None:
        self._mode = mode
        self._refresh()

    def _refresh(self) -> None:
        # Only the data the current mode draws is read from the visualizer.
        if self._mode == MODE_WAVE:
            self._samples = self._visualizer.wave()
        else:
            self._levels = column_levels(self._visualizer.bands(), self._columns)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        if self._mode == MODE_WAVE:
            self._paint_wave(painter)
        else:
            self._paint_bars(painter)
        painter.end()

    def _paint_bars(self, painter: QPainter) -> None:
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

    def _paint_wave(self, painter: QPainter) -> None:
        samples = self._samples
        if len(samples) < 2:
            return
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        height = self.height()
        middle = height / 2
        step = self.width() / (len(samples) - 1)
        path = QPainterPath()
        for index, sample in enumerate(samples):
            point = QPointF(index * step, middle - clamp(sample, -1.0, 1.0) * middle)
            if index == 0:
                path.moveTo(point)
            else:
                path.lineTo(point)
        # Neon look: wide faint layers first, then the thin bright core on top.
        for width, alpha in WAVE_GLOW:
            self._stroke_wave(painter, path, width, alpha)
        self._stroke_wave(painter, path, WAVE_CORE_WIDTH, 255)

    def _stroke_wave(self, painter: QPainter, path: QPainterPath, width: float, alpha: int) -> None:
        # Same colours as the bars: the bottom stop is the first one, the top the last.
        gradient = QLinearGradient(0, self.height(), 0, 0)
        for index, rgb in enumerate(_GRADIENT):
            colour = QColor(*rgb)
            colour.setAlpha(alpha)
            gradient.setColorAt(index / (len(_GRADIENT) - 1), colour)
        pen = QPen(
            QBrush(gradient),
            width,
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
            Qt.PenJoinStyle.RoundJoin,
        )
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)


class SpectrumSettings(QWidget):
    """Inputs for the visualizer mode, the spectrum width (columns) and height (segments)."""

    mode_changed = Signal(str)

    def __init__(self, spectrum: SpectrumWidget) -> None:
        super().__init__()
        self.setObjectName("spectrumSettings")
        self._spectrum = spectrum

        self.mode = QComboBox()
        for mode in SPECTRUM_MODES:
            self.mode.addItem("", mode)
        self.mode.setCurrentIndex(self.mode.findData(spectrum.mode))
        self.mode.currentIndexChanged.connect(self._on_mode_chosen)

        self.columns = QSpinBox()
        self.columns.setRange(MIN_COLUMNS, MAX_COLUMNS)
        self.columns.setValue(spectrum.columns)
        self.columns.valueChanged.connect(spectrum.set_columns)

        self.segments = QSpinBox()
        self.segments.setRange(MIN_SEGMENTS, MAX_SEGMENTS)
        self.segments.setValue(spectrum.segments)
        self.segments.valueChanged.connect(spectrum.set_segments)

        self._mode_label = QLabel()
        self._columns_label = QLabel()
        self._segments_label = QLabel()

        form = QFormLayout(self)
        form.setContentsMargins(0, 0, 0, 0)
        form.setVerticalSpacing(6)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        form.addRow(self._mode_label, self.mode)
        form.addRow(self._columns_label, self.columns)
        form.addRow(self._segments_label, self.segments)

        translator.language_changed.connect(self.retranslate)
        self.retranslate()
        self._update_size_inputs(spectrum.mode)

    def retranslate(self) -> None:
        self._mode_label.setText(tr("settings.mode"))
        for index, mode in enumerate(SPECTRUM_MODES):
            self.mode.setItemText(index, tr(_MODE_LABEL_KEYS[mode]))
        self._columns_label.setText(tr("settings.columns"))
        self._segments_label.setText(tr("settings.segments"))

    def _on_mode_chosen(self, index: int) -> None:
        mode = self.mode.itemData(index)
        if mode is None:
            return
        self._spectrum.set_mode(mode)
        self._update_size_inputs(mode)
        self.mode_changed.emit(mode)

    def _update_size_inputs(self, mode: str) -> None:
        # The width and height only apply to bars, so they are greyed out for the wave.
        bars = mode == MODE_BARS
        for widget in (self._columns_label, self.columns, self._segments_label, self.segments):
            widget.setEnabled(bars)
