from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, Qt, Signal
from PySide6.QtWidgets import QCheckBox, QComboBox, QLabel, QVBoxLayout, QWidget

from music_playa_gui.cover_style import COVER_STYLE_LABEL_KEYS, COVER_STYLES, DEFAULT_COVER_STYLE
from music_playa_gui.i18n import LANGUAGES, tr, translator
from music_playa_gui.widgets.spectrum import SpectrumSettings, SpectrumWidget

PANEL_WIDTH = 300
SLIDE_MS = 200


class SettingsPanel(QWidget):
    """Panel that slides in from the right edge of its parent widget."""

    language_selected = Signal(str)
    cover_style_selected = Signal(str)
    bass_glow_toggled = Signal(bool)

    def __init__(
        self,
        spectrum: SpectrumWidget,
        parent: QWidget,
        cover_style: str = DEFAULT_COVER_STYLE,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("settingsPanel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedWidth(PANEL_WIDTH)
        self._open = False

        self._title = QLabel()
        self._title.setObjectName("panelTitle")
        self._spectrum_heading = QLabel()
        self._spectrum_heading.setObjectName("sectionTitle")
        self.spectrum_settings = SpectrumSettings(spectrum)
        self._cover_heading = QLabel()
        self._cover_heading.setObjectName("sectionTitle")
        self.cover_box = QComboBox()
        for style in COVER_STYLES:
            self.cover_box.addItem("", style)
        self.cover_box.setCurrentIndex(max(self.cover_box.findData(cover_style), 0))
        self.cover_box.currentIndexChanged.connect(self._on_cover_style_chosen)
        self._effects_heading = QLabel()
        self._effects_heading.setObjectName("sectionTitle")
        self.bass_glow_box = QCheckBox()
        self.bass_glow_box.setChecked(spectrum.bass_glow)
        self.bass_glow_box.toggled.connect(self.bass_glow_toggled)
        self._language_heading = QLabel()
        self._language_heading.setObjectName("sectionTitle")
        self.language_box = QComboBox()
        for code, name in LANGUAGES.items():
            self.language_box.addItem(name, code)
        self.language_box.currentIndexChanged.connect(self._on_language_chosen)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 24, 20, 20)
        layout.setSpacing(10)
        layout.addWidget(self._title)
        layout.addSpacing(16)
        layout.addWidget(self._spectrum_heading)
        layout.addWidget(self.spectrum_settings)
        layout.addSpacing(16)
        layout.addWidget(self._cover_heading)
        layout.addWidget(self.cover_box)
        layout.addSpacing(16)
        layout.addWidget(self._effects_heading)
        layout.addWidget(self.bass_glow_box)
        layout.addSpacing(16)
        layout.addWidget(self._language_heading)
        layout.addWidget(self.language_box)
        layout.addStretch()

        self._animation = QPropertyAnimation(self, b"pos", self)
        self._animation.setDuration(SLIDE_MS)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.finished.connect(self._on_slide_finished)

        translator.language_changed.connect(self.retranslate)
        self.retranslate()
        self.hide()

    def toggle(self) -> None:
        if self._open:
            self.close_panel()
        else:
            self.open_panel()

    def open_panel(self) -> None:
        parent = self.parentWidget()
        self._open = True
        if not self.isVisible():
            self.setGeometry(parent.width(), 0, PANEL_WIDTH, parent.height())
            self.show()
        self.raise_()
        self._slide_to(parent.width() - PANEL_WIDTH)

    def close_panel(self) -> None:
        self._open = False
        self._slide_to(self.parentWidget().width())

    def place(self) -> None:
        """Re-fit to the parent after it was resized."""
        parent = self.parentWidget()
        x = parent.width() - PANEL_WIDTH if self._open else parent.width()
        self.setGeometry(x, 0, PANEL_WIDTH, parent.height())

    def retranslate(self) -> None:
        self._title.setText(tr("settings.title"))
        self._spectrum_heading.setText(tr("settings.spectrum"))
        self._cover_heading.setText(tr("settings.cover"))
        for position, style in enumerate(COVER_STYLES):
            self.cover_box.setItemText(position, tr(COVER_STYLE_LABEL_KEYS[style]))
        self._effects_heading.setText(tr("settings.effects"))
        self.bass_glow_box.setText(tr("settings.bass_glow"))
        self._language_heading.setText(tr("settings.language"))
        index = self.language_box.findData(translator.language)
        if index >= 0 and index != self.language_box.currentIndex():
            self.language_box.blockSignals(True)
            self.language_box.setCurrentIndex(index)
            self.language_box.blockSignals(False)

    def _slide_to(self, x: int) -> None:
        self._animation.stop()
        self._animation.setStartValue(self.pos())
        self._animation.setEndValue(QPoint(x, 0))
        self._animation.start()

    def _on_slide_finished(self) -> None:
        if not self._open:
            self.hide()

    def _on_cover_style_chosen(self, index: int) -> None:
        style = self.cover_box.itemData(index)
        if style is not None:
            self.cover_style_selected.emit(style)

    def _on_language_chosen(self, index: int) -> None:
        code = self.language_box.itemData(index)
        if code is not None:
            self.language_selected.emit(code)
