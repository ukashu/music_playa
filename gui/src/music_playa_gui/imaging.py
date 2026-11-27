"""Small image helpers shared by the logo and the flamingo."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPainter

_SMOOTH = Qt.TransformationMode.SmoothTransformation
_IGNORE = Qt.AspectRatioMode.IgnoreAspectRatio


def scaled_smooth(image: QImage, width: int, height: int) -> QImage:
    """The image resized to width x height without jagged edges.

    Qt's smooth scaling only samples a few source pixels, so shrinking a large image in one
    step skips pixels and leaves steps along the edges. The reduction is done in halving
    steps first and the last step is the smooth one.
    """
    while image.width() > 2 * width and image.height() > 2 * height:
        image = image.scaled(image.width() // 2, image.height() // 2, _IGNORE, _SMOOTH)
    return image.scaled(width, height, _IGNORE, _SMOOTH)


def tinted(shape: QImage, colour: QColor) -> QImage:
    """An image of one colour that is opaque only where shape is (its alpha is kept)."""
    image = QImage(shape.size(), QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(colour)
    painter = QPainter(image)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
    painter.drawImage(0, 0, shape)
    painter.end()
    return image
