import re

from mutagen import MutagenError
from mutagen.id3 import (
    COMM,
    ID3,
    ID3NoHeaderError,
    TALB,
    TCOM,
    TCON,
    TDRC,
    TIT2,
    TPE1,
    TPE2,
    TPOS,
    TRCK,
)

from .bztagerror import MetadataError

_ENCODING = 3
_TRACK_RE = re.compile(r"^\d+/\d+$")

_FRAME_BY_KEY = {
    "title": TIT2,
    "artist": TPE1,
    "album": TALB,
    "album_artist": TPE2,
    "composer": TCOM,
    "track_number": TRCK,
    "disc_number": TPOS,
    "year": TDRC,
    "genre": TCON,
    "comment": COMM,
}


def read_tags(path):
    """Return a dict of tag key -> string (or None when unset) for `path`."""
    try:
        tags = ID3(path)
    except ID3NoHeaderError:
        return {key: None for key in _FRAME_BY_KEY}
    except (MutagenError, OSError) as e:
        raise MetadataError(f"cannot read {path}: {e}") from e

    values = {}
    for key, frame in _FRAME_BY_KEY.items():
        found = tags.getall(frame.__name__)
        values[key] = str(found[0]) if found else None
    return values


def apply_changes(path, changes):
    """Write `changes` onto `path`, preserving unknown and unrelated frames.

    `track_number` must arrive as an "N/T" string (Engine composes it);
    every other value is coerced with str().
    """
    _validate(changes)
    try:
        tags = ID3(path)
    except ID3NoHeaderError:
        tags = ID3()
    except (MutagenError, OSError) as e:
        raise MetadataError(f"cannot open {path}: {e}") from e

    try:
        for key, value in changes.items():
            frame = _FRAME_BY_KEY[key]
            if frame is COMM:
                tags.setall("COMM", [
                    COMM(encoding=_ENCODING, lang="eng", desc="", text=str(value))
                ])
            else:
                tags.setall(frame.__name__, [
                    frame(encoding=_ENCODING, text=str(value))
                ])
        tags.save(path)
    except (MutagenError, OSError) as e:
        raise MetadataError(f"cannot write {path}: {e}") from e


def _validate(changes):
    unknown = set(changes) - set(_FRAME_BY_KEY)
    if unknown:
        raise MetadataError(f"unknown tag keys: {sorted(unknown)}")
    track = changes.get("track_number")
    if track is not None and not _TRACK_RE.match(str(track)):
        raise MetadataError("track_number must be an N/T value")
