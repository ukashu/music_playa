import pytest

from music_playa_gui import logo
from music_playa_gui.logo import LogoWidget, scaled_logo


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
