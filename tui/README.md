# tui

Textual interface for music_playa. It installs `music_playa_core` in editable mode and talks only to `create_app()` from `music_playa`. It does not import `music_playa.core` or `music_playa.services`.

## Startup

`__main__.py` loads `.env` from `Path.cwd()`. A missing `MUSIC_DIR` aborts the process. The start script does not change the working directory:

```bash
scripts/run_tui.sh
```

From this project's virtual environment:

```bash
tui/.venv/bin/python -m music_playa_tui
```

## Adapter

`adapter.py` implements `PlaybackListener`. When a callback arrives off the Textual thread it uses `call_from_thread`. A callback that is already on that thread updates the widgets directly, because `call_from_thread` waits for the app thread and would deadlock inside a button handler.

## Widgets

- `widgets/library_list.py` lists `Library.tracks`
- `widgets/now_playing.py` shows `Player.current` and the progress callback
- `widgets/spectrum.py` draws `Visualizer.bands()` as coloured block rows (green to orange), refreshed every 50 ms with `set_interval`. Each column is 2 characters wide. `SpectrumSettings` has two integer inputs: Width (maximum columns, 4 to 128, default 32) and Height (rows, 2 to 24, default 8). Out-of-range values are clamped, and Enter in a field shows the value actually applied. The number of columns drawn is also limited by the terminal width (`width // 2`), so a narrow terminal shows fewer bars than the Width input.
- Tests: `tui/.venv/bin/python -m pytest tui/tests` (needs `pytest` in the TUI venv)
- Play, pause, previous, and next call `Player`

Styles live in `app.tcss`.

## Stack

- Python 3.15
- Textual
- python-dotenv
- `music_playa_core` is not a declared dependency. `scripts/setup.sh` installs it from `./backend` in the same `pip` call. A relative `file:` URL would resolve against the working directory, not this file.
