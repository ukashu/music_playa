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

- `widgets/sidebar.py` is the left panel: app title, track count and the `LibraryView`
- `widgets/library_view.py` is a compact list of `Library.tracks` (index, title with artist underneath, duration); clicking a row selects and plays that track, and the current track is highlighted
- `widgets/now_playing.py` fills the centre with the cover of the current track, scaled to cover the view and dimmed (a gradient when there is no cover), with `SpectrumWidget` on top. A gear button in the top right corner toggles the settings panel. The scaled cover is cached and recomputed only on cover change and resize
- `widgets/settings_panel.py` is the settings panel that slides in from the right edge of the now-playing view (about 200 ms, over the cover, nothing moves). It holds the spectrum settings and the language selector (Polski / English)
- `widgets/player_bar.py` shows the current track with a thumbnail. The title and artist sit in a fixed-width area (280 px); text that does not fit scrolls horizontally via `widgets/marquee_label.py`. The transport row has the shuffle button (the same crossed-arrows icon in both states; cyan when shuffle is on, grey when it is off) on the left of previous, play-pause and next, and the repeat button (off / repeat all / repeat one; the icon shows `↻` or `↻¹` and turns cyan when repeat is on) on the right. Both buttons cycle through their states on click. Below it is a progress slider with times (seek on release or click), and on the right a volume slider. The play/pause icon is polled from `Player.state` together with the progress, so it also changes when the player stops on its own (for example at the end of the list). The speaker icon mutes and restores the volume on click
- `widgets/spectrum.py` draws `Visualizer.bands()` as columns of segments (default 32 x 8). `SpectrumSettings` (shown in the settings panel) holds two spin boxes: Width (columns, 4 to 128) and Height (segments, 2 to 32). Out-of-range values are clamped. The widget has no background and its lit segments are translucent, so the cover shows through. Unlit segments are not drawn. The segment colour is interpolated from cyan through violet to pink by height. It is refreshed by a `QTimer` at about 30 FPS

## Placeholder artwork

When a track has no cover (or no track is selected), `placeholder.py` supplies a vinyl record instead. The source image is `assets/vinyl-record.png` (transparent PNG). It is recoloured once, on first use, with a gradient map: the brightness of each pixel is mapped to the app palette, so the black body becomes deep violet, the grey sheen cyan and the white label neon pink. The tinting uses lookup tables (`bytes.translate`), so it takes a few milliseconds and needs no extra dependencies. `NowPlayingView` draws the record centred, whole and slightly translucent on the gradient background, and `PlayerBar` uses it as the thumbnail. A real cover always takes precedence. If the asset is missing, the widgets behave as before and show nothing.

## Language and settings

- `i18n.py` holds the interface texts in Polish and English (no `QTranslator` or `.ts` files, only a dictionary). The module-level `translator` emits `language_changed`; every widget connects its `retranslate()` to it, so changing the language in the settings panel updates the whole window at once. Track data (title, artist, album) is not translated. Polish is the default language. Adding a language means adding it to `LANGUAGES` and a column of texts to the dictionary
- `settings.py` stores the language and the spectrum width and height with `QSettings("music_playa", "music_playa_gui")` (on Linux `~/.config/music_playa/music_playa_gui.conf`). Stored values are clamped to the allowed ranges when read, and `MainWindow` writes them back whenever they change

## Stack

- Python 3.15
- PySide6
- python-dotenv
- `music_playa_core` is not a declared dependency. `scripts/setup.sh` installs it from `./backend` in the same `pip` call. A relative `file:` URL would resolve against the working directory, not this file.
