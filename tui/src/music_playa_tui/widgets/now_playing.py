from textual.widgets import Label


class NowPlaying(Label):
    def set_status(self, text: str) -> None:
        self.update(text)
