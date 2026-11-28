import pytest
from conftest import FakeVisualizer
from PySide6.QtGui import QColor

from music_playa_gui.i18n import translator
from music_playa_gui.theme import CYAN, PINK, VIOLET
from music_playa_gui.widgets.spectrum import (
    BACKGROUND_ALPHA,
    BACKGROUND_BARS,
    BACKGROUND_FALLOFF,
    BACKGROUND_MODES,
    BACKGROUND_NONE,
    BACKGROUND_WAVE,
    DEFAULT_COLUMNS,
    MAX_COLUMNS,
    MAX_SEGMENTS,
    MIN_COLUMNS,
    MIN_SEGMENTS,
    MODE_BARS,
    MODE_NONE,
    MODE_WAVE,
    SPECTRUM_MODES,
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


def _rgb(colour: QColor) -> tuple[int, int, int]:
    return colour.getRgb()[:3]


@pytest.mark.parametrize(
    ("mode", "background", "expected"),
    [
        (MODE_BARS, BACKGROUND_NONE, ["bands"]),
        (MODE_WAVE, BACKGROUND_NONE, ["wave"]),
        (MODE_NONE, BACKGROUND_NONE, []),
        (MODE_NONE, BACKGROUND_BARS, ["bands"]),
        (MODE_NONE, BACKGROUND_WAVE, ["wave"]),
        (MODE_BARS, BACKGROUND_BARS, ["bands"]),
        (MODE_WAVE, BACKGROUND_WAVE, ["wave"]),
        (MODE_BARS, BACKGROUND_WAVE, ["bands", "wave"]),
        (MODE_WAVE, BACKGROUND_BARS, ["bands", "wave"]),
    ],
)
def test_only_the_data_that_is_used_is_read(mode: str, background: str, expected: list[str]) -> None:
    visualizer = _RecordingVisualizer()
    spectrum = SpectrumWidget(visualizer, columns=4, mode=mode, background=background)
    visualizer.calls.clear()
    spectrum._refresh()
    assert sorted(visualizer.calls) == expected


def test_none_mode_draws_nothing() -> None:
    spectrum = SpectrumWidget(FakeVisualizer([1.0] * 8), columns=4, segments=4, mode=MODE_NONE)
    spectrum.resize(80, 160)
    spectrum._levels = [1.0] * 4
    spectrum._samples = [1.0] * 64
    image = spectrum.grab().toImage()
    assert not _painted(image, 10, 150 - 5)
    assert not _painted(image, 40, 1)
    assert not _painted(image, 40, 80)


def test_modes_and_backgrounds_are_listed() -> None:
    assert SPECTRUM_MODES == (MODE_BARS, MODE_WAVE, MODE_NONE)
    assert BACKGROUND_MODES == (BACKGROUND_NONE, BACKGROUND_BARS, BACKGROUND_WAVE)


def test_background_defaults_to_none_and_ignores_unknown_values() -> None:
    assert SpectrumWidget(FakeVisualizer()).background == BACKGROUND_NONE
    assert SpectrumWidget(FakeVisualizer(), background="rainbow").background == BACKGROUND_NONE
    spectrum = SpectrumWidget(FakeVisualizer(), background=BACKGROUND_BARS)
    spectrum.set_background("rainbow")
    assert spectrum.background == BACKGROUND_BARS


def test_set_background_reads_the_data_it_needs_at_once() -> None:
    visualizer = _RecordingVisualizer()
    spectrum = SpectrumWidget(visualizer, columns=4, mode=MODE_NONE)
    visualizer.calls.clear()
    spectrum.set_background(BACKGROUND_WAVE)
    assert spectrum.background == BACKGROUND_WAVE
    assert visualizer.calls == ["wave"]
    assert spectrum.background_stops()
    spectrum.set_background(BACKGROUND_NONE)
    assert spectrum.background_stops() == []


def test_refreshed_is_emitted_for_every_refresh() -> None:
    spectrum = SpectrumWidget(FakeVisualizer([0.5] * 8), columns=4, mode=MODE_NONE)
    emitted: list[int] = []
    spectrum.refreshed.connect(lambda: emitted.append(1))
    spectrum._refresh()
    spectrum.set_columns(8)
    spectrum.set_mode(MODE_BARS)
    spectrum.set_background(BACKGROUND_WAVE)
    assert len(emitted) == 4


def test_bar_stops_use_the_colour_of_the_top_lit_segment() -> None:
    spectrum = SpectrumWidget(
        FakeVisualizer([1.0, 0.5, 0.0, 0.25]), columns=4, segments=4, background=BACKGROUND_BARS
    )
    spectrum._refresh()
    colors = segment_colors(4)

    stops = spectrum.background_stops()

    assert [position for position, _ in stops] == pytest.approx([0.125, 0.375, 0.625, 0.875])
    # The empty column takes the colour of its neighbours and fades a little.
    assert [_rgb(colour) for _, colour in stops] == [_rgb(colors[3]), _rgb(colors[1]), _rgb(colors[1]), _rgb(colors[0])]
    assert [colour.alpha() for _, colour in stops] == [BACKGROUND_ALPHA, BACKGROUND_ALPHA, _faded(1), BACKGROUND_ALPHA]


def _faded(distance: int) -> int:
    return round(BACKGROUND_ALPHA * BACKGROUND_FALLOFF**distance)


def _bar_stops(levels: list[float], segments: int = 4) -> list[tuple[float, QColor]]:
    spectrum = SpectrumWidget(
        FakeVisualizer(levels), columns=len(levels), segments=segments, background=BACKGROUND_BARS
    )
    spectrum._refresh()
    return spectrum.background_stops()


def test_a_single_missing_bar_stays_almost_opaque() -> None:
    # A fully transparent stop would show as a vertical ray between the two neighbours.
    alphas = [colour.alpha() for _, colour in _bar_stops([1.0, 1.0, 0.0, 1.0, 1.0])]
    assert alphas == [BACKGROUND_ALPHA, BACKGROUND_ALPHA, _faded(1), BACKGROUND_ALPHA, BACKGROUND_ALPHA]
    assert alphas[2] > BACKGROUND_ALPHA * 0.7


def test_empty_columns_fade_out_with_the_distance_from_the_bars() -> None:
    from_left = _bar_stops([1.0, 0.0, 0.0, 0.0])
    assert [colour.alpha() for _, colour in from_left] == [BACKGROUND_ALPHA, _faded(1), _faded(2), _faded(3)]
    # They keep the colour of the bar instead of shifting towards the bottom colour.
    assert {_rgb(colour) for _, colour in from_left} == {_rgb(QColor(PINK))}

    from_right = _bar_stops([0.0, 0.0, 0.0, 1.0])
    assert [colour.alpha() for _, colour in from_right] == [_faded(3), _faded(2), _faded(1), BACKGROUND_ALPHA]
    assert {_rgb(colour) for _, colour in from_right} == {_rgb(QColor(PINK))}


def test_empty_columns_follow_the_nearest_bar() -> None:
    colors = segment_colors(4)
    stops = _bar_stops([1.0, 0.0, 0.0, 0.0, 0.25])
    assert [colour.alpha() for _, colour in stops] == [
        BACKGROUND_ALPHA,
        _faded(1),
        _faded(2),
        _faded(1),
        BACKGROUND_ALPHA,
    ]
    assert _rgb(stops[1][1]) == _rgb(colors[3])
    assert _rgb(stops[3][1]) == _rgb(colors[0])


def test_without_any_bar_the_background_is_transparent() -> None:
    stops = _bar_stops([0.0, 0.0, 0.0, 0.0])
    assert {colour.alpha() for _, colour in stops} == {0}
    assert {_rgb(colour) for _, colour in stops} == {_rgb(segment_colors(4)[0])}


@pytest.mark.parametrize("segments", [2, 4, 8, 32])
def test_a_full_bar_has_the_top_colour_whatever_the_height(segments: int) -> None:
    spectrum = SpectrumWidget(FakeVisualizer([1.0] * 4), columns=4, segments=segments, background=BACKGROUND_BARS)
    spectrum._refresh()
    assert {_rgb(colour) for _, colour in spectrum.background_stops()} == {_rgb(QColor(PINK))}


def test_bar_stop_colour_follows_the_number_of_lit_segments() -> None:
    # 0.4 of 8 segments is 3.2, so 3 are lit and the third colour is used; of 4 segments it is 2.
    for segments, lit in ((8, 3), (4, 2)):
        spectrum = SpectrumWidget(FakeVisualizer([0.4] * 4), columns=4, segments=segments, background=BACKGROUND_BARS)
        spectrum._refresh()
        colour = spectrum.background_stops()[0][1]
        assert _rgb(colour) == _rgb(segment_colors(segments)[lit - 1])


def test_levels_above_one_do_not_go_beyond_the_top_colour() -> None:
    spectrum = SpectrumWidget(FakeVisualizer([5.0] * 4), columns=4, segments=4, background=BACKGROUND_BARS)
    spectrum._refresh()
    assert _rgb(spectrum.background_stops()[0][1]) == _rgb(QColor(PINK))


def test_wave_stops_use_the_colour_the_line_has_at_each_height() -> None:
    spectrum = SpectrumWidget(FakeVisualizer(), mode=MODE_NONE, background=BACKGROUND_WAVE)
    spectrum._samples = [-1.0, 0.0, 1.0, 5.0, -5.0]

    stops = spectrum.background_stops()

    assert [position for position, _ in stops] == pytest.approx([0.0, 0.25, 0.5, 0.75, 1.0])
    assert [_rgb(colour) for _, colour in stops] == [
        _rgb(QColor(CYAN)),
        _rgb(QColor(VIOLET)),
        _rgb(QColor(PINK)),
        _rgb(QColor(PINK)),
        _rgb(QColor(CYAN)),
    ]
    assert {colour.alpha() for _, colour in stops} == {BACKGROUND_ALPHA}


def test_wave_stops_follow_the_visualizer() -> None:
    spectrum = SpectrumWidget(_RecordingVisualizer(), mode=MODE_NONE, background=BACKGROUND_WAVE)
    spectrum._refresh()
    # The samples of _RecordingVisualizer are 0.5, -0.5 and 1.0.
    assert [_rgb(colour) for _, colour in spectrum.background_stops()] == [
        _rgb(_gradient_color(0.75)),
        _rgb(_gradient_color(0.25)),
        _rgb(_gradient_color(1.0)),
    ]


@pytest.mark.parametrize("samples", [[], [0.0]])
def test_wave_without_enough_samples_has_no_stops(samples: list[float]) -> None:
    spectrum = SpectrumWidget(FakeVisualizer(), background=BACKGROUND_WAVE)
    spectrum._samples = samples
    assert spectrum.background_stops() == []


def test_stops_follow_the_background_and_not_the_displayed_mode() -> None:
    spectrum = SpectrumWidget(_RecordingVisualizer(), columns=4, segments=4, mode=MODE_WAVE, background=BACKGROUND_BARS)
    spectrum._refresh()
    assert len(spectrum.background_stops()) == 4
    spectrum.set_background(BACKGROUND_WAVE)
    assert len(spectrum.background_stops()) == 3
    spectrum.set_background(BACKGROUND_NONE)
    assert spectrum.background_stops() == []


def test_background_combo_switches_the_widget_and_emits() -> None:
    spectrum = SpectrumWidget(FakeVisualizer())
    settings = SpectrumSettings(spectrum)
    chosen: list[str] = []
    settings.background_changed.connect(chosen.append)
    assert settings.background.currentData() == BACKGROUND_NONE
    assert [settings.background.itemData(i) for i in range(settings.background.count())] == list(BACKGROUND_MODES)
    settings.background.setCurrentIndex(settings.background.findData(BACKGROUND_WAVE))
    assert spectrum.background == BACKGROUND_WAVE
    assert chosen == [BACKGROUND_WAVE]


def test_background_combo_starts_on_the_background_of_the_widget() -> None:
    settings = SpectrumSettings(SpectrumWidget(FakeVisualizer(), background=BACKGROUND_BARS))
    assert settings.background.currentData() == BACKGROUND_BARS


def test_clearing_the_background_combo_changes_nothing() -> None:
    spectrum = SpectrumWidget(FakeVisualizer(), background=BACKGROUND_BARS)
    settings = SpectrumSettings(spectrum)
    chosen: list[str] = []
    settings.background_changed.connect(chosen.append)
    settings.background.clear()
    assert spectrum.background == BACKGROUND_BARS
    assert chosen == []


@pytest.mark.parametrize(
    ("mode", "background", "enabled"),
    [
        (MODE_BARS, BACKGROUND_NONE, True),
        (MODE_WAVE, BACKGROUND_NONE, False),
        (MODE_NONE, BACKGROUND_NONE, False),
        (MODE_BARS, BACKGROUND_WAVE, True),
        (MODE_WAVE, BACKGROUND_BARS, True),
        (MODE_NONE, BACKGROUND_BARS, True),
        (MODE_NONE, BACKGROUND_WAVE, False),
    ],
)
def test_size_inputs_are_enabled_when_bars_or_colours_from_bars_use_them(
    mode: str, background: str, enabled: bool
) -> None:
    settings = SpectrumSettings(SpectrumWidget(FakeVisualizer(), mode=mode, background=background))
    for widget in (settings.columns, settings.segments, settings._columns_label, settings._segments_label):
        assert widget.isEnabled() is enabled


def test_size_inputs_follow_the_combos() -> None:
    spectrum = SpectrumWidget(FakeVisualizer(), mode=MODE_NONE)
    settings = SpectrumSettings(spectrum)
    assert not settings.columns.isEnabled()
    settings.background.setCurrentIndex(settings.background.findData(BACKGROUND_BARS))
    assert settings.columns.isEnabled() and settings.segments.isEnabled()
    settings.background.setCurrentIndex(settings.background.findData(BACKGROUND_NONE))
    assert not settings.columns.isEnabled()
    settings.mode.setCurrentIndex(settings.mode.findData(MODE_BARS))
    assert settings.columns.isEnabled()
    settings.mode.setCurrentIndex(settings.mode.findData(MODE_NONE))
    assert not settings.segments.isEnabled()


def test_none_and_background_labels_are_translated() -> None:
    settings = SpectrumSettings(SpectrumWidget(FakeVisualizer()))
    assert [settings.mode.itemText(i) for i in range(3)] == ["Słupki", "Fala", "Brak"]
    assert settings._background_label.text() == "Kolorowanie tła"
    assert [settings.background.itemText(i) for i in range(3)] == ["Brak", "Według słupków", "Według fali"]
    translator.set_language("en")
    assert [settings.mode.itemText(i) for i in range(3)] == ["Bars", "Wave", "None"]
    assert settings._background_label.text() == "Background colour"
    assert [settings.background.itemText(i) for i in range(3)] == ["None", "From bars", "From wave"]


def test_settings_form_lists_the_rows_in_order() -> None:
    settings = SpectrumSettings(SpectrumWidget(FakeVisualizer()))
    form = settings.layout()
    rows = [
        (settings._mode_label, settings.mode),
        (settings._background_label, settings.background),
        (settings._columns_label, settings.columns),
        (settings._segments_label, settings.segments),
    ]
    for row, (label, field) in enumerate(rows):
        assert form.getWidgetPosition(label) == (row, form.ItemRole.LabelRole)
        assert form.getWidgetPosition(field) == (row, form.ItemRole.FieldRole)


class _Ticks:
    """A clock that moves by one frame each time it is read."""

    def __init__(self, step: float = 0.033) -> None:
        self.now = 100.0
        self.step = step

    def __call__(self) -> float:
        self.now += self.step
        return self.now


def _bass_spectrum(bands: list[float], bass_glow: bool = True, mode: str = MODE_NONE) -> SpectrumWidget:
    spectrum = SpectrumWidget(FakeVisualizer(bands), columns=4, mode=mode, bass_glow=bass_glow)
    spectrum._clock = _Ticks()
    spectrum._last_tick = spectrum._clock()
    return spectrum


def test_bass_glow_is_off_by_default() -> None:
    assert SpectrumWidget(FakeVisualizer()).bass_glow is False
    assert SpectrumWidget(FakeVisualizer(), bass_glow=True).bass_glow is True


def test_bass_glow_alone_makes_the_widget_read_the_bands() -> None:
    visualizer = _RecordingVisualizer()
    spectrum = SpectrumWidget(visualizer, columns=4, mode=MODE_NONE, bass_glow=True)
    visualizer.calls.clear()
    spectrum._refresh()
    assert visualizer.calls == ["bands"]


def test_bass_is_not_measured_when_the_glow_is_off() -> None:
    spectrum = _bass_spectrum([0.9] * 256, bass_glow=False, mode=MODE_BARS)
    levels: list[float] = []
    spectrum.bass_changed.connect(levels.append)
    spectrum._refresh()
    spectrum._refresh()
    assert levels == []
    assert spectrum.bass_level == 0.0


def test_a_bass_hit_is_announced_in_steps_and_only_when_it_changes() -> None:
    spectrum = _bass_spectrum([0.9] * 256)
    levels: list[float] = []
    spectrum.bass_changed.connect(levels.append)

    for _ in range(40):
        spectrum._refresh()

    assert levels[0] > 0.0
    assert levels[-1] == spectrum.bass_level
    assert len(levels) == len(set(levels))  # no repeated value
    assert all(round(level * 12) == pytest.approx(level * 12) for level in levels)
    # A steady bass stops glowing again.
    for _ in range(400):
        spectrum._refresh()
    assert spectrum.bass_level == 0.0
    assert levels[-1] == 0.0


def test_the_bass_glow_uses_the_time_between_refreshes() -> None:
    slow = _bass_spectrum([0.9] * 256)
    slow._clock = _Ticks(step=1.0)
    slow._last_tick = slow._clock()
    fast = _bass_spectrum([0.9] * 256)
    slow._refresh()
    fast._refresh()
    assert slow.bass_level > fast.bass_level


def test_turning_the_bass_glow_off_resets_the_elements_once() -> None:
    spectrum = _bass_spectrum([0.9] * 256)
    spectrum._refresh()
    assert spectrum.bass_level > 0.0
    levels: list[float] = []
    spectrum.bass_changed.connect(levels.append)

    spectrum.set_bass_glow(False)
    spectrum.set_bass_glow(False)

    assert spectrum.bass_glow is False
    assert levels == [0.0]
    assert spectrum.bass_level == 0.0
    spectrum._refresh()
    assert levels == [0.0]


def test_turning_the_bass_glow_on_again_starts_from_scratch() -> None:
    spectrum = _bass_spectrum([0.9] * 256)
    for _ in range(300):
        spectrum._refresh()
    spectrum.set_bass_glow(False)
    spectrum.set_bass_glow(True)
    spectrum._refresh()
    assert spectrum.bass_level > 0.0


def test_bass_level_is_zero_without_music() -> None:
    spectrum = _bass_spectrum([0.0] * 256)
    for _ in range(10):
        spectrum._refresh()
    assert spectrum.bass_level == 0.0
