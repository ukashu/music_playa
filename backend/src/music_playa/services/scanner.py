from pathlib import Path

AUDIO_EXTENSIONS = {".wav", ".ogg", ".mp3", ".flac"}


def scan(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    files = [
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS
    ]
    return sorted(files)
