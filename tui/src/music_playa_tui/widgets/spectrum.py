from rich.text import Text
from textual.containers import Horizontal
from textual.widgets import Input, Label, Static

from music_playa.interfaces import Visualizer

COLUMNS = 32
ROWS = 8
MIN_COLUMNS = 4
MAX_COLUMNS = 128
MIN_ROWS = 2
MAX_ROWS = 24
FRAME_SECONDS = 1 / 20
COLUMN_WIDTH = 2
GAP = 0

# Colour stops, bottom to top: green, yellow, orange.
_GRADIENT = [
    (63, 207, 52),
    (228, 228, 30),
    (230, 90, 15),
]
_UNLIT_COLOR = "#1a1a1a"


def clamp(value: int, low: int, high: int) -> int:
    return min(max(value, low), high)


def clamp_float(value: float) -> float:
    return min(max(value, 0.0), 1.0)


def row_color(row: int, rows: int) -> str:
    """Hex colour of a row (0 is the bottom), interpolated between the gradient stops."""
    position = row / (rows - 1) if rows > 1 else 0.0
    scaled = clamp_float(position) * (len(_GRADIENT) - 1)
    index = min(int(scaled), len(_GRADIENT) - 2)
    fraction = scaled - index
    start, end = _GRADIENT[index], _GRADIENT[index + 1]
    red, green, blue = (round(a + (b - a) * fraction) for a, b in zip(start, end))
    return f"#{red:02x}{green:02x}{blue:02x}"


def columns_for_width(width: int, max_columns: int = COLUMNS) -> int:
    """Number of columns that fit in the given width, capped at max_columns."""
    if width <= 0:
        return max_columns
    return max(1, min(max_columns, width // (COLUMN_WIDTH + GAP)))


def column_levels(bands: list[float], columns: int = COLUMNS) -> list[float]:
    """Average the visualizer bands into a fixed number of display columns."""
    if not bands:
        return [0.0] * columns
    size = len(bands) / columns
    levels = []
    for column in range(columns):
        chunk = bands[int(column * size) : max(int((column + 1) * size), int(column * size) + 1)]
        levels.append(sum(chunk) / len(chunk))
    return levels


def render_spectrum(levels: list[float], rows: int = ROWS) -> Text:
    """Build the bar spectrum, one row of blocks per line, top row first."""
    lit = [round(clamp_float(level) * rows) for level in levels]
    colors = [row_color(row, rows) for row in range(rows)]
    text = Text(no_wrap=True)
    for row in range(rows - 1, -1, -1):
        for count in lit:
            color = colors[row] if row < count else _UNLIT_COLOR
            text.append("█" * COLUMN_WIDTH, style=color)
            text.append(" " * GAP)
        if row > 0:
            text.append("\n")
    return text


class Spectrum(Static):
    """Bar spectrum drawn with coloured block characters.

    The number of columns follows the widget width, up to max_columns. The widget
    height is the number of rows.
    """

    def __init__(
        self,
        visualizer: Visualizer,
        max_columns: int = COLUMNS,
        rows: int = ROWS,
        **kwargs: object,
    ) -> None:
        self._max_columns = clamp(max_columns, MIN_COLUMNS, MAX_COLUMNS)
        self._rows = clamp(rows, MIN_ROWS, MAX_ROWS)
        super().__init__(render_spectrum([0.0] * self._max_columns, self._rows), **kwargs)
        self._visualizer = visualizer
        self.styles.height = self._rows

    @property
    def max_columns(self) -> int:
        return self._max_columns

    @property
    def rows(self) -> int:
        return self._rows

    def set_max_columns(self, columns: int) -> None:
        self._max_columns = clamp(columns, MIN_COLUMNS, MAX_COLUMNS)
        self._refresh_bars()

    def set_rows(self, rows: int) -> None:
        self._rows = clamp(rows, MIN_ROWS, MAX_ROWS)
        self.styles.height = self._rows
        self._refresh_bars()

    def on_mount(self) -> None:
        self.set_interval(FRAME_SECONDS, self._refresh_bars)

    def _refresh_bars(self) -> None:
        columns = columns_for_width(self.size.width, self._max_columns)
        levels = column_levels(self._visualizer.bands(), columns)
        self.update(render_spectrum(levels, self._rows))


class SpectrumSettings(Horizontal):
    """Inputs for the spectrum width (columns) and height (rows)."""

    def __init__(self, spectrum: Spectrum, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._spectrum = spectrum

    def compose(self):
        yield Label("Width")
        yield Input(
            str(self._spectrum.max_columns),
            type="integer",
            max_length=3,
            compact=True,
            id="spectrum-columns",
        )
        yield Label("Height")
        yield Input(
            str(self._spectrum.rows),
            type="integer",
            max_length=2,
            compact=True,
            id="spectrum-rows",
        )

    def on_input_changed(self, event: Input.Changed) -> None:
        event.stop()
        if not event.value.isdigit():
            return
        number = int(event.value)
        if event.input.id == "spectrum-columns":
            self._spectrum.set_max_columns(number)
        elif event.input.id == "spectrum-rows":
            self._spectrum.set_rows(number)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.stop()
        if event.input.id == "spectrum-columns":
            event.input.value = str(self._spectrum.max_columns)
        elif event.input.id == "spectrum-rows":
            event.input.value = str(self._spectrum.rows)
