from pathlib import Path

from music_playa.core.queue import PlayQueue
from music_playa.models import PlaybackMode, Track


def _tracks() -> list[Track]:
    return [Track(Path("a.mp3"), "a"), Track(Path("b.mp3"), "b")]


def test_next_and_previous_move_the_queue() -> None:
    tracks = _tracks()
    queue = PlayQueue(tracks)

    assert queue.next() == tracks[1]
    assert queue.next() == tracks[1]
    assert queue.previous() == tracks[0]


def test_mode_is_remembered() -> None:
    queue = PlayQueue(_tracks())

    queue.mode = PlaybackMode.REPEAT

    assert queue.mode is PlaybackMode.REPEAT
