from music_playa_gui.i18n import translator
from music_playa_gui.widgets.library_view import LibraryView
from music_playa_gui.widgets.sidebar import Sidebar


def test_track_count_is_translated() -> None:
    sidebar = Sidebar(LibraryView(), 5)
    assert sidebar._count.text() == "5 utworów"
    translator.set_language("en")
    assert sidebar._count.text() == "5 tracks"


def test_flamingo_is_rebuilt_for_a_new_size_or_ratio() -> None:
    sidebar = Sidebar(LibraryView(), 1)
    sidebar.resize(340, 700)
    first = sidebar._flamingo_pixmap()
    assert sidebar._flamingo_pixmap() is first
    sidebar.devicePixelRatioF = lambda: 2.0
    scaled = sidebar._flamingo_pixmap()
    assert scaled is not first
    assert scaled.devicePixelRatio() == 2.0
    assert scaled.width() == 680
