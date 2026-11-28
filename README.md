# music_playa

A local music player. The logic lives in the Python package `music_playa`. The TUI and the GUI import that package directly, each from its own `.venv`. There is no server process, REST API, or WebSocket.

`backend` is a library. The TUI ([Textual](https://textual.textualize.io)) and the GUI (PySide6) call the same Python interfaces. Details of the contract, the audio engine, and each interface live in the project READMEs:

- [backend/README.md](backend/README.md)
- [tui/README.md](tui/README.md)
- [gui/README.md](gui/README.md)

## Functionality list

- play music
- pause playback
- skip song
- go to previous song (one back)
- list all songs in working directory (including subdirectories)
- get song cover art
- get current song info
- get current song progress
- change playback volume
- jump to specific position in song playback (or maybe rewind buttons)
- playback modes in order and shuffle, plus repeat off / repeat all / repeat one 
- stop playback (the next play starts from the beginning)
- audio spectrum visualizer, as bars or as a wave (GUI)
- track numbers from the tags in the GUI track list

## Layout

```
music_playa/
├── README.md
├── .gitignore
├── scripts/
│   ├── setup.sh
│   ├── run_tui.sh
│   ├── run_gui.sh
│   ├── mutation_gui.sh
│   └── bake_flamingo.py
├── backend/          # core library
├── tui/              # Textual app
└── gui/              # PySide6 app
```

## Setup

Python 3.15 is required (`requires-python = ">=3.15"` in every `pyproject.toml`). The audio spectrum visualizer also needs the `ffmpeg` binary in `PATH` (without it playback works and the spectrum stays empty). From the repository root:

```bash
scripts/setup.sh
```

That creates three virtual environments and installs each project in editable mode. The same steps by hand:

```bash
python3.15 -m venv backend/.venv
backend/.venv/bin/pip install -e "./backend[dev]"

python3.15 -m venv tui/.venv
tui/.venv/bin/pip install -e ./backend -e ./tui

python3.15 -m venv gui/.venv
gui/.venv/bin/pip install -e ./backend -e "./gui[dev]"
```

## Run

The start scripts do not change the process working directory. The app reads `.env` from the directory it was launched from (`Path.cwd()`), not from the repository directory.

```bash
scripts/run_tui.sh
scripts/run_gui.sh
```

## Scanner working directory

The library path comes from the `MUSIC_DIR` variable in a `.env` file located in the directory the app is launched from. The scan covers that directory and its subdirectories. A missing file or a missing variable aborts startup. There is no CLI argument and no silent fallback to `cwd`.

Example, when the script is started from `~/Muzyka`:

```bash
# ~/Muzyka/.env
MUSIC_DIR=/home/lexxar/Muzyka
```

`.env` is listed in `.gitignore`. The same variable applies to both the TUI and the GUI, because both call `Library` with the same directory.

Core tests, using the backend `.venv`:

```bash
backend/.venv/bin/pytest
```

GUI tests and mutation testing, using the GUI `.venv` (details in `gui/README.md`):

```bash
cd gui && .venv/bin/pytest
scripts/mutation_gui.sh
```
