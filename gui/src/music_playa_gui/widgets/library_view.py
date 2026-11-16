from PySide6.QtWidgets import QListWidget


class LibraryView(QListWidget):
    def set_tracks(self, titles: list[str]) -> None:
        self.clear()
        self.addItems(titles)
