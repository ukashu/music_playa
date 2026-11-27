from pathlib import Path

from music_playa.core.queue import PlayQueue
from music_playa.models import PlaybackMode, RepeatMode, Track


def _tracks(count: int = 2) -> list[Track]:
    return [Track(Path(f"{index}.mp3"), str(index)) for index in range(count)]


def test_next_and_previous_move_the_queue() -> None:
    tracks = _tracks()
    queue = PlayQueue(tracks)

    assert queue.next() == tracks[1]
    assert queue.previous() == tracks[0]
    assert queue.previous() == tracks[0]


def test_mode_is_remembered() -> None:
    queue = PlayQueue(_tracks())

    queue.mode = PlaybackMode.SHUFFLE

    assert queue.mode is PlaybackMode.SHUFFLE


def test_repeat_defaults_to_off_and_is_remembered() -> None:
    queue = PlayQueue(_tracks())
    assert queue.repeat is RepeatMode.OFF

    queue.repeat = RepeatMode.ONE

    assert queue.repeat is RepeatMode.ONE


def test_select_moves_to_requested_track() -> None:
    tracks = _tracks()
    queue = PlayQueue(tracks)

    assert queue.select(tracks[1]) == tracks[1]
    assert queue.current == tracks[1]


def test_repeat_off_stops_at_the_end_of_the_list() -> None:
    tracks = _tracks()
    queue = PlayQueue(tracks)
    queue.select(tracks[1])

    assert not queue.has_next()
    assert queue.previous() == tracks[0]
    assert queue.previous() == tracks[0]


def test_manual_next_on_last_track_wraps_to_first_with_repeat_off() -> None:
    tracks = _tracks()
    queue = PlayQueue(tracks)
    queue.select(tracks[1])

    assert queue.next() == tracks[0]


def test_repeat_all_wraps_next_and_previous() -> None:
    tracks = _tracks()
    queue = PlayQueue(tracks)
    queue.repeat = RepeatMode.ALL

    assert queue.next() == tracks[1]
    assert queue.next() == tracks[0]
    assert queue.previous() == tracks[1]


def test_repeat_all_has_next_even_with_one_track() -> None:
    queue = PlayQueue(_tracks(1))
    assert not queue.has_next()

    queue.repeat = RepeatMode.ALL

    assert queue.has_next()
    assert queue.next() == queue.current


def test_repeat_one_manual_navigation_does_not_stop_the_list() -> None:
    tracks = _tracks()
    queue = PlayQueue(tracks)
    queue.repeat = RepeatMode.ONE
    queue.select(tracks[1])

    assert not queue.has_next()
    assert queue.next() == tracks[0]
    assert queue.previous() == tracks[0]
    assert queue.previous() == tracks[0]


def test_shuffle_always_has_next_with_several_tracks() -> None:
    queue = PlayQueue(_tracks(3))
    queue.mode = PlaybackMode.SHUFFLE

    assert queue.has_next()


def test_shuffle_with_one_track_has_next_only_when_repeating() -> None:
    queue = PlayQueue(_tracks(1))
    queue.mode = PlaybackMode.SHUFFLE
    assert not queue.has_next()

    queue.repeat = RepeatMode.ALL

    assert queue.has_next()
