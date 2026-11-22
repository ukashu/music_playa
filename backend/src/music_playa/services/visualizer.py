import shutil
import subprocess
import threading
import time
from collections.abc import Callable
from pathlib import Path

import numpy as np

from music_playa.interfaces import AudioEngine
from music_playa.models import Track

_BANDS = 256
_WINDOW = 2048
_SAMPLE_RATE = 22050
_MIN_FREQUENCY = 40.0
_FLOOR_DB = 70.0
_FALL_PER_SECOND = 1.5


class SilentVisualizer:
    def bands(self) -> list[float]:
        return [0.0] * _BANDS

    def wave(self) -> list[float]:
        return [0.0] * _BANDS


def decode_pcm(path: Path, sample_rate: int = _SAMPLE_RATE) -> np.ndarray | None:
    """Decode a file to mono float32 samples with ffmpeg. Returns None on failure."""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        return None
    command = [
        ffmpeg,
        "-v",
        "quiet",
        "-i",
        str(path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-f",
        "f32le",
        "-",
    ]
    try:
        result = subprocess.run(command, capture_output=True, check=True)
    except (OSError, subprocess.SubprocessError):
        return None
    return np.frombuffer(result.stdout, dtype=np.float32)


class FftVisualizer:
    """Spectrum visualizer computed from the decoded track at the playback position.

    mpv does not expose samples, so the track is decoded in a background thread and
    the FFT window is taken at the engine position. Until decoding finishes, or when
    decoding fails, the bands are zero. Register it as a PlaybackListener so it
    learns about track changes.
    """

    def __init__(
        self,
        engine: AudioEngine,
        sample_rate: int = _SAMPLE_RATE,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._engine = engine
        self._rate = sample_rate
        self._clock = clock
        self._path: Path | None = None
        self._pcm: np.ndarray | None = None
        self._generation = 0
        self._thread: threading.Thread | None = None
        self._levels = np.zeros(_BANDS)
        self._last_time = clock()
        self._hann = np.hanning(_WINDOW)

        bin_width = sample_rate / _WINDOW
        edges = np.geomspace(_MIN_FREQUENCY, sample_rate / 2, _BANDS + 1)
        self._bin_freqs = np.fft.rfftfreq(_WINDOW, 1.0 / sample_rate)
        self._centers = np.sqrt(edges[:-1] * edges[1:])
        self._wide: list[tuple[int, int, int]] = []
        for band in range(_BANDS):
            low = int(edges[band] / bin_width)
            high = max(low + 1, int(round(edges[band + 1] / bin_width)))
            if high - low > 1:
                self._wide.append((band, low, high))

    def on_progress(self, position: float, duration: float) -> None:
        return None

    def on_track(self, track: Track | None) -> None:
        path = track.path if track is not None else None
        if path == self._path:
            return
        self._path = path
        self._pcm = None
        self._generation += 1
        if path is None:
            return
        generation = self._generation
        thread = threading.Thread(
            target=self._decode, args=(path, generation), daemon=True
        )
        self._thread = thread
        thread.start()

    def bands(self) -> list[float]:
        now = self._clock()
        elapsed = max(now - self._last_time, 0.0)
        self._last_time = now
        target = self._spectrum() if self._engine.is_playing else None
        fallen = np.maximum(self._levels - _FALL_PER_SECOND * elapsed, 0.0)
        if target is None:
            self._levels = fallen
        else:
            self._levels = np.maximum(target, fallen)
        return self._levels.tolist()

    def wave(self) -> list[float]:
        frame = self._frame()
        if frame is None or not self._engine.is_playing:
            return [0.0] * _BANDS
        step = _WINDOW // _BANDS
        return np.clip(frame[::step][:_BANDS], -1.0, 1.0).astype(float).tolist()

    def _decode(self, path: Path, generation: int) -> None:
        samples = decode_pcm(path, self._rate)
        if generation == self._generation:
            self._pcm = samples

    def _frame(self) -> np.ndarray | None:
        pcm = self._pcm
        if pcm is None or len(pcm) == 0:
            return None
        start = int(self._engine.position * self._rate)
        if start < 0 or start >= len(pcm):
            return None
        frame = pcm[start : start + _WINDOW]
        if len(frame) < _WINDOW:
            frame = np.pad(frame, (0, _WINDOW - len(frame)))
        return frame

    def _spectrum(self) -> np.ndarray:
        frame = self._frame()
        if frame is None:
            return np.zeros(_BANDS)
        magnitude = np.abs(np.fft.rfft(frame * self._hann)) / (_WINDOW / 4)
        levels = np.interp(self._centers, self._bin_freqs, magnitude)
        for band, low, high in self._wide:
            levels[band] = max(levels[band], magnitude[low:high].max())
        decibels = 20.0 * np.log10(levels + 1e-9)
        return np.clip((decibels + _FLOOR_DB) / _FLOOR_DB, 0.0, 1.0)
