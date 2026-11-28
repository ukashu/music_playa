"""Small image helpers shared by the logo and the flamingo."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QImage, QPainter

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


def tinted(shape: QImage, paint: QColor | QBrush) -> QImage:
    """The paint (a colour or a brush, e.g. a gradient) kept only where shape is opaque.

    The alpha of shape is kept, so its transparent background stays transparent.
    """
    image = QImage(shape.size(), QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.fillRect(image.rect(), QBrush(paint))
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
    painter.drawImage(0, 0, shape)
    painter.end()
    return image
