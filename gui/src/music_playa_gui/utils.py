"""Small helpers shared by the widgets."""


def format_time(seconds: float) -> str:
    """Seconds as "m:ss"; negative values show as 0:00."""
    minutes, secs = divmod(max(0, int(seconds)), 60)
    return f"{minutes}:{secs:02d}"


def clamp[T: (int, float)](value: T, low: T, high: T) -> T:
    """The value limited to the range low..high."""
    return min(max(value, low), high)
