import random

from music_playa.models import PlaybackMode, RepeatMode, Track


class PlayQueue:
    def __init__(self, tracks: list[Track]) -> None:
        self._tracks = list(tracks)
        self._index = 0 if tracks else -1
        self._mode = PlaybackMode.IN_ORDER
        self._repeat = RepeatMode.OFF

    @property
    def mode(self) -> PlaybackMode:
        return self._mode

    @mode.setter
    def mode(self, mode: PlaybackMode) -> None:
        self._mode = mode

    @property
    def repeat(self) -> RepeatMode:
        return self._repeat

    @repeat.setter
    def repeat(self, repeat: RepeatMode) -> None:
        self._repeat = repeat

    @property
    def current(self) -> Track | None:
        if self._index < 0 or self._index >= len(self._tracks):
            return None
        return self._tracks[self._index]

    def select(self, track: Track) -> Track | None:
        for index, candidate in enumerate(self._tracks):
            if candidate is track or candidate == track:
                self._index = index
                return candidate
        return self.current

    def rewind(self) -> Track | None:
        """Move back to the first track of the list (no-op for an empty list)."""
        if self._tracks:
            self._index = 0
        return self.current

    def has_next(self) -> bool:
        """Whether a track ends the queue with a next one to play.

        Used when a track ends naturally. With repeat ALL the queue never runs out.
        """
        if not self._tracks:
            return False
        if self._repeat is RepeatMode.ALL:
            return True
        if self._mode is PlaybackMode.SHUFFLE:
            return len(self._tracks) > 1
        return self._index + 1 < len(self._tracks)

    def next(self) -> Track | None:
        if not self._tracks:
            return None
        if self._mode is PlaybackMode.SHUFFLE:
            if len(self._tracks) == 1:
                return self.current
            choices = [index for index in range(len(self._tracks)) if index != self._index]
            self._index = random.choice(choices)
        else:
            # A manual "next" on the last track returns to the first one, whatever the
            # repeat mode. Ending on its own is governed by has_next() instead.
            self._index = (self._index + 1) % len(self._tracks)
        return self.current

    def previous(self) -> Track | None:
        if not self._tracks:
            return None
        if self._index > 0:
            self._index -= 1
        elif self._repeat is RepeatMode.ALL:
            self._index = len(self._tracks) - 1
        return self.current
