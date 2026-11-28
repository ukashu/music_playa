import pytest
from conftest import FakeVisualizer, png_bytes

from music_playa_gui.i18n import translator
from music_playa_gui.widgets.now_playing import LOGO_FILL, NowPlayingView


def _view(width: int = 400, height: int = 200) -> NowPlayingView:
    view = NowPlayingView(FakeVisualizer(), 16, 6)
    view.resize(width, height)
    return view


@pytest.mark.parametrize("ratio", [1.0, 1.5, 2.0])
def test_cover_fills_the_view_in_device_pixels(ratio: float) -> None:
    """Regression: the cover was scaled to the logical size and stretched on scaled screens."""
    view = _view()
    view.devicePixelRatioF = lambda: ratio
    view.set_cover(png_bytes(300, 300))
    view.grab()
    assert view._scaled is not None
    assert view._scaled.devicePixelRatio() == ratio
    assert max(view._scaled.width(), view._scaled.height()) == round(max(view.width(), view.height()) * ratio)
    logical = view._scaled.deviceIndependentSize()
    assert logical.width() >= view.width() - 1 and logical.height() >= view.height() - 1


def test_cover_is_rebuilt_when_the_ratio_changes() -> None:
    view = _view()
    view.set_cover(png_bytes(300, 300))
    view.grab()
    assert view._scaled.devicePixelRatio() == 1.0
    view.devicePixelRatioF = lambda: 2.0
    view.grab()
    assert view._scaled.devicePixelRatio() == 2.0


@pytest.mark.parametrize("ratio", [1.0, 1.5, 2.0])
def test_logo_without_a_cover(ratio: float) -> None:
    view = _view()
    view.devicePixelRatioF = lambda: ratio
    view.set_cover(None)
    view.grab()
    assert view._scaled is None
    assert view._logo.devicePixelRatio() == ratio
    longest = max(view._logo.width(), view._logo.height())
    assert longest == round(round(min(view.width(), view.height()) * LOGO_FILL) * ratio)


def test_broken_cover_shows_the_logo() -> None:
    view = _view()
    view.set_cover(b"broken")
    assert view._scaled is None
    assert view._logo is not None


def test_gear_toggles_the_settings_panel() -> None:
    view = _view()
    panel = view.settings_panel
    view._gear.click()
    assert panel._open
    view._gear.click()
    assert not panel._open


def test_gear_tooltip_is_translated() -> None:
    view = _view()
    assert view._gear.toolTip() == "Ustawienia"
    translator.set_language("en")
    assert view._gear.toolTip() == "Settings"


def test_view_without_size_draws_nothing() -> None:
    view = NowPlayingView(FakeVisualizer(), 16, 6)
    view.resize(0, 0)
    view.set_cover(png_bytes(20, 20))
    assert view._scaled is None and view._logo is None


def test_missing_logo_asset_leaves_the_gradient(monkeypatch, tmp_path) -> None:
    from music_playa_gui import logo

    monkeypatch.setattr(logo, "ASSET", tmp_path / "missing.png")
    monkeypatch.setattr(logo, "_tinted", None)
    view = _view()
    view.set_cover(None)
    assert view._logo is None or view._logo.isNull()
    assert not view.grab().toImage().isNull()


def test_tiny_view_still_gets_a_logo() -> None:
    view = NowPlayingView(FakeVisualizer(), 16, 6)
    view.resize(1, 1)
    view.set_cover(None)
    assert max(view._logo.width(), view._logo.height()) == 1
