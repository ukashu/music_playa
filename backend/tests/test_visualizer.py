import shutil
import subprocess
import time
from pathlib import Path
from types import SimpleNamespace

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


def test_decode_pcm_without_ffmpeg_returns_none(monkeypatch) -> None:
    monkeypatch.setattr(visualizer.shutil, "which", lambda name: None)

    assert visualizer.decode_pcm(Path("a.mp3")) is None


def test_decode_pcm_asks_ffmpeg_for_mono_float_samples(monkeypatch) -> None:
    samples = np.array([0.25, -0.5, 1.0], dtype=np.float32)
    seen: dict[str, object] = {}

    def fake_run(command, **options):
        seen["command"] = command
        seen["options"] = options
        return SimpleNamespace(stdout=samples.tobytes())

    monkeypatch.setattr(visualizer.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(visualizer.subprocess, "run", fake_run)

    decoded = visualizer.decode_pcm(Path("dir/a.mp3"))

    assert seen["command"] == [
        "/usr/bin/ffmpeg",
        "-v",
        "quiet",
        "-i",
        "dir/a.mp3",
        "-vn",
        "-ac",
        "1",
        "-ar",
        "22050",
        "-f",
        "f32le",
        "-",
    ]
    assert seen["options"] == {"capture_output": True, "check": True}
    assert decoded is not None
    assert decoded.dtype == np.float32
    assert decoded.tolist() == samples.tolist()


def test_decode_pcm_uses_the_requested_sample_rate(monkeypatch) -> None:
    commands: list[list[str]] = []

    def fake_run(command, **options):
        commands.append(command)
        return SimpleNamespace(stdout=b"")

    monkeypatch.setattr(visualizer.shutil, "which", lambda name: "ffmpeg")
    monkeypatch.setattr(visualizer.subprocess, "run", fake_run)

    visualizer.decode_pcm(Path("a.mp3"), 8000)

    assert commands[0][commands[0].index("-ar") + 1] == "8000"


@pytest.mark.parametrize(
    "error", [OSError("no exec"), subprocess.CalledProcessError(1, "ffmpeg"), subprocess.SubprocessError()]
)
def test_decode_pcm_returns_none_when_ffmpeg_fails(monkeypatch, error) -> None:
    def failing_run(command, **options):
        raise error

    monkeypatch.setattr(visualizer.shutil, "which", lambda name: "ffmpeg")
    monkeypatch.setattr(visualizer.subprocess, "run", failing_run)

    assert visualizer.decode_pcm(Path("a.mp3")) is None


def test_decoding_runs_in_a_background_thread_with_the_sample_rate(monkeypatch) -> None:
    rates: list[int] = []

    def fake_decode(path: Path, rate: int) -> np.ndarray:
        rates.append(rate)
        return _sine(440.0)

    monkeypatch.setattr(visualizer, "decode_pcm", fake_decode)
    viz = FftVisualizer(_Engine(), sample_rate=RATE, clock=_Clock())

    viz.on_track(Track(path=Path("a.mp3"), title="a"))

    assert viz._thread is not None
    assert viz._thread.daemon
    viz._thread.join()
    assert rates == [RATE]
    assert viz._pcm is not None


def test_visualizer_defaults_to_the_real_clock_and_rate() -> None:
    viz = FftVisualizer(_Engine())

    assert viz._rate == 22050
    assert viz._clock is time.monotonic


def test_on_progress_does_nothing() -> None:
    assert FftVisualizer(_Engine(), clock=_Clock()).on_progress(1.0, 2.0) is None


def test_on_track_without_a_track_twice_does_not_restart_anything() -> None:
    viz = FftVisualizer(_Engine(), clock=_Clock())

    viz.on_track(None)

    assert viz._generation == 0
    assert viz._thread is None


def test_clearing_the_track_stops_the_decoding(monkeypatch) -> None:
    viz, _engine, _clock = _loaded(monkeypatch, _sine(440.0))
    thread = viz._thread
    generation = viz._generation

    viz.on_track(None)

    assert viz._generation == generation + 1
    assert viz._pcm is None
    assert viz._thread is thread


def test_outdated_decoding_result_is_dropped(monkeypatch) -> None:
    monkeypatch.setattr(visualizer, "decode_pcm", lambda path, rate: _sine(440.0))
    viz = FftVisualizer(_Engine(), sample_rate=RATE, clock=_Clock())
    viz._generation = 3

    viz._decode(Path("old.mp3"), 2)
    assert viz._pcm is None

    viz._decode(Path("new.mp3"), 3)
    assert viz._pcm is not None


def test_changing_the_track_decodes_the_new_one(monkeypatch) -> None:
    decoded: list[Path] = []

    def fake_decode(path: Path, rate: int) -> np.ndarray:
        decoded.append(path)
        return _sine(440.0)

    monkeypatch.setattr(visualizer, "decode_pcm", fake_decode)
    viz = FftVisualizer(_Engine(), sample_rate=RATE, clock=_Clock())
    for name in ("a.mp3", "b.mp3"):
        viz.on_track(Track(path=Path(name), title=name))
        viz._thread.join()

    assert decoded == [Path("a.mp3"), Path("b.mp3")]
    assert viz._generation == 2


@pytest.mark.parametrize("volume, expected", [(-0.5, 0.0), (0.0, 0.0), (0.4, 0.4), (1.0, 1.0), (3.0, 1.0)])
def test_volume_gain_is_limited_to_the_valid_range(volume: float, expected: float) -> None:
    assert visualizer._volume_gain(volume) == expected


@pytest.mark.parametrize("frequency", [100.0, 1000.0, 8000.0])
def test_peak_band_follows_the_frequency_across_the_spectrum(monkeypatch, frequency: float) -> None:
    viz, engine, clock = _loaded(monkeypatch, _sine(frequency))
    engine.position = 1.0
    clock.now = 0.1

    bands = viz.bands()

    assert _band_frequency(viz, int(np.argmax(bands))) == pytest.approx(frequency, rel=0.1)


def test_band_centers_cover_the_audible_range_in_order() -> None:
    centers = FftVisualizer(_Engine(), sample_rate=RATE, clock=_Clock())._centers

    assert len(centers) == 256
    assert list(centers) == sorted(centers)
    assert 40.0 < centers[0] < 41.0
    assert 10000.0 < centers[-1] < RATE / 2


def test_bands_fall_at_a_fixed_speed_after_the_music_stops(monkeypatch) -> None:
    viz, engine, clock = _loaded(monkeypatch, _sine(440.0))
    engine.position = 1.0
    clock.now = 0.1
    peak = max(viz.bands())

    engine.is_playing = False
    clock.now = 0.3

    assert max(viz.bands()) == pytest.approx(peak - 1.5 * 0.2)


def test_bands_do_not_jump_when_the_clock_goes_backwards(monkeypatch) -> None:
    viz, engine, clock = _loaded(monkeypatch, _sine(440.0))
    engine.position = 1.0
    clock.now = 1.0
    peak = max(viz.bands())

    engine.is_playing = False
    clock.now = 0.5

    assert max(viz.bands()) == pytest.approx(peak)


def test_bands_keep_the_higher_of_new_and_falling_levels(monkeypatch) -> None:
    viz, engine, clock = _loaded(monkeypatch, _sine(440.0))
    engine.position = 1.0
    clock.now = 0.1
    first = viz.bands()
    clock.now = 0.11

    second = viz.bands()

    assert max(second) == pytest.approx(max(first), abs=0.02)
    assert isinstance(second, list)
    assert len(second) == 256


def test_frame_is_padded_with_silence_near_the_end(monkeypatch) -> None:
    viz, engine, _clock = _loaded(monkeypatch, np.ones(3000, dtype=np.float32))
    engine.position = 1000.5 / RATE

    frame = viz._frame()

    assert frame is not None
    assert len(frame) == 2048
    assert frame[:2000].tolist() == [1.0] * 2000
    assert frame[2000:].tolist() == [0.0] * 48


def test_frame_is_missing_outside_the_samples(monkeypatch) -> None:
    viz, engine, _clock = _loaded(monkeypatch, np.ones(3000, dtype=np.float32))

    engine.position = 2999.5 / RATE
    assert viz._frame() is not None
    engine.position = 3000.0 / RATE
    assert viz._frame() is None
    engine.position = -1.0
    assert viz._frame() is None


def test_wide_bands_are_the_ones_spanning_several_fft_bins() -> None:
    viz = FftVisualizer(_Engine(), sample_rate=RATE, clock=_Clock())
    bin_width = RATE / 2048
    edges = np.geomspace(40.0, RATE / 2, 257)
    expected = []
    for band in range(256):
        low = int(edges[band] / bin_width)
        high = max(low + 1, round(edges[band + 1] / bin_width))
        if high - low > 1:
            expected.append((band, low, high))

    assert viz._wide == expected
    # Low bands are narrower than one bin, high bands cover several of them.
    assert 0 < len(expected) < 256
    assert expected[0][0] > 0
    assert expected[-1][0] == 255
    assert any(high - low == 2 for _band, low, high in expected)


def test_frame_is_not_missing_for_a_single_sample(monkeypatch) -> None:
    viz, engine, _clock = _loaded(monkeypatch, np.array([0.5], dtype=np.float32))
    engine.position = 0.0

    frame = viz._frame()

    assert frame is not None
    assert frame[0] == 0.5
    assert frame[1:].tolist() == [0.0] * 2047


def _bin_centered_sine(bin_index: int, amplitude: float) -> np.ndarray:
    # A whole number of periods fits the 2048-sample window, so the peak is not smeared.
    t = np.arange(RATE * 5) / RATE
    frequency = bin_index * RATE / 2048
    return (amplitude * np.sin(2 * np.pi * frequency * t)).astype(np.float32)


def test_full_scale_level_is_calibrated_in_decibels(monkeypatch) -> None:
    viz, engine, clock = _loaded(monkeypatch, _bin_centered_sine(400, 0.8))
    engine.position = 1.0
    clock.now = 0.1

    # 0.8 amplitude is -1.94 dB; the display maps -70..0 dB onto 0..1.
    assert max(viz.bands()) == pytest.approx((70.0 - 1.938) / 70.0, abs=0.0005)


def test_levels_never_exceed_one(monkeypatch) -> None:
    viz, engine, clock = _loaded(monkeypatch, _bin_centered_sine(400, 5.0))
    engine.position = 1.0
    clock.now = 0.1

    bands = viz.bands()

    assert max(bands) == 1.0
    assert min(bands) >= 0.0


def test_spectrum_of_silence_is_exactly_zero(monkeypatch) -> None:
    viz, engine, _clock = _loaded(monkeypatch, np.zeros(RATE, dtype=np.float32))
    engine.position = 0.0

    assert viz._spectrum().tolist() == [0.0] * 256


def test_frame_is_missing_for_empty_samples(monkeypatch) -> None:
    viz, _engine, _clock = _loaded(monkeypatch, np.zeros(0, dtype=np.float32))

    assert viz._frame() is None


def test_wave_samples_every_eighth_value_of_the_window(monkeypatch) -> None:
    ramp = np.linspace(-1.0, 1.0, RATE * 5, dtype=np.float32)
    viz, engine, _clock = _loaded(monkeypatch, ramp)
    engine.position = 0.0

    wave = viz.wave()

    assert wave == pytest.approx(ramp[:2048:8].tolist())
    assert all(isinstance(value, float) for value in wave)


def test_wave_is_clipped_to_unit_range(monkeypatch) -> None:
    viz, engine, _clock = _loaded(monkeypatch, np.full(RATE, 3.0, dtype=np.float32))
    assert viz.wave() == [1.0] * 256

    viz, engine, _clock = _loaded(monkeypatch, np.full(RATE, -3.0, dtype=np.float32))
    assert viz.wave() == [-1.0] * 256


def test_wave_is_flat_when_paused(monkeypatch) -> None:
    viz, engine, _clock = _loaded(monkeypatch, _sine(440.0))
    engine.position = 1.0
    assert max(abs(value) for value in viz.wave()) > 0.1

    engine.is_playing = False

    assert viz.wave() == [0.0] * 256
