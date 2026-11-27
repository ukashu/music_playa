import shutil
from pathlib import Path

import numpy as np
import pytest

from music_playa.models import Track
from music_playa.services import visualizer
from music_playa.services.visualizer import FftVisualizer, SilentVisualizer

RATE = 22050


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class _Engine:
    def __init__(self) -> None:
        self.position = 0.0
        self.duration = 10.0
        self.is_playing = True
        self.volume = 1.0


def _sine(frequency: float, seconds: float = 5.0) -> np.ndarray:
    t = np.arange(int(RATE * seconds)) / RATE
    return (0.8 * np.sin(2 * np.pi * frequency * t)).astype(np.float32)


def _loaded(monkeypatch, samples: np.ndarray | None):
    monkeypatch.setattr(visualizer, "decode_pcm", lambda path, rate: samples)
    engine = _Engine()
    clock = _Clock()
    viz = FftVisualizer(engine, sample_rate=RATE, clock=clock)
    viz.on_track(Track(path=Path("a.mp3"), title="a"))
    assert viz._thread is not None
    viz._thread.join()
    return viz, engine, clock


def _band_frequency(viz: FftVisualizer, band: int) -> float:
    return float(viz._centers[band])


def test_silent_visualizer_returns_zeros() -> None:
    silent = SilentVisualizer()
    assert silent.bands() == [0.0] * 256
    assert silent.wave() == [0.0] * 256


def test_peak_band_matches_sine_frequency(monkeypatch) -> None:
    viz, engine, clock = _loaded(monkeypatch, _sine(440.0))
    engine.position = 1.0
    clock.now = 0.1
    bands = viz.bands()
    assert len(bands) == 256
    assert all(0.0 <= value <= 1.0 for value in bands)
    peak = int(np.argmax(bands))
    assert _band_frequency(viz, peak) == pytest.approx(440.0, rel=0.1)
    assert bands[peak] > 0.8


def _peak_at_volume(monkeypatch, volume: float) -> float:
    # A fresh visualizer per measurement: bands() keeps the highest level it has shown.
    viz, engine, clock = _loaded(monkeypatch, _sine(440.0))
    engine.volume = volume
    engine.position = 1.0
    clock.now = 0.1
    return max(viz.bands())


def test_half_volume_lowers_bars_by_about_6_db(monkeypatch) -> None:
    full = _peak_at_volume(monkeypatch, 1.0)
    half = _peak_at_volume(monkeypatch, 0.5)
    # 20*log10(0.5) = -6.02 dB, and the display maps 70 dB onto the full 0..1 range.
    assert full - half == pytest.approx(6.02 / 70.0, abs=0.01)
    assert half < full


def test_zero_volume_gives_zeros(monkeypatch) -> None:
    assert _peak_at_volume(monkeypatch, 0.0) == 0.0


def test_full_volume_keeps_the_full_scale_peak(monkeypatch) -> None:
    assert _peak_at_volume(monkeypatch, 1.0) > 0.8


def test_no_samples_gives_zeros(monkeypatch) -> None:
    viz, engine, clock = _loaded(monkeypatch, None)
    engine.position = 1.0
    clock.now = 0.1
    assert viz.bands() == [0.0] * 256
    assert viz.wave() == [0.0] * 256


def test_silence_gives_zeros(monkeypatch) -> None:
    viz, engine, clock = _loaded(monkeypatch, np.zeros(RATE * 5, dtype=np.float32))
    engine.position = 1.0
    clock.now = 0.1
    assert max(viz.bands()) == 0.0


def test_position_past_end_gives_zeros(monkeypatch) -> None:
    viz, engine, clock = _loaded(monkeypatch, _sine(440.0, seconds=1.0))
    engine.position = 30.0
    clock.now = 0.1
    assert max(viz.bands()) == 0.0


def test_bands_fall_to_zero_when_paused(monkeypatch) -> None:
    viz, engine, clock = _loaded(monkeypatch, _sine(440.0))
    engine.position = 1.0
    clock.now = 0.1
    assert max(viz.bands()) > 0.8

    engine.is_playing = False
    clock.now = 0.2
    partial = max(viz.bands())
    assert 0.0 < partial < 1.0
    clock.now = 10.0
    assert max(viz.bands()) == 0.0


def test_wave_has_256_samples_in_range(monkeypatch) -> None:
    viz, engine, clock = _loaded(monkeypatch, _sine(440.0))
    engine.position = 1.0
    wave = viz.wave()
    assert len(wave) == 256
    assert max(abs(value) for value in wave) > 0.1
    assert all(-1.0 <= value <= 1.0 for value in wave)


def test_track_change_discards_old_samples(monkeypatch) -> None:
    viz, engine, clock = _loaded(monkeypatch, _sine(440.0))
    engine.position = 1.0
    viz.on_track(None)
    clock.now = 0.1
    assert viz.bands() == [0.0] * 256


def test_same_track_does_not_decode_again(monkeypatch) -> None:
    calls: list[Path] = []

    def fake_decode(path: Path, rate: int) -> np.ndarray:
        calls.append(path)
        return _sine(440.0)

    monkeypatch.setattr(visualizer, "decode_pcm", fake_decode)
    viz = FftVisualizer(_Engine(), sample_rate=RATE, clock=_Clock())
    track = Track(path=Path("a.mp3"), title="a")
    viz.on_track(track)
    viz._thread.join()
    viz.on_track(track)
    assert calls == [Path("a.mp3")]


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is not installed")
def test_decode_pcm_reads_wav_with_ffmpeg(tmp_path) -> None:
    import wave

    path = tmp_path / "tone.wav"
    samples = (_sine(440.0, seconds=1.0) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(RATE)
        writer.writeframes(samples.tobytes())

    decoded = visualizer.decode_pcm(path, RATE)
    assert decoded is not None
    assert len(decoded) == pytest.approx(RATE, rel=0.02)
    assert float(np.max(np.abs(decoded))) == pytest.approx(0.8, abs=0.05)


def test_decode_pcm_returns_none_for_missing_file(tmp_path) -> None:
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg is not installed")
    decoded = visualizer.decode_pcm(tmp_path / "missing.mp3", RATE)
    assert decoded is None or len(decoded) == 0
