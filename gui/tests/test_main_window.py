import pytest
from conftest import FakeLibrary, FakeVisualizer, make_player, make_tracks, png_bytes
from PySide6.QtCore import QPoint, QRect

from music_playa.models import PlaybackMode, PlaybackState, RepeatMode
from music_playa_gui.i18n import translator
from music_playa_gui.main_window import MODES, REPEATS, MainWindow, _next_value
from music_playa_gui.settings import AppSettings
from music_playa_gui.widgets.spectrum import MODE_BARS, MODE_WAVE


@pytest.fixture
def tracks():
    return make_tracks(4)


@pytest.fixture
def window(tracks) -> MainWindow:
    covers = {tracks[1].path: png_bytes(64, 64)}
    return MainWindow(make_player(tracks), FakeLibrary(tracks, covers), FakeVisualizer())


def _selected_rows(window: MainWindow) -> list[int]:
    return [index.row() for index in window._library_view.selectionModel().selectedRows()]


def test_next_value_wraps() -> None:
    assert _next_value([1, 2, 3], 1) == 2
    assert _next_value([1, 2, 3], 3) == 1
    assert _next_value(["only"], "only") == "only"


def test_cycle_mode(window: MainWindow) -> None:
    seen = []
    for _ in MODES:
        window.cycle_mode()
        seen.append(window.player.mode)
    assert seen == [PlaybackMode.SHUFFLE, PlaybackMode.IN_ORDER]
    assert window._player_bar._playback_mode is PlaybackMode.IN_ORDER


def test_cycle_repeat(window: MainWindow) -> None:
    seen = []
    for _ in REPEATS:
        window.cycle_repeat()
        seen.append(window.player.repeat)
    assert seen == [RepeatMode.ALL, RepeatMode.ONE, RepeatMode.OFF]


def test_mode_and_repeat_buttons(window: MainWindow) -> None:
    window._player_bar._mode.click()
    window._player_bar._repeat.click()
    assert window.player.mode is PlaybackMode.SHUFFLE
    assert window.player.repeat is RepeatMode.ALL


def test_play_track(window: MainWindow, tracks) -> None:
    window.play_track(2)
    assert window.player.current == tracks[2]
    assert window.player.state is PlaybackState.PLAYING
    assert window._player_bar._toggle.text() == "⏸"
    assert _selected_rows(window) == [2]


def test_play_track_out_of_range(window: MainWindow, tracks) -> None:
    window.play_track(len(tracks))
    window.play_track(-1)
    assert window.player.state is PlaybackState.STOPPED


def test_play_first_track(window: MainWindow, tracks) -> None:
    window._player_bar._next.click()
    window.play_track(0)
    assert window.player.current == tracks[0]
    assert window.player.state is PlaybackState.PLAYING


def test_starts_with_the_current_track(window: MainWindow, tracks) -> None:
    assert window.windowTitle() == "music_playa"
    assert window._player_bar._title._text == tracks[0].title
    assert _selected_rows(window) == [0]


def test_empty_library() -> None:
    window = MainWindow(make_player([]), FakeLibrary([]), FakeVisualizer())
    assert window._player_bar._title._text == "Brak utworu"
    window.toggle_playback()
    assert window.player.state is PlaybackState.STOPPED


def test_spectrum_reads_the_visualizer(tracks) -> None:
    window = MainWindow(make_player(tracks), FakeLibrary(tracks), FakeVisualizer([1.0] * 64))
    spectrum = window._now_playing._spectrum
    spectrum._refresh()
    assert spectrum._levels == [1.0] * spectrum.columns


def test_layout_fills_the_window(window: MainWindow, shown) -> None:
    window.resize(1100, 700)
    shown(window)
    central = window.centralWidget()

    def rect(widget) -> QRect:
        return QRect(widget.mapTo(central, QPoint(0, 0)), widget.size())

    sidebar, view, bar = rect(window._sidebar), rect(window._now_playing), rect(window._player_bar)
    assert sidebar.topLeft() == QPoint(0, 0)
    assert view.top() == 0
    assert view.left() == sidebar.right() + 1
    assert view.right() == central.width() - 1
    assert sidebar.bottom() == view.bottom()
    assert bar.top() == view.bottom() + 1
    assert (bar.left(), bar.right(), bar.bottom()) == (0, central.width() - 1, central.height() - 1)


def test_clicking_a_row_plays_it(window: MainWindow, tracks) -> None:
    window._library_view.cellClicked.emit(3, 1)
    assert window.player.current == tracks[3]
    assert window.player.state is PlaybackState.PLAYING


def test_toggle_playback(window: MainWindow) -> None:
    window.toggle_playback()
    assert window.player.state is PlaybackState.PLAYING
    window.toggle_playback()
    assert window.player.state is PlaybackState.PAUSED
    assert window._player_bar._toggle.text() == "▶"


def test_poll_follows_a_player_that_stopped_on_its_own(window: MainWindow) -> None:
    window.toggle_playback()
    window.player.stop()
    window.poll_progress()
    assert window._player_bar._toggle.text() == "▶"


def test_next_and_previous_buttons(window: MainWindow, tracks) -> None:
    window._player_bar._next.click()
    assert window.player.current == tracks[1]
    assert _selected_rows(window) == [1]
    assert window._player_bar._title._text == tracks[1].title
    window._player_bar._previous.click()
    assert window.player.current == tracks[0]


def test_track_change_shows_the_cover(window: MainWindow) -> None:
    window._player_bar._next.click()
    assert window._now_playing._cover is not None
    assert window._player_bar._cover is not None
    window._player_bar._next.click()
    assert window._now_playing._cover is None


def test_seek_and_volume_reach_the_player(window: MainWindow) -> None:
    window.toggle_playback()
    window._player_bar.seek_requested.emit(42.0)
    assert window.player.position == 42.0
    window._player_bar.volume_changed.emit(0.25)
    assert window.player.volume == 0.25


def test_change_language_is_saved(window: MainWindow) -> None:
    window.change_language("en")
    assert translator.language == "en"
    assert AppSettings().language() == "en"


def test_language_comes_from_the_settings(tracks) -> None:
    AppSettings().set_language("en")
    MainWindow(make_player(tracks), FakeLibrary(tracks), FakeVisualizer())
    assert translator.language == "en"


def test_spectrum_size_is_saved_and_restored(window: MainWindow, tracks) -> None:
    spectrum_settings = window._now_playing.settings_panel.spectrum_settings
    spectrum_settings.columns.setValue(48)
    spectrum_settings.segments.setValue(12)
    settings = AppSettings()
    assert (settings.spectrum_columns(), settings.spectrum_segments()) == (48, 12)
    again = MainWindow(make_player(tracks), FakeLibrary(tracks), FakeVisualizer())
    spectrum = again._now_playing._spectrum
    assert (spectrum.columns, spectrum.segments) == (48, 12)


def test_stop_button_stops_and_resets_the_progress(window: MainWindow) -> None:
    window.play_track(1)
    window._player_bar.set_progress(30.0, 180.0)
    window._player_bar._stop.click()
    window.poll_progress()
    assert window.player.state is PlaybackState.STOPPED
    assert window.player.position == 0.0
    assert window._player_bar._progress.value() == 0
    assert window._player_bar._elapsed.text() == "0:00"
    assert window._player_bar._toggle.text() == "▶"


def test_stop_then_play_starts_from_the_beginning(window: MainWindow, tracks) -> None:
    window.play_track(0)
    window.player.seek(40.0)
    window.stop_playback()
    window.toggle_playback()
    assert window.player.current == tracks[0]
    assert window.player.position == 0.0
    assert window.player.state is PlaybackState.PLAYING


def test_spectrum_mode_is_saved_and_restored(window: MainWindow, tracks) -> None:
    spectrum_settings = window._now_playing.settings_panel.spectrum_settings
    assert AppSettings().spectrum_mode() == MODE_BARS
    spectrum_settings.mode.setCurrentIndex(spectrum_settings.mode.findData(MODE_WAVE))
    assert AppSettings().spectrum_mode() == MODE_WAVE
    again = MainWindow(make_player(tracks), FakeLibrary(tracks), FakeVisualizer())
    assert again._now_playing._spectrum.mode == MODE_WAVE
    assert again._now_playing.settings_panel.spectrum_settings.mode.currentData() == MODE_WAVE


def test_language_choice_in_the_panel(window: MainWindow) -> None:
    box = window._now_playing.settings_panel.language_box
    box.setCurrentIndex(box.findData("en"))
    assert translator.language == "en"
    assert AppSettings().language() == "en"
