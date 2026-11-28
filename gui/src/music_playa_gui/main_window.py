from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QVBoxLayout, QWidget

from music_playa.interfaces import Library, Player, Visualizer
from music_playa.models import PlaybackMode, PlaybackState, RepeatMode, Track
from music_playa_gui.bridge import PlaybackBridge
from music_playa_gui.i18n import translator
from music_playa_gui.settings import AppSettings
from music_playa_gui.widgets.library_view import LibraryView
from music_playa_gui.widgets.now_playing import NowPlayingView
from music_playa_gui.widgets.player_bar import PlayerBar
from music_playa_gui.widgets.sidebar import Sidebar

MODES = [PlaybackMode.IN_ORDER, PlaybackMode.SHUFFLE]
REPEATS = [RepeatMode.OFF, RepeatMode.ALL, RepeatMode.ONE]
PROGRESS_INTERVAL_MS = 100


def _next_value[T](values: list[T], current: T) -> T:
    """The value after current in values, wrapping round to the first one."""
    return values[(values.index(current) + 1) % len(values)]


class MainWindow(QMainWindow):
    def __init__(self, player: Player, library: Library, visualizer: Visualizer) -> None:
        super().__init__()
        self.player = player
        self.library = library
        self.setWindowTitle("music_playa")

        # The language must be set before the widgets are built so they start translated.
        self._settings = AppSettings()
        translator.set_language(self._settings.language())

        self._library_view = LibraryView()
        self._library_view.set_tracks(library.tracks)
        self._sidebar = Sidebar(self._library_view, len(library.tracks))
        self._now_playing = NowPlayingView(
            visualizer,
            self._settings.spectrum_columns(),
            self._settings.spectrum_segments(),
            self._settings.spectrum_mode(),
        )
        self._player_bar = PlayerBar()

        upper = QHBoxLayout()
        upper.setContentsMargins(0, 0, 0, 0)
        upper.setSpacing(0)
        upper.addWidget(self._sidebar)
        upper.addWidget(self._now_playing, 1)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(upper, 1)
        layout.addWidget(self._player_bar)
        self.setCentralWidget(central)

        self._bridge = PlaybackBridge()
        self._bridge.track_changed.connect(self.show_track)
        self._bridge.progress_changed.connect(self.show_progress)
        self.player.add_listener(self._bridge)

        self._player_bar.previous_clicked.connect(lambda: self.player.previous())
        self._player_bar.next_clicked.connect(lambda: self.player.next())
        self._player_bar.toggle_clicked.connect(self.toggle_playback)
        self._player_bar.stop_clicked.connect(self.stop_playback)
        self._player_bar.mode_clicked.connect(self.cycle_mode)
        self._player_bar.repeat_clicked.connect(self.cycle_repeat)
        self._player_bar.seek_requested.connect(lambda position: self.player.seek(position))
        self._player_bar.volume_changed.connect(lambda volume: self.player.set_volume(volume))
        self._library_view.cellClicked.connect(lambda row, _column: self.play_track(row))

        panel = self._now_playing.settings_panel
        panel.language_selected.connect(self.change_language)
        panel.spectrum_settings.columns.valueChanged.connect(self._settings.set_spectrum_columns)
        panel.spectrum_settings.segments.valueChanged.connect(self._settings.set_spectrum_segments)
        panel.spectrum_settings.mode_changed.connect(self._settings.set_spectrum_mode)

        self._player_bar.set_mode(self.player.mode)
        self._player_bar.set_repeat(self.player.repeat)
        self._player_bar.set_volume(self.player.volume)
        self.show_track(self.player.current)
        self.show_progress(self.player.position, self.player.duration)
        self._sync_playing()

        # The player only reports progress after user actions (play, seek, next...),
        # not while a track is playing, so the position is polled for the progress bar.
        # The play/pause icon is polled too, because the player can stop on its own
        # (for example at the end of the list) without any notification.
        self._progress_timer = QTimer(self)
        self._progress_timer.setInterval(PROGRESS_INTERVAL_MS)
        self._progress_timer.timeout.connect(self.poll_progress)
        self._progress_timer.start()

    def poll_progress(self) -> None:
        self.show_progress(self.player.position, self.player.duration)
        self._sync_playing()

    def _sync_playing(self) -> None:
        self._player_bar.set_playing(self.player.state is PlaybackState.PLAYING)

    def change_language(self, code: str) -> None:
        translator.set_language(code)
        self._settings.set_language(code)

    def toggle_playback(self) -> None:
        if self.player.state is PlaybackState.PLAYING:
            self.player.pause()
        else:
            self.player.play()
        self._sync_playing()

    def stop_playback(self) -> None:
        self.player.stop()
        self._sync_playing()

    def cycle_mode(self) -> None:
        self.player.mode = _next_value(MODES, self.player.mode)
        self._player_bar.set_mode(self.player.mode)

    def cycle_repeat(self) -> None:
        self.player.repeat = _next_value(REPEATS, self.player.repeat)
        self._player_bar.set_repeat(self.player.repeat)

    def play_track(self, row: int) -> None:
        tracks = self.library.tracks
        if 0 <= row < len(tracks):
            self.player.select(tracks[row])
            self.player.play()
            self._sync_playing()

    def show_track(self, track: Track | None) -> None:
        cover = self.library.cover(track) if track is not None else None
        self._player_bar.set_track(track, cover)
        self._now_playing.set_cover(cover)
        self._library_view.highlight_track(track)

    def show_progress(self, position: float, duration: float) -> None:
        self._player_bar.set_progress(position, duration)
