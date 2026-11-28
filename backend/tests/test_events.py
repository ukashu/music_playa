from pathlib import Path

from music_playa.events import EventBus
from music_playa.models import Track


class _Listener:
    def __init__(self, log: list[tuple[str, object]], name: str) -> None:
        self._log = log
        self._name = name

    def on_progress(self, position: float, duration: float) -> None:
        self._log.append((self._name, (position, duration)))

    def on_track(self, track: Track | None) -> None:
        self._log.append((self._name, track))


def test_bus_without_listeners_ignores_notifications() -> None:
    bus = EventBus()

    bus.notify_progress(1.0, 2.0)
    bus.notify_track(None)


def test_bus_notifies_every_listener_in_the_order_they_were_added() -> None:
    log: list[tuple[str, object]] = []
    bus = EventBus()
    bus.add(_Listener(log, "first"))
    bus.add(_Listener(log, "second"))
    track = Track(Path("a.mp3"), "a")

    bus.notify_progress(12.5, 60.0)
    bus.notify_track(track)
    bus.notify_track(None)

    assert log == [
        ("first", (12.5, 60.0)),
        ("second", (12.5, 60.0)),
        ("first", track),
        ("second", track),
        ("first", None),
        ("second", None),
    ]
