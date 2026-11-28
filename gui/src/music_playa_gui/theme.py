"""Synthwave colour palette and the application-wide Qt stylesheet."""

BACKGROUND = "#120B2E"
SURFACE = "#1B1140"
SURFACE_HOVER = "#241757"
BORDER = "#2E1F6B"
PINK = "#FF2E97"
CYAN = "#00E5FF"
VIOLET = "#8A4FFF"
TEXT = "#F3EBFF"
TEXT_MUTED = "#9A8FC4"
# Cyan through violet to pink, used by the spectrum and the logo.
SYNTHWAVE_GRADIENT = (CYAN, VIOLET, PINK)


def _rgba(colour: str, alpha: int) -> str:
    """A "#RRGGBB" colour as a stylesheet rgba() with the given alpha (0..255)."""
    red, green, blue = (int(colour[i : i + 2], 16) for i in (1, 3, 5))
    return f"rgba({red}, {green}, {blue}, {alpha})"


def build_stylesheet() -> str:
    return f"""
QWidget {{
    background-color: {BACKGROUND};
    color: {TEXT};
    font-size: 13px;
}}
QMainWindow {{
    background-color: {BACKGROUND};
}}
QWidget#spectrumSettings {{
    background: transparent;
}}
QLabel {{
    background: transparent;
}}
QLabel#muted {{
    color: {TEXT_MUTED};
}}
QLabel#appTitle {{
    font-size: 20px;
    font-weight: bold;
    color: {PINK};
}}
QWidget#trackTitle {{
    font-weight: bold;
    font-size: 14px;
}}
QWidget#trackArtist {{
    color: {TEXT_MUTED};
}}
QWidget#trackTitle, QWidget#trackArtist, QWidget#titleArea, QWidget#optionsArea {{
    background: transparent;
}}
QLabel#cover {{
    background-color: {SURFACE_HOVER};
    border-radius: 8px;
}}

QWidget#sidebar, QWidget#playerBar {{
    background-color: {SURFACE};
}}
QWidget#playerBar {{
    border-top: 1px solid {BORDER};
}}
QSlider {{
    background: transparent;
}}

QPushButton {{
    background-color: transparent;
    border: none;
    border-radius: 6px;
    padding: 6px 10px;
    color: {TEXT_MUTED};
}}
QPushButton:hover {{
    color: {TEXT};
}}
QPushButton#transportButton, QPushButton#modeButton {{
    padding: 0;
}}
QPushButton#playButton {{
    background-color: {PINK};
    color: {BACKGROUND};
    border-radius: 20px;
    font-size: 18px;
    font-weight: bold;
}}
QPushButton#playButton:hover {{
    background-color: #FF5CAD;
    color: {BACKGROUND};
}}

QSlider::groove:horizontal {{
    height: 4px;
    background: {BORDER};
    border-radius: 2px;
}}
QSlider::sub-page:horizontal {{
    background: {CYAN};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {TEXT};
    width: 12px;
    height: 12px;
    margin: -4px 0;
    border-radius: 6px;
}}
QSlider::handle:horizontal:hover {{
    background: {PINK};
}}

QTableWidget {{
    background-color: transparent;
    border: none;
    outline: none;
    gridline-color: transparent;
    selection-background-color: {_rgba(PINK, 60)};
    selection-color: {TEXT};
}}
QTableWidget::item {{
    padding-left: 8px;
    border: none;
}}
QTableWidget::item:selected {{
    background-color: {_rgba(PINK, 60)};
    color: {TEXT};
}}
QHeaderView::section {{
    background-color: {_rgba(SURFACE, 110)};
    color: {TEXT_MUTED};
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 6px 8px;
    text-align: left;
    font-weight: bold;
}}
QTableCornerButton::section {{
    background-color: {SURFACE};
    border: none;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 5px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {PINK};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}

QSpinBox {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 4px 6px;
}}
QSpinBox:focus {{
    border-color: {CYAN};
}}

QPushButton#gearButton {{
    background-color: {_rgba(BACKGROUND, 150)};
    color: {TEXT};
    border-radius: 20px;
    font-size: 28px;
    /* Glyph sits low in the button; the bottom padding lifts it to the centre. */
    padding: 0 0 2px 0;
}}
QPushButton#gearButton:hover {{
    background-color: {PINK};
    color: {BACKGROUND};
}}

QWidget#settingsPanel {{
    background-color: {SURFACE};
    border-left: 1px solid {BORDER};
}}
QLabel#panelTitle {{
    font-size: 20px;
    font-weight: bold;
    color: {PINK};
}}
QLabel#sectionTitle {{
    font-size: 12px;
    font-weight: bold;
    color: {CYAN};
}}
QWidget#settingsPanel QSpinBox, QWidget#settingsPanel QComboBox {{
    background-color: {BACKGROUND};
}}
QComboBox {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 10px;
}}
QComboBox:focus, QComboBox:on {{
    border-color: {CYAN};
}}
QComboBox QAbstractItemView {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    selection-background-color: {_rgba(PINK, 80)};
    selection-color: {TEXT};
    outline: none;
}}
"""
