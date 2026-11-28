from pathlib import Path

import pytest
from conftest import make_tracks
from PySide6.QtCore import QAbstractAnimation, QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QAbstractItemView, QApplication

from music_playa.models import Track
from music_playa_gui.i18n import translator
from music_playa_gui.widgets.library_view import (
    DURATION_COLUMN,
    INDEX_COLUMN,
    TITLE_COLUMN,
    WHEEL_MS,
    WHEEL_STEP,
    LibraryView,
)


def _selected_rows(view: LibraryView) -> list[int]:
    return [index.row() for index in view.selectionModel().selectedRows()]


def test_rows_and_texts() -> None:
    tracks = make_tracks(3)
    view = LibraryView()
    view.set_tracks(tracks)
    assert view.rowCount() == 3
    assert view.item(0, INDEX_COLUMN).text() == "1"
    assert view.item(1, TITLE_COLUMN).text() == "Song 1\nArtist"
    assert view.item(1, DURATION_COLUMN).text() == "2:02"
    assert view.item(2, TITLE_COLUMN).toolTip() == "Song 2\nArtist - Album"


@pytest.mark.parametrize(
    ("track_number", "shown"),
    [
        ("7", "7"),
        ("03", "3"),
        ("3/12", "3"),
        (" 4 /9", "4"),
        ("", "2"),
        ("x", "2"),
        ("/12", "2"),
    ],
)
def test_number_column_shows_the_track_number_from_the_tags(track_number: str, shown: str) -> None:
    track = Track(Path("/music/a.mp3"), "Song", "Artist", "Album", 60.0, track_number)
    view = LibraryView()
    view.set_tracks([make_tracks(1)[0], track])
    # The row of the track is 2 (row index 1), used when the tag has no usable number.
    assert view.item(1, INDEX_COLUMN).text() == shown


def test_set_tracks_replaces_rows() -> None:
    view = LibraryView()
    view.set_tracks(make_tracks(5))
    view.set_tracks(make_tracks(2))
    assert view.rowCount() == 2


def test_headers_are_translated() -> None:
    view = LibraryView()
    assert view.horizontalHeaderItem(TITLE_COLUMN).text() == "Tytuł"
    translator.set_language("en")
    assert view.horizontalHeaderItem(TITLE_COLUMN).text() == "Title"
    assert view.horizontalHeaderItem(DURATION_COLUMN).text() == "Time"


def test_highlight_selects_and_clears() -> None:
    tracks = make_tracks(4)
    view = LibraryView()
    view.set_tracks(tracks)
    view.highlight_track(tracks[2])
    assert _selected_rows(view) == [2]
    view.highlight_track(tracks[3])
    assert _selected_rows(view) == [3]
    view.highlight_track(None)
    assert _selected_rows(view) == []


def test_unknown_track_clears_the_selection() -> None:
    tracks = make_tracks(2)
    view = LibraryView()
    view.set_tracks(tracks)
    view.highlight_track(tracks[0])
    view.highlight_track(make_tracks(5)[4])
    assert _selected_rows(view) == []


def _scrollable() -> LibraryView:
    view = LibraryView()
    view.set_tracks(make_tracks(40))
    view.resize(300, 200)
    view.show()
    QApplication.processEvents()
    assert view.verticalScrollBar().maximum() > WHEEL_STEP
    return view


def _wheel(view: LibraryView, angle_y: int = 0, pixel_y: int = 0) -> None:
    event = QWheelEvent(
        QPointF(20, 20),
        view.mapToGlobal(QPointF(20, 20)),
        QPoint(0, pixel_y),
        QPoint(0, angle_y),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )
    QApplication.sendEvent(view.viewport(), event)


def test_list_scrolls_by_pixels() -> None:
    view = _scrollable()
    assert view.verticalScrollMode() is QAbstractItemView.ScrollMode.ScrollPerPixel
    view.close()


def test_mouse_wheel_eases_instead_of_jumping() -> None:
    view = _scrollable()
    bar = view.verticalScrollBar()
    _wheel(view, angle_y=-120)
    assert view._wheel_scroll.state() is QAbstractAnimation.State.Running
    assert bar.value() < WHEEL_STEP
    view._wheel_scroll.setCurrentTime(WHEEL_MS)
    assert bar.value() == WHEEL_STEP
    view.close()


def test_a_second_notch_continues_from_the_target() -> None:
    view = _scrollable()
    bar = view.verticalScrollBar()
    _wheel(view, angle_y=-120)
    _wheel(view, angle_y=-120)
    view._wheel_scroll.setCurrentTime(WHEEL_MS)
    assert bar.value() == 2 * WHEEL_STEP
    view.close()


def test_trackpad_pixels_move_at_once() -> None:
    view = _scrollable()
    bar = view.verticalScrollBar()
    _wheel(view, pixel_y=-17)
    assert bar.value() == 17
    assert view._wheel_scroll.state() is not QAbstractAnimation.State.Running
    view.close()


def test_same_track_is_highlighted_again_after_clearing() -> None:
    """Regression: clearSelection kept the current row, so the same track stayed unselected."""
    tracks = make_tracks(3)
    view = LibraryView()
    view.set_tracks(tracks)
    view.highlight_track(tracks[1])
    view.highlight_track(None)
    view.highlight_track(tracks[1])
    assert _selected_rows(view) == [1]


def test_wheel_without_a_notch_does_not_scroll() -> None:
    view = _scrollable()
    bar = view.verticalScrollBar()
    _wheel(view)
    assert view._wheel_scroll.state() is not QAbstractAnimation.State.Running
    assert bar.value() == 0
    view.close()
