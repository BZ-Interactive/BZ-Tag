from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TagData:
    title: str = ""
    artist: str = ""
    album: str = ""
    album_artist: str = ""
    year: str = ""
    genre: str = ""
    track: str = ""
    track_total: str = ""
    disc: str = ""
    disc_total: str = ""
    comment: str = ""
    cover_data: bytes | None = None
    cover_mime: str | None = None

    def common(self, other: TagData) -> TagData:
        """Return a TagData with values that are the same between self and other.
        Empty string means the values differ."""
        def pick(a: str, b: str) -> str:
            return a if a == b else ""

        return TagData(
            title=pick(self.title, other.title),
            artist=pick(self.artist, other.artist),
            album=pick(self.album, other.album),
            album_artist=pick(self.album_artist, other.album_artist),
            year=pick(self.year, other.year),
            genre=pick(self.genre, other.genre),
            track=pick(self.track, other.track),
            track_total=pick(self.track_total, other.track_total),
            disc=pick(self.disc, other.disc),
            disc_total=pick(self.disc_total, other.disc_total),
            comment=pick(self.comment, other.comment),
            cover_data=self.cover_data if self.cover_data == other.cover_data else None,
            cover_mime=self.cover_mime if self.cover_mime == other.cover_mime else None,
        )

    def is_empty(self) -> bool:
        return all(
            getattr(self, f) in ("", None)
            for f in self.__dataclass_fields__
            if f != "cover_data" and f != "cover_mime"
        )


@dataclass
class SongFile:
    path: Path
    tags: TagData = field(default_factory=TagData)

    @property
    def filename(self) -> str:
        return self.path.name

    @property
    def stem(self) -> str:
        return self.path.stem
