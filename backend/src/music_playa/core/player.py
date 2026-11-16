import time

from music_playa.core.queue import PlayQueue
from music_playa.events import EventBus
from music_playa.interfaces import PlaybackListener
from music_playa.models import PlaybackMode, PlaybackState, Track


class MemoryPlayer:
    """In-memory player. Position advances on a monotonic clock while playing."""

    def __init__(self, tracks: list[Track], events: EventBus) -> None:
        self._queue = PlayQueue(tracks)
        self._events = events
        self._state = PlaybackState.STOPPED
        self._position = 0.0
        self._played_at: float | None = None
        self._volume = 1.0
        self._duration = 180.0

    @property
    def current(self) -> Track | None:
        return self._queue.current

    @property
    def position(self) -> float:
        if self._state is PlaybackState.PLAYING and self._played_at is not None:
            elapsed = time.monotonic() - self._played_at
            return min(self._duration, self._position + elapsed)
        return self._position

    @property
    def mode(self) -> PlaybackMode:
        return self._queue.mode

    @mode.setter
    def mode(self, mode: PlaybackMode) -> None:
        self._queue.mode = mode
        self._emit()

    def play(self) -> None:
        if self.current is None:
            return
        if self._state is not PlaybackState.PLAYING:
            self._state = PlaybackState.PLAYING
            self._played_at = time.monotonic()
        self._emit()

    def pause(self) -> None:
        if self._state is PlaybackState.PLAYING:
            self._position = self.position
            self._played_at = None
            self._state = PlaybackState.PAUSED
        self._emit()

    def next(self) -> None:
        self._queue.next()
        self._restart_position()
        self._emit()

    def previous(self) -> None:
        self._queue.previous()
        self._restart_position()
        self._emit()

    def seek(self, position: float) -> None:
        self._position = min(max(position, 0.0), self._duration)
        if self._state is PlaybackState.PLAYING:
            self._played_at = time.monotonic()
        self._emit()

    def set_volume(self, volume: float) -> None:
        self._volume = min(max(volume, 0.0), 1.0)
        self._emit()

    def add_listener(self, listener: PlaybackListener) -> None:
        self._events.add(listener)

    def _restart_position(self) -> None:
        self._position = 0.0
        self._played_at = time.monotonic() if self._state is PlaybackState.PLAYING else None

    def _emit(self) -> None:
        self._events.notify_track(self.current)
        self._events.notify_progress(self.position, self._duration)
