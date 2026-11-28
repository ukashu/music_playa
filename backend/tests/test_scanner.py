from pathlib import Path

from music_playa.services.scanner import scan


def test_scan_finds_mp3_in_subdirectory(tmp_path: Path) -> None:
    album = tmp_path / "album"
    album.mkdir()
    song = album / "song.mp3"
    song.write_bytes(b"not-audio")
    (tmp_path / "notes.txt").write_text("ignore")

    assert scan(tmp_path) == [song]


def test_scan_of_a_missing_directory_is_empty(tmp_path: Path) -> None:
    assert scan(tmp_path / "missing") == []


def test_scan_of_a_file_is_empty(tmp_path: Path) -> None:
    song = tmp_path / "song.mp3"
    song.write_bytes(b"x")

    assert scan(song) == []


def test_scan_accepts_every_supported_extension_in_any_case(tmp_path: Path) -> None:
    names = ["a.wav", "b.OGG", "c.Mp3", "d.flac", "e.FLAC"]
    for name in names:
        (tmp_path / name).write_bytes(b"x")
    for name in ["f.m4a", "g.txt", "h.mp3.bak", "mp3"]:
        (tmp_path / name).write_bytes(b"x")

    assert [path.name for path in scan(tmp_path)] == sorted(names)


def test_scan_ignores_directories_named_like_audio(tmp_path: Path) -> None:
    (tmp_path / "folder.mp3").mkdir()
    song = tmp_path / "real.mp3"
    song.write_bytes(b"x")

    assert scan(tmp_path) == [song]


def test_scan_returns_sorted_paths_from_nested_directories(tmp_path: Path) -> None:
    deep = tmp_path / "b" / "c"
    deep.mkdir(parents=True)
    (tmp_path / "a").mkdir()
    paths = [deep / "z.mp3", tmp_path / "a" / "m.mp3", tmp_path / "top.mp3"]
    for path in paths:
        path.write_bytes(b"x")

    assert scan(tmp_path) == sorted(paths)
