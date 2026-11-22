from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Button, Footer, Header, ListView

from music_playa.interfaces import Library, Player, Visualizer
from music_playa.models import PlaybackMode, Track
from music_playa_tui.adapter import TextualAdapter
from music_playa_tui.widgets.library_list import LibraryList
from music_playa_tui.widgets.now_playing import NowPlaying
from music_playa_tui.widgets.spectrum import SpectrumPlaceholder


class MusicApp(App[None]):
    CSS_PATH = "app.tcss"
    TITLE = "music_playa"

    def __init__(self, player: Player, library: Library, visualizer: Visualizer) -> None:
        super().__init__()
        self.player = player
        self.library = library
        self.visualizer = visualizer

    def compose(self) -> ComposeResult:
        yield Header()
        yield NowPlaying(id="now-playing")
        yield LibraryList(id="library")
        with Horizontal(id="controls"):
            yield Button("Play", id="play")
            yield Button("Pause", id="pause")
            yield Button("Stop", id="stop")
            yield Button("Previous", id="previous")
            yield Button("Next", id="next")
        with Horizontal(id="test-controls"):
            yield Button("Mode: In Order", id="mode")
            yield Button("Seek 3s from End", id="seek-end")
            yield Button("Volume -", id="volume-down")
            yield Button("Volume +", id="volume-up")
        yield SpectrumPlaceholder(band_count=len(self.visualizer.bands()))
        yield Footer()

    def on_mount(self) -> None:
        library = self.query_one(LibraryList)
        library.set_tracks([track.title for track in self.library.tracks])
        self.player.add_listener(TextualAdapter(self))
        self._volume = self.player.volume
        self.show_track(self.player.current)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        actions = {
            "play": self.player.play,
            "pause": self.player.pause,
            "stop": self.player.stop,
            "next": self.player.next,
            "previous": self.player.previous,
        }
        action = actions.get(event.button.id or "")
        if action is not None:
            action()
            return
        if event.button.id == "mode":
            modes = [
                PlaybackMode.IN_ORDER,
                PlaybackMode.SHUFFLE,
                PlaybackMode.REPEAT,
            ]
            index = modes.index(self.player.mode)
            self.player.mode = modes[(index + 1) % len(modes)]
            event.button.label = f"Mode: {self.player.mode.value.replace('_', ' ').title()}"
        elif event.button.id == "seek-end":
            self.player.seek(max(self.player.duration - 3.0, 0.0))
        elif event.button.id == "volume-down":
            self._volume = max(self._volume - 0.1, 0.0)
            self.player.set_volume(self._volume)
        elif event.button.id == "volume-up":
            self._volume = min(self._volume + 0.1, 1.0)
            self.player.set_volume(self._volume)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.list_view.id != "library":
            return
        tracks = self.library.tracks
        if 0 <= event.index < len(tracks):
            self.player.select(tracks[event.index])

    def show_track(self, track: Track | None) -> None:
        title = track.title if track is not None else "No track"
        self.query_one(NowPlaying).set_status(f"{title}  {self.player.position:.1f}s")

    def show_progress(self, position: float, duration: float) -> None:
        track = self.player.current
        title = track.title if track is not None else "No track"
        self.query_one(NowPlaying).set_status(f"{title}  {position:.1f}/{duration:.1f}s")
