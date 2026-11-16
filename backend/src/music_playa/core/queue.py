import random

from music_playa.models import PlaybackMode, Track


class PlayQueue:
    def __init__(self, tracks: list[Track]) -> None:
        self._tracks = list(tracks)
        self._index = 0 if tracks else -1
        self._mode = PlaybackMode.IN_ORDER

    @property
    def mode(self) -> PlaybackMode:
        return self._mode

    @mode.setter
    def mode(self, mode: PlaybackMode) -> None:
        self._mode = mode

    @property
    def current(self) -> Track | None:
        if self._index < 0 or self._index >= len(self._tracks):
            return None
        return self._tracks[self._index]

    def next(self) -> Track | None:
        if not self._tracks:
            return None
        if self._mode is PlaybackMode.SHUFFLE:
            if len(self._tracks) == 1:
                return self.current
            choices = [index for index in range(len(self._tracks)) if index != self._index]
            self._index = random.choice(choices)
        elif self._mode is PlaybackMode.REPEAT:
            self._index = (self._index + 1) % len(self._tracks)
        elif self._index + 1 < len(self._tracks):
            self._index += 1
        return self.current

    def previous(self) -> Track | None:
        if not self._tracks:
            return None
        if self._index > 0:
            self._index -= 1
        elif self._mode is PlaybackMode.REPEAT:
            self._index = len(self._tracks) - 1
        return self.current
