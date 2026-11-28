import pytest
from conftest import make_tracks, png_bytes
from PySide6.QtGui import QColor, QPixmap

from music_playa.models import PlaybackMode, RepeatMode
from music_playa_gui.i18n import translator
from music_playa_gui.theme import CYAN, SURFACE
from music_playa_gui.widgets.icons import ICON_PX
from music_playa_gui.widgets.player_bar import (
    EDGE_MARGIN,
    PLAYER_BORDER,
    PROGRESS_STEPS,
    THUMB_SIZE,
    PlayerBar,
)


def _record(signal) -> list:
    received = []
    signal.connect(lambda *args: received.append(args[0] if len(args) == 1 else args))
    return received


def _settle(bar: PlayerBar) -> None:
    for _ in range(1000):
        if not bar._smooth_timer.isActive():
            return
        bar._ease_progress()
    raise AssertionError("progress never settled")


def _has_colour(button, colour: str) -> bool:
    image = button.icon().pixmap(ICON_PX, ICON_PX).toImage()
    target = QColor(colour)
    return any(
        image.pixelColor(x, y).alpha() == 255 and image.pixelColor(x, y).rgb() == target.rgb()
        for x in range(ICON_PX)
        for y in range(ICON_PX)
    )


def test_no_track_text() -> None:
    bar = PlayerBar()
    assert bar._title._text == "Brak utworu"
    assert bar._artist._text == ""
    translator.set_language("en")
    assert bar._title._text == "No track"


def test_track_text() -> None:
    bar = PlayerBar()
    bar.set_track(make_tracks(1)[0], None)
    assert bar._title._text == "Song 0"
    assert bar._artist._text == "Artist"


def test_set_playing_switches_the_glyph() -> None:
    bar = PlayerBar()
    assert bar._toggle.text() == "▶"
    bar.set_playing(True)
    assert bar._toggle.text() == "⏸"
    bar.set_playing(False)
    assert bar._toggle.text() == "▶"


def test_large_jump_snaps() -> None:
    bar = PlayerBar()
    bar.set_progress(30.0, 120.0)
    assert bar._shown_position == 30.0
    assert not bar._smooth_timer.isActive()
    assert bar._progress.value() == 250
    assert bar._elapsed.text() == "0:30"
    assert bar._total.text() == "2:00"


def test_small_step_eases() -> None:
    bar = PlayerBar()
    bar.set_progress(30.0, 120.0)
    bar.set_progress(30.5, 120.0)
    assert bar._smooth_timer.isActive()
    assert bar._shown_position == 30.0
    bar._ease_progress()
    assert 30.0 < bar._shown_position < 30.5
    _settle(bar)
    assert bar._shown_position == 30.5


def test_no_duration_keeps_the_slider_at_zero() -> None:
    bar = PlayerBar()
    bar.set_progress(10.0, 0.0)
    assert bar._progress.value() == 0


def test_progress_is_not_moved_while_dragging() -> None:
    bar = PlayerBar()
    bar.set_progress(10.0, 100.0)
    bar._progress.setSliderDown(True)
    bar.set_progress(50.0, 100.0)
    assert bar._progress.value() == 100
    bar._progress.setSliderDown(False)


def test_drag_shows_the_time_and_seeks_on_release() -> None:
    bar = PlayerBar()
    seeks = _record(bar.seek_requested)
    bar.set_progress(10.0, 100.0)
    bar._progress.setSliderDown(True)
    bar._progress.setSliderPosition(500)
    assert bar._elapsed.text() == "0:50"
    bar._progress.setSliderDown(False)
    assert seeks == [pytest.approx(50.0)]


def test_release_without_duration_does_not_seek() -> None:
    bar = PlayerBar()
    seeks = _record(bar.seek_requested)
    bar._progress.setSliderDown(True)
    bar._progress.setSliderPosition(500)
    bar._progress.setSliderDown(False)
    assert seeks == []


def test_short_seek_does_not_jump_back() -> None:
    """Regression: after a short seek the slider went back to the old position and eased forward."""
    bar = PlayerBar()
    bar.set_progress(10.0, 100.0)
    bar._progress.setSliderDown(True)
    bar._progress.setSliderPosition(110)  # 11 s, less than SNAP_SECONDS away
    bar._progress.setSliderDown(False)
    assert bar._shown_position == pytest.approx(11.0)
    bar.set_progress(11.0, 100.0)
    bar._ease_progress()
    assert bar._progress.value() == 110


def test_set_volume_does_not_emit() -> None:
    bar = PlayerBar()
    volumes = _record(bar.volume_changed)
    bar.set_volume(0.4)
    assert bar._volume.value() == 40
    assert volumes == []


def test_mute_and_restore() -> None:
    bar = PlayerBar()
    volumes = _record(bar.volume_changed)
    bar.set_volume(0.6)
    bar.toggle_mute()
    assert bar._volume.value() == 0
    assert bar._speaker._muted
    assert bar._speaker.toolTip() == "Włącz dźwięk"
    bar.toggle_mute()
    assert bar._volume.value() == 60
    assert not bar._speaker._muted
    assert bar._speaker.toolTip() == "Wycisz"
    assert volumes == [0.0, 0.6]


def test_speaker_click_toggles_mute() -> None:
    bar = PlayerBar()
    bar._speaker.clicked.emit()
    assert bar._volume.value() == 0


def test_mode_tooltip_and_colour() -> None:
    bar = PlayerBar()
    assert bar._mode.toolTip() == "Tryb: Po kolei"
    assert not _has_colour(bar._mode, CYAN)
    bar.set_mode(PlaybackMode.SHUFFLE)
    assert bar._mode.toolTip() == "Tryb: Losowo"
    assert _has_colour(bar._mode, CYAN)
    translator.set_language("en")
    assert bar._mode.toolTip() == "Mode: Shuffle"


@pytest.mark.parametrize(
    ("repeat", "tooltip", "active"),
    [
        (RepeatMode.OFF, "Powtarzanie: Wyłączone", False),
        (RepeatMode.ALL, "Powtarzanie: Powtarzaj całą listę", True),
        (RepeatMode.ONE, "Powtarzanie: Powtarzaj jeden utwór", True),
    ],
)
def test_repeat_tooltip_and_colour(repeat: RepeatMode, tooltip: str, active: bool) -> None:
    bar = PlayerBar()
    bar.set_repeat(repeat)
    assert bar._repeat.toolTip() == tooltip
    assert _has_colour(bar._repeat, CYAN) is active


def test_buttons_emit_signals() -> None:
    bar = PlayerBar()
    names = ["previous_clicked", "toggle_clicked", "next_clicked", "mode_clicked", "repeat_clicked"]
    received = {name: _record(getattr(bar, name)) for name in names}
    for button in (bar._previous, bar._toggle, bar._next, bar._mode, bar._repeat):
        button.click()
    assert all(len(calls) == 1 for calls in received.values())


@pytest.mark.parametrize("width", [900, 1280, 1920])
def test_play_button_is_centred(width: int, shown) -> None:
    bar = PlayerBar()
    bar.resize(width, bar.height())
    shown(bar)
    centre = bar._toggle.mapTo(bar, bar._toggle.rect().center()).x()
    assert abs(centre - width / 2) <= 1


def _recorded_thumbs(bar: PlayerBar) -> list[QPixmap]:
    shown: list[QPixmap] = []
    original = bar._thumb.setPixmap

    def record(pixmap: QPixmap) -> None:
        shown.append(pixmap)
        original(pixmap)

    bar._thumb.setPixmap = record
    return shown


def test_cover_thumbnail_in_device_pixels() -> None:
    bar = PlayerBar()
    shown = _recorded_thumbs(bar)
    bar.devicePixelRatioF = lambda: 1.5
    bar.set_track(make_tracks(1)[0], png_bytes(300, 300))
    assert shown[-1].devicePixelRatio() == 1.5
    assert shown[-1].width() == round(THUMB_SIZE * 1.5)


def test_thumbnail_follows_a_ratio_change() -> None:
    """Regression: the cover thumbnail was made at logical size and not rebuilt for a new ratio."""
    bar = PlayerBar()
    shown = _recorded_thumbs(bar)
    bar.set_track(make_tracks(1)[0], png_bytes(300, 200))
    assert shown[-1].devicePixelRatio() == 1.0
    bar.devicePixelRatioF = lambda: 2.0
    bar.grab()
    assert shown[-1].devicePixelRatio() == 2.0
    assert shown[-1].width() == 2 * THUMB_SIZE
    assert shown[-1].height() == 2 * THUMB_SIZE


def test_logo_thumbnail_without_a_cover() -> None:
    bar = PlayerBar()
    shown = _recorded_thumbs(bar)
    bar.devicePixelRatioF = lambda: 2.0
    bar.set_track(make_tracks(1)[0], b"not an image")
    assert shown[-1].devicePixelRatio() == 2.0
    assert max(shown[-1].width(), shown[-1].height()) == 2 * THUMB_SIZE


def test_grid_is_rebuilt_for_a_new_ratio() -> None:
    bar = PlayerBar()
    bar.resize(800, bar.height())
    bar.grab()
    assert bar._grid.devicePixelRatio() == 1.0
    bar.devicePixelRatioF = lambda: 2.0
    bar.grab()
    assert bar._grid.devicePixelRatio() == 2.0
    assert bar._grid.width() == 2 * bar.width()


def test_progress_steps_match_the_slider_range() -> None:
    bar = PlayerBar()
    assert bar._progress.maximum() == PROGRESS_STEPS


def _slider_at(slider, fraction: float):
    from PySide6.QtCore import QPoint

    return QPoint(round(slider.width() * fraction), slider.height() // 2)


def test_click_on_the_slider_jumps_there(shown) -> None:
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    bar = PlayerBar()
    bar.resize(900, bar.height())
    shown(bar)
    seeks = _record(bar.seek_requested)
    bar.set_progress(0.0, 100.0)
    slider = bar._progress
    QTest.mouseClick(slider, Qt.MouseButton.LeftButton, pos=_slider_at(slider, 0.5))
    assert abs(slider.value() - PROGRESS_STEPS / 2) < 40
    assert len(seeks) == 1 and abs(seeks[0] - 50.0) < 4


def test_dragging_the_slider_follows_the_mouse(shown) -> None:
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    bar = PlayerBar()
    bar.resize(900, bar.height())
    shown(bar)
    bar.set_progress(0.0, 100.0)
    slider = bar._progress
    QTest.mousePress(slider, Qt.MouseButton.LeftButton, pos=_slider_at(slider, 0.2))
    assert slider.isSliderDown()
    QTest.mouseMove(slider, _slider_at(slider, 0.8))
    assert slider.value() > 700
    QTest.mouseRelease(slider, Qt.MouseButton.LeftButton, pos=_slider_at(slider, 0.8))
    assert not slider.isSliderDown()


def test_other_mouse_buttons_do_not_drag(shown) -> None:
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    bar = PlayerBar()
    bar.resize(900, bar.height())
    shown(bar)
    slider = bar._progress
    QTest.mouseClick(slider, Qt.MouseButton.RightButton, pos=_slider_at(slider, 0.5))
    assert not slider.isSliderDown()
    assert slider.value() == 0
    QTest.mouseMove(slider, _slider_at(slider, 0.7))
    assert slider.value() == 0


def test_speaker_icon_click_and_paint(shown) -> None:
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    bar = PlayerBar()
    shown(bar)
    speaker = bar._speaker
    clicks = _record(speaker.clicked)
    QTest.mouseClick(speaker, Qt.MouseButton.LeftButton)
    QTest.mouseClick(speaker, Qt.MouseButton.RightButton)
    assert len(clicks) == 1
    assert bar._volume.value() == 0
    muted = speaker.grab().toImage()
    QTest.mouseClick(speaker, Qt.MouseButton.LeftButton)
    assert speaker.grab().toImage() != muted
    speaker.set_muted(False)  # same state: nothing to redraw
    assert not speaker._muted


def test_easing_pauses_while_dragging() -> None:
    bar = PlayerBar()
    bar.set_progress(10.0, 100.0)
    bar.set_progress(10.5, 100.0)
    bar._progress.setSliderDown(True)
    bar._ease_progress()
    assert bar._shown_position == 10.0
    bar._progress.setSliderDown(False)


def test_cover_is_a_square_in_the_bottom_left_corner(shown) -> None:
    """The cover fills the bar's height, touches the left edge and has no margin."""
    bar = PlayerBar()
    bar.resize(900, bar.height())
    shown(bar)
    thumb = bar._thumb
    assert thumb.width() == thumb.height() == THUMB_SIZE
    assert thumb.height() == bar.height() - PLAYER_BORDER
    assert thumb.mapTo(bar, thumb.rect().topLeft()).x() == 0
    assert thumb.mapTo(bar, thumb.rect().topLeft()).y() == PLAYER_BORDER


def test_wide_cover_gets_bars_on_top_and_bottom() -> None:
    bar = PlayerBar()
    bar.set_track(make_tracks(1)[0], png_bytes(400, 100, "#3060c0"))
    image = bar._thumb.pixmap().toImage()
    assert (image.width(), image.height()) == (THUMB_SIZE, THUMB_SIZE)
    centre = THUMB_SIZE // 2
    # 4:1 picture: it is about 24 px tall in the middle, so the bars above and below are background.
    assert image.pixelColor(centre, 0) == QColor(SURFACE)
    assert image.pixelColor(centre, THUMB_SIZE - 1) == QColor(SURFACE)
    assert image.pixelColor(centre, centre) == QColor("#3060c0")
    # The whole width is the cover, so the left and right edges are not background.
    assert image.pixelColor(0, centre) == QColor("#3060c0")


def test_tall_cover_gets_bars_on_the_sides() -> None:
    bar = PlayerBar()
    bar.set_track(make_tracks(1)[0], png_bytes(100, 400, "#3060c0"))
    image = bar._thumb.pixmap().toImage()
    centre = THUMB_SIZE // 2
    assert image.pixelColor(0, centre) == QColor(SURFACE)
    assert image.pixelColor(THUMB_SIZE - 1, centre) == QColor(SURFACE)
    assert image.pixelColor(centre, 0) == QColor("#3060c0")


def test_square_cover_has_no_bars() -> None:
    bar = PlayerBar()
    bar.set_track(make_tracks(1)[0], png_bytes(300, 300, "#3060c0"))
    image = bar._thumb.pixmap().toImage()
    for x, y in ((0, 0), (THUMB_SIZE - 1, 0), (0, THUMB_SIZE - 1), (THUMB_SIZE - 1, THUMB_SIZE - 1)):
        assert image.pixelColor(x, y) == QColor("#3060c0")


def test_stop_button_emits_and_is_labelled() -> None:
    bar = PlayerBar()
    stops = _record(bar.stop_clicked)
    bar._stop.click()
    assert len(stops) == 1
    assert bar._stop.toolTip() == "Zatrzymaj"
    translator.set_language("en")
    assert bar._stop.toolTip() == "Stop"


def test_stop_button_is_on_the_right_next_to_the_speaker(shown) -> None:
    bar = PlayerBar()
    bar.resize(900, bar.height())
    shown(bar)
    stop = bar._stop
    centre = stop.mapTo(bar, stop.rect().center()).x()
    assert centre > bar.width() / 2
    assert centre < bar._speaker.mapTo(bar, bar._speaker.rect().center()).x()


def test_options_are_not_at_the_window_edge(shown) -> None:
    bar = PlayerBar()
    bar.resize(900, bar.height())
    shown(bar)
    volume = bar._volume
    assert bar.width() - volume.mapTo(bar, volume.rect().topRight()).x() == EDGE_MARGIN + 1
