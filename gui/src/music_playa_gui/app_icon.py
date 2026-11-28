"""The application icon: the white logo on a rounded square filled with the synthwave gradient.

It is drawn at startup, at several sizes, so the window manager can pick the one that fits
(a small one for a taskbar, a large one for an alt-tab list).
"""

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QImage, QLinearGradient, QPainter, QPainterPath, QPixmap

from music_playa_gui.imaging import scaled_smooth
from music_playa_gui.logo import ASSET
from music_playa_gui.theme import SYNTHWAVE_GRADIENT

SIZES = (16, 24, 32, 48, 64, 128, 256)
CORNER_RADIUS = 0.22  # share of the side
LOGO_SHARE = 0.68  # share of the side taken by the logo


def icon_image(side: int) -> QImage:
    """The icon as a side x side image; the corners outside the rounded square are transparent."""
    image = QImage(side, side, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    radius = side * CORNER_RADIUS
    shape = QPainterPath()
    shape.addRoundedRect(QRectF(0, 0, side, side), radius, radius)
    gradient = QLinearGradient(0, 0, side, side)
    for index, colour in enumerate(SYNTHWAVE_GRADIENT):
        gradient.setColorAt(index / (len(SYNTHWAVE_GRADIENT) - 1), QColor(colour))
    painter.fillPath(shape, gradient)

    logo = QImage(str(ASSET))
    if not logo.isNull():
        scale = side * LOGO_SHARE / max(logo.width(), logo.height())
        logo = scaled_smooth(
            logo, max(1, round(logo.width() * scale)), max(1, round(logo.height() * scale))
        )
        painter.drawImage((side - logo.width()) // 2, (side - logo.height()) // 2, logo)
    painter.end()
    return image


def app_icon() -> QIcon:
    icon = QIcon()
    for side in SIZES:
        icon.addPixmap(QPixmap.fromImage(icon_image(side)))
    return icon
