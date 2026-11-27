"""Minimal two-language (Polish / English) translation of the interface texts."""

from PySide6.QtCore import QObject, Signal

LANGUAGES = {"pl": "Polski", "en": "English"}
DEFAULT_LANGUAGE = "pl"

_TEXTS: dict[str, dict[str, str]] = {
    "settings.tooltip": {"pl": "Ustawienia", "en": "Settings"},
    "settings.title": {"pl": "Ustawienia", "en": "Settings"},
    "settings.spectrum": {"pl": "Spektrum", "en": "Spectrum"},
    "settings.columns": {"pl": "Szerokość (kolumny)", "en": "Width (columns)"},
    "settings.segments": {"pl": "Wysokość (segmenty)", "en": "Height (segments)"},
    "settings.language": {"pl": "Język", "en": "Language"},
    "library.title": {"pl": "Tytuł", "en": "Title"},
    "library.time": {"pl": "Czas", "en": "Time"},
    "player.no_track": {"pl": "Brak utworu", "en": "No track"},
    "player.mode": {"pl": "Tryb: {mode}", "en": "Mode: {mode}"},
    "mode.in_order": {"pl": "Po kolei", "en": "In order"},
    "mode.shuffle": {"pl": "Losowo", "en": "Shuffle"},
    "player.repeat": {"pl": "Powtarzanie: {state}", "en": "Repeat: {state}"},
    "repeat.off": {"pl": "Wyłączone", "en": "Off"},
    "repeat.all": {"pl": "Powtarzaj całą listę", "en": "Repeat all"},
    "repeat.one": {"pl": "Powtarzaj jeden utwór", "en": "Repeat one"},
    "volume.mute": {"pl": "Wycisz", "en": "Mute"},
    "volume.unmute": {"pl": "Włącz dźwięk", "en": "Unmute"},
}


class Translator(QObject):
    """Holds the current language and notifies widgets when it changes."""

    language_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._language = DEFAULT_LANGUAGE

    @property
    def language(self) -> str:
        return self._language

    def set_language(self, code: str) -> None:
        if code not in LANGUAGES or code == self._language:
            return
        self._language = code
        self.language_changed.emit()

    def tr(self, key: str, **values: str) -> str:
        text = _TEXTS[key][self._language]
        return text.format(**values) if values else text


translator = Translator()


def tr(key: str, **values: str) -> str:
    return translator.tr(key, **values)


def count_tracks(count: int) -> str:
    """"1 track" / "5 tracks" in English, "1 utwór" / "2 utwory" / "5 utworów" in Polish."""
    if translator.language == "en":
        return f"{count} {'track' if count == 1 else 'tracks'}"
    if count == 1:
        word = "utwór"
    elif count % 10 in (2, 3, 4) and count % 100 not in (12, 13, 14):
        word = "utwory"
    else:
        word = "utworów"
    return f"{count} {word}"
