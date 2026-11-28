from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPaintEvent, QPixmap
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from music_playa_gui.i18n import count_tracks, translator
from music_playa_gui.logo import LogoWidget
from music_playa_gui.theme import CYAN, PINK
from music_playa_gui.utils import clamp
from music_playa_gui.widgets.flamingo import flamingo_pixmap
from music_playa_gui.widgets.library_view import LibraryView

LOGO_SIZE = 40  # logical px; the logo sits in front of the title


# The flamingo keeps the same size and place whatever the window size. Its head is FLAMINGO_TOP
# px below the top of the panel; the legs are cut off if the window is too short.
FLAMINGO_TOP = 253  # logical px from the top of the panel to the top of the bird
FLAMINGO_HEIGHT = 681  # logical px, the bird's height

# The title and the logo glow with the bass as a halo around them: its blur radius (logical px)
# goes from the first to the second value with the level, and its colour fades in with it.
GLOW_BLUR_MIN = 6.0
GLOW_BLUR_MAX = 34.0


def _glow_effect(colour: str) -> QGraphicsDropShadowEffect:
    """A halo of the given colour around a widget, switched off until the bass makes it glow."""
    effect = QGraphicsDropShadowEffect()
    effect.setOffset(0, 0)
    effect.setColor(QColor(colour))
    effect.setEnabled(False)
    return effect


def _apply_glow(effect: QGraphicsDropShadowEffect, colour: str, level: float) -> None:
    halo = QColor(colour)
    halo.setAlpha(round(255 * level))
    effect.setColor(halo)
    effect.setBlurRadius(GLOW_BLUR_MIN + (GLOW_BLUR_MAX - GLOW_BLUR_MIN) * level)
    effect.setEnabled(level > 0.0)


class Sidebar(QWidget):
    """Left panel: app title, track count and the list of all tracks."""

    def __init__(self, library_view: LibraryView, track_count: int) -> None:
        super().__init__()
        self.setObjectName("sidebar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedWidth(340)
        self._flamingo: QPixmap | None = None
        self._flamingo_key: tuple | None = None
        self._flamingo_glow: QPixmap | None = None  # made when the bass first needs it
        self._glow = 0.0

        self._logo = LogoWidget(LOGO_SIZE)
        self._logo_glow = _glow_effect(CYAN)
        self._logo.setGraphicsEffect(self._logo_glow)

        title = QLabel("music_playa")
        title.setObjectName("appTitle")
        self._title_glow = _glow_effect(PINK)
        title.setGraphicsEffect(self._title_glow)
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

    def set_glow(self, level: float) -> None:
        """Make the flamingo, the title and the logo glow; level is the bass, 0 (none) to 1."""
        level = clamp(level, 0.0, 1.0)
        if level == self._glow:
            return
        self._glow = level
        _apply_glow(self._title_glow, PINK, level)
        _apply_glow(self._logo_glow, CYAN, level)
        self.update()

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
            self._flamingo_glow = None
        return self._flamingo

    def _glowing_flamingo(self) -> QPixmap:
        """The lit-up flamingo with its halo, for the key of the normal one (made just before)."""
        if self._flamingo_glow is None:
            size, ratio = QSize(self.width(), self.height()), self.devicePixelRatioF()
            self._flamingo_glow = flamingo_pixmap(size, FLAMINGO_TOP, FLAMINGO_HEIGHT, ratio, glow=True)
        return self._flamingo_glow

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        # The flamingo is drawn over the list and title.
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self._flamingo_pixmap())
        if self._glow > 0.0:
            # The lit-up flamingo goes over the normal one, as opaque as the bass is strong.
            painter.setOpacity(self._glow)
            painter.drawPixmap(0, 0, self._glowing_flamingo())
        painter.end()
