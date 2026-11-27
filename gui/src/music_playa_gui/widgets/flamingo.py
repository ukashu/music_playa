"""Neon flamingo for the left panel.

assets/flamingo.png is made once by scripts/bake_flamingo.py: the drawing is cropped, flipped
to face right, turned into white lines on a transparent background and given a soft glow. The
app therefore only loads it, scales it to the size it is given and tints it with the theme
colour; none of the image processing runs at startup.
"""

from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap

from music_playa_gui.imaging import scaled_smooth, tinted
from music_playa_gui.theme import PINK

ASSET = Path(__file__).parent.parent / "assets" / "flamingo.png"

RIGHT_MARGIN = 20  # logical px between the beak and the right edge, where the cover view starts
BIRD_OPACITY = 0.6  # the whole flamingo is drawn at this opacity, so it sits darker behind the text

_source: QImage | None = None
_bird: tuple[tuple[int, int], QImage] | None = None  # the last scaled and tinted bird, by size


def _source_image() -> QImage:
    """The baked white drawing, loaded once."""
    global _source
    if _source is None:
        _source = QImage(str(ASSET))
    return _source


def _bird_image(width: int, height: int) -> QImage:
    """The drawing scaled to width x height and tinted. The size rarely changes, so it is cached."""
    global _bird
    if _bird is None or _bird[0] != (width, height):
        _bird = ((width, height), tinted(scaled_smooth(_source_image(), width, height), QColor(PINK)))
    return _bird[1]


def flamingo_pixmap(size: QSize, top: int, bird_height: int, ratio: float = 1.0) -> QPixmap:
    """The neon flamingo facing right, drawn at a fixed size and position.

    The bird is bird_height logical px tall and its top edge sits top px below the top of the
    pixmap, whatever the pixmap's size. Its width follows the drawing's proportions and it is
    anchored to the top-right corner with a small margin from the right edge. If the pixmap is
    too short, the bottom of the bird (the legs) is cut off. Empty if the asset is missing.

    Everything is painted in device pixels. The device pixel ratio is set only at the end,
    because a pixmap that already has one is painted in logical units, which would draw the
    (device-sized) picture too large on scaled screens.
    """
    pixmap = QPixmap(round(size.width() * ratio), round(size.height() * ratio))
    pixmap.fill(Qt.GlobalColor.transparent)
    source = _source_image()
    if not size.isEmpty() and not source.isNull() and bird_height > 0:
        height = round(bird_height * ratio)
        width = round(height * source.width() / source.height())
        painter = QPainter(pixmap)
        painter.setOpacity(BIRD_OPACITY)
        # Anchored to the top-right corner with a small margin; if the bird is wider than
        # the panel, the left side is cut off.
        x = pixmap.width() - width - round(RIGHT_MARGIN * ratio)
        painter.drawImage(x, round(top * ratio), _bird_image(width, height))
        painter.end()

    pixmap.setDevicePixelRatio(ratio)
    return pixmap
