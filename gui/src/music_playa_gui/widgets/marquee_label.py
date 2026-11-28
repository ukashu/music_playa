from PySide6.QtCore import QEvent, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QPainter, QPalette, QResizeEvent
from PySide6.QtWidgets import QSizePolicy, QWidget

TICK_MS = 30
SPEED_PX = 1
GAP_PX = 48
HOLD_TICKS = 60  # pause at the start of each cycle, about 1.8 s


class MarqueeLabel(QWidget):
    """One line of text that scrolls horizontally when it does not fit the width."""

    def __init__(self) -> None:
        super().__init__()
        self._text = ""
        self._offset = 0.0
        self._hold = HOLD_TICKS
        self._timer = QTimer(self)
        self._timer.setInterval(TICK_MS)
        self._timer.timeout.connect(self._tick)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def setText(self, text: str) -> None:
        self._text = text
        self._reset()

    def sizeHint(self) -> QSize:
        return QSize(0, self.fontMetrics().height() + 2)

    def minimumSizeHint(self) -> QSize:
        return QSize(0, self.fontMetrics().height() + 2)

    def _text_width(self) -> int:
        return self.fontMetrics().horizontalAdvance(self._text)

    def _overflows(self) -> bool:
        return self._text_width() > self.width()

    def _reset(self) -> None:
        self._offset = 0.0
        self._hold = HOLD_TICKS
        if self._overflows():
            if not self._timer.isActive():
                self._timer.start()
        else:
            self._timer.stop()
        self.update()

    def _tick(self) -> None:
        if self._hold > 0:
            self._hold -= 1
            return
        self._offset += SPEED_PX
        if self._offset >= self._text_width() + GAP_PX:
            self._offset = 0.0
            self._hold = HOLD_TICKS
        self.update()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._reset()

    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.Type.FontChange:
            self._reset()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setPen(self.palette().color(QPalette.ColorRole.WindowText))
        painter.setFont(self.font())
        flags = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        width = self._text_width() + 1
        if not self._overflows():
            painter.drawText(QRectF(0, 0, self.width(), self.height()), flags, self._text)
        else:
            cycle = self._text_width() + GAP_PX
            # Two copies one cycle apart make the loop seamless.
            for start in (-self._offset, cycle - self._offset):
                painter.drawText(QRectF(start, 0, width, self.height()), flags, self._text)
        painter.end()
