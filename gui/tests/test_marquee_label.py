import pytest
from PySide6.QtWidgets import QApplication

from music_playa_gui.widgets.marquee_label import GAP_PX, HOLD_TICKS, SPEED_PX, MarqueeLabel

LONG = "a title that is much too long for the label"


@pytest.fixture
def label(shown):
    def make(width: int, text: str) -> MarqueeLabel:
        widget = MarqueeLabel()
        widget.resize(width, widget.sizeHint().height())
        shown(widget)
        widget.setText(text)
        return widget

    return make


def test_short_text_does_not_scroll(label) -> None:
    assert not label(400, "short")._timer.isActive()


def test_long_text_scrolls_after_the_hold(label) -> None:
    widget = label(40, LONG)
    assert widget._timer.isActive()
    for _ in range(HOLD_TICKS):
        widget._tick()
    assert widget._offset == 0.0
    widget._tick()
    assert widget._offset == SPEED_PX


def test_scroll_wraps_and_holds_again(label) -> None:
    widget = label(40, LONG)
    widget._hold = 0
    widget._offset = widget._text_width() + GAP_PX - SPEED_PX
    widget._tick()
    assert widget._offset == 0.0
    assert widget._hold == HOLD_TICKS


def test_new_text_restarts_from_the_beginning(label) -> None:
    widget = label(40, LONG)
    widget._hold = 0
    widget._tick()
    widget.setText("short")
    assert widget._offset == 0.0
    assert not widget._timer.isActive()


def test_widening_stops_the_scroll(label) -> None:
    widget = label(40, LONG)
    widget.resize(2000, widget.height())
    QApplication.processEvents()
    assert not widget._timer.isActive()


def test_size_hint_follows_the_font() -> None:
    widget = MarqueeLabel()
    assert widget.sizeHint().height() == widget.fontMetrics().height() + 2
    assert widget.minimumSizeHint().width() == 0


def test_overflowing_text_is_painted_twice(label) -> None:
    widget = label(40, LONG)
    widget._hold = 0
    widget._offset = 10.0
    assert not widget.grab().toImage().isNull()


def test_font_change_restarts_the_scroll(label) -> None:
    widget = label(40, "fits")
    assert not widget._timer.isActive()
    font = widget.font()
    font.setPointSize(40)
    widget.setFont(font)
    QApplication.processEvents()
    assert widget._timer.isActive()


def test_resize_keeps_a_running_timer(label) -> None:
    widget = label(40, LONG)
    widget.resize(60, widget.height())
    QApplication.processEvents()
    assert widget._timer.isActive()
