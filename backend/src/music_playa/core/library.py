from pathlib import Path

from music_playa.models import Track
from music_playa.services.cover_art import CoverArt
from music_playa.services.scanner import scan


class FileLibrary:
    def __init__(self, music_dir: Path) -> None:
        self._covers = CoverArt()
        self._tracks = [Track(path=path, title=path.stem) for path in scan(music_dir)]

    @property
    def tracks(self) -> list[Track]:
        return list(self._tracks)

    def cover(self, track: Track) -> bytes | None:
        return self._covers.for_track(track)
