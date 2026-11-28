import locale
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from PySide6.QtWidgets import QApplication

from music_playa import create_app
from music_playa_gui.app_icon import app_icon
from music_playa_gui.main_window import MainWindow
from music_playa_gui.theme import build_stylesheet


def main() -> None:
    load_dotenv(Path.cwd() / ".env")
    music_dir = os.environ.get("MUSIC_DIR")
    if not music_dir:
        print(
            "MUSIC_DIR is missing. Add it to .env in the directory you launched the app from.",
            file=sys.stderr,
        )
        raise SystemExit(1)
    player, library, visualizer = create_app(music_dir)
    app = QApplication(sys.argv)
    app.setStyleSheet(build_stylesheet())
    app.setWindowIcon(app_icon())
    # QApplication switches LC_NUMERIC to the user's locale (e.g. pl_PL), which
    # libmpv does not support and which makes seek commands fail. Restore "C".
    locale.setlocale(locale.LC_NUMERIC, "C")
    window = MainWindow(player, library, visualizer)
    window.resize(1100, 700)
    window.show()
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()
