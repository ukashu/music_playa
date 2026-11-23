from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class PlaybackState(Enum):
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"


class PlaybackMode(Enum):
    IN_ORDER = "in_order"
    SHUFFLE = "shuffle"
    REPEAT = "repeat"


@dataclass(frozen=True)
class Track:
    path: Path
    title: str
    artist: str = "Unknown Artist"
    album: str = "Unknown Album"
    duration: float = 0.0
    track_number: str = ""
