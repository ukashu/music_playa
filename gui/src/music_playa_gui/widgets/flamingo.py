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

# The halo of the glowing bird: the bird shrunk by these factors and enlarged again is a soft blur
# of it, wide and narrow. It is drawn this many times, as the blur alone is faint.
HALO_SHRINKS = (14, 6)
HALO_PASSES = 2
HALO_PADDING = 20  # the halo reaches this fraction (1 / value) of the bird's size beyond it

_source: QImage | None = None
_bird: tuple[tuple[int, int], QImage] | None = None  # the last scaled and tinted bird, by size
_halo: tuple[tuple[int, int], QImage] | None = None  # the last blurred bird, by size


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


def halo_padding(width: int, height: int) -> int:
    """Pixels the halo of a bird of this size reaches beyond the bird on every side."""
    return max(width, height) // HALO_PADDING


def _halo_image(width: int, height: int) -> QImage:
    """The bird blurred into a soft halo. It is halo_padding larger than the bird on every side,
    so the blur is not cut off at the bird's edges. Cached like the bird."""
    global _halo
    if _halo is None or _halo[0] != (width, height):
        pad = halo_padding(width, height)
        full_width, full_height = width + 2 * pad, height + 2 * pad
        padded = QImage(full_width, full_height, QImage.Format.Format_ARGB32_Premultiplied)
        padded.fill(Qt.GlobalColor.transparent)
        painter = QPainter(padded)
        painter.drawImage(pad, pad, _bird_image(width, height))
        painter.end()

        image = QImage(padded.size(), QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        for shrink in HALO_SHRINKS:
            small = scaled_smooth(padded, max(full_width // shrink, 1), max(full_height // shrink, 1))
            painter.drawImage(
                0,
                0,
                small.scaled(
                    full_width,
                    full_height,
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                ),
            )
        painter.end()
        _halo = ((width, height), image)
    return _halo[1]


def flamingo_pixmap(
    size: QSize, top: int, bird_height: int, ratio: float = 1.0, glow: bool = False
) -> QPixmap:
    """The neon flamingo facing right, drawn at a fixed size and position.

    The bird is bird_height logical px tall and its top edge sits top px below the top of the
    pixmap, whatever the pixmap's size. Its width follows the drawing's proportions and it is
    anchored to the top-right corner with a small margin from the right edge. If the pixmap is
    too short, the bottom of the bird (the legs) is cut off. Empty if the asset is missing.

    With glow the bird is drawn at full opacity and with a soft halo around it. It is meant to go
    over the normal one, more or less opaque with the bass, so the bird lights up and glows.

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
        # Anchored to the top-right corner with a small margin; if the bird is wider than
        # the panel, the left side is cut off.
        x = pixmap.width() - width - round(RIGHT_MARGIN * ratio)
        y = round(top * ratio)
        if glow:
            pad = halo_padding(width, height)
            for _ in range(HALO_PASSES):
                painter.drawImage(x - pad, y - pad, _halo_image(width, height))
        else:
            painter.setOpacity(BIRD_OPACITY)
        painter.drawImage(x, y, _bird_image(width, height))
        painter.end()

    pixmap.setDevicePixelRatio(ratio)
    return pixmap
