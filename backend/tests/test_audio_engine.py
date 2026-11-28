import locale
from pathlib import Path

import pytest

from music_playa.core import audio_engine


class _FakeMPV:
    def __init__(self) -> None:
        self.time_pos: float | None = None
        self.duration: float | None = None
        self.pause = False
        self.volume = 100.0
        self.calls: list[tuple[object, ...]] = []
        self.callbacks: dict[str, object] = {}

    def event_callback(self, name: str):
        def decorator(fn):
            self.callbacks[name] = fn
            return fn

        return decorator

    def stop(self) -> None:
        self.calls.append(("stop",))
        self.time_pos = None
        self.duration = None

    def loadfile(self, path: str) -> None:
        self.calls.append(("loadfile", path))
        self.duration = 120.0
        self.time_pos = 0.0

    def seek(
        self,
        position: float,
        reference: str = "relative",
        precision: str = "keyframes",
    ) -> None:
        self.calls.append(("seek", position, reference, precision))
        self.time_pos = position


def test_audio_engine_uses_mpv_transport_properties(monkeypatch) -> None:
    fake_mpv = _FakeMPV()
    monkeypatch.setattr(audio_engine.mpv, "MPV", lambda: fake_mpv)
    engine = audio_engine.AudioEngine()

    path = Path("track.mp3")
    assert engine.load(path) == 120.0
    assert fake_mpv.pause
    assert ("loadfile", str(path)) in fake_mpv.calls

    engine.play()
    assert not fake_mpv.pause
    assert fake_mpv.calls.count(("loadfile", str(path))) == 1

    engine.pause()
    engine.seek(45.0)
    assert fake_mpv.pause
    assert engine.position == 45.0
    assert ("seek", 45.0, "absolute", "exact") in fake_mpv.calls

    engine.set_volume(0.25)
    assert fake_mpv.volume == 25.0


def test_audio_engine_forces_c_numeric_locale(monkeypatch) -> None:
    fake_mpv = _FakeMPV()
    monkeypatch.setattr(audio_engine.mpv, "MPV", lambda: fake_mpv)
    original = locale.setlocale(locale.LC_NUMERIC)
    try:
        try:
            locale.setlocale(locale.LC_NUMERIC, "pl_PL.UTF-8")
        except locale.Error:
            pytest.skip("pl_PL.UTF-8 locale is not installed")
        audio_engine.AudioEngine()
        assert locale.setlocale(locale.LC_NUMERIC) == "C"
    finally:
        locale.setlocale(locale.LC_NUMERIC, original)


def test_audio_engine_ignores_non_finite_duration(monkeypatch) -> None:
    fake_mpv = _FakeMPV()
    monkeypatch.setattr(audio_engine.mpv, "MPV", lambda: fake_mpv)
    engine = audio_engine.AudioEngine()

    path = Path("track.mp3")
    engine.load(path)
    fake_mpv.duration = float("nan")
    assert engine.duration == 120.0

    fake_mpv.duration = float("inf")
    assert engine.duration == 120.0

    # Seeking to a non-finite position must not reach mpv.
    calls_before = list(fake_mpv.calls)
    engine.seek(float("nan"))
    assert fake_mpv.calls == calls_before


def _engine(monkeypatch) -> tuple[audio_engine.AudioEngine, _FakeMPV]:
    fake = _FakeMPV()
    monkeypatch.setattr(audio_engine.mpv, "MPV", lambda: fake)
    return audio_engine.AudioEngine(), fake


def _seeks(fake: _FakeMPV) -> list[tuple[object, ...]]:
    return [call for call in fake.calls if call[0] == "seek"]


def test_end_of_file_ends_a_playing_track(monkeypatch) -> None:
    engine, fake = _engine(monkeypatch)
    ended: list[int] = []
    engine.set_track_ended_callback(lambda: ended.append(1))
    engine.load(Path("a.mp3"))
    engine.play()

    fake.callbacks["end-file"](None)

    assert ended == [1]
    assert not engine.is_playing
    # The track is no longer playing, so a second event is not a second ending.
    fake.callbacks["end-file"](None)
    assert ended == [1]


def test_end_of_file_while_not_playing_is_ignored(monkeypatch) -> None:
    engine, fake = _engine(monkeypatch)
    ended: list[int] = []
    engine.set_track_ended_callback(lambda: ended.append(1))
    engine.load(Path("a.mp3"))

    fake.callbacks["end-file"](None)

    assert ended == []


def test_end_of_file_without_a_callback_changes_nothing(monkeypatch) -> None:
    engine, fake = _engine(monkeypatch)
    engine.load(Path("a.mp3"))
    engine.play()

    fake.callbacks["end-file"](None)

    assert engine.is_playing


def test_is_playing_follows_play_and_pause(monkeypatch) -> None:
    engine, _fake = _engine(monkeypatch)
    assert not engine.is_playing
    engine.load(Path("a.mp3"))
    assert not engine.is_playing
    engine.play()
    assert engine.is_playing
    engine.pause()
    assert not engine.is_playing


def test_volume_is_kept_and_limited(monkeypatch) -> None:
    engine, fake = _engine(monkeypatch)
    assert engine.volume == 1.0
    engine.set_volume(0.3)
    assert engine.volume == 0.3
    assert fake.volume == pytest.approx(30.0)
    engine.set_volume(1.5)
    assert engine.volume == 1.0
    assert fake.volume == 100.0
    engine.set_volume(-1.0)
    assert engine.volume == 0.0
    assert fake.volume == 0.0


def test_play_without_a_loaded_track_does_nothing(monkeypatch) -> None:
    engine, fake = _engine(monkeypatch)
    fake.pause = True
    engine.play()
    assert fake.pause is True
    assert not engine.is_playing


def test_play_while_playing_does_nothing(monkeypatch) -> None:
    engine, fake = _engine(monkeypatch)
    engine.load(Path("a.mp3"))
    engine.play()
    fake.pause = True
    engine.play()
    assert fake.pause is True


def test_play_after_the_end_starts_from_the_beginning(monkeypatch) -> None:
    engine, fake = _engine(monkeypatch)
    engine.load(Path("a.mp3"))
    fake.time_pos = 120.0
    engine.play()
    assert _seeks(fake) == [("seek", 0.0, "absolute", "exact")]
    assert engine.position == 0.0


def test_play_before_the_end_does_not_seek(monkeypatch) -> None:
    engine, fake = _engine(monkeypatch)
    engine.load(Path("a.mp3"))
    fake.time_pos = 119.9
    engine.play()
    assert _seeks(fake) == []
    assert fake.pause is False


def test_pause_remembers_the_position(monkeypatch) -> None:
    engine, fake = _engine(monkeypatch)
    engine.load(Path("a.mp3"))
    engine.play()
    fake.time_pos = 33.0
    engine.pause()
    assert fake.pause
    fake.time_pos = None
    assert engine.position == 33.0


def test_pause_when_not_playing_does_nothing(monkeypatch) -> None:
    engine, fake = _engine(monkeypatch)
    engine.load(Path("a.mp3"))
    fake.pause = False
    engine.pause()
    assert fake.pause is False


def test_position_ignores_missing_and_non_finite_readings(monkeypatch) -> None:
    engine, fake = _engine(monkeypatch)
    fake.time_pos = 10.0
    assert engine.position == 10.0
    for reading in (None, float("nan"), float("inf")):
        fake.time_pos = reading
        assert engine.position == 10.0


def test_seek_is_limited_to_the_track(monkeypatch) -> None:
    engine, fake = _engine(monkeypatch)
    engine.load(Path("a.mp3"))
    engine.seek(500.0)
    assert _seeks(fake)[-1] == ("seek", 120.0, "absolute", "exact")
    assert engine.position == 120.0
    engine.seek(-5.0)
    assert _seeks(fake)[-1] == ("seek", 0.0, "absolute", "exact")
    assert engine.position == 0.0


def test_seek_before_loading_does_not_reach_mpv(monkeypatch) -> None:
    engine, fake = _engine(monkeypatch)
    engine.seek(10.0)
    assert fake.calls == []
    assert engine.position == 10.0


def test_stop_resets_the_engine(monkeypatch) -> None:
    engine, fake = _engine(monkeypatch)
    engine.load(Path("a.mp3"))
    engine.play()
    fake.time_pos = 40.0
    engine.stop()
    assert fake.calls[-1] == ("stop",)
    assert not engine.is_playing
    assert engine.position == 0.0
    assert engine.duration == 0.0
    # Nothing is loaded any more, so play has nothing to start.
    fake.pause = True
    engine.play()
    assert fake.pause is True


def test_load_stops_the_previous_track_first(monkeypatch) -> None:
    engine, fake = _engine(monkeypatch)
    engine.load(Path("a.mp3"))
    assert fake.calls[0] == ("stop",)
    assert fake.calls[1] == ("loadfile", "a.mp3")
    assert fake.pause


def _engine_that_reports_nothing(monkeypatch) -> tuple[audio_engine.AudioEngine, _FakeMPV]:
    """An engine whose mpv never reports a position or a duration."""
    engine, fake = _engine(monkeypatch)
    fake.loadfile = lambda path: fake.calls.append(("loadfile", path))
    return engine, fake


def test_new_engine_is_idle_at_the_start(monkeypatch) -> None:
    engine, _fake = _engine(monkeypatch)

    assert engine.position == 0.0
    assert engine.duration == 0.0
    assert engine.is_playing is False


def test_load_starts_from_zero_until_mpv_reports_more(monkeypatch) -> None:
    engine, _fake = _engine_that_reports_nothing(monkeypatch)

    assert engine.load(Path("a.mp3")) == 0.0
    assert engine.position == 0.0
    assert engine.duration == 0.0


def test_pause_and_stop_leave_the_engine_not_playing(monkeypatch) -> None:
    engine, _fake = _engine(monkeypatch)
    engine.load(Path("a.mp3"))
    engine.play()

    engine.pause()
    assert engine.is_playing is False

    engine.play()
    engine.stop()
    assert engine.is_playing is False


def test_play_with_an_unknown_duration_does_not_seek(monkeypatch) -> None:
    engine, fake = _engine_that_reports_nothing(monkeypatch)
    engine.load(Path("a.mp3"))

    engine.play()

    assert _seeks(fake) == []


def test_play_after_the_end_of_a_very_short_track_rewinds(monkeypatch) -> None:
    engine, fake = _engine_that_reports_nothing(monkeypatch)
    engine.load(Path("a.mp3"))
    fake.duration = 0.5
    fake.time_pos = 0.5

    engine.play()

    assert _seeks(fake) == [("seek", 0.0, "absolute", "exact")]


def test_seek_is_limited_to_a_very_short_track(monkeypatch) -> None:
    engine, fake = _engine_that_reports_nothing(monkeypatch)
    engine.load(Path("a.mp3"))
    fake.duration = 0.5

    engine.seek(5.0)

    assert _seeks(fake) == [("seek", 0.5, "absolute", "exact")]
