from pathlib import Path

from music_playa.core.audio_engine import AudioEngine as ConcreteAudioEngine
from music_playa.core.library import FileLibrary
from music_playa.core.player import MemoryPlayer
from music_playa.events import EventBus
from music_playa.interfaces import Library, Player, Visualizer
from music_playa.services.visualizer import FftVisualizer

__all__ = ["Library", "Player", "Visualizer", "create_app"]


def create_app(music_dir: str | Path) -> tuple[Player, Library, Visualizer]:
    library = FileLibrary(Path(music_dir))
    engine = ConcreteAudioEngine()
    player = MemoryPlayer(library.tracks, EventBus(), engine)
    visualizer = FftVisualizer(engine)
    player.add_listener(visualizer)
    return player, library, visualizer
