from types import SimpleNamespace

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
