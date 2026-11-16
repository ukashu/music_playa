import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from music_playa import create_app
from music_playa_tui.app import MusicApp


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
    MusicApp(player, library, visualizer).run()


if __name__ == "__main__":
    main()
