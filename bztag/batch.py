from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from bztag.models import SongFile, TagData
from bztag.utils import apply_tags, apply_track_numbers, parse_pattern, write_tags


@dataclass
class BatchChange:
    """A single pending change for preview."""
    song: SongFile
    old_filename: str
    new_filename: str
    old_tags: TagData
    new_tags: TagData


@dataclass
class RenameChange:
    """A rename-only change for preview."""
    song: SongFile
    old_name: str
    new_name: str


@dataclass
class ReorderChange:
    """A track reordering change for preview."""
    song: SongFile
    old_track: str
    new_track: str
    new_track_total: str


def build_rename_preview(songs: list[SongFile], pattern: str) -> list[RenameChange]:
    """Build a list of RenameChanges showing what rename would do."""
    changes = []
    for song in songs:
        new_stem = parse_pattern(pattern, song.tags)
        new_name = f"{new_stem}.mp3"
        changes.append(
            RenameChange(
                song=song,
                old_name=song.filename,
                new_name=new_name,
            )
        )
    return changes


def build_reorder_preview(
    songs: list[SongFile], start: int = 1
) -> list[ReorderChange]:
    """Build a list of ReorderChanges showing new track numbers."""
    total = len(songs)
    changes = []
    for i, song in enumerate(songs):
        new_num = str(start + i).zfill(2)
        changes.append(
            ReorderChange(
                song=song,
                old_track=song.tags.track or "0",
                new_track=new_num,
                new_track_total=str(total).zfill(2),
            )
        )
    return changes


def build_batch_edit_preview(
    songs: list[SongFile], updates: TagData
) -> list[BatchChange]:
    """Build preview of applying tag updates to multiple files."""
    changes = []
    for song in songs:
        merged = TagData(
            title=updates.title or song.tags.title,
            artist=updates.artist or song.tags.artist,
            album=updates.album or song.tags.album,
            album_artist=updates.album_artist or song.tags.album_artist,
            year=updates.year or song.tags.year,
            genre=updates.genre or song.tags.genre,
            track=updates.track or song.tags.track,
            track_total=updates.track_total or song.tags.track_total,
            disc=updates.disc or song.tags.disc,
            disc_total=updates.disc_total or song.tags.disc_total,
            comment=updates.comment or song.tags.comment,
            cover_data=updates.cover_data or song.tags.cover_data,
            cover_mime=updates.cover_mime or song.tags.cover_mime,
        )
        changes.append(
            BatchChange(
                song=song,
                old_filename=song.filename,
                new_filename=song.filename,
                old_tags=TagData(**vars(song.tags)),
                new_tags=merged,
            )
        )
    return changes


def execute_renames(changes: list[RenameChange]) -> list[tuple[Path, Path]]:
    """Execute renames from preview changes. Returns old->new path pairs."""
    results = []
    for change in changes:
        old_path = change.song.path
        new_path = old_path.with_name(change.new_name)
        counter = 1
        while new_path.exists() and new_path != old_path:
            stem = new_path.stem
            new_path = old_path.with_name(f"{stem} ({counter}).mp3")
            counter += 1
        if new_path != old_path:
            old_path.rename(new_path)
            change.song.path = new_path
            results.append((old_path, new_path))
    return results


def execute_reorders(changes: list[ReorderChange]) -> None:
    """Execute track reordering from preview changes."""
    total = changes[0].new_track_total if changes else "1"
    for change in changes:
        change.song.tags.track = change.new_track
        change.song.tags.track_total = total
        write_tags(change.song)


def execute_batch_edit(changes: list[BatchChange]) -> None:
    """Execute batch tag edits from preview changes."""
    for change in changes:
        change.song.tags = change.new_tags
        write_tags(change.song)
