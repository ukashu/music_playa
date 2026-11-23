from pathlib import Path
from types import SimpleNamespace

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
