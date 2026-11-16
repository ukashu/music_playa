from PySide6.QtWidgets import QLabel, QMainWindow, QVBoxLayout, QWidget

from music_playa.interfaces import Library, Player, Visualizer
from music_playa.models import Track
from music_playa_gui.bridge import PlaybackBridge
from music_playa_gui.widgets.controls import Transport
from music_playa_gui.widgets.library_view import LibraryView


class MainWindow(QMainWindow):
    def __init__(self, player: Player, library: Library, visualizer: Visualizer) -> None:
        super().__init__()
        self.player = player
        self.library = library
        self.setWindowTitle("music_playa")

        self._status = QLabel("No track")
        self._library_view = LibraryView()
        self._library_view.set_tracks([track.title for track in library.tracks])
        self._transport = Transport()
        self._spectrum = QLabel(f"spectrum placeholder ({len(visualizer.bands())} bands)")

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addWidget(self._status)
        layout.addWidget(self._library_view)
        layout.addWidget(self._transport)
        layout.addWidget(self._spectrum)
        self.setCentralWidget(central)

        self._bridge = PlaybackBridge()
        self._bridge.track_changed.connect(self.show_track)
        self._bridge.progress_changed.connect(self.show_progress)
        self.player.add_listener(self._bridge)

        self._transport.play.clicked.connect(lambda: self.player.play())
        self._transport.pause.clicked.connect(lambda: self.player.pause())
        self._transport.next.clicked.connect(lambda: self.player.next())
        self._transport.previous.clicked.connect(lambda: self.player.previous())
        self.show_track(self.player.current)

    def show_track(self, track: Track | None) -> None:
        title = track.title if track is not None else "No track"
        self._status.setText(f"{title}  {self.player.position:.1f}s")

    def show_progress(self, position: float, duration: float) -> None:
        track = self.player.current
        title = track.title if track is not None else "No track"
        self._status.setText(f"{title}  {position:.1f}/{duration:.1f}s")
