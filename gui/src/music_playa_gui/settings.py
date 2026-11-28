"""Persistent GUI settings, stored with QSettings.

They are the language, the spectrum mode, size and background colouring, the cover style and
whether the elements glow with the bass.
"""

from PySide6.QtCore import QSettings

from music_playa_gui.cover_style import COVER_STYLES, DEFAULT_COVER_STYLE
from music_playa_gui.i18n import DEFAULT_LANGUAGE, LANGUAGES
from music_playa_gui.utils import clamp
from music_playa_gui.widgets.spectrum import (
    BACKGROUND_MODES,
    BACKGROUND_NONE,
    DEFAULT_COLUMNS,
    DEFAULT_SEGMENTS,
    MAX_COLUMNS,
    MAX_SEGMENTS,
    MIN_COLUMNS,
    MIN_SEGMENTS,
    MODE_BARS,
    SPECTRUM_MODES,
)


DEFAULT_BASS_GLOW = True


def _bounded_int(value: object, default: int, low: int, high: int) -> int:
    try:
        number = int(value)  # type: ignore[call-overload]
    except (TypeError, ValueError):
        return default
    return clamp(number, low, high)


def _bool(value: object, default: bool) -> bool:
    """A stored flag; QSettings may hand it back as a bool or as the text "true" or "false"."""
    if isinstance(value, bool):
        return value
    text = str(value).lower()
    if text in ("true", "1"):
        return True
    if text in ("false", "0"):
        return False
    return default


class AppSettings:
    def __init__(self) -> None:
        self._store = QSettings("music_playa", "music_playa_gui")

    def language(self) -> str:
        value = str(self._store.value("language"))
        return value if value in LANGUAGES else DEFAULT_LANGUAGE

    def set_language(self, code: str) -> None:
        self._store.setValue("language", code)

    def spectrum_columns(self) -> int:
        value = self._store.value("spectrum/columns")
        return _bounded_int(value, DEFAULT_COLUMNS, MIN_COLUMNS, MAX_COLUMNS)

    def set_spectrum_columns(self, columns: int) -> None:
        self._store.setValue("spectrum/columns", columns)

    def spectrum_segments(self) -> int:
        value = self._store.value("spectrum/segments")
        return _bounded_int(value, DEFAULT_SEGMENTS, MIN_SEGMENTS, MAX_SEGMENTS)

    def set_spectrum_segments(self, segments: int) -> None:
        self._store.setValue("spectrum/segments", segments)

    def spectrum_mode(self) -> str:
        value = self._store.value("spectrum/mode")
        return value if value in SPECTRUM_MODES else MODE_BARS

    def set_spectrum_mode(self, mode: str) -> None:
        self._store.setValue("spectrum/mode", mode)

    def spectrum_background(self) -> str:
        value = self._store.value("spectrum/background")
        return value if value in BACKGROUND_MODES else BACKGROUND_NONE

    def set_spectrum_background(self, background: str) -> None:
        self._store.setValue("spectrum/background", background)

    def cover_style(self) -> str:
        value = self._store.value("cover/style")
        return value if value in COVER_STYLES else DEFAULT_COVER_STYLE

    def set_cover_style(self, style: str) -> None:
        self._store.setValue("cover/style", style)

    def bass_glow(self) -> bool:
        return _bool(self._store.value("effects/bass_glow"), DEFAULT_BASS_GLOW)

    def set_bass_glow(self, enabled: bool) -> None:
        self._store.setValue("effects/bass_glow", enabled)
