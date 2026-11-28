import math

import pytest

from music_playa_gui.bass import (
    ATTACK_SECONDS,
    BASS_BANDS,
    LEVEL_STEPS,
    RELEASE_SECONDS,
    BassMeter,
    quantized,
)

FRAME = 0.033


def _bands(bass: float, rest: float = 0.0, count: int = 256) -> list[float]:
    return [bass] * BASS_BANDS + [rest] * (count - BASS_BANDS)


def _run(meter: BassMeter, bands: list[float], seconds: float) -> float:
    level = 0.0
    for _ in range(round(seconds / FRAME)):
        level = meter.update(bands, FRAME)
    return level


def test_silence_gives_no_glow() -> None:
    meter = BassMeter()
    assert _run(meter, _bands(0.0), 2.0) == 0.0


def test_a_hit_after_silence_rises_at_the_attack_speed() -> None:
    level = BassMeter().update(_bands(0.9), FRAME)
    assert level == pytest.approx(1.0 - math.exp(-FRAME / ATTACK_SECONDS))


def test_a_hit_on_a_steady_bass_flashes_strongly() -> None:
    meter = BassMeter()
    _run(meter, _bands(0.6), 10.0)
    assert _run(meter, _bands(0.9), 3 * FRAME) > 0.6


def test_a_steady_loud_bass_stops_glowing() -> None:
    meter = BassMeter()
    first = meter.update(_bands(0.9), FRAME)
    assert first > 0.4
    assert _run(meter, _bands(0.9), 10.0) < 0.05


def test_a_small_wobble_of_a_steady_bass_glows_less_than_a_hit() -> None:
    wobble = BassMeter()
    _run(wobble, _bands(0.7), 10.0)
    hit = BassMeter()
    _run(hit, _bands(0.4), 10.0)
    assert _run(wobble, _bands(0.75), 3 * FRAME) < _run(hit, _bands(0.9), 3 * FRAME)


def test_the_glow_falls_when_the_bass_stops() -> None:
    meter = BassMeter()
    peak = meter.update(_bands(0.9), 1.0)
    assert peak > 0.9
    level = meter.update(_bands(0.0), RELEASE_SECONDS)
    assert level == pytest.approx(peak * math.exp(-1.0))
    assert _run(meter, _bands(0.0), 2.0) < 0.01


def test_the_glow_falls_slower_than_it_rises() -> None:
    assert RELEASE_SECONDS > ATTACK_SECONDS


def test_only_the_lowest_bands_count() -> None:
    assert BassMeter().update(_bands(0.0, rest=1.0), 1.0) == 0.0
    assert BassMeter().update(_bands(1.0, rest=0.0), 1.0) > 0.9


def test_bass_is_the_average_of_the_lowest_bands() -> None:
    half = [1.0] * (BASS_BANDS // 2) + [0.0] * (BASS_BANDS // 2) + [0.0] * 100
    # One band in two is full, so the average is 0.5 and the target reaches 1 with the gain of 2.
    full = BassMeter().update([1.0] * BASS_BANDS, 100.0)
    partial = BassMeter().update(half, 100.0)
    assert full == pytest.approx(1.0)
    assert partial == pytest.approx(1.0)
    quarter = [0.25] * BASS_BANDS
    assert BassMeter().update(quarter, 100.0) == pytest.approx(0.5)


def test_fewer_bands_than_the_bass_range_are_averaged_as_they_are() -> None:
    assert BassMeter().update([0.25] * 8, 100.0) == pytest.approx(0.5)


def test_no_bands_give_no_glow() -> None:
    assert BassMeter().update([], 1.0) == 0.0


def test_time_does_not_run_backwards_or_stand_still() -> None:
    meter = BassMeter()
    assert meter.update(_bands(1.0), -1.0) == 0.0
    assert meter.update(_bands(1.0), 0.0) == 0.0


def test_the_average_can_reach_the_top_without_dividing_by_zero() -> None:
    meter = BassMeter()
    meter.update(_bands(1.0), 1000.0)
    level = meter.update(_bands(1.0), FRAME)
    assert 0.0 <= level <= 1.0


def test_reset_forgets_the_average_and_the_glow() -> None:
    meter = BassMeter()
    _run(meter, _bands(0.9), 10.0)
    meter.reset()
    assert meter.update(_bands(0.9), FRAME) == pytest.approx(1.0 - math.exp(-FRAME / ATTACK_SECONDS))


def test_quantized_snaps_to_steps() -> None:
    assert quantized(0.0) == 0.0
    assert quantized(1.0) == 1.0
    assert quantized(0.5) == 0.5
    assert quantized(0.04) == 0.0
    assert quantized(0.05) == pytest.approx(1 / LEVEL_STEPS)
    assert quantized(0.97) == 1.0


def test_quantized_stays_within_the_range() -> None:
    assert quantized(-3.0) == 0.0
    assert quantized(3.0) == 1.0
