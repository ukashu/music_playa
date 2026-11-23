from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QMainWindow, QVBoxLayout, QWidget

from music_playa.interfaces import Library, Player, Visualizer
from music_playa.models import PlaybackMode, Track
from music_playa_gui.bridge import PlaybackBridge
from music_playa_gui.widgets.controls import Transport
from music_playa_gui.widgets.library_view import LibraryView
from music_playa_gui.widgets.spectrum import SpectrumSettings, SpectrumWidget


class MainWindow(QMainWindow):
    def __init__(self, player: Player, library: Library, visualizer: Visualizer) -> None:
        super().__init__()
        self.player = player
        self.library = library
        self.setWindowTitle("music_playa")

        self._status = QLabel("No track")
        self._cover = QLabel()
        self._cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._cover.setFixedSize(220, 220)
        self._cover.hide()
        self._library_view = LibraryView()
        self._library_view.set_tracks(library.tracks)
        self._transport = Transport()
        self._spectrum = SpectrumWidget(visualizer)
        self._spectrum_settings = SpectrumSettings(self._spectrum)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addWidget(self._status)
        layout.addWidget(self._cover, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self._library_view)
        layout.addWidget(self._transport)
        layout.addWidget(self._spectrum_settings)
        layout.addWidget(self._spectrum)
        self.setCentralWidget(central)

        self._bridge = PlaybackBridge()
        self._bridge.track_changed.connect(self.show_track)
        self._bridge.progress_changed.connect(self.show_progress)
        self.player.add_listener(self._bridge)

        self._transport.play.clicked.connect(lambda: self.player.play())
        self._transport.pause.clicked.connect(lambda: self.player.pause())
        self._transport.stop.clicked.connect(lambda: self.player.stop())
        self._transport.next.clicked.connect(lambda: self.player.next())
        self._transport.previous.clicked.connect(lambda: self.player.previous())
        self._transport.mode.clicked.connect(self.cycle_mode)
        self._transport.seek_end.clicked.connect(self.seek_near_end)
        self._transport.volume_down.clicked.connect(lambda: self.change_volume(-0.1))
        self._transport.volume_up.clicked.connect(lambda: self.change_volume(0.1))
        self._library_view.cellClicked.connect(self.select_track)
        self.update_volume_label()
        self.show_track(self.player.current)

    def cycle_mode(self) -> None:
        modes = [
            PlaybackMode.IN_ORDER,
            PlaybackMode.SHUFFLE,
            PlaybackMode.REPEAT,
        ]
        index = modes.index(self.player.mode)
        self.player.mode = modes[(index + 1) % len(modes)]
        self._transport.mode.setText(f"Mode: {self.player.mode.value.replace('_', ' ').title()}")

    def seek_near_end(self) -> None:
        duration = self.player.duration
        self.player.seek(max(duration - 3.0, 0.0))

    def change_volume(self, change: float) -> None:
        self.player.set_volume(self.player.volume + change)
        self.update_volume_label()

    def update_volume_label(self) -> None:
        self._transport.volume_label.setText(f"Volume: {round(self.player.volume * 100)}%")

    def select_track(self, row: int, column: int) -> None:
        tracks = self.library.tracks
        if 0 <= row < len(tracks):
            self.player.select(tracks[row])

    def show_track(self, track: Track | None) -> None:
        title = track.title if track is not None else "No track"
        self._status.setText(f"{title}  {self.player.position:.1f}s")
        self.show_cover(track)

    def show_cover(self, track: Track | None) -> None:
        self._cover.clear()
        self._cover.hide()
        if track is None:
            return

        cover = self.library.cover(track)
        if cover is None:
            return

        pixmap = QPixmap()
        if not pixmap.loadFromData(cover):
            return

        self._cover.setPixmap(
            pixmap.scaled(
                self._cover.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        self._cover.show()

    def show_progress(self, position: float, duration: float) -> None:
        track = self.player.current
        title = track.title if track is not None else "No track"
        self._status.setText(f"{title}  {position:.1f}/{duration:.1f}s")
