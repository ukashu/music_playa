"""Persistent GUI settings (language and spectrum size), stored with QSettings."""

from PySide6.QtCore import QSettings

from music_playa_gui.i18n import DEFAULT_LANGUAGE, LANGUAGES
from music_playa_gui.utils import clamp
from music_playa_gui.widgets.spectrum import (
    DEFAULT_COLUMNS,
    DEFAULT_SEGMENTS,
    MAX_COLUMNS,
    MAX_SEGMENTS,
    MIN_COLUMNS,
    MIN_SEGMENTS,
)


def _bounded_int(value: object, default: int, low: int, high: int) -> int:
    try:
        number = int(value)  # type: ignore[call-overload]
    except (TypeError, ValueError):
        return default
    return clamp(number, low, high)


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
