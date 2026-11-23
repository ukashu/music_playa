from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
)

from music_playa.models import Track


class LibraryView(QTableWidget):
    def __init__(self) -> None:
        super().__init__(0, 5)
        self.setHorizontalHeaderLabels(["#", "Title", "Artist", "Album", "Duration"])
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.verticalHeader().hide()
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

    def set_tracks(self, tracks: list[Track]) -> None:
        self.setRowCount(len(tracks))
        for row, track in enumerate(tracks):
            values = (
                track.track_number,
                track.title,
                track.artist,
                track.album,
                _format_duration(track.duration),
            )
            for column, value in enumerate(values):
                self.setItem(row, column, QTableWidgetItem(value))


def _format_duration(duration: float) -> str:
    minutes, seconds = divmod(max(0, int(duration)), 60)
    return f"{minutes}:{seconds:02d}"
