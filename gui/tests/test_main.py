import pytest
from PySide6.QtWidgets import QApplication

from music_playa_gui import __main__ as entry


def test_missing_music_dir_aborts(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("MUSIC_DIR", raising=False)
    monkeypatch.setattr(entry, "create_app", lambda directory: pytest.fail("must not start"))
    with pytest.raises(SystemExit) as exit_info:
        entry.main()
    assert exit_info.value.code == 1
    assert "MUSIC_DIR" in capsys.readouterr().err


def test_env_file_is_read_from_the_working_directory(monkeypatch, tmp_path) -> None:
    from conftest import FakeLibrary, FakeVisualizer, make_player, make_tracks

    (tmp_path / ".env").write_text(f"MUSIC_DIR={tmp_path}\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("MUSIC_DIR", raising=False)
    tracks = make_tracks(2)
    created = []

    def create_app(directory):
        created.append(directory)
        return make_player(tracks), FakeLibrary(tracks), FakeVisualizer()

    shown = []
    monkeypatch.setattr(entry, "create_app", create_app)
    monkeypatch.setattr(entry.MainWindow, "show", lambda window: shown.append(window.size()))
    real_app = QApplication.instance()

    class AppDouble:
        """The test session already has a QApplication; this one only supplies exec()."""

        def __init__(self, argv) -> None:
            pass

        def setStyleSheet(self, sheet: str) -> None:
            real_app.setStyleSheet(sheet)

        def exec(self) -> int:
            return 7

    monkeypatch.setattr(entry, "QApplication", AppDouble)
    with pytest.raises(SystemExit) as exit_info:
        entry.main()
    real_app.setStyleSheet("")
    assert exit_info.value.code == 7
    assert created == [str(tmp_path)]
    assert (shown[0].width(), shown[0].height()) == (1100, 700)
