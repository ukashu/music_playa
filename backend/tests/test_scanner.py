from pathlib import Path

from music_playa.services.scanner import scan


def test_scan_finds_mp3_in_subdirectory(tmp_path: Path) -> None:
    album = tmp_path / "album"
    album.mkdir()
    song = album / "song.mp3"
    song.write_bytes(b"not-audio")
    (tmp_path / "notes.txt").write_text("ignore")

    assert scan(tmp_path) == [song]
