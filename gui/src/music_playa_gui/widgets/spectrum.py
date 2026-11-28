import time

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QComboBox, QFormLayout, QLabel, QSpinBox, QWidget

from music_playa.interfaces import Visualizer
from music_playa_gui.bass import BassMeter, quantized
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
# Bars show the band levels; the wave draws the raw samples as one line; none draws nothing.
MODE_BARS = "bars"
MODE_WAVE = "wave"
MODE_NONE = "none"
SPECTRUM_MODES = (MODE_BARS, MODE_WAVE, MODE_NONE)
# The background colouring follows the bars (the colour of the top lit segment of each column)
# or the wave (the colour of the line at each point), whatever the spectrum itself shows.
BACKGROUND_NONE = "none"
BACKGROUND_BARS = "bars"
BACKGROUND_WAVE = "wave"
BACKGROUND_MODES = (BACKGROUND_NONE, BACKGROUND_BARS, BACKGROUND_WAVE)
BACKGROUND_ALPHA = 150  # translucent, so the cover or the plain background still shows through
# A column with nothing lit gets the alpha of its neighbours times this per column of distance, so
# a single missing bar stays almost opaque and only a wide empty area fades out.
BACKGROUND_FALLOFF = 0.75
# (width, alpha) of the glow layers under the wave, widest first, and the width of the core.
WAVE_GLOW = ((10.0, 35), (5.0, 80))
WAVE_CORE_WIDTH = 2.0
_MODE_LABEL_KEYS = {
    MODE_BARS: "settings.mode_bars",
    MODE_WAVE: "settings.mode_wave",
    MODE_NONE: "settings.mode_none",
}
_BACKGROUND_LABEL_KEYS = {
    BACKGROUND_NONE: "settings.background_none",
    BACKGROUND_BARS: "settings.background_bars",
    BACKGROUND_WAVE: "settings.background_wave",
}

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
    """Spectrum drawn as columns of coloured segments, as a wave line, or not at all.

    It also supplies the colours for the background colouring (background_stops), which
    NowPlayingView paints behind it. refreshed is emitted after every data refresh.

    With bass_glow on, the same bands also feed a BassMeter, and bass_changed is emitted with the
    glow level (0..1, in steps) whenever it changes, for the elements that glow with the bass.
    """

    refreshed = Signal()
    bass_changed = Signal(float)

    def __init__(
        self,
        visualizer: Visualizer,
        columns: int = DEFAULT_COLUMNS,
        segments: int = DEFAULT_SEGMENTS,
        mode: str = MODE_BARS,
        background: str = BACKGROUND_NONE,
        bass_glow: bool = False,
    ) -> None:
        super().__init__()
        self._visualizer = visualizer
        self._columns = clamp(columns, MIN_COLUMNS, MAX_COLUMNS)
        self._segments = clamp(segments, MIN_SEGMENTS, MAX_SEGMENTS)
        self._colors = segment_colors(self._segments)
        self._mode = mode
        self._background = background if background in BACKGROUND_MODES else BACKGROUND_NONE
        self._levels = [0.0] * self._columns
        self._samples: list[float] = []
        self._bass_glow = bass_glow
        self._bass_meter = BassMeter()
        self._bass_level = 0.0
        self._clock = time.monotonic
        self._last_tick = self._clock()
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

    @property
    def background(self) -> str:
        return self._background

    @property
    def bass_glow(self) -> bool:
        return self._bass_glow

    @property
    def bass_level(self) -> float:
        """The glow level last announced by bass_changed."""
        return self._bass_level

    def set_bass_glow(self, enabled: bool) -> None:
        self._bass_glow = enabled
        if not enabled:
            # The elements go back to their resting look, and start from scratch next time.
            self._bass_meter.reset()
            self._set_bass_level(0.0)

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

    def set_background(self, background: str) -> None:
        if background not in BACKGROUND_MODES:
            return
        self._background = background
        self._refresh()

    def background_stops(self) -> list[tuple[float, QColor]]:
        """Colour stops (position 0..1 across the width, colour) for the background colouring.

        Empty when the colouring is off or there is no data to follow.
        """
        if self._background == BACKGROUND_BARS:
            return self._bar_stops()
        if self._background == BACKGROUND_WAVE:
            return self._wave_stops()
        return []

    def _bar_stops(self) -> list[tuple[float, QColor]]:
        """One stop at the middle of each column, in the colour of its top lit segment.

        A column with nothing lit is transparent, but it takes the colour and a faded alpha from
        the nearest lit columns (see BACKGROUND_FALLOFF). Without that, one missing bar would
        show as a transparent vertical ray between its neighbours.
        """
        lit = [self._lit_segments(level) for level in self._levels]
        colors = [QColor(self._colors[max(count - 1, 0)]) for count in lit]
        alphas = [float(BACKGROUND_ALPHA) if count else 0.0 for count in lit]
        columns = len(lit)
        # Spread from the left and then from the right, so each column keeps the strongest
        # (nearest) source and its colour.
        for order, step in ((range(1, columns), -1), (range(columns - 2, -1, -1), 1)):
            for column in order:
                faded = alphas[column + step] * BACKGROUND_FALLOFF
                if faded > alphas[column]:
                    alphas[column] = faded
                    colors[column] = QColor(colors[column + step])
        stops = []
        for column, (color, alpha) in enumerate(zip(colors, alphas)):
            color.setAlpha(round(alpha))
            stops.append(((column + 0.5) / columns, color))
        return stops

    def _wave_stops(self) -> list[tuple[float, QColor]]:
        """One stop per sample, in the colour the wave line has at the height of that sample."""
        samples = self._samples
        if len(samples) < 2:
            return []
        stops = []
        for index, sample in enumerate(samples):
            color = _gradient_color((sample + 1.0) / 2.0)
            color.setAlpha(BACKGROUND_ALPHA)
            stops.append((index / (len(samples) - 1), color))
        return stops

    def _lit_segments(self, level: float) -> int:
        return round(clamp(level, 0.0, 1.0) * self._segments)

    def _needs_bands(self) -> bool:
        return self._mode == MODE_BARS or self._background == BACKGROUND_BARS or self._bass_glow

    def _needs_wave(self) -> bool:
        return self._mode == MODE_WAVE or self._background == BACKGROUND_WAVE

    def _refresh(self) -> None:
        # Only the data that is drawn, used for the colouring or for the bass is read.
        if self._needs_wave():
            self._samples = self._visualizer.wave()
        if self._needs_bands():
            bands = self._visualizer.bands()
            self._levels = column_levels(bands, self._columns)
            self._update_bass(bands)
        self.update()
        self.refreshed.emit()

    def _update_bass(self, bands: list[float]) -> None:
        now = self._clock()
        elapsed = now - self._last_tick
        self._last_tick = now
        if self._bass_glow:
            self._set_bass_level(quantized(self._bass_meter.update(bands, elapsed)))

    def _set_bass_level(self, level: float) -> None:
        if level != self._bass_level:
            self._bass_level = level
            self.bass_changed.emit(level)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        if self._mode == MODE_WAVE:
            self._paint_wave(painter)
        elif self._mode == MODE_BARS:
            self._paint_bars(painter)
        painter.end()

    def _paint_bars(self, painter: QPainter) -> None:
        columns = len(self._levels)
        segments = self._segments
        column_width = self.width() / columns
        segment_height = self.height() / segments
        gap = min(4.0, column_width * 0.25, segment_height * 0.25)
        for column, level in enumerate(self._levels):
            lit = self._lit_segments(level)
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
    """Inputs for the visualizer mode, the background colouring, and the spectrum size.

    The size is the width (columns) and the height (segments).
    """

    mode_changed = Signal(str)
    background_changed = Signal(str)

    def __init__(self, spectrum: SpectrumWidget) -> None:
        super().__init__()
        self.setObjectName("spectrumSettings")
        self._spectrum = spectrum

        self.mode = QComboBox()
        for mode in SPECTRUM_MODES:
            self.mode.addItem("", mode)
        self.mode.setCurrentIndex(self.mode.findData(spectrum.mode))
        self.mode.currentIndexChanged.connect(self._on_mode_chosen)

        self.background = QComboBox()
        for background in BACKGROUND_MODES:
            self.background.addItem("", background)
        self.background.setCurrentIndex(self.background.findData(spectrum.background))
        self.background.currentIndexChanged.connect(self._on_background_chosen)

        self.columns = QSpinBox()
        self.columns.setRange(MIN_COLUMNS, MAX_COLUMNS)
        self.columns.setValue(spectrum.columns)
        self.columns.valueChanged.connect(spectrum.set_columns)

        self.segments = QSpinBox()
        self.segments.setRange(MIN_SEGMENTS, MAX_SEGMENTS)
        self.segments.setValue(spectrum.segments)
        self.segments.valueChanged.connect(spectrum.set_segments)

        self._mode_label = QLabel()
        self._background_label = QLabel()
        self._columns_label = QLabel()
        self._segments_label = QLabel()

        form = QFormLayout(self)
        form.setContentsMargins(0, 0, 0, 0)
        form.setVerticalSpacing(6)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        form.addRow(self._mode_label, self.mode)
        form.addRow(self._background_label, self.background)
        form.addRow(self._columns_label, self.columns)
        form.addRow(self._segments_label, self.segments)

        translator.language_changed.connect(self.retranslate)
        self.retranslate()
        self._update_size_inputs()

    def retranslate(self) -> None:
        self._mode_label.setText(tr("settings.mode"))
        for index, mode in enumerate(SPECTRUM_MODES):
            self.mode.setItemText(index, tr(_MODE_LABEL_KEYS[mode]))
        self._background_label.setText(tr("settings.background"))
        for index, background in enumerate(BACKGROUND_MODES):
            self.background.setItemText(index, tr(_BACKGROUND_LABEL_KEYS[background]))
        self._columns_label.setText(tr("settings.columns"))
        self._segments_label.setText(tr("settings.segments"))

    def _on_mode_chosen(self, index: int) -> None:
        mode = self.mode.itemData(index)
        if mode is None:
            return
        self._spectrum.set_mode(mode)
        self._update_size_inputs()
        self.mode_changed.emit(mode)

    def _on_background_chosen(self, index: int) -> None:
        background = self.background.itemData(index)
        if background is None:
            return
        self._spectrum.set_background(background)
        self._update_size_inputs()
        self.background_changed.emit(background)

    def _update_size_inputs(self) -> None:
        # The width and height shape the bars and the colours taken from them, so they are
        # greyed out unless the spectrum shows bars or the background follows the bars.
        bars = self._spectrum.mode == MODE_BARS or self._spectrum.background == BACKGROUND_BARS
        for widget in (self._columns_label, self.columns, self._segments_label, self.segments):
            widget.setEnabled(bars)
