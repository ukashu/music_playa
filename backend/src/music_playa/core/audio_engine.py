from pathlib import Path

import mpv


class AudioEngine:
    """Audio playback engine backed by mpv."""

    def __init__(self) -> None:
        self.player = mpv.MPV()

        self._loaded_path: Path | None = None
        self._position = 0.0
        self._duration = 0.0
        self._playing = False
        self._volume = 1.0

    @property
    def position(self) -> float:
        position = self.player.time_pos
        if position is not None:
            self._position = float(position)
        return self._position

    @property
    def duration(self) -> float:
        duration = self.player.duration
        if duration is not None:
            self._duration = float(duration)
        return self._duration

    @property
    def is_playing(self) -> bool:
        return self._playing

    def load(self, path: Path) -> float:
        self.stop()
        self._loaded_path = path
        self._position = 0.0
        self._duration = 0.0
        self.player.pause = True
        self.player.loadfile(str(path))
        return self.duration

    def play(self) -> None:
        if self._loaded_path is None:
            return
        if not self._playing:
            duration = self.duration
            if duration > 0.0 and self.position >= duration:
                self.seek(0.0)
            self.player.pause = False
            self._playing = True

    def pause(self) -> None:
        if self._playing:
            self._position = self.position
            self.player.pause = True
            self._playing = False

    def stop(self) -> None:
        self.player.stop()
        self._loaded_path = None
        self._position = 0.0
        self._duration = 0.0
        self._playing = False

    def seek(self, position: float) -> None:
        duration = self.duration
        self._position = max(position, 0.0)
        if duration > 0.0:
            self._position = min(self._position, duration)
        if self._loaded_path is not None:
            self.player.seek(
                self._position,
                reference="absolute",
                precision="exact",
            )

    def set_volume(self, volume: float) -> None:
        self._volume = min(max(volume, 0.0), 1.0)
        self.player.volume = self._volume * 100.0
