import time

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QImage, QLinearGradient, QPainter, QPixmap, QResizeEvent
from PySide6.QtWidgets import QPushButton, QVBoxLayout, QWidget

from music_playa.interfaces import Visualizer
from music_playa_gui.cover_style import COVER_DISC, COVER_STYLES, DEFAULT_COVER_STYLE
from music_playa_gui.i18n import tr, translator
from music_playa_gui.logo import covered_logo, scaled_logo
from music_playa_gui.theme import BACKGROUND
from music_playa_gui.utils import advance_angle
from music_playa_gui.widgets.settings_panel import SettingsPanel
from music_playa_gui.widgets.spectrum import (
    DEFAULT_COLUMNS,
    BACKGROUND_NONE,
    DEFAULT_SEGMENTS,
    FRAME_MS,
    MODE_BARS,
    SpectrumWidget,
)

_DIM = QColor(18, 11, 46, 170)
_GRADIENT_TOP = QColor(18, 11, 46)
_GRADIENT_BOTTOM = QColor(36, 23, 87)
_FLAT = QColor(BACKGROUND)
GEAR_SIZE = 40
GEAR_MARGIN = 16
LOGO_FILL = 0.9  # share of the shorter side taken by the logo
LOGO_OPACITY = 0.8  # keeps the logo in the background, like the dimmed cover
SPIN_PERIOD_S = 6.0  # seconds the disc takes for one turn while a track plays


class NowPlayingView(QWidget):
    """Dimmed cover art filling the view, with the spectrum drawn on top.

    A gear button in the top right corner opens the settings panel, which
    slides in over the right edge of the view. bass_changed passes on the glow level of the bass
    (see SpectrumWidget) for the other panels.
    """

    bass_changed = Signal(float)

    def __init__(
        self,
        visualizer: Visualizer,
        columns: int = DEFAULT_COLUMNS,
        segments: int = DEFAULT_SEGMENTS,
        mode: str = MODE_BARS,
        cover_style: str = DEFAULT_COVER_STYLE,
        background: str = BACKGROUND_NONE,
        bass_glow: bool = False,
    ) -> None:
        super().__init__()
        self.setObjectName("nowPlaying")
        self._cover: QImage | None = None
        self._scaled: QPixmap | None = None
        self._logo: QPixmap | None = None
        self._disc: QPixmap | None = None
        self._ratio = 0.0
        self._cover_style = cover_style if cover_style in COVER_STYLES else DEFAULT_COVER_STYLE
        self._playing = False
        self._angle = 0.0
        self._clock = time.monotonic
        self._last_tick = 0.0
        self._tinted = False

        self._spin_timer = QTimer(self)
        self._spin_timer.setInterval(FRAME_MS)
        self._spin_timer.timeout.connect(self._spin)

        self._spectrum = SpectrumWidget(visualizer, columns, segments, mode, background, bass_glow)
        self._spectrum.refreshed.connect(self._on_spectrum_refreshed)
        self._spectrum.bass_changed.connect(self.bass_changed)

        layout = QVBoxLayout(self)
        # The visualizer uses the full width and height of the view. Only the top keeps a strip
        # for the gear button, so the bars do not run under it.
        layout.setContentsMargins(0, GEAR_SIZE + 2 * GEAR_MARGIN, 0, 0)
        layout.addWidget(self._spectrum, 1)

        self._settings_panel = SettingsPanel(self._spectrum, self, self._cover_style)
        self._settings_panel.cover_style_selected.connect(self.set_cover_style)
        self._gear = QPushButton("⚙", self)
        self._gear.setObjectName("gearButton")
        self._gear.setFixedSize(GEAR_SIZE, GEAR_SIZE)
        self._gear.setCursor(Qt.CursorShape.PointingHandCursor)
        self._gear.clicked.connect(self.toggle_settings)
        translator.language_changed.connect(self.retranslate)
        self.retranslate()

    @property
    def settings_panel(self) -> SettingsPanel:
        return self._settings_panel

    def toggle_settings(self) -> None:
        self._settings_panel.toggle()
        self._gear.raise_()

    def retranslate(self) -> None:
        self._gear.setToolTip(tr("settings.tooltip"))

    @property
    def cover_style(self) -> str:
        return self._cover_style

    @property
    def angle(self) -> float:
        """Degrees the disc is turned by (always 0 in the fill style)."""
        return self._angle

    def set_cover(self, data: bytes | None) -> None:
        image = QImage()
        self._cover = image if data is not None and image.loadFromData(data) else None
        self._rescale()
        self.update()

    def set_bass_glow(self, enabled: bool) -> None:
        self._spectrum.set_bass_glow(enabled)

    def set_cover_style(self, style: str) -> None:
        if style not in COVER_STYLES or style == self._cover_style:
            return
        self._cover_style = style
        self._rescale()
        self._update_spin()
        self.update()

    def set_playing(self, playing: bool) -> None:
        """The disc only turns while a track plays; it stays where it is when paused."""
        self._playing = playing
        self._update_spin()

    def _on_spectrum_refreshed(self) -> None:
        # The background colouring follows the spectrum, so it is repainted with every refresh,
        # and once more after it was switched off so that the colours disappear.
        if self._spectrum.background != BACKGROUND_NONE or self._tinted:
            self.update()

    def _update_spin(self) -> None:
        spinning = self._playing and self._cover_style == COVER_DISC
        if spinning and not self._spin_timer.isActive():
            # Time before the start must not count, or the disc would jump on resume.
            self._last_tick = self._clock()
            self._spin_timer.start()
        elif not spinning and self._spin_timer.isActive():
            self._spin_timer.stop()

    def _spin(self) -> None:
        now = self._clock()
        self._angle = advance_angle(self._angle, now - self._last_tick, SPIN_PERIOD_S)
        self._last_tick = now
        self.update()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._rescale()
        self._gear.move(self.width() - GEAR_SIZE - GEAR_MARGIN, GEAR_MARGIN)
        self._settings_panel.place()
        self._gear.raise_()

    def _rescale(self) -> None:
        """Cache the scaled artwork; the spectrum repaints this ~30 times a second.

        In the fill style a cover is scaled to fill the view. Without a cover the logo is
        scaled to fit inside it instead, so it stays whole. In the disc style the logo is
        always shown, filled with the cover when there is one. All are prepared in device
        pixels, so they are not stretched on scaled screens.
        """
        self._scaled = None
        self._logo = None
        self._disc = None
        ratio = self.devicePixelRatioF()
        self._ratio = ratio
        if self.width() == 0 or self.height() == 0:
            return
        disc = self._cover_style == COVER_DISC
        if self._cover is not None and not disc:
            self._scaled = QPixmap.fromImage(
                self._cover.scaled(
                    round(self.width() * ratio),
                    round(self.height() * ratio),
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            self._scaled.setDevicePixelRatio(ratio)
            return
        side = round(round(min(self.width(), self.height()) * LOGO_FILL) * ratio)
        if disc and self._cover is not None:
            self._disc = covered_logo(self._cover, side, ratio)
        else:
            self._logo = scaled_logo(side, ratio)

    def paintEvent(self, event) -> None:
        # The device pixel ratio can change after the first resize (the screen reports its
        # scale a moment later), so the cached artwork is checked here, not only at resize.
        if self.devicePixelRatioF() != self._ratio:
            self._rescale()
        painter = QPainter(self)
        if self._cover_style == COVER_DISC:
            self._paint_disc(painter)
        elif self._scaled is None:
            self._paint_gradient(painter)
            self._paint_tint(painter)
            if self._logo is not None:
                painter.setOpacity(LOGO_OPACITY)
                self._draw_centred(painter, self._logo)
        else:
            self._draw_centred(painter, self._scaled)
            painter.fillRect(self.rect(), _DIM)
            self._paint_tint(painter)
        painter.end()

    def _paint_tint(self, painter: QPainter) -> None:
        """The background colouring: a horizontal gradient with one colour stop per bar or sample."""
        stops = self._spectrum.background_stops()
        self._tinted = bool(stops)
        if not stops:
            return
        gradient = QLinearGradient(0, 0, self.width(), 0)
        for position, colour in stops:
            gradient.setColorAt(position, colour)
        painter.fillRect(self.rect(), gradient)

    def _paint_gradient(self, painter: QPainter) -> None:
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0.0, _GRADIENT_TOP)
        gradient.setColorAt(1.0, _GRADIENT_BOTTOM)
        painter.fillRect(self.rect(), gradient)

    def _paint_disc(self, painter: QPainter) -> None:
        """A plain background and the cover on the disc, or the gradient and the logo without one."""
        if self._disc is not None:
            painter.fillRect(self.rect(), _FLAT)
            self._paint_tint(painter)
            pixmap = self._disc
        else:
            self._paint_gradient(painter)
            self._paint_tint(painter)
            painter.setOpacity(LOGO_OPACITY)
            pixmap = self._logo
        if pixmap is None:
            return
        logical = pixmap.deviceIndependentSize()
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.translate(self.width() / 2, self.height() / 2)
        painter.rotate(self._angle)
        painter.drawPixmap(round(-logical.width() / 2), round(-logical.height() / 2), pixmap)

    def _draw_centred(self, painter: QPainter, pixmap: QPixmap) -> None:
        logical = pixmap.deviceIndependentSize()
        painter.drawPixmap(
            round((self.width() - logical.width()) / 2),
            round((self.height() - logical.height()) / 2),
            pixmap,
        )
