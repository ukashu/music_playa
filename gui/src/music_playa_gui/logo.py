"""The app logo, tinted with the synthwave gradient.

It is the sidebar header icon and the artwork shown when a track has no cover.
"""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QImage, QLinearGradient, QPainter, QPaintEvent, QPixmap
from PySide6.QtWidgets import QWidget

from music_playa_gui.imaging import scaled_smooth, tinted
from music_playa_gui.theme import SYNTHWAVE_GRADIENT

ASSET = Path(__file__).parent / "assets" / "logo_white.png"

_tinted: QImage | None = None


def _tinted_logo() -> QImage:
    """The white logo coloured with the synthwave gradient, from top left to bottom right."""
    source = QImage(str(ASSET))
    if source.isNull():
        return QImage()
    gradient = QLinearGradient(0, 0, source.width(), source.height())
    for index, colour in enumerate(SYNTHWAVE_GRADIENT):
        gradient.setColorAt(index / (len(SYNTHWAVE_GRADIENT) - 1), QColor(colour))
    image = tinted(source, QBrush(gradient))
    # The source edges are hard (the alpha jumps from 0 to full in one pixel), which shows
    # as steps once the logo is shrunk. A half-size round trip softens them by a pixel or two.
    width, height = image.width(), image.height()
    softened = image.scaled(
        width // 2,
        height // 2,
        Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    return softened.scaled(
        width,
        height,
        Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


def _tinted_image() -> QImage:
    """The tinted logo at full size, computed once."""
    global _tinted
    if _tinted is None:
        _tinted = _tinted_logo()
    return _tinted


def _fitted_logo(longest: int) -> QImage:
    """The tinted logo shrunk so that its longer side is longest pixels (null when impossible)."""
    image = _tinted_image()
    if image.isNull() or longest < 1:
        return QImage()
    scale = longest / max(image.width(), image.height())
    width = max(1, round(image.width() * scale))
    height = max(1, round(image.height() * scale))
    return scaled_smooth(image, width, height)


def scaled_logo(longest: int, ratio: float = 1.0) -> QPixmap:
    """The logo fitted inside a square whose side is longest device pixels.

    It is shrunk with scaled_smooth, so its edges stay smooth. The pixmap is marked with
    ratio at the end.
    """
    image = _fitted_logo(longest)
    if image.isNull():
        return QPixmap()
    pixmap = QPixmap.fromImage(image)
    pixmap.setDevicePixelRatio(ratio)
    return pixmap


def covered_logo(cover: QImage, longest: int, ratio: float = 1.0) -> QPixmap:
    """The logo filled with the cover instead of the gradient.

    The cover is scaled to cover the whole logo (the part that does not fit is cropped around
    the centre) and kept only where the logo is opaque, so the logo works as a mask on the
    cover. Sized like scaled_logo.
    """
    shape = _fitted_logo(longest)
    if shape.isNull() or cover.isNull():
        return QPixmap()
    fill = cover.scaled(
        shape.width(),
        shape.height(),
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )
    image = QImage(shape.size(), QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.drawImage((shape.width() - fill.width()) // 2, (shape.height() - fill.height()) // 2, fill)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
    painter.drawImage(0, 0, shape)
    painter.end()
    pixmap = QPixmap.fromImage(image)
    pixmap.setDevicePixelRatio(ratio)
    return pixmap


class LogoWidget(QWidget):
    """The logo at a fixed logical size, always made in the window's device pixels.

    The device pixel ratio of a window can still be 1 when the first resize arrives and
    change a moment later, when the screen reports its real scale. The pixmap is therefore
    checked at paint time and rebuilt when the ratio differs, instead of once at resize.
    """

    def __init__(self, size: int) -> None:
        super().__init__()
        self.setFixedSize(size, size)
        self._pixmap = QPixmap()
        self._ratio = 0.0

    def paintEvent(self, event: QPaintEvent) -> None:
        ratio = self.devicePixelRatioF()
        if ratio != self._ratio:
            self._ratio = ratio
            self._pixmap = scaled_logo(round(self.width() * ratio), ratio)
        if not self._pixmap.isNull():
            painter = QPainter(self)
            painter.drawPixmap(0, 0, self._pixmap)
            painter.end()
