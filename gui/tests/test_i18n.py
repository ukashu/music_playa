import pytest

from music_playa_gui.i18n import _TEXTS, DEFAULT_LANGUAGE, LANGUAGES, Translator, count_tracks, tr, translator


def test_default_language() -> None:
    assert Translator().language == DEFAULT_LANGUAGE == "pl"


def test_change_language_emits_once() -> None:
    local = Translator()
    calls = []
    local.language_changed.connect(lambda: calls.append(local.language))
    local.set_language("en")
    local.set_language("en")
    assert local.language == "en"
    assert calls == ["en"]


def test_unknown_language_is_ignored() -> None:
    local = Translator()
    calls = []
    local.language_changed.connect(lambda: calls.append(True))
    local.set_language("de")
    assert local.language == DEFAULT_LANGUAGE
    assert calls == []


def test_tr_follows_language() -> None:
    assert tr("player.no_track") == "Brak utworu"
    translator.set_language("en")
    assert tr("player.no_track") == "No track"


def test_tr_without_required_values_fails() -> None:
    with pytest.raises(KeyError):
        tr("player.mode")


def test_tr_formats_values() -> None:
    assert tr("player.mode", mode="Losowo") == "Tryb: Losowo"
    translator.set_language("en")
    assert tr("player.repeat", state="Off") == "Repeat: Off"


def test_every_text_has_every_language() -> None:
    for key, texts in _TEXTS.items():
        assert set(texts) == set(LANGUAGES), key


@pytest.mark.parametrize(
    ("count", "text"),
    [
        (0, "0 utworów"),
        (1, "1 utwór"),
        (2, "2 utwory"),
        (3, "3 utwory"),
        (4, "4 utwory"),
        (5, "5 utworów"),
        (11, "11 utworów"),
        (12, "12 utworów"),
        (13, "13 utworów"),
        (14, "14 utworów"),
        (22, "22 utwory"),
        (23, "23 utwory"),
        (25, "25 utworów"),
        (112, "112 utworów"),
        (122, "122 utwory"),
    ],
)
def test_count_tracks_polish(count: int, text: str) -> None:
    assert count_tracks(count) == text


@pytest.mark.parametrize(("count", "text"), [(0, "0 tracks"), (1, "1 track"), (2, "2 tracks"), (21, "21 tracks")])
def test_count_tracks_english(count: int, text: str) -> None:
    translator.set_language("en")
    assert count_tracks(count) == text
