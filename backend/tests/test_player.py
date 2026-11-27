from pathlib import Path

from music_playa import create_app
from music_playa.core.player import MemoryPlayer
from music_playa.events import EventBus
from music_playa.models import PlaybackState, RepeatMode, Track


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
        self._on_ended = None
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

    def set_track_ended_callback(self, callback) -> None:
        self._on_ended = callback

    def finish_track(self) -> None:
        """Simulate the engine reporting that the loaded track has ended."""
        if self._playing and self._on_ended is not None:
            self._playing = False
            self._on_ended()


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


def _two_tracks() -> list[Track]:
    return [Track(Path("a.mp3"), "a"), Track(Path("b.mp3"), "b")]


def test_repeat_off_plays_next_then_stops_at_the_end() -> None:
    tracks = _two_tracks()
    engine = _FakeEngine()
    player = MemoryPlayer(tracks, EventBus(), engine)
    player.play()

    engine.finish_track()
    assert player.current == tracks[1]
    assert engine.loaded_path == tracks[1].path
    assert engine.is_playing

    engine.finish_track()
    # The list ends without repeat: playback stops and the first track is cued.
    assert player.current == tracks[0]
    assert engine.loaded_path is None
    assert not engine.is_playing


def test_state_follows_play_pause_stop_and_end_of_list() -> None:
    tracks = _two_tracks()
    engine = _FakeEngine()
    player = MemoryPlayer(tracks, EventBus(), engine)
    assert player.state is PlaybackState.STOPPED

    player.play()
    assert player.state is PlaybackState.PLAYING
    player.pause()
    assert player.state is PlaybackState.PAUSED
    player.play()
    assert player.state is PlaybackState.PLAYING

    engine.finish_track()
    assert player.state is PlaybackState.PLAYING
    engine.finish_track()
    assert player.state is PlaybackState.STOPPED


def test_manual_next_on_last_track_plays_first_with_repeat_off() -> None:
    tracks = _two_tracks()
    engine = _FakeEngine()
    player = MemoryPlayer(tracks, EventBus(), engine)
    player.play()
    player.select(tracks[1])

    player.next()

    assert player.current == tracks[0]
    assert engine.loaded_path == tracks[0].path
    assert engine.is_playing


def test_repeat_all_wraps_to_the_first_track() -> None:
    tracks = _two_tracks()
    engine = _FakeEngine()
    player = MemoryPlayer(tracks, EventBus(), engine)
    player.repeat = RepeatMode.ALL
    player.play()

    engine.finish_track()
    engine.finish_track()

    assert player.current == tracks[0]
    assert engine.loaded_path == tracks[0].path
    assert engine.is_playing


def test_repeat_all_loops_a_single_track() -> None:
    tracks = [Track(Path("a.mp3"), "a")]
    engine = _FakeEngine()
    player = MemoryPlayer(tracks, EventBus(), engine)
    player.repeat = RepeatMode.ALL
    player.play()

    for _ in range(3):
        engine.finish_track()
        assert engine.loaded_path == tracks[0].path
        assert engine.is_playing


def test_repeat_one_restarts_the_same_track_until_changed() -> None:
    tracks = _two_tracks()
    engine = _FakeEngine()
    player = MemoryPlayer(tracks, EventBus(), engine)
    player.repeat = RepeatMode.ONE
    player.play()

    for _ in range(3):
        engine.finish_track()
        assert player.current == tracks[0]
        assert engine.loaded_path == tracks[0].path
        assert engine.is_playing


def test_repeat_one_manual_next_moves_to_the_following_track() -> None:
    tracks = _two_tracks()
    engine = _FakeEngine()
    player = MemoryPlayer(tracks, EventBus(), engine)
    player.repeat = RepeatMode.ONE
    player.play()

    player.next()
    assert player.current == tracks[1]
    assert engine.is_playing

    engine.finish_track()
    assert player.current == tracks[1]
    assert engine.loaded_path == tracks[1].path
    assert engine.is_playing


def test_setting_repeat_notifies_listeners() -> None:
    recorder = _Recorder()
    player = MemoryPlayer(_two_tracks(), EventBus(), _FakeEngine())
    player.add_listener(recorder)
    before = len(recorder.tracks)

    player.repeat = RepeatMode.ALL

    assert player.repeat is RepeatMode.ALL
    assert len(recorder.tracks) == before + 1
