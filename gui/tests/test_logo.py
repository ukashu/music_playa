import pytest
from PySide6.QtGui import QColor, QImage, QPainter

from music_playa_gui import logo
from music_playa_gui.logo import LogoWidget, covered_logo, scaled_logo


def _cover(width: int, height: int, stripes: list[tuple[float, str]]) -> QImage:
    """A cover of vertical stripes: (share of the width, colour) from left to right."""
    image = QImage(width, height, QImage.Format.Format_ARGB32)
    image.fill(QColor("black"))
    painter = QPainter(image)
    left = 0.0
    for share, colour in stripes:
        painter.fillRect(round(left * width), 0, round(share * width) + 1, height, QColor(colour))
        left += share
    painter.end()
    return image


def _opaque(image: QImage) -> list[tuple[int, int, QColor]]:
    return [
        (x, y, image.pixelColor(x, y))
        for x in range(0, image.width(), 3)
        for y in range(0, image.height(), 3)
        if image.pixelColor(x, y).alpha() == 255
    ]


@pytest.mark.parametrize(("longest", "ratio"), [(40, 1.0), (60, 1.5), (80, 2.0)])
def test_scaled_logo_size_and_ratio(longest: int, ratio: float) -> None:
    pixmap = scaled_logo(longest, ratio)
    assert max(pixmap.width(), pixmap.height()) == longest
    assert pixmap.devicePixelRatio() == ratio
    logical = pixmap.deviceIndependentSize()
    assert max(logical.width(), logical.height()) == pytest.approx(longest / ratio)


def test_scaled_logo_is_tinted_and_transparent_around() -> None:
    image = scaled_logo(200).toImage()
    assert image.pixelColor(0, 0).alpha() == 0
    opaque = [
        image.pixelColor(x, y)
        for x in range(0, image.width(), 4)
        for y in range(0, image.height(), 4)
        if image.pixelColor(x, y).alpha() == 255
    ]
    assert opaque
    # Tinted with the gradient, so no opaque pixel stays white.
    assert all(min(c.red(), c.green(), c.blue()) < 200 for c in opaque)


def test_scaled_logo_too_small() -> None:
    assert scaled_logo(0).isNull()


def test_missing_asset(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(logo, "ASSET", tmp_path / "missing.png")
    monkeypatch.setattr(logo, "_tinted", None)
    assert scaled_logo(40).isNull()


def test_logo_widget_rebuilds_when_the_ratio_changes() -> None:
    widget = LogoWidget(40)
    widget.grab()
    assert widget._pixmap.devicePixelRatio() == 1.0
    assert max(widget._pixmap.width(), widget._pixmap.height()) == 40
    widget.devicePixelRatioF = lambda: 2.0
    widget.grab()
    assert widget._pixmap.devicePixelRatio() == 2.0
    assert max(widget._pixmap.width(), widget._pixmap.height()) == 80


def test_logo_widget_without_asset_draws_nothing(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(logo, "ASSET", tmp_path / "missing.png")
    monkeypatch.setattr(logo, "_tinted", None)
    widget = LogoWidget(40)
    image = widget.grab().toImage()
    assert not image.isNull()
    assert widget._pixmap.isNull()


@pytest.mark.parametrize(("longest", "ratio"), [(40, 1.0), (60, 1.5), (80, 2.0)])
def test_covered_logo_has_the_size_and_ratio_of_the_logo(longest: int, ratio: float) -> None:
    pixmap = covered_logo(_cover(50, 50, [(1.0, "#00ff00")]), longest, ratio)
    assert (pixmap.width(), pixmap.height()) == (scaled_logo(longest, ratio).width(), scaled_logo(longest, ratio).height())
    assert max(pixmap.width(), pixmap.height()) == longest
    assert pixmap.devicePixelRatio() == ratio


def test_covered_logo_shows_the_cover_only_where_the_logo_is_opaque() -> None:
    image = covered_logo(_cover(80, 80, [(1.0, "#00ff00")]), 200).toImage()
    assert image.pixelColor(0, 0).alpha() == 0
    opaque = _opaque(image)
    assert opaque
    # Filled with the cover, not tinted with the gradient.
    assert all(c.green() > 240 and c.red() < 15 and c.blue() < 15 for _x, _y, c in opaque)
    # The same shape as the gradient logo.
    shape = scaled_logo(200).toImage()
    assert all(shape.pixelColor(x, y).alpha() > 0 for x, y, _c in opaque)


def test_covered_logo_crops_a_wide_cover_around_its_centre() -> None:
    cover = _cover(400, 100, [(0.25, "#ff0000"), (0.5, "#00ff00"), (0.25, "#0000ff")])
    opaque = _opaque(covered_logo(cover, 200).toImage())
    assert opaque
    assert all(c.green() > 240 and c.red() < 15 and c.blue() < 15 for _x, _y, c in opaque)


def test_covered_logo_crops_a_tall_cover_around_its_centre() -> None:
    cover = QImage(100, 400, QImage.Format.Format_ARGB32)
    cover.fill(QColor("#ff0000"))
    painter = QPainter(cover)
    painter.fillRect(0, 100, 100, 200, QColor("#00ff00"))
    painter.end()
    opaque = _opaque(covered_logo(cover, 200).toImage())
    assert opaque
    assert all(c.green() > 240 and c.red() < 15 for _x, _y, c in opaque)


def test_covered_logo_without_a_cover_or_room() -> None:
    assert covered_logo(QImage(), 100).isNull()
    assert covered_logo(_cover(10, 10, [(1.0, "#00ff00")]), 0).isNull()


def test_covered_logo_without_asset(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(logo, "ASSET", tmp_path / "missing.png")
    monkeypatch.setattr(logo, "_tinted", None)
    assert covered_logo(_cover(10, 10, [(1.0, "#00ff00")]), 40).isNull()
