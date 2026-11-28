"""How strongly the bass hits at the moment, for the elements that glow with it.

The bands of the visualizer are spread over a logarithmic scale from 40 Hz and are in decibels,
so the bass is high for most of a track and its raw level hardly pulses. The glow follows how far
the bass is above its own recent average instead, so it flashes on a kick and settles when the
bass is steady.
"""

import math

from music_playa_gui.utils import clamp

BASS_BANDS = 64  # the lowest bands, about 40 to 160 Hz
AVERAGE_SECONDS = 1.5  # time the running average of the bass takes to follow it
ATTACK_SECONDS = 0.04  # time the glow takes to rise to a stronger bass
RELEASE_SECONDS = 0.25  # time the glow takes to fall when the bass gets weaker
GAIN = 2.0  # how many times the headroom above the average one has to fill to reach full glow
MIN_HEADROOM = 0.05  # keeps the division sane when the average is close to the top
LEVEL_STEPS = 12  # the level is given in this many steps, so the screen is not redrawn for nothing


def _follow(current: float, target: float, elapsed: float, seconds: float) -> float:
    """current moved towards target, as an exponential approach with the given time constant."""
    return current + (target - current) * (1.0 - math.exp(-elapsed / seconds))


def quantized(level: float) -> float:
    """The level (0..1) rounded to the nearest of LEVEL_STEPS steps."""
    return round(clamp(level, 0.0, 1.0) * LEVEL_STEPS) / LEVEL_STEPS


class BassMeter:
    """Turns the bands of every frame into a glow level between 0 (no hit) and 1 (a strong hit)."""

    def __init__(self) -> None:
        self._average = 0.0
        self._level = 0.0

    def update(self, bands: list[float], elapsed: float) -> float:
        """The glow level after a frame; elapsed is the time since the previous one, in seconds."""
        elapsed = max(elapsed, 0.0)
        lowest = bands[:BASS_BANDS]
        bass = sum(lowest) / len(lowest) if lowest else 0.0
        headroom = max(1.0 - self._average, MIN_HEADROOM)
        target = clamp((bass - self._average) / headroom * GAIN, 0.0, 1.0)
        self._average = _follow(self._average, bass, elapsed, AVERAGE_SECONDS)
        seconds = ATTACK_SECONDS if target > self._level else RELEASE_SECONDS
        self._level = _follow(self._level, target, elapsed, seconds)
        return self._level

    def reset(self) -> None:
        self._average = 0.0
        self._level = 0.0
