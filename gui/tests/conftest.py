import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

import pytest
from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QSettings
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication, QWidget

from music_playa.core.player import MemoryPlayer
from music_playa.events import EventBus
from music_playa.models import Track
from music_playa_gui.i18n import DEFAULT_LANGUAGE, translator


class FakeEngine:
    """Audio engine without audio: it only keeps the state MemoryPlayer asks for."""

    def __init__(self, duration: float = 180.0) -> None:
        self.position = 0.0
        self.duration = 0.0
        self.is_playing = False
        self.volume = 1.0
        self._length = duration

    def set_track_ended_callback(self, callback) -> None:
        self.on_ended = callback

    def load(self, path: Path) -> float:
        self.position = 0.0
        self.duration = self._length
        return self.duration

    def play(self) -> None:
        self.is_playing = True

    def pause(self) -> None:
        self.is_playing = False

    def stop(self) -> None:
        self.is_playing = False
        self.position = 0.0

    def seek(self, position: float) -> None:
        self.position = min(max(position, 0.0), self.duration)

    def set_volume(self, volume: float) -> None:
        self.volume = volume


class FakeLibrary:
    def __init__(self, tracks: list[Track], covers: dict[Path, bytes] | None = None) -> None:
        self.tracks = tracks
        self._covers = covers or {}

    def cover(self, track: Track) -> bytes | None:
        assert track is not None, "the GUI must not ask for the cover of no track"
        return self._covers.get(track.path)


class FakeVisualizer:
    def __init__(self, bands: list[float] | None = None) -> None:
        self.levels = bands if bands is not None else [0.0] * 64

    def bands(self) -> list[float]:
        return self.levels

    def wave(self) -> list[float]:
        return []


def make_tracks(count: int) -> list[Track]:
    return [
        Track(Path(f"/music/{index}.mp3"), f"Song {index}", "Artist", "Album", 61.0 * (index + 1), str(index + 1))
        for index in range(count)
    ]


def png_bytes(width: int, height: int, colour: str = "#00ff00") -> bytes:
    image = QImage(width, height, QImage.Format.Format_ARGB32)
    image.fill(QColor(colour))
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    return bytes(data.data())


def make_player(tracks: list[Track]) -> MemoryPlayer:
    return MemoryPlayer(tracks, EventBus(), FakeEngine())


@pytest.fixture(scope="session", autouse=True)
def qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture
def shown():
    """Shows widgets and closes them after the test, also when it fails.

    A widget left open after a failure keeps receiving events in later tests, which can crash Qt.
    """
    widgets: list[QWidget] = []

    def show(widget: QWidget) -> None:
        widgets.append(widget)
        widget.show()
        QApplication.processEvents()

    yield show
    for widget in widgets:
        widget.close()
    QApplication.processEvents()


@pytest.fixture(autouse=True)
def fail_on_qt_handler_errors(monkeypatch):
    """Fails the test when a Qt event handler (paintEvent, resizeEvent...) raised.

    PySide only prints such exceptions, so the test would pass, and the broken state can crash
    a later test instead.
    """
    errors: list[BaseException] = []
    monkeypatch.setattr(sys, "excepthook", lambda kind, error, trace: errors.append(error))
    yield
    if errors:
        pytest.fail(f"exception in a Qt event handler: {errors[0]!r}")


@pytest.fixture(autouse=True)
def isolated_state(tmp_path: Path):
    """Settings go to a temporary folder and every test starts in the default language."""
    for settings_format in (QSettings.Format.NativeFormat, QSettings.Format.IniFormat):
        QSettings.setPath(settings_format, QSettings.Scope.UserScope, str(tmp_path))
    translator.set_language(DEFAULT_LANGUAGE)
    yield
    translator.set_language(DEFAULT_LANGUAGE)
