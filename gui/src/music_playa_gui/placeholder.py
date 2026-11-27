"""Vinyl record artwork used when a track has no cover, tinted to the app palette."""

from pathlib import Path

from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import Qt

ASSET = Path(__file__).parent / "assets" / "vinyl-record.png"
SIZE = 1024  # multiple of 4, so every image row is exactly SIZE bytes (no padding)

# Gradient map: brightness of the source (0 black .. 255 white) -> colour.
# Black record body -> deep violet, grey sheen -> cyan, white label -> neon pink.
_STOPS: list[tuple[int, tuple[int, int, int]]] = [
    (0, (26, 12, 66)),
    (30, (60, 30, 135)),
    (90, (0, 190, 230)),
    (170, (138, 79, 255)),
    (255, (255, 60, 155)),
]

_cache: QPixmap | None = None


def _channel_table(channel: int) -> bytes:
    """256-entry lookup table that maps brightness to one colour channel."""
    table = bytearray(256)
    for level in range(256):
        for (low, low_color), (high, high_color) in zip(_STOPS, _STOPS[1:]):
            if low <= level <= high:
                fraction = (level - low) / (high - low)
                table[level] = round(low_color[channel] + (high_color[channel] - low_color[channel]) * fraction)
                break
    return bytes(table)


def _themed_vinyl() -> QImage:
    source = QImage(str(ASSET))
    if source.isNull():
        return QImage()
    source = source.scaled(
        SIZE,
        SIZE,
        Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    pixels = SIZE * SIZE
    # constBits() is only a view of the image's memory, so the converted images
    # must stay referenced until their bytes are copied out.
    gray_image = source.convertToFormat(QImage.Format.Format_Grayscale8)
    alpha_image = source.convertToFormat(QImage.Format.Format_Alpha8)
    gray = gray_image.constBits().tobytes()[:pixels]
    alpha = alpha_image.constBits().tobytes()[:pixels]

    # Bytes.translate and slice assignment run in C, so tinting a 1024 x 1024
    # image is a few milliseconds, without per-pixel Python code.
    rgba = bytearray(pixels * 4)
    for channel in range(3):
        rgba[channel::4] = gray.translate(_channel_table(channel))
    rgba[3::4] = alpha
    # QImage only wraps the buffer, so keep it alive until copy() gives the image its own data.
    buffer = bytes(rgba)
    image = QImage(buffer, SIZE, SIZE, SIZE * 4, QImage.Format.Format_RGBA8888).copy()
    del buffer
    return image


def vinyl_pixmap() -> QPixmap:
    """The tinted vinyl record, computed once. A null pixmap if the asset is missing."""
    global _cache
    if _cache is None:
        _cache = QPixmap.fromImage(_themed_vinyl())
    return _cache
