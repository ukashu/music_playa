from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QLinearGradient, QPainter, QPixmap, QResizeEvent
from PySide6.QtWidgets import QPushButton, QVBoxLayout, QWidget

from music_playa.interfaces import Visualizer
from music_playa_gui.i18n import tr, translator
from music_playa_gui.logo import scaled_logo
from music_playa_gui.widgets.settings_panel import SettingsPanel
from music_playa_gui.widgets.spectrum import DEFAULT_COLUMNS, DEFAULT_SEGMENTS, SpectrumWidget

_DIM = QColor(18, 11, 46, 170)
_GRADIENT_TOP = QColor(18, 11, 46)
_GRADIENT_BOTTOM = QColor(36, 23, 87)
GEAR_SIZE = 40
GEAR_MARGIN = 16
LOGO_FILL = 0.9  # share of the shorter side taken by the logo
LOGO_OPACITY = 0.8  # keeps the logo in the background, like the dimmed cover


class NowPlayingView(QWidget):
    """Dimmed cover art filling the view, with the spectrum drawn on top.

    A gear button in the top right corner opens the settings panel, which
    slides in over the right edge of the view.
    """

    def __init__(
        self,
        visualizer: Visualizer,
        columns: int = DEFAULT_COLUMNS,
        segments: int = DEFAULT_SEGMENTS,
    ) -> None:
        super().__init__()
        self.setObjectName("nowPlaying")
        self._cover: QImage | None = None
        self._scaled: QPixmap | None = None
        self._logo: QPixmap | None = None
        self._ratio = 0.0

        self._spectrum = SpectrumWidget(visualizer, columns, segments)

        layout = QVBoxLayout(self)
        # The visualizer uses the full width and height of the view. Only the top keeps a strip
        # for the gear button, so the bars do not run under it.
        layout.setContentsMargins(0, GEAR_SIZE + 2 * GEAR_MARGIN, 0, 0)
        layout.addWidget(self._spectrum, 1)

        self._settings_panel = SettingsPanel(self._spectrum, self)
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

    def set_cover(self, data: bytes | None) -> None:
        image = QImage()
        self._cover = image if data is not None and image.loadFromData(data) else None
        self._rescale()
        self.update()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._rescale()
        self._gear.move(self.width() - GEAR_SIZE - GEAR_MARGIN, GEAR_MARGIN)
        self._settings_panel.place()
        self._gear.raise_()

    def _rescale(self) -> None:
        """Cache the scaled artwork; the spectrum repaints this ~30 times a second.

        A cover is scaled to fill the view. Without a cover the logo is
        scaled to fit inside it instead, so it stays whole. Both are prepared in
        device pixels, so they are not stretched on scaled screens.
        """
        self._scaled = None
        self._logo = None
        ratio = self.devicePixelRatioF()
        self._ratio = ratio
        if self.width() == 0 or self.height() == 0:
            return
        if self._cover is not None:
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
        side = round(min(self.width(), self.height()) * LOGO_FILL)
        self._logo = scaled_logo(round(side * ratio), ratio)

    def paintEvent(self, event) -> None:
        # The device pixel ratio can change after the first resize (the screen reports its
        # scale a moment later), so the cached artwork is checked here, not only at resize.
        if self.devicePixelRatioF() != self._ratio:
            self._rescale()
        painter = QPainter(self)
        if self._scaled is None:
            gradient = QLinearGradient(0, 0, 0, self.height())
            gradient.setColorAt(0.0, _GRADIENT_TOP)
            gradient.setColorAt(1.0, _GRADIENT_BOTTOM)
            painter.fillRect(self.rect(), gradient)
            if self._logo is not None:
                painter.setOpacity(LOGO_OPACITY)
                self._draw_centred(painter, self._logo)
        else:
            self._draw_centred(painter, self._scaled)
            painter.fillRect(self.rect(), _DIM)
        painter.end()

    def _draw_centred(self, painter: QPainter, pixmap: QPixmap) -> None:
        logical = pixmap.deviceIndependentSize()
        painter.drawPixmap(
            round((self.width() - logical.width()) / 2),
            round((self.height() - logical.height()) / 2),
            pixmap,
        )
