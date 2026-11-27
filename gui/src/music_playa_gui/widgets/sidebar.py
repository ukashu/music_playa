from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from music_playa_gui.i18n import count_tracks, translator
from music_playa_gui.widgets.library_view import LibraryView


class Sidebar(QWidget):
    """Left panel: app title, track count and the list of all tracks."""

    def __init__(self, library_view: LibraryView, track_count: int) -> None:
        super().__init__()
        self.setObjectName("sidebar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedWidth(340)

        title = QLabel("music_playa")
        title.setObjectName("appTitle")
        self._track_count = track_count
        self._count = QLabel()
        self._count.setObjectName("muted")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 20, 12, 8)
        layout.setSpacing(4)
        layout.addWidget(title)
        layout.addWidget(self._count)
        layout.addSpacing(8)
        layout.addWidget(library_view, 1)

        translator.language_changed.connect(self.retranslate)
        self.retranslate()

    def retranslate(self) -> None:
        self._count.setText(count_tracks(self._track_count))
