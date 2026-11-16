from music_playa.interfaces import PlaybackListener
from music_playa.models import Track


class EventBus:
    def __init__(self) -> None:
        self._listeners: list[PlaybackListener] = []

    def add(self, listener: PlaybackListener) -> None:
        self._listeners.append(listener)

    def notify_progress(self, position: float, duration: float) -> None:
        for listener in self._listeners:
            listener.on_progress(position, duration)

    def notify_track(self, track: Track | None) -> None:
        for listener in self._listeners:
            listener.on_track(track)
