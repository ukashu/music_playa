import pytest
from PySide6.QtGui import QColor

from music_playa_gui.i18n import translator
from music_playa_gui.theme import CYAN, PINK
from music_playa_gui.widgets.library_view import LibraryView
from music_playa_gui.widgets.sidebar import GLOW_BLUR_MAX, GLOW_BLUR_MIN, Sidebar


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


def _pinkness(image) -> int:
    """How much pink the image has (red above green); the plain background has none."""
    return sum(
        max(image.pixelColor(x, y).red() - image.pixelColor(x, y).green(), 0)
        for x in range(0, image.width(), 2)
        for y in range(0, image.height(), 2)
    )


def _sidebar() -> Sidebar:
    sidebar = Sidebar(LibraryView(), 3)
    sidebar.resize(340, 700)
    sidebar.grab()  # the first grab of a new widget is made before its style is applied
    return sidebar


def test_nothing_glows_at_rest() -> None:
    sidebar = _sidebar()
    assert sidebar._glow == 0.0
    assert not sidebar._title_glow.isEnabled()
    assert not sidebar._logo_glow.isEnabled()


def test_the_title_and_the_logo_glow_with_the_level() -> None:
    sidebar = _sidebar()
    sidebar.set_glow(1.0)
    for effect, colour in ((sidebar._title_glow, PINK), (sidebar._logo_glow, CYAN)):
        assert effect.isEnabled()
        assert effect.blurRadius() == GLOW_BLUR_MAX
        assert effect.color().alpha() == 255
        assert effect.color().rgb() == QColor(colour).rgb()
    sidebar.set_glow(0.5)
    assert sidebar._title_glow.blurRadius() == pytest.approx((GLOW_BLUR_MIN + GLOW_BLUR_MAX) / 2)
    assert sidebar._title_glow.color().alpha() == round(255 * 0.5)
    assert sidebar._title_glow.isEnabled()


def test_the_glow_goes_out_at_level_zero() -> None:
    sidebar = _sidebar()
    sidebar.set_glow(0.7)
    sidebar.set_glow(0.0)
    assert not sidebar._title_glow.isEnabled()
    assert not sidebar._logo_glow.isEnabled()


def test_the_level_is_kept_between_zero_and_one() -> None:
    sidebar = _sidebar()
    sidebar.set_glow(3.0)
    assert sidebar._glow == 1.0
    sidebar.set_glow(-1.0)
    assert sidebar._glow == 0.0


def test_the_same_level_does_not_repaint(monkeypatch) -> None:
    sidebar = _sidebar()
    updates: list[int] = []
    monkeypatch.setattr(sidebar, "update", lambda *args: updates.append(1))
    sidebar.set_glow(0.4)
    sidebar.set_glow(0.4)
    assert len(updates) == 1
    sidebar.set_glow(0.5)
    assert len(updates) == 2


def test_the_glowing_flamingo_is_made_once_per_size_and_ratio() -> None:
    sidebar = _sidebar()
    sidebar._flamingo_pixmap()
    glowing = sidebar._glowing_flamingo()
    assert sidebar._glowing_flamingo() is glowing
    assert glowing.size() == sidebar._flamingo_pixmap().size()
    sidebar.devicePixelRatioF = lambda: 2.0
    sidebar._flamingo_pixmap()
    assert sidebar._glowing_flamingo() is not glowing
    assert sidebar._glowing_flamingo().devicePixelRatio() == 2.0


def test_the_flamingo_lights_up_and_goes_back_to_normal() -> None:
    sidebar = _sidebar()
    resting = sidebar.grab().toImage()
    sidebar.set_glow(1.0)
    glowing = sidebar.grab().toImage()
    assert _pinkness(glowing) > _pinkness(resting)
    sidebar.set_glow(0.0)
    assert sidebar.grab().toImage() == resting


def test_a_weaker_bass_lights_the_flamingo_less() -> None:
    sidebar = _sidebar()
    sidebar.set_glow(0.3)
    weak = _pinkness(sidebar.grab().toImage())
    sidebar.set_glow(1.0)
    assert _pinkness(sidebar.grab().toImage()) > weak
