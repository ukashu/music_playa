from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
)

from music_playa.models import Track
from music_playa_gui.i18n import tr, translator
from music_playa_gui.utils import format_time

ROW_HEIGHT = 56
INDEX_COLUMN, TITLE_COLUMN, DURATION_COLUMN = range(3)


class LibraryView(QTableWidget):
    """Compact list of all tracks: index, title with artist underneath, duration."""

    def __init__(self) -> None:
        super().__init__(0, 3)
        self._tracks: list[Track] = []
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.setShowGrid(False)
        self.verticalHeader().hide()
        self.verticalHeader().setDefaultSectionSize(ROW_HEIGHT)
        header = self.horizontalHeader()
        header.setHighlightSections(False)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(INDEX_COLUMN, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(DURATION_COLUMN, QHeaderView.ResizeMode.Fixed)
        self.setColumnWidth(INDEX_COLUMN, 40)
        self.setColumnWidth(DURATION_COLUMN, 56)
        # The sidebar paints a flamingo behind this list, so the viewport stays clear.
        self.viewport().setAutoFillBackground(False)

        translator.language_changed.connect(self.retranslate)
        self.retranslate()

    def retranslate(self) -> None:
        self.setHorizontalHeaderLabels(["#", tr("library.title"), tr("library.time")])

    def set_tracks(self, tracks: list[Track]) -> None:
        self._tracks = list(tracks)
        self.setRowCount(len(tracks))
        for row, track in enumerate(tracks):
            values = (
                str(row + 1),
                f"{track.title}\n{track.artist}",
                format_time(track.duration),
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setToolTip(f"{track.title}\n{track.artist} - {track.album}")
                self.setItem(row, column, item)

    def highlight_track(self, track: Track | None) -> None:
        """Select the row of the given track, or clear the selection."""
        if track is None or track not in self._tracks:
            self.clearSelection()
            return
        row = self._tracks.index(track)
        # clearSelection keeps the current row, so the selection itself is compared.
        if [index.row() for index in self.selectionModel().selectedRows()] != [row]:
            self.selectRow(row)
            self.scrollToItem(self.item(row, TITLE_COLUMN))
