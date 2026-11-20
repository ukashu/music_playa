import time
from pathlib import Path


class AudioEngine:
    """Temporary in-memory implementation of the audio engine seam.

    Replace this implementation with a SoLoud-backed engine later. The public
    operations match the internal AudioEngine protocol used by MemoryPlayer.
    """

    def __init__(self) -> None:
        self._loaded_path: Path | None = None
        self._position = 0.0
        self._duration = 0.0
        self._playing = False
        self._played_at: float | None = None
        self._volume = 1.0

    @property
    def position(self) -> float:
        if self._playing and self._played_at is not None:
            elapsed = time.monotonic() - self._played_at
            return min(self._duration, self._position + elapsed)
        return self._position

    @property
    def duration(self) -> float:
        return self._duration

    @property
    def is_playing(self) -> bool:
        return self._playing

    def load(self, path: Path) -> float:
        self.stop()
        self._loaded_path = path
        self._duration = 180.0
        return self._duration

    def play(self) -> None:
        if self._loaded_path is None:
            return
        if not self._playing:
            if self.position >= self._duration:
                self._position = 0.0
            self._played_at = time.monotonic()
            self._playing = True

    def pause(self) -> None:
        if self._playing:
            self._position = self.position
            self._played_at = None
            self._playing = False

    def stop(self) -> None:
        self._position = 0.0
        self._played_at = None
        self._playing = False

    def seek(self, position: float) -> None:
        self._position = min(max(position, 0.0), self._duration)
        if self._playing:
            self._played_at = time.monotonic()

    def set_volume(self, volume: float) -> None:
        self._volume = min(max(volume, 0.0), 1.0)
