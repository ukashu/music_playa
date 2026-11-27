from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPainter, QPaintEvent, QPixmap, QResizeEvent
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from music_playa_gui.i18n import count_tracks, translator
from music_playa_gui.widgets.flamingo import flamingo_pixmap
from music_playa_gui.widgets.library_view import LibraryView


# The flamingo keeps the same size and place whatever the window size. Its head is FLAMINGO_TOP
# px below the top of the panel; the legs are cut off if the window is too short.
FLAMINGO_TOP = 253  # logical px from the top of the panel to the top of the bird
FLAMINGO_HEIGHT = 681  # logical px, the bird's height


class Sidebar(QWidget):
    """Left panel: app title, track count and the list of all tracks."""

    def __init__(self, library_view: LibraryView, track_count: int) -> None:
        super().__init__()
        self.setObjectName("sidebar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedWidth(340)
        self._flamingo: QPixmap | None = None

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

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        # The flamingo is drawn over the list and title. Built once per size, not on every paint.
        size = QSize(self.width(), self.height())
        self._flamingo = flamingo_pixmap(size, FLAMINGO_TOP, FLAMINGO_HEIGHT, self.devicePixelRatioF())

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        if self._flamingo is not None:
            painter = QPainter(self)
            painter.drawPixmap(0, 0, self._flamingo)
            painter.end()
