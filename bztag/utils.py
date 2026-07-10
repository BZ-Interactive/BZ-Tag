from __future__ import annotations

import re
from pathlib import Path

from mutagen.id3 import (
    ID3,
    ID3NoHeaderError,
    TIT2,
    TPE1,
    TALB,
    TPE2,
    TDRC,
    TCON,
    TRCK,
    TPOS,
    COMM,
    APIC,
)
from mutagen.mp3 import MP3

from bztag.models import SongFile, TagData


def read_tags(path: Path) -> SongFile:
    """Read ID3 tags from an MP3 file."""
    tags = TagData()
    try:
        audio = ID3(path)
    except ID3NoHeaderError:
        return SongFile(path=path, tags=tags)

    def get(frame_id: str) -> str:
        frame = audio.get(frame_id)
        if frame:
            return str(frame.text[0]) if hasattr(frame, "text") else str(frame)
        return ""

    tags.title = get("TIT2")
    tags.artist = get("TPE1")
    tags.album = get("TALB")
    tags.album_artist = get("TPE2")
    tags.year = get("TDRC")
    tags.genre = get("TCON")
    tags.comment = get("COMM::'XXX'")

    trck = get("TRCK")
    if "/" in trck:
        parts = trck.split("/")
        tags.track = parts[0].strip()
        tags.track_total = parts[1].strip()
    else:
        tags.track = trck.strip()

    tpos = get("TPOS")
    if "/" in tpos:
        parts = tpos.split("/")
        tags.disc = parts[0].strip()
        tags.disc_total = parts[1].strip()
    else:
        tags.disc = tpos.strip()

    for key in audio:
        if key.startswith("APIC"):
            pic = audio[key]
            tags.cover_data = pic.data
            tags.cover_mime = pic.mime
            break

    return SongFile(path=path, tags=tags)


def write_tags(song: SongFile) -> None:
    """Write TagData back to an MP3 file's ID3 tags."""
    try:
        audio = ID3(song.path)
    except ID3NoHeaderError:
        audio = ID3()

    t = song.tags

    audio["TIT2"] = TIT2(encoding=3, text=t.title)
    audio["TPE1"] = TPE1(encoding=3, text=t.artist)
    audio["TALB"] = TALB(encoding=3, text=t.album)
    audio["TPE2"] = TPE2(encoding=3, text=t.album_artist)
    audio["TDRC"] = TDRC(encoding=3, text=t.year)
    audio["TCON"] = TCON(encoding=3, text=t.genre)

    if t.track:
        trck = f"{t.track}/{t.track_total}" if t.track_total else t.track
        audio["TRCK"] = TRCK(encoding=3, text=trck)

    if t.disc:
        tpos = f"{t.disc}/{t.disc_total}" if t.disc_total else t.disc
        audio["TPOS"] = TPOS(encoding=3, text=tpos)

    if t.comment:
        audio["COMM::'XXX'"] = COMM(encoding=3, lang="eng", desc="'XXX'", text=t.comment)

    if t.cover_data and t.cover_mime:
        audio.delall("APIC")
        audio["APIC"] = APIC(
            encoding=3,
            mime=t.cover_mime,
            type=3,
            desc="Cover",
            data=t.cover_data,
        )
    elif not t.cover_data:
        audio.delall("APIC")

    audio.save(song.path)


def apply_tags(song: SongFile, updates: TagData) -> None:
    """Merge non-empty fields from updates into song.tags, then write."""
    t = song.tags
    u = updates

    if u.title:
        t.title = u.title
    if u.artist:
        t.artist = u.artist
    if u.album:
        t.album = u.album
    if u.album_artist:
        t.album_artist = u.album_artist
    if u.year:
        t.year = u.year
    if u.genre:
        t.genre = u.genre
    if u.track:
        t.track = u.track
    if u.track_total:
        t.track_total = u.track_total
    if u.disc:
        t.disc = u.disc
    if u.disc_total:
        t.disc_total = u.disc_total
    if u.comment:
        t.comment = u.comment
    if u.cover_data:
        t.cover_data = u.cover_data
        t.cover_mime = u.cover_mime

    write_tags(song)


PATTERN_TOKENS = {
    "track": "track",
    "title": "title",
    "artist": "artist",
    "album": "album",
    "album_artist": "album_artist",
    "year": "year",
    "genre": "genre",
    "disc": "disc",
    "comment": "comment",
}


def parse_pattern(pattern: str, tags: TagData) -> str:
    """Replace {token} placeholders in pattern with tag values."""
    result = pattern
    for token, field_name in PATTERN_TOKENS.items():
        value = getattr(tags, field_name, "")
        result = result.replace(f"{{{token}}}", value or "unknown")
    result = re.sub(r"[/\\:*?\"<>|]", "_", result)
    return result


def apply_track_numbers(songs: list[SongFile], start: int = 1) -> None:
    """Set track numbers sequentially for a list of songs."""
    total = len(songs)
    for i, song in enumerate(songs):
        song.tags.track = str(start + i).zfill(2)
        song.tags.track_total = str(total).zfill(2)


def rename_file(song: SongFile, pattern: str) -> Path:
    """Rename an MP3 file based on a pattern. Returns the new path."""
    new_stem = parse_pattern(pattern, song.tags)
    new_path = song.path.with_name(f"{new_stem}.mp3")
    counter = 1
    while new_path.exists() and new_path != song.path:
        new_path = song.path.with_name(f"{new_stem} ({counter}).mp3")
        counter += 1
    if new_path != song.path:
        song.path.rename(new_path)
        song.path = new_path
    return new_path


def get_mp3_files(directory: Path) -> list[Path]:
    """Return sorted list of MP3 files in a directory (non-recursive)."""
    return sorted(
        p for p in directory.iterdir()
        if p.is_file() and p.suffix.lower() == ".mp3"
    )
