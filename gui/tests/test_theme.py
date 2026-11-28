import pytest
from PySide6.QtWidgets import QApplication

from music_playa_gui import theme
from music_playa_gui.theme import SYNTHWAVE_GRADIENT, _rgba, build_stylesheet


def test_rgba() -> None:
    assert _rgba("#FF2E97", 60) == "rgba(255, 46, 151, 60)"
    assert _rgba("#000000", 0) == "rgba(0, 0, 0, 0)"
    assert _rgba("#00E5FF", 255) == "rgba(0, 229, 255, 255)"


def test_gradient_stops() -> None:
    assert SYNTHWAVE_GRADIENT == (theme.CYAN, theme.VIOLET, theme.PINK)


def test_stylesheet_uses_the_palette() -> None:
    sheet = build_stylesheet()
    for colour in (theme.BACKGROUND, theme.SURFACE, theme.PINK, theme.CYAN, theme.TEXT):
        assert colour in sheet
    assert "rgba(255, 46, 151, 60)" in sheet
    assert "{" not in sheet.replace("{", "", sheet.count("}"))  # braces are balanced


def test_stylesheet_is_accepted_by_qt() -> None:
    app = QApplication.instance()
    previous = app.styleSheet()
    try:
        app.setStyleSheet(build_stylesheet())
        assert app.styleSheet() == build_stylesheet()
    finally:
        app.setStyleSheet(previous)


@pytest.mark.parametrize("name", ["PINK", "CYAN", "VIOLET", "BACKGROUND", "TEXT_MUTED"])
def test_colours_are_hex(name: str) -> None:
    value = getattr(theme, name)
    assert len(value) == 7 and value.startswith("#")
    int(value[1:], 16)
