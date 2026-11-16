from textual.widgets import Label, ListItem, ListView


class LibraryList(ListView):
    def set_tracks(self, titles: list[str]) -> None:
        self.clear()
        for title in titles:
            self.append(ListItem(Label(title)))
