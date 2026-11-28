from base64 import b64encode
from pathlib import Path
from types import SimpleNamespace

import pytest
from mutagen import MutagenError
from mutagen.flac import Picture

from music_playa.models import Track
from music_playa.services import cover_art


def test_cover_art_returns_none_for_unsupported_or_missing_art(monkeypatch) -> None:
    track = Track(Path("track.unknown"), "Track")
    monkeypatch.setattr(cover_art, "File", lambda _path: None)
    assert cover_art.CoverArt().for_track(track) is None

    audio = SimpleNamespace(tags={})
    monkeypatch.setattr(cover_art, "File", lambda _path: audio)
    assert cover_art.CoverArt().for_track(track) is None


def test_cover_art_reads_id3_picture_data(monkeypatch) -> None:
    image = b"embedded image bytes"
    tags = SimpleNamespace(getall=lambda key: [SimpleNamespace(data=image)] if key == "APIC" else [])
    audio = SimpleNamespace(tags=tags, pictures=[])
    track = Track(Path("track.mp3"), "Track")
    monkeypatch.setattr(cover_art, "File", lambda _path: audio)

    assert cover_art.CoverArt().for_track(track) == image


def test_cover_art_ignores_invalid_vorbis_picture_block(monkeypatch) -> None:
    audio = SimpleNamespace(tags={"metadata_block_picture": ["not-base64"]}, pictures=[])
    track = Track(Path("track.ogg"), "Track")
    monkeypatch.setattr(cover_art, "File", lambda _path: audio)

    assert cover_art.CoverArt().for_track(track) is None


def test_cover_art_opens_the_track_file(monkeypatch) -> None:
    opened: list[Path] = []

    def fake_file(path):
        opened.append(path)
        return None

    monkeypatch.setattr(cover_art, "File", fake_file)

    cover_art.CoverArt().for_track(Track(Path("dir/track.mp3"), "Track"))

    assert opened == [Path("dir/track.mp3")]


def test_cover_art_returns_none_without_tags(monkeypatch) -> None:
    audio = SimpleNamespace(tags=None, pictures=[SimpleNamespace(data=b"unused")])
    monkeypatch.setattr(cover_art, "File", lambda _path: audio)

    assert cover_art.CoverArt().for_track(Track(Path("track.flac"), "Track")) is None


def test_cover_art_returns_none_for_a_file_without_a_tag_attribute(monkeypatch) -> None:
    monkeypatch.setattr(cover_art, "File", lambda _path: SimpleNamespace())

    assert cover_art.CoverArt().for_track(Track(Path("track.wav"), "Track")) is None


def test_cover_art_rejects_a_vorbis_block_with_stray_characters(monkeypatch) -> None:
    picture = Picture()
    picture.data = b"vorbis image"
    block = b64encode(picture.write()).decode("ascii") + "!"
    audio = SimpleNamespace(tags={"metadata_block_picture": [block]}, pictures=[])
    monkeypatch.setattr(cover_art, "File", lambda _path: audio)

    assert cover_art.CoverArt().for_track(Track(Path("track.ogg"), "Track")) is None


def test_cover_art_reads_the_first_flac_picture(monkeypatch) -> None:
    pictures = [SimpleNamespace(data=b"first"), SimpleNamespace(data=b"second")]
    audio = SimpleNamespace(tags={}, pictures=pictures)
    monkeypatch.setattr(cover_art, "File", lambda _path: audio)

    assert cover_art.CoverArt().for_track(Track(Path("track.flac"), "Track")) == b"first"


def test_cover_art_reads_the_first_id3_frame(monkeypatch) -> None:
    frames = [SimpleNamespace(data=b"first"), SimpleNamespace(data=b"second")]
    tags = SimpleNamespace(getall=lambda key: frames)
    audio = SimpleNamespace(tags=tags)
    monkeypatch.setattr(cover_art, "File", lambda _path: audio)

    assert cover_art.CoverArt().for_track(Track(Path("track.mp3"), "Track")) == b"first"


def test_cover_art_falls_through_when_id3_has_no_frames(monkeypatch) -> None:
    class Tags(dict):
        def getall(self, key: str) -> list[object]:
            assert key == "APIC"
            return []

    audio = SimpleNamespace(tags=Tags(), pictures=[])
    monkeypatch.setattr(cover_art, "File", lambda _path: audio)

    assert cover_art.CoverArt().for_track(Track(Path("track.mp3"), "Track")) is None


def test_cover_art_decodes_a_vorbis_picture_block(monkeypatch) -> None:
    picture = Picture()
    picture.data = b"vorbis image"
    block = b64encode(picture.write()).decode("ascii")
    audio = SimpleNamespace(tags={"metadata_block_picture": [block]}, pictures=[])
    monkeypatch.setattr(cover_art, "File", lambda _path: audio)

    assert cover_art.CoverArt().for_track(Track(Path("track.ogg"), "Track")) == b"vorbis image"


@pytest.mark.parametrize("error", [MutagenError("bad"), OSError("gone"), ValueError("odd")])
def test_cover_art_returns_none_when_the_file_cannot_be_read(monkeypatch, error) -> None:
    def broken(_path):
        raise error

    monkeypatch.setattr(cover_art, "File", broken)

    assert cover_art.CoverArt().for_track(Track(Path("track.mp3"), "Track")) is None
