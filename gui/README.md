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

The player only emits `on_progress` after actions (play, pause, seek, next, ...), not while a track is playing. To keep the progress bar and the elapsed time live, `MainWindow` also polls `Player.position` and `Player.duration` with a `QTimer` every 100 ms (`PROGRESS_INTERVAL_MS`). The slider eases toward each new reading (`SMOOTH_TAU_S`, about 0.12 s) so it does not jump between polls; a change larger than 1.5 s, such as a seek or a new track, is applied at once. While the user drags the slider, neither the poll nor the easing moves it.

## Widgets

The window follows a Spotify-like layout: the list of all tracks on the left, a now-playing view in the centre (dimmed cover art with the spectrum drawn on top) and a player bar at the bottom. Colours and the application stylesheet live in `theme.py` (synthwave palette: navy/violet background, neon pink and cyan accents). `__main__.py` applies it with `app.setStyleSheet(...)`.

- `widgets/sidebar.py` is the left panel: app title, track count and the `LibraryView`. The list takes the full width of the panel, so the selection and the header reach both edges; only the title and the count keep a 12 px inset. The title is preceded by the app logo (`assets/logo_white.png`), tinted with the synthwave gradient (cyan, violet, pink). It draws a neon flamingo over the whole panel height (`widgets/flamingo.py`). The picture, `assets/flamingo.png`, is baked once by `scripts/bake_flamingo.py` from `assets/flamingo.jpg`: cropped to the bird, flipped to face right, with the navy background removed, monochrome (white lines on a transparent background) and with a soft glow. The app only loads it, scales it (`imaging.scaled_smooth`) and tints it with the theme pink; none of the image processing runs at startup. The bird is drawn at a fixed size and place: its head sits 253 px below the top of the panel and it is 681 px tall, anchored to the top-right corner with a 20 px margin from the right edge, so the legs are cut off when the window is short. The whole bird is drawn at 60% opacity so it sits darker behind the track text, and the scaled bird is cached, so resizing the window does not redo it. Like the logo and the player bar grid, it is built at paint time for the window's current device pixel ratio, because that ratio can still be 1 at the first resize and change a moment later, when the screen reports its real scale; building it only at resize left the picture stretched and jagged until the window was resized. The list background is transparent, so the bird shows through behind the track list
- `widgets/library_view.py` is a compact list of `Library.tracks` (index, title with artist underneath, duration); clicking a row selects and plays that track, and the current track is highlighted
- `widgets/now_playing.py` fills the centre with the cover of the current track, scaled to cover the view and dimmed (a gradient when there is no cover), with `SpectrumWidget` on top. A gear button in the top right corner toggles the settings panel. The scaled cover is cached and recomputed only on cover change, resize and a change of the device pixel ratio; it is scaled in device pixels, so it stays sharp on scaled screens.
- `widgets/backdrop.py` paints a cached, transparent decoration: `grid_pixmap` makes a perspective grid whose lines point at a vanishing point, which the player bar puts at the centre of the window. They are rebuilt only on resize (the bar also on move), and the constants at the top of the file (spacing, colours, opacity) tune the look
- `widgets/settings_panel.py` is the settings panel that slides in from the right edge of the now-playing view (about 200 ms, over the cover, nothing moves). It holds the spectrum settings and the language selector (Polski / English)
- `widgets/player_bar.py` shows the current track with a thumbnail (the cover, or the logo without one), made in device pixels and rebuilt when the device pixel ratio changes. The title and artist sit in a fixed-width area (280 px); text that does not fit scrolls horizontally via `widgets/marquee_label.py`. The left and right columns have the same fixed width (280 px), so the transport row, with the play button, stays centred on the bar whatever the window width. The transport row has the shuffle button (the same crossed-arrows icon in both states; cyan when shuffle is on, grey when it is off) on the left of previous, play-pause and next, and the repeat button (off / repeat all / repeat one; the icon shows `↻` or `↻¹` and turns cyan when repeat is on) on the right. Both buttons cycle through their states on click. Below it is a progress slider with times (seek on release or click; the slider stays at the chosen position instead of easing back from the old one), and on the right a volume slider. The play/pause icon is polled from `Player.state` together with the progress, so it also changes when the player stops on its own (for example at the end of the list). The speaker icon mutes and restores the volume on click
- `widgets/spectrum.py` draws `Visualizer.bands()` as columns of segments (default 32 x 8). `SpectrumSettings` (shown in the settings panel) holds two spin boxes: Width (columns, 4 to 128) and Height (segments, 2 to 32). Out-of-range values are clamped. The widget has no background and its lit segments are translucent, so the cover shows through. Unlit segments are not drawn. The segment colour is interpolated from cyan through violet to pink by height. It is refreshed by a `QTimer` at about 30 FPS

## Placeholder artwork

When a track has no cover (or no track is selected), the app logo is shown instead. `logo.py` loads `assets/logo_white.png` (a white logo on a transparent background) and colours it with `imaging.tinted`, which takes a colour or a brush (here a gradient of `theme.SYNTHWAVE_GRADIENT`: cyan, violet, pink, from top left to bottom right) and keeps it only where the logo is opaque, so the background stays transparent. The flamingo uses the same function with the theme pink. The result is computed once, on first use. The logo's edges are softened by a pixel or two, and it is shrunk in halving steps before the final smooth scale (`scaled_logo`), so its edges stay smooth at small sizes. It is prepared in device pixels (scaled by the widget's device pixel ratio), so it is not stretched on scaled screens. `NowPlayingView` draws the logo centred, whole and slightly translucent on the gradient background, `PlayerBar` uses it as the thumbnail, and `Sidebar` shows it in front of the title. A real cover always takes precedence. If the asset is missing, the widgets show nothing.

## Language and settings

- `i18n.py` holds the interface texts in Polish and English (no `QTranslator` or `.ts` files, only a dictionary). The module-level `translator` emits `language_changed`; every widget connects its `retranslate()` to it, so changing the language in the settings panel updates the whole window at once. Track data (title, artist, album) is not translated. Polish is the default language. Adding a language means adding it to `LANGUAGES` and a column of texts to the dictionary
- `settings.py` stores the language and the spectrum width and height with `QSettings("music_playa", "music_playa_gui")` (on Linux `~/.config/music_playa/music_playa_gui.conf`). Stored values are clamped to the allowed ranges when read, and `MainWindow` writes them back whenever they change

## Helpers

- `utils.py`: `format_time` (seconds as `m:ss`, used by the player bar and the track list) and `clamp`
- `imaging.py`: `scaled_smooth` (shrinking in halving steps, also used by `scripts/bake_flamingo.py`) and `tinted`
- `theme.py`: the palette, `SYNTHWAVE_GRADIENT` (shared by the spectrum and the logo) and the stylesheet

## Tests

The tests use pytest without plugins and run offscreen (`QT_QPA_PLATFORM=offscreen`, set in `tests/conftest.py`), so they need no display. `conftest.py` creates one `QApplication` for the session, redirects `QSettings` to a temporary folder for every test, resets the language and provides fakes: `MemoryPlayer` from the core with an engine that plays nothing, a library and a visualizer. A test fails if a Qt event handler (for example `paintEvent`) raised, because PySide only prints such errors. Screens with a scaled device pixel ratio are simulated by replacing `devicePixelRatioF` on the widget.

```bash
cd gui && .venv/bin/pytest
```

Coverage comes from `pytest-cov` (the `[dev]` extra). Line and branch coverage of the `music_playa_gui` package is configured in `[tool.coverage.*]` in `pyproject.toml`, and the report fails below 95%. It is not enabled by default, so plain `pytest` and the mutation run stay fast:

```bash
cd gui && .venv/bin/pytest --cov --cov-report=term-missing
cd gui && .venv/bin/pytest --cov --cov-report=html   # report in gui/htmlcov/index.html
```

The current total is 99%. What is left are a few branches that only exit a function (`->exit`) and the `super()` call in `ClickSlider.mouseMoveEvent` for a move without a pressed button.

## Mutation testing

`scripts/mutation_gui.sh` runs [mutmut](https://github.com/boxed/mutmut) (mutatest does not support Python 3.15) and prints the surviving mutants. The configuration is in `[tool.mutmut]` in `pyproject.toml`. Only the modules with logic are mutated (`utils.py`, `i18n.py`, `settings.py`, `widgets/spectrum.py`, `widgets/backdrop.py`, `main_window.py`), because mutants of drawing code are mostly equivalent. Workers are started from a fork server (`process_isolation = "forkserver"`): forked straight from the main process they inherit its `QApplication`, and then hang or report wrong results. Mutants are written to `gui/mutants/`, which is ignored by git.

```bash
scripts/mutation_gui.sh
gui/.venv/bin/mutmut show <mutant name>   # from gui/, the diff of one mutant
```

## Stack

- Python 3.15
- PySide6
- python-dotenv
- pytest and mutmut: `[dev]` extra
- `music_playa_core` is not a declared dependency. `scripts/setup.sh` installs it from `./backend` in the same `pip` call. A relative `file:` URL would resolve against the working directory, not this file.
