import math

from PySide6.QtCore import QPoint, QPointF, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QImage,
    QMouseEvent,
    QMoveEvent,
    QPainter,
    QPaintEvent,
    QPixmap,
    QPolygonF,
    QResizeEvent,
)
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QStyle,
    QStyleOptionSlider,
    QVBoxLayout,
    QWidget,
)

from music_playa.models import PlaybackMode, RepeatMode, Track
from music_playa_gui.i18n import tr, translator
from music_playa_gui.logo import scaled_logo
from music_playa_gui.theme import CYAN, SURFACE, TEXT, TEXT_MUTED
from music_playa_gui.utils import clamp, format_time
from music_playa_gui.widgets.backdrop import GRID_GLOW_BOOST, grid_pixmap
from music_playa_gui.widgets.icons import ICON_PX, Icon, make_icon, stroke_pen
from music_playa_gui.widgets.marquee_label import MarqueeLabel

PROGRESS_STEPS = 1000
PLAYER_HEIGHT = 96
# The stylesheet draws a 1 px line on top of the bar; everything else is below it.
PLAYER_BORDER = 1
# The cover is a square that fills the bar from the left edge to the bottom edge.
THUMB_SIZE = PLAYER_HEIGHT - PLAYER_BORDER
# Space kept between the edge of the window and the centre and options columns.
EDGE_MARGIN = 16
INFO_WIDTH = 280
# Previous, next, shuffle and repeat share one button size and icon size.
TRANSPORT_SIZE = 36
# The player reports its position in steps, so the slider eases toward each new
# reading instead of jumping to it. A jump larger than SNAP_SECONDS (a seek or
# a new track) is applied at once.
SMOOTH_TICK_MS = 16
SMOOTH_TAU_S = 0.12
SNAP_SECONDS = 1.5

_REPEAT_ICONS = {
    RepeatMode.OFF: Icon.REPEAT,
    RepeatMode.ALL: Icon.REPEAT,
    RepeatMode.ONE: Icon.REPEAT_ONE,
}
_REPEAT_LABEL_KEYS = {
    RepeatMode.OFF: "repeat.off",
    RepeatMode.ALL: "repeat.all",
    RepeatMode.ONE: "repeat.one",
}


def _square_fit(image: QImage, side: int) -> QImage:
    """The whole image inside a side x side square, centred.

    A cover that is not square leaves strips at the top and bottom (or at the sides), and
    they are filled with the bar's background colour, so the cover is never cropped.
    """
    fitted = image.scaled(
        side,
        side,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    square = QImage(side, side, QImage.Format.Format_ARGB32_Premultiplied)
    square.fill(QColor(SURFACE))
    painter = QPainter(square)
    painter.drawImage((side - fitted.width()) // 2, (side - fitted.height()) // 2, fitted)
    painter.end()
    return square


class ClickSlider(QSlider):
    """Horizontal slider that jumps to the clicked position and follows the mouse.

    The default QSlider only drags when the press lands exactly on its handle, so a
    click near the ends or at the top or bottom edge of the widget moved the value
    without ever emitting sliderReleased. Here a left press anywhere on the widget
    starts a drag, and the value is mapped over the range the handle can travel.
    """

    def __init__(self) -> None:
        super().__init__(Qt.Orientation.Horizontal)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _value_at(self, x: float) -> int:
        option = QStyleOptionSlider()
        self.initStyleOption(option)
        style = self.style()
        groove = style.subControlRect(
            QStyle.ComplexControl.CC_Slider, option, QStyle.SubControl.SC_SliderGroove, self
        )
        handle = style.subControlRect(
            QStyle.ComplexControl.CC_Slider, option, QStyle.SubControl.SC_SliderHandle, self
        )
        # The handle's centre travels from groove start + half a handle to groove end - half.
        span = groove.width() - handle.width()
        offset = x - groove.x() - handle.width() / 2
        return QStyle.sliderValueFromPosition(
            self.minimum(), self.maximum(), round(offset), span
        )

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.setSliderDown(True)
            self.setSliderPosition(self._value_at(event.position().x()))
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.isSliderDown():
            self.setSliderPosition(self._value_at(event.position().x()))
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.isSliderDown():
            self.setSliderDown(False)
            event.accept()
            return
        super().mouseReleaseEvent(event)


class SpeakerIcon(QWidget):
    """Clickable speaker glyph drawn with QPainter, so it does not depend on emoji fonts.

    Shows sound waves normally and a cross when muted.
    """

    SIZE = 20
    clicked = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._muted = False

    def set_muted(self, muted: bool) -> None:
        if muted != self._muted:
            self._muted = muted
            self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(TEXT_MUTED if self._muted else TEXT)
        painter.setPen(stroke_pen(color, 1.8))
        painter.setBrush(color)
        painter.drawPolygon(
            QPolygonF(
                [
                    QPointF(2, 7),
                    QPointF(6, 7),
                    QPointF(11, 3),
                    QPointF(11, 17),
                    QPointF(6, 13),
                    QPointF(2, 13),
                ]
            )
        )
        painter.setBrush(Qt.BrushStyle.NoBrush)
        if self._muted:
            painter.drawLine(QPointF(14, 7), QPointF(19, 13))
            painter.drawLine(QPointF(19, 7), QPointF(14, 13))
        else:
            # Two sound waves on the right side, centred on the cone's centre (11, 10).
            for radius in (4.5, 8.0):
                rect = QRectF(11 - radius, 10 - radius, 2 * radius, 2 * radius)
                painter.drawArc(rect, -45 * 16, 90 * 16)
        painter.end()


class PlayerBar(QWidget):
    """Bottom bar: now playing info, transport, progress, mode and volume."""

    previous_clicked = Signal()
    toggle_clicked = Signal()
    next_clicked = Signal()
    mode_clicked = Signal()
    repeat_clicked = Signal()
    stop_clicked = Signal()
    seek_requested = Signal(float)
    volume_changed = Signal(float)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("playerBar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedHeight(PLAYER_HEIGHT)
        self._duration = 0.0
        self._target_position = 0.0
        self._shown_position = 0.0
        self._smooth_timer = QTimer(self)
        self._smooth_timer.setInterval(SMOOTH_TICK_MS)
        self._smooth_timer.timeout.connect(self._ease_progress)
        self._track: Track | None = None
        self._playback_mode = PlaybackMode.IN_ORDER
        self._repeat_mode = RepeatMode.OFF
        self._grid: QPixmap | None = None
        self._grid_key: tuple | None = None
        self._grid_args: tuple | None = None  # what the grid was made from
        self._grid_glow: QPixmap | None = None  # the glowing grid, made when the bass first needs it
        self._glow = 0.0
        self._cover: QImage | None = None  # the thumbnail shows the logo when None
        self._thumb_ratio = 0.0

        layout = QHBoxLayout(self)
        # No margin on the left or top, so the cover sits in the corner. Both side columns
        # have the same fixed width, so the transport controls sit in the middle of the bar
        # (and of the window) whatever the window size.
        layout.setContentsMargins(0, PLAYER_BORDER, 0, 0)
        layout.addWidget(self._build_info())
        layout.addLayout(self._build_center(), 1)
        layout.addWidget(self._build_options_area())

        translator.language_changed.connect(self.retranslate)
        self.retranslate()
        self.set_track(None, None)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._rebuild_grid()

    def moveEvent(self, event: QMoveEvent) -> None:
        # Resizing the window moves the bar, and with it the window centre.
        super().moveEvent(event)
        self._rebuild_grid()

    def _rebuild_grid(self, update: bool = True) -> None:
        # The grid sits below the 1 px top border, which the stylesheet draws, and its
        # lines point at the centre of the window (above the bar).
        window = self.window()
        origin = self.mapTo(window, QPoint(0, 1))
        size = QSize(self.width(), max(self.height() - 1, 0))
        vanishing_x = window.width() / 2 - origin.x()
        horizon = origin.y() - window.height() / 2
        key = (size, round(vanishing_x), round(horizon), self.devicePixelRatioF())
        if key == self._grid_key:
            return
        self._grid_key = key
        self._grid_args = (size, self.devicePixelRatioF(), vanishing_x, horizon)
        self._grid = grid_pixmap(*self._grid_args)
        self._grid_glow = None
        if update:
            self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        # The stylesheet paints the background first; the grid goes over it and the
        # child widgets (transparent, apart from hover states) are drawn above.
        super().paintEvent(event)
        # The device pixel ratio can change after the first resize, so the pictures made for
        # it are checked here too: the grid and the thumbnail.
        self._rebuild_grid(update=False)
        if self._thumb_ratio != self.devicePixelRatioF():
            self._show_thumb()
        if self._grid is not None:
            painter = QPainter(self)
            painter.drawPixmap(0, 1, self._grid)
            if self._glow > 0.0:
                # The glowing grid goes over the normal one, as opaque as the bass is strong.
                painter.setOpacity(self._glow)
                painter.drawPixmap(0, 1, self._glowing_grid())
            painter.end()

    def set_glow(self, level: float) -> None:
        """Make the grid glow; level is how strongly the bass hits, 0 (not at all) to 1."""
        level = clamp(level, 0.0, 1.0)
        if level != self._glow:
            self._glow = level
            self.update()

    def _glowing_grid(self) -> QPixmap:
        # Made from the same arguments as the grid, so it has the same size and vanishing point.
        if self._grid_glow is None:
            self._grid_glow = grid_pixmap(*self._grid_args, GRID_GLOW_BOOST)
        return self._grid_glow

    def _build_info(self) -> QWidget:
        self._thumb = QLabel()
        self._thumb.setObjectName("cover")
        self._thumb.setFixedSize(THUMB_SIZE, THUMB_SIZE)
        self._title = MarqueeLabel()
        self._title.setObjectName("trackTitle")
        self._artist = MarqueeLabel()
        self._artist.setObjectName("trackArtist")

        texts = QVBoxLayout()
        texts.setSpacing(0)
        texts.addStretch()
        texts.addWidget(self._title)
        texts.addWidget(self._artist)
        texts.addStretch()

        info = QHBoxLayout()
        info.setContentsMargins(0, 0, 0, 0)
        info.setSpacing(12)
        info.addWidget(self._thumb)
        info.addLayout(texts, 1)

        # Fixed width: long titles scroll inside it instead of resizing the bar.
        container = QWidget()
        container.setObjectName("titleArea")
        container.setFixedWidth(INFO_WIDTH)
        container.setLayout(info)
        return container

    def _build_center(self) -> QVBoxLayout:
        # The mode and repeat icons and tooltips are set by retranslate.
        self._mode = self._icon_button("modeButton", self.mode_clicked)
        self._repeat = self._icon_button("modeButton", self.repeat_clicked)
        self._previous = self._icon_button("transportButton", self.previous_clicked)
        self._previous.setIcon(make_icon(Icon.PREVIOUS, TEXT_MUTED))
        self._next = self._icon_button("transportButton", self.next_clicked)
        self._next.setIcon(make_icon(Icon.NEXT, TEXT_MUTED))
        self._toggle = QPushButton("▶")
        self._toggle.setObjectName("playButton")
        self._toggle.setFixedSize(40, 40)
        self._toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle.clicked.connect(self.toggle_clicked)

        # Shuffle sits left of "previous", repeat right of "next".
        buttons = QHBoxLayout()
        buttons.setSpacing(12)
        buttons.addStretch()
        buttons.addWidget(self._mode)
        buttons.addWidget(self._previous)
        buttons.addWidget(self._toggle)
        buttons.addWidget(self._next)
        buttons.addWidget(self._repeat)
        buttons.addStretch()

        self._elapsed = QLabel("0:00")
        self._elapsed.setObjectName("muted")
        self._total = QLabel("0:00")
        self._total.setObjectName("muted")
        self._progress = ClickSlider()
        self._progress.setRange(0, PROGRESS_STEPS)
        self._progress.sliderMoved.connect(self._on_progress_moved)
        self._progress.sliderReleased.connect(self._on_progress_released)

        timeline = QHBoxLayout()
        timeline.setSpacing(8)
        timeline.addWidget(self._elapsed)
        timeline.addWidget(self._progress, 1)
        timeline.addWidget(self._total)

        center = QVBoxLayout()
        center.setContentsMargins(EDGE_MARGIN, 0, EDGE_MARGIN, 0)
        center.addLayout(buttons)
        center.addLayout(timeline)
        return center

    def _build_options(self) -> QHBoxLayout:
        # Stop sits in the options column, so the play button stays in the middle.
        self._stop = self._icon_button("transportButton", self.stop_clicked)
        self._stop.setIcon(make_icon(Icon.STOP, TEXT_MUTED))
        self._speaker = SpeakerIcon()
        self._speaker.clicked.connect(self.toggle_mute)
        self._volume = ClickSlider()
        self._volume.setRange(0, 100)
        self._volume.setValue(100)
        self._volume.setFixedWidth(110)
        self._volume.valueChanged.connect(self._on_volume_changed)
        self._last_volume = 100

        options = QHBoxLayout()
        options.setContentsMargins(0, 0, EDGE_MARGIN, 0)
        options.setSpacing(8)
        options.addStretch()
        options.addWidget(self._stop)
        options.addWidget(self._speaker)
        options.addWidget(self._volume)
        return options

    def _build_options_area(self) -> QWidget:
        # Same fixed width as the info column on the left, so the centre column is centred.
        container = QWidget()
        container.setObjectName("optionsArea")
        container.setFixedWidth(INFO_WIDTH)
        container.setLayout(self._build_options())
        return container

    @staticmethod
    def _icon_button(object_name: str, signal: Signal) -> QPushButton:
        button = QPushButton()
        button.setObjectName(object_name)
        button.setIconSize(QSize(ICON_PX, ICON_PX))
        button.setFixedSize(TRANSPORT_SIZE, TRANSPORT_SIZE)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(signal)
        return button

    @staticmethod
    def _show_toggle(button: QPushButton, icon: Icon, active: bool, tooltip: str) -> None:
        # The glyph is the same in both states; only the colour shows whether it is on.
        button.setIcon(make_icon(icon, CYAN if active else TEXT_MUTED))
        button.setToolTip(tooltip)

    def _on_progress_moved(self, value: int) -> None:
        self._elapsed.setText(format_time(self._duration * value / PROGRESS_STEPS))

    def _on_progress_released(self) -> None:
        if self._duration <= 0:
            return
        position = self._duration * self._progress.value() / PROGRESS_STEPS
        # Shown at once, so the slider neither jumps back nor eases toward the old position.
        self._target_position = self._shown_position = position
        self._smooth_timer.stop()
        self._apply_shown_position()
        self.seek_requested.emit(position)

    def set_playing(self, playing: bool) -> None:
        self._toggle.setText("⏸" if playing else "▶")

    def retranslate(self) -> None:
        self._show_track_text()
        self.set_mode(self._playback_mode)
        self.set_repeat(self._repeat_mode)
        self._stop.setToolTip(tr("player.stop"))
        self._update_speaker()

    def set_mode(self, mode: PlaybackMode) -> None:
        self._playback_mode = mode
        self._show_toggle(
            self._mode,
            Icon.SHUFFLE,
            mode is not PlaybackMode.IN_ORDER,
            tr("player.mode", mode=tr(f"mode.{mode.value}")),
        )

    def set_repeat(self, repeat: RepeatMode) -> None:
        self._repeat_mode = repeat
        self._show_toggle(
            self._repeat,
            _REPEAT_ICONS[repeat],
            repeat is not RepeatMode.OFF,
            tr("player.repeat", state=tr(_REPEAT_LABEL_KEYS[repeat])),
        )

    def set_volume(self, volume: float) -> None:
        self._volume.blockSignals(True)
        self._volume.setValue(round(volume * 100))
        self._volume.blockSignals(False)
        self._on_volume_changed(self._volume.value(), emit=False)

    def toggle_mute(self) -> None:
        """Mute sets the volume to 0; clicking again restores the last non-zero volume."""
        if self._volume.value() == 0:
            self._volume.setValue(self._last_volume)
        else:
            self._volume.setValue(0)

    def _on_volume_changed(self, value: int, emit: bool = True) -> None:
        if value > 0:
            self._last_volume = value
        if emit:
            self.volume_changed.emit(value / 100)
        self._update_speaker()

    def _update_speaker(self) -> None:
        muted = self._volume.value() == 0
        self._speaker.set_muted(muted)
        self._speaker.setToolTip(tr("volume.unmute" if muted else "volume.mute"))

    def set_track(self, track: Track | None, cover: bytes | None) -> None:
        self._track = track
        self._show_track_text()
        image = QImage()
        self._cover = image if cover is not None and image.loadFromData(cover) else None
        self._show_thumb()

    def _show_thumb(self) -> None:
        """The cover, or the logo without one, made in device pixels so it is not stretched."""
        ratio = self.devicePixelRatioF()
        self._thumb_ratio = ratio
        side = round(THUMB_SIZE * ratio)
        if self._cover is None:
            pixmap = scaled_logo(side, ratio)
        else:
            pixmap = QPixmap.fromImage(_square_fit(self._cover, side))
            pixmap.setDevicePixelRatio(ratio)
        self._thumb.setPixmap(pixmap)

    def _show_track_text(self) -> None:
        track = self._track
        self._title.setText(track.title if track is not None else tr("player.no_track"))
        self._artist.setText(track.artist if track is not None else "")

    def set_progress(self, position: float, duration: float) -> None:
        self._duration = duration
        self._total.setText(format_time(duration))
        self._target_position = position
        if self._progress.isSliderDown():
            return
        if abs(position - self._shown_position) > SNAP_SECONDS:
            self._shown_position = position
            self._smooth_timer.stop()
            self._apply_shown_position()
            return
        if not self._smooth_timer.isActive():
            self._smooth_timer.start()

    def _ease_progress(self) -> None:
        if self._progress.isSliderDown():
            return
        remaining = self._target_position - self._shown_position
        if abs(remaining) < 0.01:
            self._shown_position = self._target_position
            self._smooth_timer.stop()
        else:
            factor = 1.0 - math.exp(-SMOOTH_TICK_MS / 1000 / SMOOTH_TAU_S)
            self._shown_position += remaining * factor
        self._apply_shown_position()

    def _apply_shown_position(self) -> None:
        self._elapsed.setText(format_time(self._shown_position))
        if self._duration > 0:
            value = round(self._shown_position / self._duration * PROGRESS_STEPS)
        else:
            value = 0
        self._progress.blockSignals(True)
        self._progress.setValue(clamp(value, 0, PROGRESS_STEPS))
        self._progress.blockSignals(False)
