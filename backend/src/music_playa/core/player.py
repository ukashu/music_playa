from music_playa.core.audio_engine import AudioEngine as ConcreteAudioEngine
from music_playa.core.queue import PlayQueue
from music_playa.events import EventBus
from music_playa.interfaces import AudioEngine, PlaybackListener
from music_playa.models import PlaybackMode, PlaybackState, Track


class MemoryPlayer:
    """Player implementation that delegates audio operations to an engine."""

    def __init__(
        self,
        tracks: list[Track],
        events: EventBus,
        engine: AudioEngine | None = None,
    ) -> None:
        self._queue = PlayQueue(tracks)
        self._events = events
        self._engine = engine if engine is not None else ConcreteAudioEngine()
        self._state = PlaybackState.STOPPED
        self._volume = 1.0
        self._loaded_track: Track | None = None

    @property
    def current(self) -> Track | None:
        return self._queue.current

    @property
    def position(self) -> float:
        return self._engine.position

    @property
    def duration(self) -> float:
        return self._engine.duration

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
        if self._loaded_track is not self.current:
            self._engine.load(self.current.path)
            self._loaded_track = self.current
        if self._state is not PlaybackState.PLAYING:
            self._state = PlaybackState.PLAYING
        self._engine.play()
        self._emit()

    def pause(self) -> None:
        if self._state is PlaybackState.PLAYING:
            self._engine.pause()
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
        self._engine.seek(position)
        self._emit()

    def set_volume(self, volume: float) -> None:
        self._volume = min(max(volume, 0.0), 1.0)
        self._engine.set_volume(self._volume)
        self._emit()

    def add_listener(self, listener: PlaybackListener) -> None:
        self._events.add(listener)

    def _restart_position(self) -> None:
        self._engine.stop()
        self._loaded_track = None
        if self.current is not None:
            self._engine.load(self.current.path)
            self._loaded_track = self.current
            if self._state is PlaybackState.PLAYING:
                self._engine.play()

    def _emit(self) -> None:
        self._events.notify_track(self.current)
        self._events.notify_progress(self.position, self.duration)
