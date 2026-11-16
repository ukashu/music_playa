from music_playa.models import Track


class CoverArt:
    def for_track(self, track: Track) -> bytes | None:
        """Placeholder. Cover art will come from tags or cover.jpg."""
        return None
