import pytest
from conftest import FakeVisualizer, png_bytes
from PySide6.QtGui import QColor

from music_playa_gui.cover_style import COVER_DISC, COVER_FILL
from music_playa_gui.i18n import translator
from music_playa_gui.theme import BACKGROUND, PINK, VIOLET
from music_playa_gui.widgets.spectrum import (
    BACKGROUND_ALPHA,
    BACKGROUND_BARS,
    BACKGROUND_NONE,
    BACKGROUND_WAVE,
    MODE_NONE,
)
from music_playa_gui.widgets.now_playing import LOGO_FILL, SPIN_PERIOD_S, NowPlayingView


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


class _Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def _disc_view(width: int = 400, height: int = 400) -> NowPlayingView:
    view = NowPlayingView(FakeVisualizer(), 16, 6, cover_style=COVER_DISC)
    view.resize(width, height)
    return view


def _is_green(colour: QColor) -> bool:
    return colour.green() > 200 and colour.red() < 60 and colour.blue() < 60


def _green_pixels(view: NowPlayingView) -> int:
    image = view.grab().toImage()
    return sum(
        _is_green(image.pixelColor(x, y))
        for x in range(0, image.width(), 3)
        for y in range(0, image.height(), 3)
    )


def test_fill_is_the_default_style() -> None:
    view = _view()
    assert view.cover_style == COVER_FILL
    assert view.settings_panel.cover_box.currentData() == COVER_FILL


def test_unknown_style_in_the_constructor_falls_back_to_fill() -> None:
    assert NowPlayingView(FakeVisualizer(), cover_style="cube").cover_style == COVER_FILL


def test_disc_with_a_cover_fills_the_logo_on_a_flat_background() -> None:
    view = _disc_view()
    view.set_cover(png_bytes(300, 300))
    image = view.grab().toImage()
    assert view._scaled is None
    assert view._logo is None
    assert view._disc is not None
    assert image.pixelColor(0, 0) == QColor(BACKGROUND)
    assert image.pixelColor(view.width() - 1, view.height() - 1) == QColor(BACKGROUND)
    assert _green_pixels(view) > 100


def test_disc_without_a_cover_shows_the_gradient_logo_on_the_gradient() -> None:
    view = _disc_view()
    view.set_cover(None)
    image = view.grab().toImage()
    assert view._disc is None
    assert view._logo is not None
    assert image.pixelColor(0, 0) == QColor(18, 11, 46)
    assert image.pixelColor(0, view.height() - 1) != QColor(BACKGROUND)
    assert _green_pixels(view) == 0


def test_disc_with_a_broken_cover_shows_the_logo() -> None:
    view = _disc_view()
    view.set_cover(b"broken")
    assert view._disc is None
    assert view._logo is not None


@pytest.mark.parametrize("ratio", [1.0, 1.5, 2.0])
def test_disc_is_made_in_device_pixels(ratio: float) -> None:
    view = _disc_view()
    view.devicePixelRatioF = lambda: ratio
    view.set_cover(png_bytes(300, 300))
    view.grab()
    assert view._disc.devicePixelRatio() == ratio
    longest = max(view._disc.width(), view._disc.height())
    assert longest == round(round(min(view.width(), view.height()) * LOGO_FILL) * ratio)


def test_disc_is_rebuilt_when_the_ratio_changes() -> None:
    view = _disc_view()
    view.set_cover(png_bytes(300, 300))
    view.grab()
    assert view._disc.devicePixelRatio() == 1.0
    view.devicePixelRatioF = lambda: 2.0
    view.grab()
    assert view._disc.devicePixelRatio() == 2.0


def test_switching_the_style_rebuilds_the_artwork() -> None:
    view = _view()
    view.set_cover(png_bytes(300, 300))
    assert view._scaled is not None and view._disc is None
    view.set_cover_style(COVER_DISC)
    assert view.cover_style == COVER_DISC
    assert view._scaled is None and view._disc is not None
    view.set_cover_style(COVER_FILL)
    assert view._scaled is not None and view._disc is None


def test_unknown_style_is_ignored() -> None:
    view = _view()
    view.set_cover(png_bytes(300, 300))
    view.set_cover_style("cube")
    assert view.cover_style == COVER_FILL
    assert view._scaled is not None


def test_choosing_the_style_in_the_panel_changes_the_view() -> None:
    view = _view()
    box = view.settings_panel.cover_box
    box.setCurrentIndex(box.findData(COVER_DISC))
    assert view.cover_style == COVER_DISC
    box.setCurrentIndex(box.findData(COVER_FILL))
    assert view.cover_style == COVER_FILL


def test_panel_starts_on_the_style_of_the_view() -> None:
    assert _disc_view().settings_panel.cover_box.currentData() == COVER_DISC


def test_disc_turns_only_while_playing() -> None:
    view = _disc_view()
    clock = _Clock()
    view._clock = clock
    assert not view._spin_timer.isActive()
    assert view.angle == 0.0

    view.set_playing(True)
    assert view._spin_timer.isActive()
    clock.now += SPIN_PERIOD_S / 4
    view._spin()
    assert view.angle == pytest.approx(90.0)
    clock.now += SPIN_PERIOD_S / 4
    view._spin()
    assert view.angle == pytest.approx(180.0)

    view.set_playing(False)
    assert not view._spin_timer.isActive()
    assert view.angle == pytest.approx(180.0)


def test_disc_resumes_from_where_it_stopped_without_a_jump() -> None:
    view = _disc_view()
    clock = _Clock()
    view._clock = clock
    view.set_playing(True)
    clock.now += SPIN_PERIOD_S / 4
    view._spin()
    view.set_playing(False)

    clock.now += 1000.0
    view.set_playing(True)
    assert view.angle == pytest.approx(90.0)
    clock.now += SPIN_PERIOD_S / 4
    view._spin()
    assert view.angle == pytest.approx(180.0)


def test_playing_again_while_spinning_keeps_the_same_timer_run() -> None:
    view = _disc_view()
    clock = _Clock()
    view._clock = clock
    view.set_playing(True)
    clock.now += 1.0
    view.set_playing(True)
    view._spin()
    assert view.angle == pytest.approx(360.0 / SPIN_PERIOD_S)


def test_angle_wraps_after_a_full_turn() -> None:
    view = _disc_view()
    clock = _Clock()
    view._clock = clock
    view.set_playing(True)
    clock.now += SPIN_PERIOD_S * 1.25
    view._spin()
    assert view.angle == pytest.approx(90.0)


def test_fill_style_never_turns() -> None:
    view = _view()
    view.set_playing(True)
    assert not view._spin_timer.isActive()
    assert view.angle == 0.0


def test_changing_the_style_starts_and_stops_the_spin() -> None:
    view = _view()
    view.set_playing(True)
    view.set_cover_style(COVER_DISC)
    assert view._spin_timer.isActive()
    view.set_cover_style(COVER_FILL)
    assert not view._spin_timer.isActive()


def test_setting_the_same_style_changes_nothing() -> None:
    view = _disc_view()
    view.set_cover(png_bytes(300, 300))
    disc = view._disc
    view.set_cover_style(COVER_DISC)
    assert view._disc is disc


def test_turned_disc_is_painted_turned() -> None:
    view = _disc_view()
    view.set_cover(png_bytes(300, 300))
    straight = view.grab().toImage()
    view._angle = 90.0
    assert view.grab().toImage() != straight
    assert _green_pixels(view) > 100


@pytest.mark.parametrize("style", [COVER_FILL, COVER_DISC])
def test_paint_without_any_artwork_draws_only_the_background(style: str) -> None:
    view = _view()
    view.set_cover_style(style)
    view.set_cover(None)
    # Grabbing delivers the pending resize, which would build the logo again.
    view._rescale = lambda: None
    view._logo = None
    image = view.grab().toImage()
    assert view._logo is None
    assert image.pixelColor(0, 0) == QColor(18, 11, 46)


def _tint_view(style: str, background: str = BACKGROUND_BARS, bands=None, cover: bool = True) -> NowPlayingView:
    # The visualizer itself is switched off, so only the background colouring is drawn.
    view = NowPlayingView(
        FakeVisualizer(bands or [1.0] * 8),
        4,
        4,
        mode=MODE_NONE,
        cover_style=style,
        background=background,
    )
    view.resize(400, 400)
    view.set_cover(png_bytes(300, 300) if cover else None)
    view._spectrum._refresh()
    return view


def _blended(base: QColor, top: QColor, alpha: int = BACKGROUND_ALPHA) -> tuple[int, int, int]:
    return tuple(round((t * alpha + b * (255 - alpha)) / 255) for b, t in zip(base.getRgb()[:3], top.getRgb()[:3]))


def _close(colour: QColor, expected: tuple[int, int, int]) -> bool:
    return all(abs(a - b) <= 2 for a, b in zip(colour.getRgb()[:3], expected))


def test_disc_style_tints_the_flat_background_behind_the_disc() -> None:
    view = _tint_view(COVER_DISC)
    image = view.grab().toImage()
    expected = _blended(QColor(BACKGROUND), QColor(PINK))
    assert _close(image.pixelColor(0, 0), expected)
    assert _close(image.pixelColor(view.width() - 1, view.height() - 1), expected)
    # The disc is drawn over the colours.
    assert _green_pixels(view) > 100


def test_disc_style_without_a_cover_tints_the_gradient() -> None:
    view = _tint_view(COVER_DISC, cover=False)
    plain = _tint_view(COVER_DISC, background=BACKGROUND_NONE, cover=False)
    corner = QColor(18, 11, 46)
    assert _close(view.grab().toImage().pixelColor(0, 0), _blended(corner, QColor(PINK)))
    assert plain.grab().toImage().pixelColor(0, 0) == corner


def test_fill_style_tints_the_dimmed_cover() -> None:
    tinted = _tint_view(COVER_FILL).grab().toImage().pixelColor(0, 0)
    plain = _tint_view(COVER_FILL, background=BACKGROUND_NONE).grab().toImage().pixelColor(0, 0)
    assert tinted.red() > plain.red() + 40
    assert tinted.green() < plain.green()


def test_fill_style_without_a_cover_tints_the_gradient() -> None:
    view = _tint_view(COVER_FILL, cover=False)
    assert _close(view.grab().toImage().pixelColor(0, 0), _blended(QColor(18, 11, 46), QColor(PINK)))


def test_tint_is_a_smooth_horizontal_gradient() -> None:
    # The two left columns are full and the two right ones are empty, so they fade out.
    view = _tint_view(COVER_DISC, bands=[1.0, 1.0, 0.0, 0.0])
    image = view.grab().toImage()
    base = QColor(BACKGROUND)
    assert _close(image.pixelColor(0, 0), _blended(base, QColor(PINK)))
    assert _close(image.pixelColor(view.width() - 1, 0), _blended(base, QColor(PINK), round(BACKGROUND_ALPHA * 0.75**2)))
    # The colour changes step by step from one edge to the other, without dips.
    reds = [image.pixelColor(x, 0).red() for x in range(0, view.width(), 20)]
    assert reds == sorted(reds, reverse=True)
    assert reds[0] > reds[-1] + 40
    # The colour is the same from top to bottom.
    assert image.pixelColor(10, 0) == image.pixelColor(10, view.height() - 1)


def test_tint_follows_the_wave() -> None:
    class _Wave(FakeVisualizer):
        def wave(self) -> list[float]:
            return [0.0, 1.0]

    view = NowPlayingView(_Wave(), 4, 4, mode=MODE_NONE, cover_style=COVER_DISC, background=BACKGROUND_WAVE)
    view.resize(400, 400)
    view.set_cover(png_bytes(300, 300))
    view._spectrum._refresh()
    image = view.grab().toImage()
    # The left edge has the colour of a sample in the middle (violet) and the right edge the top (pink).
    assert _close(image.pixelColor(0, 0), _blended(QColor(BACKGROUND), QColor(VIOLET)))
    assert _close(image.pixelColor(view.width() - 1, 0), _blended(QColor(BACKGROUND), QColor(PINK)))


@pytest.mark.parametrize("style", [COVER_FILL, COVER_DISC])
def test_no_background_colouring_changes_nothing(style: str) -> None:
    view = _tint_view(style, background=BACKGROUND_NONE)
    assert view._spectrum.background_stops() == []
    image = view.grab().toImage()
    if style == COVER_DISC:
        assert image.pixelColor(0, 0) == QColor(BACKGROUND)


def test_background_passed_to_the_constructor_reaches_the_spectrum() -> None:
    assert _tint_view(COVER_FILL, background=BACKGROUND_WAVE)._spectrum.background == BACKGROUND_WAVE


def test_view_is_repainted_with_the_spectrum_only_while_it_is_coloured(monkeypatch) -> None:
    view = _tint_view(COVER_DISC)
    updates: list[int] = []
    monkeypatch.setattr(view, "update", lambda *args: updates.append(1))

    view._spectrum._refresh()
    assert len(updates) == 1

    # After switching the colouring off the view is painted once more to clear the colours.
    view.grab()
    assert view._tinted
    view._spectrum.set_background(BACKGROUND_NONE)
    assert len(updates) == 2
    view.grab()
    assert not view._tinted
    view._spectrum._refresh()
    assert len(updates) == 2


def _glowing_view() -> NowPlayingView:
    view = NowPlayingView(FakeVisualizer([0.9] * 256), 4, 4, mode=MODE_NONE, bass_glow=True)
    # A second passes between two frames, so the first hit is measured in full.
    view._spectrum._last_tick = 0.0
    view._spectrum._clock = lambda: 1.0
    return view


def test_bass_glow_is_passed_to_the_spectrum_and_its_level_is_forwarded() -> None:
    view = _glowing_view()
    assert view._spectrum.bass_glow is True
    levels: list[float] = []
    view.bass_changed.connect(levels.append)
    view._spectrum._refresh()
    assert levels and levels[0] > 0.0


def test_bass_glow_can_be_switched_off_in_the_view() -> None:
    view = _glowing_view()
    view._spectrum._refresh()
    levels: list[float] = []
    view.bass_changed.connect(levels.append)
    view.set_bass_glow(False)
    assert view._spectrum.bass_glow is False
    assert levels == [0.0]


def test_bass_glow_is_off_by_default_in_the_view() -> None:
    assert NowPlayingView(FakeVisualizer())._spectrum.bass_glow is False
