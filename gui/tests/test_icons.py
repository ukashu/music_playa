import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from music_playa_gui.widgets.icons import ICON_PX, Icon, make_icon, stroke_pen


@pytest.mark.parametrize("kind", list(Icon))
def test_every_icon_is_drawn_in_its_colour(kind: Icon) -> None:
    image = make_icon(kind, "#00E5FF").pixmap(ICON_PX, ICON_PX).toImage()
    assert (image.width(), image.height()) == (ICON_PX, ICON_PX)
    assert image.pixelColor(0, 0).alpha() == 0
    opaque = [
        image.pixelColor(x, y)
        for x in range(ICON_PX)
        for y in range(ICON_PX)
        if image.pixelColor(x, y).alpha() == 255
    ]
    assert opaque
    assert all(c.red() < 40 and c.blue() > 200 for c in opaque)


def test_repeat_one_differs_from_repeat() -> None:
    repeat = make_icon(Icon.REPEAT, "#FFFFFF").pixmap(ICON_PX, ICON_PX).toImage()
    repeat_one = make_icon(Icon.REPEAT_ONE, "#FFFFFF").pixmap(ICON_PX, ICON_PX).toImage()
    assert repeat != repeat_one


def test_stroke_pen() -> None:
    pen = stroke_pen(QColor("red"), 1.5)
    assert pen.color() == QColor("red")
    assert pen.widthF() == 1.5
    assert pen.capStyle() is Qt.PenCapStyle.RoundCap
    assert pen.joinStyle() is Qt.PenJoinStyle.RoundJoin
    assert stroke_pen(QColor("red")).widthF() == 2.0
