from pathlib import Path

from music_playa.core import library
from music_playa.core.library import FileLibrary
from music_playa.models import Track


def test_library_builds_tracks_from_the_metadata(monkeypatch, tmp_path: Path) -> None:
    song = tmp_path / "song.mp3"
    song.write_bytes(b"x")
    metadata = {
        "title": "Title",
        "artist": "Artist",
        "album": "Album",
        "duration": 61.5,
        "track_number": "3/12",
    }
    read_paths: list[Path] = []

    def fake_read(path: Path) -> dict[str, object]:
        read_paths.append(path)
        return metadata

    monkeypatch.setattr(library, "read", fake_read)

    assert FileLibrary(tmp_path).tracks == [
        Track(song, "Title", "Artist", "Album", 61.5, "3/12")
    ]
    assert read_paths == [song]


def test_library_falls_back_to_defaults_without_metadata(monkeypatch, tmp_path: Path) -> None:
    song = tmp_path / "plain song.mp3"
    song.write_bytes(b"x")
    monkeypatch.setattr(library, "read", lambda path: {})

    assert FileLibrary(tmp_path).tracks == [
        Track(song, "plain song", "Unknown Artist", "Unknown Album", 0.0, "")
    ]


def test_library_lists_the_tracks_in_scan_order(monkeypatch, tmp_path: Path) -> None:
    for name in ("b.mp3", "a.mp3"):
        (tmp_path / name).write_bytes(b"x")
    monkeypatch.setattr(library, "read", lambda path: {})

    assert [track.title for track in FileLibrary(tmp_path).tracks] == ["a", "b"]


def test_library_of_an_empty_directory_has_no_tracks(tmp_path: Path) -> None:
    assert FileLibrary(tmp_path).tracks == []


def test_library_returns_a_copy_of_the_tracks(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "a.mp3").write_bytes(b"x")
    monkeypatch.setattr(library, "read", lambda path: {})
    files = FileLibrary(tmp_path)

    files.tracks.clear()

    assert len(files.tracks) == 1


def test_library_asks_the_cover_service_for_the_cover(monkeypatch, tmp_path: Path) -> None:
    requested: list[Track] = []

    class Covers:
        def for_track(self, track: Track) -> bytes:
            requested.append(track)
            return b"cover"

    monkeypatch.setattr(library, "CoverArt", Covers)
    files = FileLibrary(tmp_path)
    track = Track(Path("a.mp3"), "a")

    assert files.cover(track) == b"cover"
    assert requested == [track]
