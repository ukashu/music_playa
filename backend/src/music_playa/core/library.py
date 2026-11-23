from pathlib import Path

from music_playa.models import Track
from music_playa.services.cover_art import CoverArt
from music_playa.services.metadata import read
from music_playa.services.scanner import scan


class FileLibrary:
    def __init__(self, music_dir: Path) -> None:
        self._covers = CoverArt()
        self._tracks: list[Track] = []

        for path in scan(music_dir):
            metadata = read(path)
            self._tracks.append(
                Track(
                    path=path,
                    title=str(metadata.get("title", path.stem)),
                    artist=str(metadata.get("artist", "Unknown Artist")),
                    album=str(metadata.get("album", "Unknown Album")),
                    duration=float(metadata.get("duration", 0.0)),
                    track_number=str(metadata.get("track_number", "")),
                )
            )

    @property
    def tracks(self) -> list[Track]:
        return list(self._tracks)

    def cover(self, track: Track) -> bytes | None:
        return self._covers.for_track(track)
