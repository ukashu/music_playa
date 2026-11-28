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


def test_empty_queue_has_nothing_to_play() -> None:
    queue = PlayQueue([])

    assert queue.current is None
    assert queue.next() is None
    assert queue.previous() is None
    assert queue.rewind() is None
    assert not queue.has_next()
    assert queue.select(Track(Path("x.mp3"), "x")) is None


def test_queue_does_not_share_the_list_with_the_caller() -> None:
    tracks = _tracks()
    queue = PlayQueue(tracks)

    tracks.clear()

    assert queue.current == Track(Path("0.mp3"), "0")


def test_select_unknown_track_keeps_the_current_one() -> None:
    tracks = _tracks(3)
    queue = PlayQueue(tracks)
    queue.select(tracks[1])

    assert queue.select(Track(Path("other.mp3"), "other")) == tracks[1]
    assert queue.current == tracks[1]


def test_select_finds_an_equal_track() -> None:
    tracks = _tracks(3)
    queue = PlayQueue(tracks)

    assert queue.select(Track(Path("2.mp3"), "2")) is tracks[2]
    assert queue.current is tracks[2]


def test_rewind_returns_to_the_first_track() -> None:
    tracks = _tracks(3)
    queue = PlayQueue(tracks)
    queue.select(tracks[2])

    assert queue.rewind() == tracks[0]
    assert queue.current == tracks[0]


def test_in_order_has_next_until_the_last_track() -> None:
    tracks = _tracks(3)
    queue = PlayQueue(tracks)

    assert queue.has_next()
    queue.select(tracks[1])
    assert queue.has_next()
    queue.select(tracks[2])
    assert not queue.has_next()


def test_shuffle_picks_another_track(monkeypatch) -> None:
    tracks = _tracks(3)
    queue = PlayQueue(tracks)
    queue.mode = PlaybackMode.SHUFFLE
    queue.select(tracks[1])
    offered: list[list[int]] = []

    def choose(indices: list[int]) -> int:
        offered.append(list(indices))
        return indices[-1]

    monkeypatch.setattr("music_playa.core.queue.random.choice", choose)

    assert queue.next() == tracks[2]
    assert offered == [[0, 2]]
    assert queue.current == tracks[2]


def test_shuffle_has_next_with_at_least_two_tracks() -> None:
    queue = PlayQueue(_tracks(2))
    queue.mode = PlaybackMode.SHUFFLE
    assert queue.has_next()

    single = PlayQueue(_tracks(1))
    single.mode = PlaybackMode.SHUFFLE
    assert not single.has_next()


def test_next_moves_forward_one_track_and_wraps_at_the_end() -> None:
    tracks = _tracks(3)
    queue = PlayQueue(tracks)

    assert queue.next() == tracks[1]
    assert queue.next() == tracks[2]
    assert queue.next() == tracks[0]


def test_shuffle_with_one_track_stays_on_it() -> None:
    tracks = _tracks(1)
    queue = PlayQueue(tracks)
    queue.mode = PlaybackMode.SHUFFLE

    assert queue.next() == tracks[0]
    assert queue.current == tracks[0]


def test_previous_wraps_only_when_repeating_all() -> None:
    tracks = _tracks(3)
    queue = PlayQueue(tracks)
    queue.repeat = RepeatMode.ALL

    assert queue.previous() == tracks[2]
    queue.repeat = RepeatMode.OFF
    queue.select(tracks[0])
    assert queue.previous() == tracks[0]


def test_previous_steps_back_one_track() -> None:
    tracks = _tracks(3)
    queue = PlayQueue(tracks)
    queue.select(tracks[2])

    assert queue.previous() == tracks[1]
    assert queue.previous() == tracks[0]
