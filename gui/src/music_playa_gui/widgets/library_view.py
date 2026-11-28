from PySide6.QtCore import QAbstractAnimation, QEasingCurve, QPropertyAnimation, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
)

from music_playa.models import Track
from music_playa_gui.i18n import tr, translator
from music_playa_gui.utils import clamp, format_time

ROW_HEIGHT = 56
# One notch of a mouse wheel. It is eased in, because a notch arrives as a single jump.
WHEEL_STEP = 48
WHEEL_MS = 160
INDEX_COLUMN, TITLE_COLUMN, DURATION_COLUMN = range(3)


def _number_text(track: Track, row: int) -> str:
    """The track number from the tags ("3" or "3/12"), or the row number without one."""
    number = track.track_number.split("/")[0].strip()
    return str(int(number)) if number.isdecimal() else str(row + 1)


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
        # The default scrolls a whole row per step, so the list jumps instead of sliding.
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self._wheel_scroll = QPropertyAnimation(self.verticalScrollBar(), b"value", self)
        self._wheel_scroll.setDuration(WHEEL_MS)
        self._wheel_scroll.setEasingCurve(QEasingCurve.Type.OutCubic)
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

    def wheelEvent(self, event: QWheelEvent) -> None:
        bar = self.verticalScrollBar()
        pixels = event.pixelDelta().y()
        if pixels:
            # A trackpad already reports every pixel, so easing it would only add lag.
            self._wheel_scroll.stop()
            bar.setValue(bar.value() - pixels)
            event.accept()
            return
        notches = event.angleDelta().y() / 120
        if notches == 0 or bar.maximum() == bar.minimum():
            super().wheelEvent(event)
            return
        origin = (
            int(self._wheel_scroll.endValue())
            if self._wheel_scroll.state() is QAbstractAnimation.State.Running
            else bar.value()
        )
        target = clamp(round(origin - notches * WHEEL_STEP), bar.minimum(), bar.maximum())
        self._wheel_scroll.stop()
        self._wheel_scroll.setStartValue(bar.value())
        self._wheel_scroll.setEndValue(target)
        self._wheel_scroll.start()
        event.accept()

    def retranslate(self) -> None:
        self.setHorizontalHeaderLabels(["#", tr("library.title"), tr("library.time")])

    def set_tracks(self, tracks: list[Track]) -> None:
        self._tracks = list(tracks)
        self.setRowCount(len(tracks))
        for row, track in enumerate(tracks):
            values = (
                _number_text(track, row),
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
