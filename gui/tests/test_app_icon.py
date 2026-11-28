from pathlib import Path

from PySide6.QtCore import QSize

from music_playa_gui import app_icon as icon_module
from music_playa_gui.app_icon import SIZES, app_icon, icon_image


def _white_pixels(image) -> int:
    count = 0
    for x in range(image.width()):
        for y in range(image.height()):
            colour = image.pixelColor(x, y)
            if colour.alpha() == 255 and min(colour.red(), colour.green(), colour.blue()) > 240:
                count += 1
    return count


def test_icon_has_every_size() -> None:
    icon = app_icon()
    assert not icon.isNull()
    assert {(size.width(), size.height()) for size in icon.availableSizes()} == {
        (side, side) for side in SIZES
    }
    assert icon.pixmap(QSize(64, 64)).size() == QSize(64, 64)


def test_corners_are_transparent_and_the_edges_are_not() -> None:
    image = icon_image(128)
    assert image.pixelColor(0, 0).alpha() == 0
    assert image.pixelColor(127, 127).alpha() == 0
    assert image.pixelColor(64, 2).alpha() == 255


def test_background_is_the_gradient() -> None:
    image = icon_image(128)
    # Points near the corners, outside the logo: cyan at the top left, pink at the bottom right.
    top_left, bottom_right = image.pixelColor(12, 12), image.pixelColor(115, 115)
    assert top_left.red() < 100 and top_left.blue() > 200
    assert bottom_right.red() > 200 and bottom_right.green() < 120


def test_logo_is_drawn_in_white() -> None:
    assert _white_pixels(icon_image(128)) > 1000


def test_missing_logo_leaves_only_the_background(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(icon_module, "ASSET", tmp_path / "missing.png")
    image = icon_image(64)
    assert _white_pixels(image) == 0
    assert image.pixelColor(32, 32).alpha() == 255
