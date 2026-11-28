import pytest
from PySide6.QtCore import QSettings

from music_playa_gui.cover_style import COVER_DISC, COVER_FILL
from music_playa_gui.settings import AppSettings, _bool, _bounded_int
from music_playa_gui.widgets.spectrum import (
    BACKGROUND_BARS,
    BACKGROUND_NONE,
    BACKGROUND_WAVE,
    DEFAULT_COLUMNS,
    DEFAULT_SEGMENTS,
    MAX_COLUMNS,
    MAX_SEGMENTS,
    MIN_COLUMNS,
    MIN_SEGMENTS,
    MODE_BARS,
    MODE_WAVE,
)


def _raw() -> QSettings:
    return QSettings("music_playa", "music_playa_gui")


def test_defaults() -> None:
    settings = AppSettings()
    assert settings.language() == "pl"
    assert settings.spectrum_columns() == DEFAULT_COLUMNS
    assert settings.spectrum_segments() == DEFAULT_SEGMENTS


def test_values_are_saved() -> None:
    settings = AppSettings()
    settings.set_language("en")
    settings.set_spectrum_columns(64)
    settings.set_spectrum_segments(12)
    again = AppSettings()
    assert again.language() == "en"
    assert again.spectrum_columns() == 64
    assert again.spectrum_segments() == 12


def test_unknown_language_falls_back() -> None:
    _raw().setValue("language", "xx")
    assert AppSettings().language() == "pl"


def test_out_of_range_values_are_clamped() -> None:
    raw = _raw()
    raw.setValue("spectrum/columns", 1000)
    raw.setValue("spectrum/segments", 0)
    raw.sync()
    settings = AppSettings()
    assert settings.spectrum_columns() == MAX_COLUMNS
    assert settings.spectrum_segments() == MIN_SEGMENTS


def test_broken_values_fall_back_to_defaults() -> None:
    raw = _raw()
    raw.setValue("spectrum/columns", "many")
    raw.setValue("spectrum/segments", "")
    raw.sync()
    settings = AppSettings()
    assert settings.spectrum_columns() == DEFAULT_COLUMNS
    assert settings.spectrum_segments() == DEFAULT_SEGMENTS


def test_spectrum_mode_defaults_to_bars() -> None:
    assert AppSettings().spectrum_mode() == MODE_BARS


def test_spectrum_mode_is_saved() -> None:
    AppSettings().set_spectrum_mode(MODE_WAVE)
    assert AppSettings().spectrum_mode() == MODE_WAVE


def test_unknown_spectrum_mode_falls_back_to_bars() -> None:
    _raw().setValue("spectrum/mode", "sphere")
    assert AppSettings().spectrum_mode() == MODE_BARS


def test_bounded_int() -> None:
    assert _bounded_int("7", 3, 1, 10) == 7
    assert _bounded_int(None, 3, 1, 10) == 3
    assert _bounded_int("x", 3, 1, 10) == 3
    assert _bounded_int(0, 3, 1, 10) == 1
    assert _bounded_int(11, 3, 1, 10) == 10
    assert _bounded_int(MIN_COLUMNS, 3, MIN_COLUMNS, MAX_SEGMENTS) == MIN_COLUMNS


def test_cover_style_defaults_to_fill() -> None:
    assert AppSettings().cover_style() == COVER_FILL


def test_cover_style_is_saved() -> None:
    AppSettings().set_cover_style(COVER_DISC)
    assert AppSettings().cover_style() == COVER_DISC


def test_unknown_cover_style_falls_back_to_fill() -> None:
    _raw().setValue("cover/style", "cube")
    assert AppSettings().cover_style() == COVER_FILL


def test_spectrum_background_defaults_to_none() -> None:
    assert AppSettings().spectrum_background() == BACKGROUND_NONE


def test_spectrum_background_is_saved() -> None:
    AppSettings().set_spectrum_background(BACKGROUND_BARS)
    assert AppSettings().spectrum_background() == BACKGROUND_BARS
    AppSettings().set_spectrum_background(BACKGROUND_WAVE)
    assert AppSettings().spectrum_background() == BACKGROUND_WAVE


def test_unknown_spectrum_background_falls_back_to_none() -> None:
    _raw().setValue("spectrum/background", "rainbow")
    assert AppSettings().spectrum_background() == BACKGROUND_NONE


def test_bass_glow_is_on_by_default() -> None:
    assert AppSettings().bass_glow() is True


def test_bass_glow_is_saved() -> None:
    AppSettings().set_bass_glow(False)
    assert AppSettings().bass_glow() is False
    AppSettings().set_bass_glow(True)
    assert AppSettings().bass_glow() is True


@pytest.mark.parametrize(
    ("stored", "expected"),
    [("true", True), ("false", False), ("TRUE", True), ("False", False), ("1", True), ("0", False)],
)
def test_bass_glow_reads_the_text_forms(stored: str, expected: bool) -> None:
    _raw().setValue("effects/bass_glow", stored)
    assert AppSettings().bass_glow() is expected


def test_unknown_bass_glow_value_falls_back_to_the_default() -> None:
    _raw().setValue("effects/bass_glow", "maybe")
    assert AppSettings().bass_glow() is True


def test_bool_helper_reads_true_even_when_the_default_is_false() -> None:
    assert _bool("true", False) is True
    assert _bool("TRUE", False) is True
    assert _bool("1", False) is True
    assert _bool("false", True) is False
    assert _bool("0", True) is False


def test_bool_helper() -> None:
    assert _bool(True, False) is True
    assert _bool(False, True) is False
    assert _bool(None, True) is True
    assert _bool(None, False) is False
