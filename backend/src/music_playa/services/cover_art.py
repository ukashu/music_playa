from base64 import b64decode
from binascii import Error as Base64Error

from mutagen import File, MutagenError
from mutagen.flac import Picture

from music_playa.models import Track


class CoverArt:
    def for_track(self, track: Track) -> bytes | None:
        try:
            audio = File(track.path)
            if audio is None:
                return None

            tags = getattr(audio, "tags", None)
            if tags is None:
                return None

            pictures = getattr(audio, "pictures", None)
            if pictures:
                return pictures[0].data

            getall = getattr(tags, "getall", None)
            if getall:
                frames = getall("APIC")
                if frames:
                    return frames[0].data

            picture_blocks = tags.get("metadata_block_picture")
            if picture_blocks:
                return Picture(b64decode(picture_blocks[0], validate=True)).data
        except (MutagenError, OSError, ValueError, Base64Error):
            return None

        return None
