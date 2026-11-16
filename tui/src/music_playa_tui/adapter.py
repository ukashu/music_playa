from __future__ import annotations

import threading
from collections.abc import Callable
from typing import TYPE_CHECKING

from music_playa.models import Track

if TYPE_CHECKING:
    from music_playa_tui.app import MusicApp


class TextualAdapter:
    """PlaybackListener that forwards callbacks onto the Textual thread.

    call_from_thread waits until the app thread runs the callback. Invoking it
    from that same thread deadlocks, so a callback that already arrives there
    updates the widgets directly.
    """

    def __init__(self, app: MusicApp) -> None:
        self._app = app

    def on_progress(self, position: float, duration: float) -> None:
        self._invoke(self._app.show_progress, position, duration)

    def on_track(self, track: Track | None) -> None:
        self._invoke(self._app.show_track, track)

    def _invoke(self, callback: Callable[..., None], *args: object) -> None:
        if threading.current_thread() is threading.main_thread():
            callback(*args)
            return
        self._app.call_from_thread(callback, *args)
