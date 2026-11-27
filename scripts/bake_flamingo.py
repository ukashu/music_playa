"""Bake gui/src/music_playa_gui/assets/flamingo.png from flamingo.jpg.

The GUI only loads the result, so none of this runs when the app starts. The steps:

1. Crop the drawing (the navy background around the pink lines is cut away).
2. Flip it so the flamingo faces right.
3. Shrink it to HEIGHT px, in halving steps so the thin lines stay smooth.
4. Brightness becomes opacity (the navy background turns transparent) and the colour
   becomes plain white, so the picture is monochrome. The app tints it with the theme colour.
5. A soft glow (a much smaller copy of the lines stretched back up) is added under the lines.

Run it with the GUI virtualenv, from anywhere:

    QT_QPA_PLATFORM=offscreen gui/.venv/bin/python scripts/bake_flamingo.py
"""

from pathlib import Path

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QImage, QPainter

ASSETS = Path(__file__).resolve().parent.parent / "gui" / "src" / "music_playa_gui" / "assets"
SOURCE = ASSETS / "flamingo.jpg"
TARGET = ASSETS / "flamingo.png"

HEIGHT = 1400  # px; enough for the bird's height (681 logical px) on screens scaled up to 2x
BACKGROUND_LEVEL = 45  # brightness (0..255) at or below this is fully transparent
LINE_LEVEL = 140  # brightness at or above this is fully opaque
CROP_MARGIN = 0.02  # extra space around the drawing, as a share of its size
GLOW_DOWNSCALE = 25  # the glow is a copy of the lines this many times smaller, stretched back
GLOW_OPACITY = 0.8  # strength of the glow under the lines

SMOOTH = Qt.TransformationMode.SmoothTransformation
IGNORE = Qt.AspectRatioMode.IgnoreAspectRatio


def gray_bytes(image: QImage) -> bytes:
    """The pixels of a Grayscale8 image without the padding at the end of each row."""
    stride = image.bytesPerLine()
    width = image.width()
    raw = image.constBits().tobytes()
    return b"".join(raw[y * stride : y * stride + width] for y in range(image.height()))


def content_bounds(gray: QImage) -> QRect:
    """The smallest rectangle holding every pixel above the background level, plus a margin."""
    width, height = gray.width(), gray.height()
    lit = gray_bytes(gray).translate(bytes(255 if level > BACKGROUND_LEVEL else 0 for level in range(256)))
    rows = [y for y in range(height) if b"\xff" in lit[y * width : (y + 1) * width]]
    top, bottom = rows[0], rows[-1]
    band = lit[top * width : (bottom + 1) * width]
    columns = [x for x in range(width) if b"\xff" in band[x::width]]
    left, right = columns[0], columns[-1]
    pad_x = round((right - left) * CROP_MARGIN)
    pad_y = round((bottom - top) * CROP_MARGIN)
    left, right = max(0, left - pad_x), min(width - 1, right + pad_x)
    top, bottom = max(0, top - pad_y), min(height - 1, bottom + pad_y)
    return QRect(left, top, right - left + 1, bottom - top + 1)


def shrink(image: QImage, width: int, height: int) -> QImage:
    """Resize in halving steps first: one smooth step from a big size would skip pixels."""
    while image.width() > 2 * width and image.height() > 2 * height:
        image = image.scaled(image.width() // 2, image.height() // 2, IGNORE, SMOOTH)
    return image.scaled(width, height, IGNORE, SMOOTH)


def white_with_alpha(alpha: bytes, width: int, height: int) -> QImage:
    """A white image whose opacity is taken from alpha, one byte per pixel."""
    count = width * height
    rgba = bytearray(b"\xff" * (count * 4))
    rgba[3::4] = alpha
    buffer = bytes(rgba)
    image = QImage(buffer, width, height, width * 4, QImage.Format.Format_RGBA8888).copy()
    del buffer
    return image


def main() -> None:
    source = QImage(str(SOURCE))
    if source.isNull():
        raise SystemExit(f"cannot read {SOURCE}")

    bounds = content_bounds(source.convertToFormat(QImage.Format.Format_Grayscale8))
    cropped = source.copy(bounds).flipped(Qt.Orientation.Horizontal)  # it faces left; flip it
    width = round(HEIGHT * cropped.width() / cropped.height())
    scaled = shrink(cropped, width, HEIGHT)

    gray = scaled.convertToFormat(QImage.Format.Format_Grayscale8)
    table = bytes(
        round(max(0.0, min(1.0, (level - BACKGROUND_LEVEL) / (LINE_LEVEL - BACKGROUND_LEVEL))) * 255)
        for level in range(256)
    )
    lines = white_with_alpha(gray_bytes(gray).translate(table), width, HEIGHT)

    small = lines.scaled(max(1, width // GLOW_DOWNSCALE), max(1, HEIGHT // GLOW_DOWNSCALE), IGNORE, SMOOTH)
    glow = small.scaled(width, HEIGHT, IGNORE, SMOOTH)

    result = QImage(width, HEIGHT, QImage.Format.Format_ARGB32_Premultiplied)
    result.fill(Qt.GlobalColor.transparent)
    painter = QPainter(result)
    painter.setOpacity(GLOW_OPACITY)
    painter.drawImage(0, 0, glow)
    painter.setOpacity(1.0)
    painter.drawImage(0, 0, lines)
    painter.end()

    if not result.save(str(TARGET), "PNG"):
        raise SystemExit(f"cannot write {TARGET}")
    print(f"{TARGET.name}: {width}x{HEIGHT}, {TARGET.stat().st_size // 1024} KiB")


if __name__ == "__main__":
    main()
