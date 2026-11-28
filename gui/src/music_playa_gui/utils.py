"""Small helpers shared by the widgets."""


def format_time(seconds: float) -> str:
    """Seconds as "m:ss"; negative values show as 0:00."""
    minutes, secs = divmod(max(0, int(seconds)), 60)
    return f"{minutes}:{secs:02d}"


def advance_angle(angle: float, elapsed: float, period: float) -> float:
    """The angle in degrees (0 up to 360) after a turn of one full circle per period seconds.

    A negative elapsed time (a clock that went backwards) does not turn the angle back.
    """
    return (angle + 360.0 * max(elapsed, 0.0) / period) % 360.0


def clamp[T: (int, float)](value: T, low: T, high: T) -> T:
    """The value limited to the range low..high."""
    return min(max(value, low), high)
