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

    def event_callback(self, name: str):
        def decorator(fn):
            return fn

        return decorator

    def stop(self) -> None:
        self.calls.append(("stop",))

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
