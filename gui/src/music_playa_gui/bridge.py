from PySide6.QtCore import QObject, Signal

from music_playa.models import Track


class PlaybackBridge(QObject):
    """PlaybackListener that forwards callbacks as Qt signals."""

    track_changed = Signal(object)
    progress_changed = Signal(float, float)

    def on_track(self, track: Track | None) -> None:
        self.track_changed.emit(track)

    def on_progress(self, position: float, duration: float) -> None:
        self.progress_changed.emit(position, duration)
