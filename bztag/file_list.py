from __future__ import annotations

from pathlib import Path

from textual import on
from textual.binding import Binding
from textual.message import Message
from textual.widgets import DataTable

from bztag.utils import get_mp3_files, read_tags
from bztag.models import SongFile


class FilesSelected(Message):
    def __init__(self, songs: list[SongFile]) -> None:
        self.songs = songs
        super().__init__()


class FileFocused(Message):
    def __init__(self, song: SongFile) -> None:
        self.song = song
        super().__init__()


class FileList(DataTable):
    """DataTable showing MP3 files with checkbox-style multi-select."""

    BINDINGS = [
        Binding("space", "toggle_selection", "Select"),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._songs: list[SongFile] = []
        self._selected_keys: set[str] = set()
        self.cursor_type = "row"
        self.zebra_stripes = True

    def compose(self):
        yield from super().compose()

    def on_mount(self) -> None:
        self.add_column("Sel", width=3, key="sel")
        self.add_column("Track", width=5, key="track")
        self.add_column("Title", width=30, key="title")
        self.add_column("Artist", width=20, key="artist")
        self.add_column("Album", width=20, key="album")
        self.add_column("Year", width=5, key="year")

    def load_directory(self, directory: Path) -> None:
        self.clear()
        self._songs = []
        self._selected_keys.clear()

        mp3_files = get_mp3_files(directory)
        for p in mp3_files:
            song = read_tags(p)
            self._songs.append(song)
            row_key = p.name
            self.add_row(
                "\u25a1",
                song.tags.track or "",
                song.tags.title or p.stem,
                song.tags.artist or "",
                song.tags.album or "",
                song.tags.year or "",
                key=row_key,
            )

    def get_selected_songs(self) -> list[SongFile]:
        return [s for s in self._songs if s.path.name in self._selected_keys]

    def action_toggle_selection(self) -> None:
        """Toggle selection on the current row via Space."""
        if not self._songs:
            return
        row = self.cursor_row
        if row < 0 or row >= len(self._songs):
            return
        row_key = self._songs[row].path.name
        if row_key in self._selected_keys:
            self._selected_keys.discard(row_key)
            self.update_cell(row_key, "sel", "\u25a1", update_width=True)
        else:
            self._selected_keys.add(row_key)
            self.update_cell(row_key, "sel", "\u25a0", update_width=True)
        self.post_message(FilesSelected(self.get_selected_songs()))

    @on(DataTable.RowHighlighted)
    def on_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        row = self.cursor_row
        if 0 <= row < len(self._songs):
            self.post_message(FileFocused(self._songs[row]))

    @on(DataTable.RowSelected)
    def on_row_selected(self, event: DataTable.RowSelected) -> None:
        pass

    def select_all(self) -> None:
        for song in self._songs:
            key = song.path.name
            self._selected_keys.add(key)
            self.update_cell(key, "sel", "\u25a0", update_width=True)
        self.post_message(FilesSelected(self.get_selected_songs()))

    def deselect_all(self) -> None:
        for song in self._songs:
            key = song.path.name
            self._selected_keys.discard(key)
            self.update_cell(key, "sel", "\u25a1", update_width=True)
        self.post_message(FilesSelected([]))
