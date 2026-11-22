import asyncio
from pathlib import Path

import music_playa_tui
from music_playa_tui.widgets.spectrum import (
    COLUMN_WIDTH,
    COLUMNS,
    GAP,
    MAX_COLUMNS,
    MAX_ROWS,
    MIN_COLUMNS,
    MIN_ROWS,
    ROWS,
    Spectrum,
    SpectrumSettings,
    column_levels,
    columns_for_width,
    render_spectrum,
    row_color,
)
from textual.app import App


class _Visualizer:
    def bands(self) -> list[float]:
        return [0.5] * 256

    def wave(self) -> list[float]:
        return [0.0] * 256


class _SpectrumApp(App[None]):
    CSS_PATH = str(Path(music_playa_tui.__file__).parent / "app.tcss")

    def compose(self):
        spectrum = Spectrum(_Visualizer(), id="spectrum")
        yield SpectrumSettings(spectrum, id="spectrum-settings")
        yield spectrum


def test_columns_for_width_caps_at_columns() -> None:
    assert columns_for_width(200) == COLUMNS
    assert columns_for_width(78) == COLUMNS


def test_columns_for_width_shrinks_with_narrow_widget() -> None:
    assert columns_for_width(40) == 40 // (COLUMN_WIDTH + GAP)
    assert columns_for_width(10) == 5


def test_columns_for_width_never_below_one() -> None:
    assert columns_for_width(1) == 1


def test_columns_for_width_unknown_size_uses_default() -> None:
    assert columns_for_width(0) == COLUMNS


def test_column_levels_produces_requested_column_count() -> None:
    assert len(column_levels([0.25] * 256, COLUMNS)) == COLUMNS
    assert len(column_levels([0.25] * 256, 10)) == 10
    assert column_levels([], 4) == [0.0] * 4


def test_render_spectrum_line_width_matches_columns() -> None:
    levels = [0.5] * COLUMNS
    text = render_spectrum(levels)
    lines = text.plain.split("\n")
    assert len(lines) == ROWS
    assert all(len(line) == COLUMNS * (COLUMN_WIDTH + GAP) for line in lines)


def test_render_spectrum_full_bars_fill_every_row() -> None:
    text = render_spectrum([1.0] * COLUMNS)
    assert text.plain.count("█") == COLUMNS * COLUMN_WIDTH * ROWS


def test_spectrum_widget_width_follows_terminal() -> None:
    async def run(width: int) -> int:
        app = _SpectrumApp()
        async with app.run_test(size=(width, 30)) as pilot:
            await pilot.pause()
            return app.query_one(Spectrum).size.width

    for terminal_width, expected_columns in [(80, 32), (100, 32), (120, 32)]:
        widget_width = asyncio.run(run(terminal_width))
        assert widget_width > 0
        assert columns_for_width(widget_width) == min(COLUMNS, widget_width // 2)
        assert columns_for_width(widget_width) <= expected_columns
    narrow = asyncio.run(run(30))
    assert columns_for_width(narrow) == narrow // (COLUMN_WIDTH + GAP)


def test_columns_for_width_respects_custom_maximum() -> None:
    assert columns_for_width(200, 10) == 10
    assert columns_for_width(8, 10) == 8 // (COLUMN_WIDTH + GAP)


def test_render_spectrum_uses_requested_row_count() -> None:
    for rows in (2, 8, 16, 24):
        text = render_spectrum([1.0] * 6, rows)
        lines = text.plain.split("\n")
        assert len(lines) == rows
        assert text.plain.count("█") == 6 * COLUMN_WIDTH * rows


def test_row_color_goes_from_green_to_orange() -> None:
    assert row_color(0, 8) == "#3fcf34"
    assert row_color(7, 8) == "#e65a0f"
    assert len({row_color(row, 16) for row in range(16)}) == 16


def test_spectrum_clamps_columns_and_rows() -> None:
    spectrum = Spectrum(_Visualizer(), max_columns=1000, rows=1000)
    assert spectrum.max_columns == MAX_COLUMNS
    assert spectrum.rows == MAX_ROWS
    spectrum = Spectrum(_Visualizer(), max_columns=0, rows=0)
    assert spectrum.max_columns == MIN_COLUMNS
    assert spectrum.rows == MIN_ROWS


def test_inputs_change_spectrum_width_and_height() -> None:
    async def run() -> tuple[int, int, int, int, str]:
        app = _SpectrumApp()
        async with app.run_test(size=(100, 40)) as pilot:
            await pilot.pause()
            spectrum = app.query_one(Spectrum)
            app.query_one("#spectrum-columns").value = "12"
            app.query_one("#spectrum-rows").value = "14"
            await pilot.pause()
            columns, rows, height = spectrum.max_columns, spectrum.rows, spectrum.size.height
            app.query_one("#spectrum-columns").value = "1000"
            await pilot.pause()
            capped = spectrum.max_columns
            app.query_one("#spectrum-columns").focus()
            await pilot.press("enter")
            await pilot.pause()
            return columns, rows, height, capped, app.query_one("#spectrum-columns").value

    columns, rows, height, capped, shown = asyncio.run(run())
    assert columns == 12
    assert rows == 14
    assert height == 14
    assert capped == MAX_COLUMNS
    assert shown == str(MAX_COLUMNS)


def test_non_numeric_input_is_ignored() -> None:
    async def run() -> int:
        app = _SpectrumApp()
        async with app.run_test(size=(100, 40)) as pilot:
            await pilot.pause()
            app.query_one("#spectrum-columns").value = ""
            await pilot.pause()
            return app.query_one(Spectrum).max_columns

    assert asyncio.run(run()) == COLUMNS
