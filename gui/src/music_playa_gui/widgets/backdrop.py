"""Decorative backdrops painted once per size and cached by the widgets.

- scanlines_pixmap: the fine horizontal lines of a CRT / VHS picture, copied from
  the reference texture (bright lines over dark gaps).
  Used as a filter over the cover.
- grid_pixmap: a perspective grid whose lines converge on a vanishing point, which
  the player bar places at the centre of the window. Used behind the player bar.

They return transparent pixmaps, so they can be drawn over anything. The
constants below are the knobs for tuning the look.
"""

import math

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)

from music_playa_gui.theme import PINK

# Scanlines, based on the reference texture (8 px period, 3 px lines), made coarser
SCANLINE_PERIOD = 12.0  # distance between two bright lines, in pixels
SCANLINE_LINE = 5.0  # thickness of each bright line, in pixels
SCANLINE_COLOR = (150, 166, 131)  # the muted yellow-green of the lit lines
SCANLINE_LINE_ALPHA = 45  # 0..255, how strongly the lit lines tint the cover
SCANLINE_GAP_ALPHA = 150  # 0..255, how dark the gaps between lines are

# Grid
GRID_RADIAL_SPACING = 64.0  # distance between radial lines on the bottom edge
GRID_HORIZONTAL_LINES = 5  # horizontal lines, spaced by perspective
GRID_ALPHA_TOP = 100  # 0..255, near the horizon
GRID_ALPHA_BOTTOM = 40  # 0..255, at the bottom edge
# Radial lines reach this many widths to each side. Lines far from the centre are
# almost horizontal and pile up at the horizon, so this is kept small.
GRID_REACH = 1.5

def _blank(size: QSize, ratio: float) -> QPixmap:
    pixmap = QPixmap(round(size.width() * ratio), round(size.height() * ratio))
    pixmap.setDevicePixelRatio(ratio)
    pixmap.fill(Qt.GlobalColor.transparent)
    return pixmap


def scanlines_pixmap(size: QSize, ratio: float = 1.0) -> QPixmap:
    pixmap = _blank(size, ratio)
    if size.isEmpty():
        return pixmap

    width = float(size.width())
    height = float(size.height())
    painter = QPainter(pixmap)
    painter.setPen(Qt.PenStyle.NoPen)

    # Dark gaps first, then the lit lines on top of them.
    gap = QColor(0, 0, 0, SCANLINE_GAP_ALPHA)
    painter.fillRect(QRectF(0, 0, width, height), gap)
    lit = QColor(*SCANLINE_COLOR)
    lit.setAlpha(SCANLINE_LINE_ALPHA)
    y = 0.0
    while y < height:
        painter.fillRect(QRectF(0, y, width, SCANLINE_LINE), lit)
        y += SCANLINE_PERIOD
    painter.end()
    return pixmap


def grid_pixmap(
    size: QSize,
    ratio: float = 1.0,
    vanishing_x: float | None = None,
    horizon: float = 1.0,
) -> QPixmap:
    """A perspective grid; its radial lines point at (vanishing_x, -horizon).

    The vanishing point is given in pixmap coordinates: vanishing_x along the width
    (the middle by default) and horizon as the distance above the top edge. Lines
    are clipped to the pixmap, so a distant vanishing point gives almost vertical
    lines that still aim at it.
    """
    pixmap = _blank(size, ratio)
    if size.isEmpty():
        return pixmap

    width = float(size.width())
    height = float(size.height())
    centre = width / 2 if vanishing_x is None else vanishing_x
    horizon = max(horizon, 1.0)
    depth = horizon + height  # distance from the vanishing point to the bottom edge

    # The gradient fades the lines from strong at the top to faint at the bottom.
    top = QColor(PINK)
    top.setAlpha(GRID_ALPHA_TOP)
    bottom = QColor(PINK)
    bottom.setAlpha(GRID_ALPHA_BOTTOM)
    gradient = QLinearGradient(0, 0, 0, height)
    gradient.setColorAt(0.0, top)
    gradient.setColorAt(1.0, bottom)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QBrush(gradient), 1.0))

    # Radial lines: each runs from the vanishing point to a bottom position, which is
    # spread around the vanishing x. The top end is scaled to match the perspective.
    shrink = horizon / depth
    count = math.ceil(width * GRID_REACH / GRID_RADIAL_SPACING)
    for index in range(-count, count + 1):
        offset = index * GRID_RADIAL_SPACING
        painter.drawLine(
            QPointF(centre + offset * shrink, 0.0), QPointF(centre + offset, height)
        )

    # Horizontal lines are evenly spaced in depth, so they bunch up toward the horizon.
    far = depth / horizon
    for step in range(1, GRID_HORIZONTAL_LINES + 1):
        z = 1.0 + (far - 1.0) * step / (GRID_HORIZONTAL_LINES + 1)
        y = min(max(depth / z - horizon, 0.5), height - 0.5)
        painter.drawLine(QPointF(0, y), QPointF(width, y))
    painter.end()
    return pixmap
