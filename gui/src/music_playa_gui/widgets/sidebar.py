from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPainter, QPaintEvent, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from music_playa_gui.i18n import count_tracks, translator
from music_playa_gui.logo import LogoWidget
from music_playa_gui.widgets.flamingo import flamingo_pixmap
from music_playa_gui.widgets.library_view import LibraryView

LOGO_SIZE = 40  # logical px; the logo sits in front of the title


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
        self._flamingo_key: tuple | None = None

        self._logo = LogoWidget(LOGO_SIZE)

        title = QLabel("music_playa")
        title.setObjectName("appTitle")
        self._track_count = track_count
        self._count = QLabel()
        self._count.setObjectName("muted")

        header = QHBoxLayout()
        header.setSpacing(8)
        header.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        header.addWidget(self._logo)
        header.addWidget(title)
        header.addStretch(1)

        # The title and count keep a 12 px inset; the list takes the full width of the panel,
        # so its selection and header reach both edges.
        top = QVBoxLayout()
        top.setContentsMargins(12, 0, 12, 0)
        top.setSpacing(4)
        top.addLayout(header)
        top.addWidget(self._count)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 20, 0, 8)
        layout.setSpacing(0)
        layout.addLayout(top)
        layout.addSpacing(8)
        layout.addWidget(library_view, 1)

        translator.language_changed.connect(self.retranslate)
        self.retranslate()

    def retranslate(self) -> None:
        self._count.setText(count_tracks(self._track_count))

    def _flamingo_pixmap(self) -> QPixmap:
        """The flamingo for the current size and screen scale, built once per combination.

        It is made at paint time, not at resize: the window's device pixel ratio can still be
        1 at the first resize and change right after, which left the picture stretched (with
        jagged edges) until the next resize.
        """
        ratio = self.devicePixelRatioF()
        key = (self.width(), self.height(), ratio)
        if key != self._flamingo_key or self._flamingo is None:
            self._flamingo_key = key
            size = QSize(self.width(), self.height())
            self._flamingo = flamingo_pixmap(size, FLAMINGO_TOP, FLAMINGO_HEIGHT, ratio)
        return self._flamingo

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        # The flamingo is drawn over the list and title.
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self._flamingo_pixmap())
        painter.end()
