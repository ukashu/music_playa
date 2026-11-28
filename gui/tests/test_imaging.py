from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QBrush, QColor, QImage, QLinearGradient

from music_playa_gui.imaging import scaled_smooth, tinted


def _shape() -> QImage:
    """Left half opaque white, right half transparent."""
    image = QImage(20, 10, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    for x in range(10):
        for y in range(10):
            image.setPixelColor(x, y, QColor(255, 255, 255, 255))
    return image


def test_scaled_smooth_gives_the_requested_size() -> None:
    image = QImage(1000, 600, QImage.Format.Format_ARGB32)
    image.fill(QColor("red"))
    for width, height in ((100, 60), (499, 301), (1000, 600), (2000, 50)):
        result = scaled_smooth(image, width, height)
        assert (result.width(), result.height()) == (width, height)


def test_scaled_smooth_keeps_a_flat_colour() -> None:
    image = QImage(800, 800, QImage.Format.Format_ARGB32)
    image.fill(QColor(10, 200, 30))
    result = scaled_smooth(image, 37, 37)
    assert result.pixelColor(18, 18) == QColor(10, 200, 30)


def test_tinted_with_a_colour_keeps_the_alpha() -> None:
    result = tinted(_shape(), QColor("#FF2E97"))
    assert result.size() == _shape().size()
    inside = result.pixelColor(2, 5)
    assert inside.alpha() == 255
    assert (inside.red(), inside.green(), inside.blue()) == (0xFF, 0x2E, 0x97)
    assert result.pixelColor(15, 5).alpha() == 0


def test_tinted_with_a_gradient() -> None:
    gradient = QLinearGradient(QPointF(0, 0), QPointF(10, 0))
    gradient.setColorAt(0.0, QColor("blue"))
    gradient.setColorAt(1.0, QColor("red"))
    result = tinted(_shape(), QBrush(gradient))
    left, right = result.pixelColor(0, 5), result.pixelColor(9, 5)
    assert left.blue() > left.red()
    assert right.red() > right.blue()
    assert result.pixelColor(15, 5).alpha() == 0
