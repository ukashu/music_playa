"""Neon flamingo for the left panel, made from the bundled line drawing.

The source drawing is a dark navy picture with pink lines. It is turned into a
pink neon sign: colour is dropped, brightness becomes opacity (so the navy
background disappears), the lines get a soft glow, and the result is fitted to
the size it is given. The conversion uses lookup tables (bytes.translate), so
it needs no per-pixel Python code.
"""

from pathlib import Path

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap

from music_playa_gui.theme import PINK

ASSET = Path(__file__).parent.parent / "assets" / "flamingo.jpg"

# Brightness of the source (0 black .. 255 white) -> opacity of the neon line.
BACKGROUND_LEVEL = 45  # at or below this the navy background is fully transparent
LINE_LEVEL = 140  # at or above this the line is fully opaque
GLOW_DOWNSCALE = 12  # the glow is a much smaller copy of the lines, stretched back up
GLOW_OPACITY = 0.8  # strength of the glow under the sharp lines
BIRD_OPACITY = 0.6  # the whole flamingo is drawn at this opacity, so it sits darker behind the text
RIGHT_MARGIN = 20  # logical px between the beak and the right edge, where the cover view starts


def _alpha_table() -> bytes:
    table = bytearray(256)
    for level in range(256):
        fraction = (level - BACKGROUND_LEVEL) / (LINE_LEVEL - BACKGROUND_LEVEL)
        table[level] = round(max(0.0, min(1.0, fraction)) * 255)
    return bytes(table)


_ALPHA_TABLE = _alpha_table()
_MARGIN = 0.02  # extra space kept around the drawing, as a share of its size

_source: QImage | None = None


def _content_bounds(gray: QImage) -> QRect:
    """The smallest rectangle that holds every line, i.e. every pixel above the background."""
    stride = gray.bytesPerLine()
    width, height = gray.width(), gray.height()
    raw = gray.constBits().tobytes()
    line_mask = bytes(255 if level > BACKGROUND_LEVEL else 0 for level in range(256))

    rows = [y for y in range(height) if b"\xff" in raw[y * stride : y * stride + width].translate(line_mask)]
    if not rows:
        return QRect(0, 0, width, height)
    top, bottom = rows[0], rows[-1]
    band = raw[top * stride : bottom * stride + width]
    columns = [x for x in range(width) if b"\xff" in band[x::stride].translate(line_mask)]
    left, right = columns[0], columns[-1]

    pad_x = round((right - left) * _MARGIN)
    pad_y = round((bottom - top) * _MARGIN)
    left, right = max(0, left - pad_x), min(width - 1, right + pad_x)
    top, bottom = max(0, top - pad_y), min(height - 1, bottom + pad_y)
    return QRect(left, top, right - left + 1, bottom - top + 1)


def _source_image() -> QImage:
    """The drawing cropped to the flamingo and flipped to face right, loaded once."""
    global _source
    if _source is None:
        image = QImage(str(ASSET))
        if not image.isNull():
            bounds = _content_bounds(image.convertToFormat(QImage.Format.Format_Grayscale8))
            # The drawing faces left, so flip it to face right.
            image = image.copy(bounds).mirrored(True, False)
        _source = image
    return _source


def _neon_image(source: QImage, width: int, height: int) -> QImage:
    """The drawing as pink lines with opacity taken from brightness."""
    if source.isNull() or width < 1 or height < 1:
        return QImage()
    scaled = source.scaled(
        width,
        height,
        Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    w, h = scaled.width(), scaled.height()
    # Keep the converted image alive until its bytes are copied out.
    gray_image = scaled.convertToFormat(QImage.Format.Format_Grayscale8)
    stride = gray_image.bytesPerLine()
    raw = gray_image.constBits().tobytes()
    # Grayscale rows may be padded to 4 bytes; keep only the real pixels.
    gray = b"".join(raw[y * stride : y * stride + w] for y in range(h))
    alpha = gray.translate(_ALPHA_TABLE)

    count = w * h
    colour = QColor(PINK)
    rgba = bytearray(count * 4)
    rgba[0::4] = bytes([colour.red()]) * count
    rgba[1::4] = bytes([colour.green()]) * count
    rgba[2::4] = bytes([colour.blue()]) * count
    rgba[3::4] = alpha
    # QImage only wraps the buffer, so copy() gives the image its own data.
    buffer = bytes(rgba)
    image = QImage(buffer, w, h, w * 4, QImage.Format.Format_RGBA8888).copy()
    del buffer
    return image


def _with_glow(image: QImage) -> QPixmap:
    sharp = QPixmap.fromImage(image)
    w, h = sharp.width(), sharp.height()
    small = sharp.scaled(
        max(1, w // GLOW_DOWNSCALE),
        max(1, h // GLOW_DOWNSCALE),
        Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    blurred = small.scaled(
        w,
        h,
        Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )

    result = QPixmap(w, h)
    result.fill(Qt.GlobalColor.transparent)
    painter = QPainter(result)
    painter.setOpacity(GLOW_OPACITY)
    painter.drawPixmap(0, 0, blurred)
    painter.setOpacity(1.0)
    painter.drawPixmap(0, 0, sharp)
    painter.end()
    return result


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
        image = _neon_image(source, width, height)
        if not image.isNull():
            drawn = _with_glow(image)
            painter = QPainter(pixmap)
            painter.setOpacity(BIRD_OPACITY)
            # Anchored to the top-right corner with a small margin; if the bird is wider than
            # the panel, the left side is cut off.
            x = pixmap.width() - width - round(RIGHT_MARGIN * ratio)
            painter.drawPixmap(x, round(top * ratio), drawn)
            painter.end()

    pixmap.setDevicePixelRatio(ratio)
    return pixmap
