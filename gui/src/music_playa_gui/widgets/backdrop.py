"""Decorative backdrop painted once per size and cached by the player bar.

grid_pixmap: a perspective grid whose lines converge on a vanishing point, which
the player bar places at the centre of the window.

It returns a transparent pixmap, so it can be drawn over anything. The
constants below are the knobs for tuning the look.
"""

import math

from PySide6.QtCore import QPointF, QSize, Qt
from PySide6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPen, QPixmap

from music_playa_gui.theme import PINK
from music_playa_gui.utils import clamp

# Grid
GRID_RADIAL_SPACING = 64.0  # distance between radial lines on the bottom edge
GRID_HORIZONTAL_LINES = 5  # horizontal lines, spaced by perspective
GRID_ALPHA_TOP = 100  # 0..255, near the horizon
GRID_ALPHA_BOTTOM = 40  # 0..255, at the bottom edge
# Radial lines reach this many widths to each side. Lines far from the centre are
# almost horizontal and pile up at the horizon, so this is kept small.
GRID_REACH = 1.5
# The glowing grid (see grid_pixmap) has stronger and thicker lines, with a faint wide halo under
# them. The player bar draws it over the normal grid, more or less opaque with the bass.
GRID_GLOW_BOOST = 3.0
GRID_LINE_WIDTH = 1.0
GRID_GLOW_WIDTH_GAIN = 0.3  # extra line width for each unit of boost above 1
GRID_HALO_WIDTH = 5.0
GRID_HALO_ALPHA = 0.25  # of the (boosted) alpha of the lines

def _blank(size: QSize, ratio: float) -> QPixmap:
    pixmap = QPixmap(round(size.width() * ratio), round(size.height() * ratio))
    pixmap.setDevicePixelRatio(ratio)
    pixmap.fill(Qt.GlobalColor.transparent)
    return pixmap


def _fade(height: float, scale: float) -> QLinearGradient:
    """The gradient that fades the lines from strong at the top to faint at the bottom."""
    top = QColor(PINK)
    top.setAlpha(min(round(GRID_ALPHA_TOP * scale), 255))
    bottom = QColor(PINK)
    bottom.setAlpha(min(round(GRID_ALPHA_BOTTOM * scale), 255))
    gradient = QLinearGradient(0, 0, 0, height)
    gradient.setColorAt(0.0, top)
    gradient.setColorAt(1.0, bottom)
    return gradient


def _passes(boost: float) -> list[tuple[float, float]]:
    """(pen width, alpha scale) of every stroke of the grid, the wide halo first."""
    passes = [(GRID_LINE_WIDTH + (boost - 1.0) * GRID_GLOW_WIDTH_GAIN, boost)]
    if boost > 1.0:
        passes.insert(0, (GRID_HALO_WIDTH, boost * GRID_HALO_ALPHA))
    return passes


def grid_pixmap(
    size: QSize, ratio: float, vanishing_x: float, horizon: float, boost: float = 1.0
) -> QPixmap:
    """A perspective grid; its radial lines point at (vanishing_x, -horizon).

    With a boost above 1 the lines are that many times stronger (up to full opacity) and a bit
    thicker, and a faint wide halo is drawn under them: the grid as it looks when it glows.

    The vanishing point is given in pixmap coordinates: vanishing_x along the width
    and horizon as the distance above the top edge (at least 1). Lines
    are clipped to the pixmap, so a distant vanishing point gives almost vertical
    lines that still aim at it.
    """
    pixmap = _blank(size, ratio)
    if size.isEmpty():
        return pixmap

    width = float(size.width())
    height = float(size.height())
    horizon = max(horizon, 1.0)
    depth = horizon + height  # distance from the vanishing point to the bottom edge

    lines = []

    # Radial lines: each runs from the vanishing point to a bottom position, which is
    # spread around the vanishing x. The top end is scaled to match the perspective.
    shrink = horizon / depth
    count = math.ceil(width * GRID_REACH / GRID_RADIAL_SPACING)
    for index in range(-count, count + 1):
        offset = index * GRID_RADIAL_SPACING
        lines.append(
            (QPointF(vanishing_x + offset * shrink, 0.0), QPointF(vanishing_x + offset, height))
        )

    # Horizontal lines are evenly spaced in depth, so they bunch up toward the horizon.
    far = depth / horizon
    for step in range(1, GRID_HORIZONTAL_LINES + 1):
        z = 1.0 + (far - 1.0) * step / (GRID_HORIZONTAL_LINES + 1)
        y = clamp(depth / z - horizon, 0.5, height - 0.5)
        lines.append((QPointF(0, y), QPointF(width, y)))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    for pen_width, scale in _passes(boost):
        painter.setPen(QPen(QBrush(_fade(height, scale)), pen_width))
        for start, end in lines:
            painter.drawLine(start, end)
    painter.end()
    return pixmap
