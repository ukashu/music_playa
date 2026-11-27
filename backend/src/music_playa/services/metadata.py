from pathlib import Path

from mutagen import File


def read(path: Path) -> dict[str, str | float]:
    try:
        tags = File(path, easy=True)
    except Exception:
        return {}

    if tags is None:
        return {}

    return {
        "title": _first(tags, "title") or path.stem,
        "artist": _first(tags, "artist") or "Unknown Artist",
        "album": _first(tags, "album") or "Unknown Album",
        "track_number": _first(tags, "tracknumber") or "",
        "duration": float(tags.info.length) if getattr(tags, "info", None) else 0.0
    }

def _first(tags: object, key: str) -> str:
    # mutagen's easy tags are a mapping (tags["artist"]), not attributes.
    getter = getattr(tags, "get", None)
    values = getter(key) if getter is not None else getattr(tags, key, None)
    if values:
        return str(values[0])
    return ""
