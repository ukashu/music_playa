import pytest
from conftest import FakeVisualizer
from PySide6.QtGui import QColor

from music_playa_gui.i18n import translator
from music_playa_gui.theme import CYAN, PINK, VIOLET
from music_playa_gui.widgets.spectrum import (
    DEFAULT_COLUMNS,
    MAX_COLUMNS,
    MAX_SEGMENTS,
    MIN_COLUMNS,
    MIN_SEGMENTS,
    SpectrumSettings,
    SpectrumWidget,
    _gradient_color,
    column_levels,
    segment_colors,
)


def test_gradient_ends_and_middle() -> None:
    assert _gradient_color(0.0) == QColor(CYAN)
    assert _gradient_color(0.5) == QColor(VIOLET)
    assert _gradient_color(1.0) == QColor(PINK)


def test_gradient_is_clamped() -> None:
    assert _gradient_color(-1.0) == QColor(CYAN)
    assert _gradient_color(2.0) == QColor(PINK)


def test_gradient_interpolates() -> None:
    quarter = _gradient_color(0.25)
    cyan, violet = QColor(CYAN), QColor(VIOLET)
    assert quarter.red() == round((cyan.red() + violet.red()) / 2)
    assert quarter.green() == round((cyan.green() + violet.green()) / 2)
    assert quarter.blue() == round((cyan.blue() + violet.blue()) / 2)


def test_segment_colors() -> None:
    colors = segment_colors(5)
    assert len(colors) == 5
    assert colors[0] == QColor(CYAN)
    assert colors[2] == QColor(VIOLET)
    assert colors[-1] == QColor(PINK)


def test_single_segment_is_the_bottom_colour() -> None:
    assert segment_colors(1) == [QColor(CYAN)]


def test_column_levels_empty_bands() -> None:
    assert column_levels([], 4) == [0.0] * 4
    assert column_levels([]) == [0.0] * DEFAULT_COLUMNS


def test_column_levels_averages() -> None:
    assert column_levels([0.0, 1.0, 0.5, 0.5], 2) == [0.5, 0.5]
    assert column_levels([1.0, 1.0, 0.0, 0.0, 0.2, 0.4], 3) == pytest.approx([1.0, 0.0, 0.3])


def test_column_levels_more_columns_than_bands() -> None:
    assert column_levels([0.2, 0.8], 4) == [0.2, 0.2, 0.8, 0.8]


def test_widget_clamps_sizes() -> None:
    spectrum = SpectrumWidget(FakeVisualizer(), columns=1, segments=1000)
    assert spectrum.columns == MIN_COLUMNS
    assert spectrum.segments == MAX_SEGMENTS
    spectrum.set_columns(10_000)
    spectrum.set_segments(-3)
    assert spectrum.columns == MAX_COLUMNS
    assert spectrum.segments == MIN_SEGMENTS


def test_widget_reads_the_visualizer() -> None:
    visualizer = FakeVisualizer([1.0] * 8)
    spectrum = SpectrumWidget(visualizer, columns=4, segments=4)
    assert spectrum._levels == [0.0] * 4
    spectrum._refresh()
    assert spectrum._levels == [1.0] * 4
    spectrum.set_columns(8)
    assert spectrum._levels == [1.0] * 8
    spectrum.set_segments(6)
    assert len(spectrum._colors) == 6


def test_widget_paints_lit_segments() -> None:
    spectrum = SpectrumWidget(FakeVisualizer([1.0] * 4), columns=4, segments=4)
    spectrum.resize(80, 80)
    spectrum._refresh()
    image = spectrum.grab().toImage()
    # Full bars: the bottom segment is cyan and the top one pink.
    assert image.pixelColor(10, 75).blue() > 200
    assert image.pixelColor(10, 5).red() > 200


def test_settings_spin_boxes_drive_the_widget() -> None:
    spectrum = SpectrumWidget(FakeVisualizer(), columns=16, segments=6)
    settings = SpectrumSettings(spectrum)
    assert settings.columns.value() == 16
    assert settings.segments.value() == 6
    assert (settings.columns.minimum(), settings.columns.maximum()) == (MIN_COLUMNS, MAX_COLUMNS)
    assert (settings.segments.minimum(), settings.segments.maximum()) == (MIN_SEGMENTS, MAX_SEGMENTS)
    settings.columns.setValue(40)
    settings.segments.setValue(10)
    assert spectrum.columns == 40
    assert spectrum.segments == 10


def test_settings_labels() -> None:
    settings = SpectrumSettings(SpectrumWidget(FakeVisualizer()))
    form = settings.layout()
    assert form.labelForField(settings.columns) is settings._columns_label
    assert form.labelForField(settings.segments) is settings._segments_label
    assert settings._columns_label.text() == "Szerokość (kolumny)"
    assert settings._segments_label.text() == "Wysokość (segmenty)"
    translator.set_language("en")
    assert settings._columns_label.text() == "Width (columns)"
    assert settings._segments_label.text() == "Height (segments)"
