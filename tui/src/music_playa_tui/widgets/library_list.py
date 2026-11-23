from rich.text import Text
from textual.widgets import Label, ListItem, ListView

from music_playa.models import Track


class LibraryList(ListView):
    def set_tracks(self, tracks: list[Track]) -> None:
        self.clear()
        for track in tracks:
            details = Text(track.title, style="bold")
            details.append(f"\n{track.artist} · {track.album}", style="dim")
            if track.track_number:
                details.append(f"\nTrack {track.track_number}", style="dim")
            details.append(f"\n{_format_duration(track.duration)}", style="cyan")
            self.append(ListItem(Label(details)))


def _format_duration(duration: float) -> str:
    minutes, seconds = divmod(max(0, int(duration)), 60)
    return f"{minutes}:{seconds:02d}"
