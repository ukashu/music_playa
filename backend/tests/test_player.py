from pathlib import Path

from music_playa import create_app
from music_playa.models import Track


class _Recorder:
    def __init__(self) -> None:
        self.tracks: list[Track | None] = []

    def on_progress(self, position: float, duration: float) -> None:
        return None

    def on_track(self, track: Track | None) -> None:
        self.tracks.append(track)


def test_next_and_previous_move_the_queue(tmp_path: Path) -> None:
    album = tmp_path / "album"
    album.mkdir()
    (album / "a.mp3").write_bytes(b"a")
    (album / "b.mp3").write_bytes(b"b")
    player, library, _visualizer = create_app(tmp_path)
    recorder = _Recorder()
    player.add_listener(recorder)

    assert [track.title for track in library.tracks] == ["a", "b"]
    assert player.current is not None
    assert player.current.title == "a"

    player.next()
    assert player.current.title == "b"
    assert recorder.tracks[-1] is not None
    assert recorder.tracks[-1].title == "b"

    player.previous()
    assert player.current.title == "a"
