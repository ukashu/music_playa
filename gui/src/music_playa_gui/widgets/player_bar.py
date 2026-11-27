import math

from PySide6.QtCore import QPoint, QPointF, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QMouseEvent,
    QMoveEvent,
    QPainter,
    QPaintEvent,
    QPen,
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
from music_playa_gui.placeholder import vinyl_pixmap
from music_playa_gui.theme import CYAN, TEXT, TEXT_MUTED
from music_playa_gui.widgets.backdrop import grid_pixmap
from music_playa_gui.widgets.icons import ICON_PX, Icon, make_icon
from music_playa_gui.widgets.marquee_label import MarqueeLabel

PROGRESS_STEPS = 1000
THUMB_SIZE = 56
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

def format_time(seconds: float) -> str:
    minutes, secs = divmod(max(0, int(seconds)), 60)
    return f"{minutes}:{secs:02d}"


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
        painter.setPen(
            QPen(color, 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        )
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
    seek_requested = Signal(float)
    volume_changed = Signal(float)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("playerBar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedHeight(96)
        self._duration = 0.0
        self._target_position = 0.0
        self._shown_position = 0.0
        self._playing = False
        self._smooth_timer = QTimer(self)
        self._smooth_timer.setInterval(SMOOTH_TICK_MS)
        self._smooth_timer.timeout.connect(self._ease_progress)
        self._track: Track | None = None
        self._playback_mode = PlaybackMode.IN_ORDER
        self._repeat_mode = RepeatMode.OFF
        self._grid: QPixmap | None = None
        self._grid_key: tuple | None = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.addWidget(self._build_info())
        layout.addLayout(self._build_center(), 2)
        layout.addLayout(self._build_options(), 1)

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

    def _rebuild_grid(self) -> None:
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
        self._grid = grid_pixmap(size, self.devicePixelRatioF(), vanishing_x, horizon)
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        # The stylesheet paints the background first; the grid goes over it and the
        # child widgets (transparent, apart from hover states) are drawn above.
        super().paintEvent(event)
        if self._grid is not None:
            painter = QPainter(self)
            painter.drawPixmap(0, 1, self._grid)
            painter.end()

    @property
    def playing(self) -> bool:
        return self._playing

    def _build_info(self) -> QWidget:
        self._thumb = QLabel()
        self._thumb.setObjectName("cover")
        self._thumb.setFixedSize(THUMB_SIZE, THUMB_SIZE)
        self._title = MarqueeLabel()
        self._title.setObjectName("trackTitle")
        self._artist = MarqueeLabel("")
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
        self._mode = QPushButton()
        self._mode.setObjectName("modeButton")
        self._mode.setIconSize(QSize(ICON_PX, ICON_PX))
        self._mode.setFixedSize(TRANSPORT_SIZE, TRANSPORT_SIZE)
        self._mode.setCursor(Qt.CursorShape.PointingHandCursor)
        self._mode.clicked.connect(self.mode_clicked)
        self.set_mode(PlaybackMode.IN_ORDER)

        self._repeat = QPushButton()
        self._repeat.setObjectName("modeButton")
        self._repeat.setIconSize(QSize(ICON_PX, ICON_PX))
        self._repeat.setFixedSize(TRANSPORT_SIZE, TRANSPORT_SIZE)
        self._repeat.setCursor(Qt.CursorShape.PointingHandCursor)
        self._repeat.clicked.connect(self.repeat_clicked)
        self.set_repeat(RepeatMode.OFF)

        self._previous = self._transport_button(Icon.PREVIOUS, self.previous_clicked)
        self._next = self._transport_button(Icon.NEXT, self.next_clicked)
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
        center.addLayout(buttons)
        center.addLayout(timeline)
        return center

    def _build_options(self) -> QHBoxLayout:
        self._speaker = SpeakerIcon()
        self._speaker.clicked.connect(self.toggle_mute)
        self._volume = ClickSlider()
        self._volume.setRange(0, 100)
        self._volume.setValue(100)
        self._volume.setFixedWidth(110)
        self._volume.valueChanged.connect(self._on_volume_changed)
        self._last_volume = 100

        options = QHBoxLayout()
        options.setSpacing(8)
        options.addStretch()
        options.addWidget(self._speaker)
        options.addWidget(self._volume)
        return options

    @staticmethod
    def _transport_button(icon: Icon, signal: Signal) -> QPushButton:
        button = QPushButton()
        button.setObjectName("transportButton")
        button.setIcon(make_icon(icon, TEXT_MUTED))
        button.setIconSize(QSize(ICON_PX, ICON_PX))
        button.setFixedSize(TRANSPORT_SIZE, TRANSPORT_SIZE)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(signal)
        return button

    def _on_progress_moved(self, value: int) -> None:
        self._elapsed.setText(format_time(self._duration * value / PROGRESS_STEPS))

    def _on_progress_released(self) -> None:
        if self._duration > 0:
            self.seek_requested.emit(self._duration * self._progress.value() / PROGRESS_STEPS)

    def set_playing(self, playing: bool) -> None:
        self._playing = playing
        self._toggle.setText("⏸" if playing else "▶")

    def retranslate(self) -> None:
        self._show_track_text()
        self._mode.setToolTip(tr("player.mode", mode=tr(f"mode.{self._playback_mode.value}")))
        self._repeat.setToolTip(
            tr("player.repeat", state=tr(_REPEAT_LABEL_KEYS[self._repeat_mode]))
        )
        self._update_speaker()

    def set_mode(self, mode: PlaybackMode) -> None:
        self._playback_mode = mode
        active = mode is not PlaybackMode.IN_ORDER
        # Same shuffle glyph in both states; only the colour shows whether it is on.
        self._mode.setIcon(make_icon(Icon.SHUFFLE, CYAN if active else TEXT_MUTED))
        self._mode.setToolTip(tr("player.mode", mode=tr(f"mode.{mode.value}")))
        self._mode.setProperty("active", active)
        self._mode.style().unpolish(self._mode)
        self._mode.style().polish(self._mode)

    def set_repeat(self, repeat: RepeatMode) -> None:
        self._repeat_mode = repeat
        active = repeat is not RepeatMode.OFF
        self._repeat.setIcon(make_icon(_REPEAT_ICONS[repeat], CYAN if active else TEXT_MUTED))
        self._repeat.setToolTip(tr("player.repeat", state=tr(_REPEAT_LABEL_KEYS[repeat])))
        self._repeat.setProperty("active", active)
        self._repeat.style().unpolish(self._repeat)
        self._repeat.style().polish(self._repeat)

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
        pixmap = QPixmap()
        if cover is None or not pixmap.loadFromData(cover):
            pixmap = vinyl_pixmap()  # no cover: show the vinyl record instead
        self._thumb.clear()
        if not pixmap.isNull():
            self._thumb.setPixmap(
                pixmap.scaled(
                    self._thumb.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

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
        self._progress.setValue(min(max(value, 0), PROGRESS_STEPS))
        self._progress.blockSignals(False)
