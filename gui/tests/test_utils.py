import pytest

from music_playa_gui.utils import advance_angle, clamp, format_time


@pytest.mark.parametrize(
    ("seconds", "text"),
    [
        (0, "0:00"),
        (5, "0:05"),
        (59, "0:59"),
        (60, "1:00"),
        (61.9, "1:01"),
        (599, "9:59"),
        (3599, "59:59"),
        (3600, "60:00"),
        (-12, "0:00"),
    ],
)
def test_format_time(seconds: float, text: str) -> None:
    assert format_time(seconds) == text


@pytest.mark.parametrize(
    ("value", "expected"),
    [(-1, 0), (0, 0), (5, 5), (10, 10), (11, 10)],
)
def test_clamp_int(value: int, expected: int) -> None:
    assert clamp(value, 0, 10) == expected


def test_clamp_float() -> None:
    assert clamp(0.25, 0.0, 1.0) == 0.25
    assert clamp(-0.5, 0.0, 1.0) == 0.0
    assert clamp(1.5, 0.0, 1.0) == 1.0


@pytest.mark.parametrize(
    ("angle", "elapsed", "period", "expected"),
    [
        (0.0, 1.0, 4.0, 90.0),
        (90.0, 1.0, 4.0, 180.0),
        (0.0, 2.0, 8.0, 90.0),
        (350.0, 1.0, 4.0, 80.0),
        (0.0, 4.0, 4.0, 0.0),
        (10.0, 0.0, 4.0, 10.0),
        (10.0, 9.0, 4.0, 100.0),
    ],
)
def test_advance_angle(angle: float, elapsed: float, period: float, expected: float) -> None:
    assert advance_angle(angle, elapsed, period) == pytest.approx(expected)


def test_advance_angle_does_not_turn_back_when_the_clock_goes_backwards() -> None:
    assert advance_angle(45.0, -3.0, 4.0) == 45.0
