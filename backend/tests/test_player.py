from pathlib import Path

from music_playa import create_app
from music_playa.core.player import MemoryPlayer
from music_playa.events import EventBus
from music_playa.models import Track


class _Recorder:
    def __init__(self) -> None:
        self.tracks: list[Track | None] = []

    def on_progress(self, position: float, duration: float) -> None:
        return None

    def on_track(self, track: Track | None) -> None:
        self.tracks.append(track)


class _FakeEngine:
    def __init__(self, durations: dict[Path, float] | None = None) -> None:
        self._durations = durations or {}
        self._position = 0.0
        self._duration = 0.0
        self._playing = False
        self._volume = 1.0
        self.loaded_path: Path | None = None

    @property
    def position(self) -> float:
        return self._position

    @property
    def duration(self) -> float:
        return self._duration

    @property
    def is_playing(self) -> bool:
        return self._playing

    def load(self, path: Path) -> float:
        self.stop()
        self.loaded_path = path
        self._duration = self._durations.get(path, 100.0)
        return self._duration

    def play(self) -> None:
        self._playing = self.loaded_path is not None

    def pause(self) -> None:
        self._playing = False

    def stop(self) -> None:
        self._position = 0.0
        self._playing = False
        self.loaded_path = None

    def seek(self, position: float) -> None:
        self._position = min(max(position, 0.0), self._duration)

    def set_volume(self, volume: float) -> None:
        self._volume = min(max(volume, 0.0), 1.0)


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


def test_player_delegates_transport_operations_to_engine() -> None:
    tracks = [
        Track(Path("a.mp3"), "a"),
        Track(Path("b.mp3"), "b"),
    ]
    engine = _FakeEngine({tracks[0].path: 120.0})
    player = MemoryPlayer(tracks, EventBus(), engine)

    player.play()

    assert engine.loaded_path == tracks[0].path
    assert engine.is_playing
    assert player.position == 0.0
    assert player.duration == 120.0

    player.pause()
    assert not engine.is_playing

    player.seek(45.0)
    assert player.position == 45.0

    player.set_volume(0.25)
    assert engine._volume == 0.25
    assert player.position == 45.0


def test_track_change_reloads_engine_and_preserves_playing_state() -> None:
    tracks = [
        Track(Path("a.mp3"), "a"),
        Track(Path("b.mp3"), "b"),
    ]
    engine = _FakeEngine()
    player = MemoryPlayer(tracks, EventBus(), engine)

    player.play()
    assert engine.loaded_path == tracks[0].path
    assert engine.is_playing

    player.next()
    assert engine.loaded_path == tracks[1].path
    assert engine.is_playing

    player.pause()
    player.previous()
    assert engine.loaded_path == tracks[0].path
    assert not engine.is_playing


def test_stop_select_and_volume() -> None:
    tracks = [
        Track(Path("a.mp3"), "a"),
        Track(Path("b.mp3"), "b"),
    ]
    engine = _FakeEngine()
    player = MemoryPlayer(tracks, EventBus(), engine)

    player.play()
    player.set_volume(0.25)
    assert player.volume == 0.25

    player.select(tracks[1])
    assert player.current == tracks[1]
    assert engine.loaded_path == tracks[1].path

    player.stop()
    assert engine.loaded_path is None
