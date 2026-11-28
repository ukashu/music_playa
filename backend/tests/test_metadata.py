from pathlib import Path
from types import SimpleNamespace

from music_playa.services import metadata
from music_playa.services.metadata import read


def test_read_takes_artist_from_the_tag_mapping(monkeypatch, tmp_path) -> None:
    class Tags(dict):
        info = SimpleNamespace(length=12.5)

    tags = Tags(title=["Song"], artist=["Narkopop"], album=["Album"], tracknumber=["3"])
    monkeypatch.setattr("music_playa.services.metadata.File", lambda path, easy=True: tags)

    result = read(tmp_path / "a.mp3")

    assert result["artist"] == "Narkopop"
    assert result["title"] == "Song"
    assert result["album"] == "Album"
    assert result["track_number"] == "3"
    assert result["duration"] == 12.5


def test_read_falls_back_when_the_file_has_no_tags(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("music_playa.services.metadata.File", lambda path, easy=True: None)

    result = read(tmp_path / "plain.mp3")

    assert result == {}


def test_read_opens_the_file_with_easy_tags(monkeypatch, tmp_path) -> None:
    calls: list[tuple[Path, bool]] = []

    def fake_file(path, easy):
        calls.append((path, easy))
        return None

    monkeypatch.setattr(metadata, "File", fake_file)

    read(tmp_path / "a.mp3")

    assert calls == [(tmp_path / "a.mp3", True)]


def test_read_returns_nothing_for_an_unreadable_file(monkeypatch, tmp_path) -> None:
    def broken(path, easy=True):
        raise ValueError("broken")

    monkeypatch.setattr(metadata, "File", broken)

    assert read(tmp_path / "a.mp3") == {}


def test_read_uses_defaults_for_missing_values(monkeypatch, tmp_path) -> None:
    tags = {"title": [], "artist": []}
    monkeypatch.setattr(metadata, "File", lambda path, easy=True: tags)

    result = read(tmp_path / "Some Song.mp3")

    assert result == {
        "title": "Some Song",
        "artist": "Unknown Artist",
        "album": "Unknown Album",
        "track_number": "",
        "duration": 0.0,
    }


def test_read_uses_the_first_value_as_text(monkeypatch, tmp_path) -> None:
    tags = {"title": ["First", "Second"], "tracknumber": [7]}
    monkeypatch.setattr(metadata, "File", lambda path, easy=True: tags)

    result = read(tmp_path / "a.mp3")

    assert result["title"] == "First"
    assert result["track_number"] == "7"


def test_read_supports_tags_exposed_as_attributes(monkeypatch, tmp_path) -> None:
    tags = SimpleNamespace(artist=["Band"], info=SimpleNamespace(length=3))
    monkeypatch.setattr(metadata, "File", lambda path, easy=True: tags)

    result = read(tmp_path / "a.mp3")

    assert result["artist"] == "Band"
    assert result["title"] == "a"
    assert result["duration"] == 3.0
    assert isinstance(result["duration"], float)
