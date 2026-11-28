from conftest import make_tracks

from music_playa_gui.i18n import translator
from music_playa_gui.widgets.library_view import DURATION_COLUMN, INDEX_COLUMN, TITLE_COLUMN, LibraryView


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


def test_same_track_is_highlighted_again_after_clearing() -> None:
    """Regression: clearSelection kept the current row, so the same track stayed unselected."""
    tracks = make_tracks(3)
    view = LibraryView()
    view.set_tracks(tracks)
    view.highlight_track(tracks[1])
    view.highlight_track(None)
    view.highlight_track(tracks[1])
    assert _selected_rows(view) == [1]
