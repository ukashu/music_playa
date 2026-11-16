# gui

PySide6 interface for music_playa. It installs `music_playa_core` in editable mode and talks only to `create_app()` from `music_playa`. It does not import `music_playa.core` or `music_playa.services`.

## Startup

`__main__.py` loads `.env` from `Path.cwd()`. A missing `MUSIC_DIR` aborts the process before the window opens. The start script does not change the working directory:

```bash
scripts/run_gui.sh
```

From this project's virtual environment:

```bash
gui/.venv/bin/python -m music_playa_gui
```

## Bridge

`bridge.py` implements `PlaybackListener` and emits Qt signals (`track_changed`, `progress_changed`). It does not add methods that are not in the protocol. `MainWindow` connects those signals to its labels.

## Widgets

- `widgets/library_view.py` lists `Library.tracks`
- `widgets/controls.py` calls play, pause, previous, and next on `Player`
- the spectrum label is a placeholder. It reports how many bands `Visualizer.bands()` returns and does not draw an FFT

## Stack

- Python 3.15
- PySide6
- python-dotenv
- `music_playa_core` is not a declared dependency. `scripts/setup.sh` installs it from `./backend` in the same `pip` call. A relative `file:` URL would resolve against the working directory, not this file.
