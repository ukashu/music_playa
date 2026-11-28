from PySide6.QtCore import QSettings

from music_playa_gui.settings import AppSettings, _bounded_int
from music_playa_gui.widgets.spectrum import (
    DEFAULT_COLUMNS,
    DEFAULT_SEGMENTS,
    MAX_COLUMNS,
    MAX_SEGMENTS,
    MIN_COLUMNS,
    MIN_SEGMENTS,
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


def test_bounded_int() -> None:
    assert _bounded_int("7", 3, 1, 10) == 7
    assert _bounded_int(None, 3, 1, 10) == 3
    assert _bounded_int("x", 3, 1, 10) == 3
    assert _bounded_int(0, 3, 1, 10) == 1
    assert _bounded_int(11, 3, 1, 10) == 10
    assert _bounded_int(MIN_COLUMNS, 3, MIN_COLUMNS, MAX_SEGMENTS) == MIN_COLUMNS
