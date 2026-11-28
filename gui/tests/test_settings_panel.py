import pytest
from conftest import FakeVisualizer
from PySide6.QtWidgets import QWidget

from music_playa_gui.i18n import translator
from music_playa_gui.widgets.settings_panel import PANEL_WIDTH, SLIDE_MS, SettingsPanel
from music_playa_gui.widgets.spectrum import SpectrumWidget


@pytest.fixture
def parent(shown) -> QWidget:
    widget = QWidget()
    widget.resize(800, 600)
    widget.panel = SettingsPanel(SpectrumWidget(FakeVisualizer()), widget)
    shown(widget)
    return widget


@pytest.fixture
def panel(parent) -> SettingsPanel:
    return parent.panel


def _finish(panel: SettingsPanel) -> None:
    panel._animation.setCurrentTime(SLIDE_MS)


def test_starts_hidden(panel: SettingsPanel) -> None:
    assert not panel.isVisible()
    assert not panel._open


def test_open_slides_in_from_the_right(panel: SettingsPanel) -> None:
    panel.toggle()
    assert panel.isVisible()
    assert panel.x() >= 800 - PANEL_WIDTH
    _finish(panel)
    assert panel.geometry().getRect() == (800 - PANEL_WIDTH, 0, PANEL_WIDTH, 600)


def test_close_hides_after_the_slide(panel: SettingsPanel) -> None:
    panel.open_panel()
    _finish(panel)
    panel.toggle()
    assert panel.isVisible()
    _finish(panel)
    assert not panel.isVisible()
    assert panel.x() == 800


def test_place_follows_the_parent(parent: QWidget, panel: SettingsPanel) -> None:
    panel.open_panel()
    _finish(panel)
    parent.resize(1000, 500)
    panel.place()
    assert panel.geometry().getRect() == (1000 - PANEL_WIDTH, 0, PANEL_WIDTH, 500)
    panel.close_panel()
    _finish(panel)
    panel.place()
    assert panel.x() == 1000


def test_language_choice_emits(panel: SettingsPanel) -> None:
    chosen = []
    panel.language_selected.connect(chosen.append)
    panel.language_box.setCurrentIndex(panel.language_box.findData("en"))
    assert chosen == ["en"]


def test_language_change_elsewhere_updates_the_box_quietly(panel: SettingsPanel) -> None:
    chosen = []
    panel.language_selected.connect(chosen.append)
    translator.set_language("en")
    assert panel.language_box.currentData() == "en"
    assert panel._title.text() == "Settings"
    assert chosen == []


def test_open_twice_does_not_jump_back(panel: SettingsPanel) -> None:
    panel.open_panel()
    _finish(panel)
    panel.open_panel()
    assert panel.x() >= 800 - PANEL_WIDTH
    assert panel.isVisible()


def test_unknown_language_in_the_box_is_ignored(panel: SettingsPanel) -> None:
    chosen = []
    panel.language_selected.connect(chosen.append)
    panel._on_language_chosen(-1)
    assert chosen == []
