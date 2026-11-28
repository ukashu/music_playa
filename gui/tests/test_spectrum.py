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
    MODE_BARS,
    MODE_WAVE,
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


class _RecordingVisualizer(FakeVisualizer):
    """Remembers which of the two readings the widget asked for."""

    def __init__(self) -> None:
        super().__init__([0.5] * 8)
        self.calls: list[str] = []

    def bands(self) -> list[float]:
        self.calls.append("bands")
        return super().bands()

    def wave(self) -> list[float]:
        self.calls.append("wave")
        return [0.5, -0.5, 1.0]


def test_wave_mode_reads_only_the_wave() -> None:
    visualizer = _RecordingVisualizer()
    spectrum = SpectrumWidget(visualizer, mode=MODE_WAVE)
    visualizer.calls.clear()
    spectrum._refresh()
    assert visualizer.calls == ["wave"]
    assert spectrum._samples == [0.5, -0.5, 1.0]


def test_bars_mode_reads_only_the_bands() -> None:
    visualizer = _RecordingVisualizer()
    spectrum = SpectrumWidget(visualizer, columns=4, mode=MODE_BARS)
    visualizer.calls.clear()
    spectrum._refresh()
    assert visualizer.calls == ["bands"]
    assert spectrum._levels == [0.5] * 4


def test_set_mode_switches_the_data() -> None:
    spectrum = SpectrumWidget(_RecordingVisualizer(), columns=4)
    assert spectrum.mode == MODE_BARS
    spectrum.set_mode(MODE_WAVE)
    assert spectrum.mode == MODE_WAVE
    assert spectrum._samples == [0.5, -0.5, 1.0]
    spectrum.set_mode(MODE_BARS)
    assert spectrum._levels == [0.5] * 4


def test_set_columns_in_wave_mode_reads_the_wave() -> None:
    visualizer = _RecordingVisualizer()
    spectrum = SpectrumWidget(visualizer, mode=MODE_WAVE)
    visualizer.calls.clear()
    spectrum.set_columns(8)
    assert visualizer.calls == ["wave"]
    assert spectrum.columns == 8


def _painted(image, x: int, y: int) -> bool:
    """Whether a pixel differs from the empty background, which is read at a corner the line never reaches."""
    return image.pixelColor(x, y) != image.pixelColor(79, 150)


def test_wave_is_a_line_at_the_height_of_each_sample() -> None:
    spectrum = SpectrumWidget(FakeVisualizer(), mode=MODE_WAVE)
    spectrum.resize(80, 160)
    spectrum._samples = [1.0] * 64  # the highest point: the top edge of the view
    image = spectrum.grab().toImage()
    assert _painted(image, 40, 1)
    assert not _painted(image, 40, 80)


def test_flat_wave_is_drawn_in_the_middle() -> None:
    spectrum = SpectrumWidget(FakeVisualizer(), mode=MODE_WAVE)
    spectrum.resize(80, 160)
    spectrum._samples = [0.0] * 64
    image = spectrum.grab().toImage()
    assert _painted(image, 40, 80)
    assert not _painted(image, 40, 5)


def test_wave_without_samples_draws_nothing() -> None:
    spectrum = SpectrumWidget(FakeVisualizer(), mode=MODE_WAVE)
    spectrum.resize(80, 160)
    spectrum._samples = [0.0]
    image = spectrum.grab().toImage()
    assert not _painted(image, 40, 80)


def test_mode_combo_switches_the_widget_and_emits() -> None:
    spectrum = SpectrumWidget(FakeVisualizer())
    settings = SpectrumSettings(spectrum)
    chosen: list[str] = []
    settings.mode_changed.connect(chosen.append)
    assert settings.mode.currentData() == MODE_BARS
    settings.mode.setCurrentIndex(settings.mode.findData(MODE_WAVE))
    assert spectrum.mode == MODE_WAVE
    assert chosen == [MODE_WAVE]


def test_clearing_the_mode_combo_changes_nothing() -> None:
    spectrum = SpectrumWidget(FakeVisualizer(), mode=MODE_WAVE)
    settings = SpectrumSettings(spectrum)
    chosen: list[str] = []
    settings.mode_changed.connect(chosen.append)
    settings.mode.clear()
    assert spectrum.mode == MODE_WAVE
    assert chosen == []


def test_size_inputs_are_only_enabled_for_bars() -> None:
    spectrum = SpectrumWidget(FakeVisualizer(), mode=MODE_WAVE)
    settings = SpectrumSettings(spectrum)
    assert not settings.columns.isEnabled()
    assert not settings.segments.isEnabled()
    assert not settings._columns_label.isEnabled()
    settings.mode.setCurrentIndex(settings.mode.findData(MODE_BARS))
    assert settings.columns.isEnabled()
    assert settings.segments.isEnabled()
    assert settings._segments_label.isEnabled()


def test_mode_labels_are_translated() -> None:
    settings = SpectrumSettings(SpectrumWidget(FakeVisualizer()))
    assert settings._mode_label.text() == "Tryb"
    assert [settings.mode.itemText(index) for index in range(2)] == ["Słupki", "Fala"]
    translator.set_language("en")
    assert settings._mode_label.text() == "Mode"
    assert [settings.mode.itemText(index) for index in range(2)] == ["Bars", "Wave"]


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
