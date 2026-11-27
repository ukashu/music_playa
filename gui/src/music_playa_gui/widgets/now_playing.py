from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPixmap, QResizeEvent
from PySide6.QtWidgets import QPushButton, QVBoxLayout, QWidget

from music_playa.interfaces import Visualizer
from music_playa_gui.i18n import tr, translator
from music_playa_gui.placeholder import vinyl_pixmap
from music_playa_gui.widgets.backdrop import scanlines_pixmap
from music_playa_gui.widgets.settings_panel import SettingsPanel
from music_playa_gui.widgets.spectrum import DEFAULT_COLUMNS, DEFAULT_SEGMENTS, SpectrumWidget

_DIM = QColor(18, 11, 46, 170)
_GRADIENT_TOP = QColor(18, 11, 46)
_GRADIENT_BOTTOM = QColor(36, 23, 87)
GEAR_SIZE = 40
GEAR_MARGIN = 16
VINYL_FILL = 0.9  # share of the shorter side taken by the vinyl record
PLACEHOLDER_SCANLINE_OPACITY = 0.6  # scanlines over the gradient and vinyl, which are not dimmed
VINYL_OPACITY = 0.8  # keeps the record in the background, like the dimmed cover


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
        self._cover: QPixmap | None = None
        self._scaled: QPixmap | None = None
        self._vinyl: QPixmap | None = None
        self._scanlines: QPixmap | None = None

        self._spectrum = SpectrumWidget(visualizer, columns, segments)

        layout = QVBoxLayout(self)
        # The top margin leaves a strip for the gear button.
        layout.setContentsMargins(24, GEAR_SIZE + 2 * GEAR_MARGIN, 24, 24)
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
    def spectrum(self) -> SpectrumWidget:
        return self._spectrum

    @property
    def settings_panel(self) -> SettingsPanel:
        return self._settings_panel

    def toggle_settings(self) -> None:
        self._settings_panel.toggle()
        self._gear.raise_()

    def retranslate(self) -> None:
        self._gear.setToolTip(tr("settings.tooltip"))

    def set_cover(self, data: bytes | None) -> None:
        pixmap = QPixmap()
        self._cover = pixmap if data is not None and pixmap.loadFromData(data) else None
        self._rescale()
        self.update()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._rescale()
        # Cached like the artwork: the spectrum repaints this view ~30 times a second.
        ratio = self.devicePixelRatioF()
        self._scanlines = scanlines_pixmap(self.size(), ratio)
        self._gear.move(self.width() - GEAR_SIZE - GEAR_MARGIN, GEAR_MARGIN)
        self._settings_panel.place()
        self._gear.raise_()

    def _rescale(self) -> None:
        """Cache the scaled artwork; the spectrum repaints this ~30 times a second.

        A cover is scaled to fill the view. Without a cover the vinyl record is
        scaled to fit inside it instead, so it stays a whole disc.
        """
        self._scaled = None
        self._vinyl = None
        if self.width() == 0 or self.height() == 0:
            return
        if self._cover is not None:
            self._scaled = self._cover.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            return
        vinyl = vinyl_pixmap()
        if not vinyl.isNull():
            side = round(min(self.width(), self.height()) * VINYL_FILL)
            self._vinyl = vinyl.scaled(
                side,
                side,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        if self._scaled is None:
            gradient = QLinearGradient(0, 0, 0, self.height())
            gradient.setColorAt(0.0, _GRADIENT_TOP)
            gradient.setColorAt(1.0, _GRADIENT_BOTTOM)
            painter.fillRect(self.rect(), gradient)
            if self._vinyl is not None:
                painter.setOpacity(VINYL_OPACITY)
                painter.drawPixmap(
                    (self.width() - self._vinyl.width()) // 2,
                    (self.height() - self._vinyl.height()) // 2,
                    self._vinyl,
                )
            # No dimming layer here, so the lines are toned down to match the cover.
            self._paint_scanlines(painter, PLACEHOLDER_SCANLINE_OPACITY)
        else:
            offset = QPoint(
                (self.width() - self._scaled.width()) // 2,
                (self.height() - self._scaled.height()) // 2,
            )
            painter.drawPixmap(offset, self._scaled)
            # The scanlines go on the cover itself, under the dimming layer.
            self._paint_scanlines(painter, 1.0)
            painter.fillRect(self.rect(), _DIM)
        painter.end()

    def _paint_scanlines(self, painter: QPainter, opacity: float) -> None:
        painter.setOpacity(opacity)
        if self._scanlines is not None:
            painter.drawPixmap(0, 0, self._scanlines)
