"""Playback control icons drawn with QPainter.

Text glyphs (⏮ ⇄ ↻ …) come from different fallback fonts and end up with different
sizes, so the navigation icons are painted instead. Every icon uses the same
ICON_PX square, so they all look the same size.
"""

from enum import Enum

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPen, QPixmap, QPolygonF

ICON_PX = 24


class Icon(Enum):
    PREVIOUS = "previous"
    NEXT = "next"
    SHUFFLE = "shuffle"
    REPEAT = "repeat"
    REPEAT_ONE = "repeat_one"


def make_icon(kind: Icon, color: str) -> QIcon:
    pixmap = QPixmap(ICON_PX, ICON_PX)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    _DRAWERS[kind](painter, QColor(color))
    painter.end()
    return QIcon(pixmap)


def _stroke(color: QColor, width: float = 2.0) -> QPen:
    return QPen(color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)


def _arrowhead(painter: QPainter, tip: QPointF, dx: float, dy: float, color: QColor) -> None:
    """Filled triangle with its tip at `tip`, pointing along the unit vector (dx, dy)."""
    size = 4.5
    half = 3.6
    back_x, back_y = tip.x() - dx * size, tip.y() - dy * size
    perp_x, perp_y = -dy * half, dx * half
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    painter.drawPolygon(
        QPolygonF(
            [
                tip,
                QPointF(back_x + perp_x, back_y + perp_y),
                QPointF(back_x - perp_x, back_y - perp_y),
            ]
        )
    )
    painter.setBrush(Qt.BrushStyle.NoBrush)


def _filled_triangle(painter: QPainter, points: list[tuple[float, float]], color: QColor) -> None:
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    painter.drawPolygon(QPolygonF([QPointF(x, y) for x, y in points]))
    painter.setBrush(Qt.BrushStyle.NoBrush)


def _previous(painter: QPainter, color: QColor) -> None:
    painter.setPen(_stroke(color))
    painter.drawLine(QPointF(6, 6), QPointF(6, 18))
    _filled_triangle(painter, [(18, 6), (18, 18), (9, 12)], color)


def _next(painter: QPainter, color: QColor) -> None:
    painter.setPen(_stroke(color))
    painter.drawLine(QPointF(18, 6), QPointF(18, 18))
    _filled_triangle(painter, [(6, 6), (6, 18), (15, 12)], color)


def _shuffle(painter: QPainter, color: QColor) -> None:
    painter.setPen(_stroke(color))
    painter.drawPolyline(QPolygonF([QPointF(4, 8), QPointF(9, 8), QPointF(15, 16), QPointF(19, 16)]))
    painter.drawPolyline(QPolygonF([QPointF(4, 16), QPointF(9, 16), QPointF(15, 8), QPointF(19, 8)]))
    _arrowhead(painter, QPointF(20, 16), 1.0, 0.0, color)
    _arrowhead(painter, QPointF(20, 8), 1.0, 0.0, color)


def _loop(painter: QPainter, color: QColor) -> None:
    # Rounded rectangle with arrowheads on opposite sides, circulating clockwise.
    painter.setPen(_stroke(color))
    painter.drawRoundedRect(QRectF(4.5, 6.5, 15, 11), 3.5, 3.5)
    _arrowhead(painter, QPointF(19.5, 14), 0.0, 1.0, color)
    _arrowhead(painter, QPointF(4.5, 10), 0.0, -1.0, color)


def _repeat(painter: QPainter, color: QColor) -> None:
    _loop(painter, color)


def _repeat_one(painter: QPainter, color: QColor) -> None:
    _loop(painter, color)
    painter.setPen(color)
    font = QFont()
    font.setPixelSize(9)
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(QRectF(0, 0, ICON_PX, ICON_PX), Qt.AlignmentFlag.AlignCenter, "1")


_DRAWERS = {
    Icon.PREVIOUS: _previous,
    Icon.NEXT: _next,
    Icon.SHUFFLE: _shuffle,
    Icon.REPEAT: _repeat,
    Icon.REPEAT_ONE: _repeat_one,
}
