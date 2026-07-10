from __future__ import annotations

from pathlib import Path

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.widgets import Button, Input, Label, Static

from bztag.models import SongFile, TagData

FIELD_IDS = [
    "field-filename", "field-title", "field-artist", "field-album",
    "field-album-artist", "field-year", "field-track", "field-track-total",
    "field-genre", "field-comment", "field-disc", "field-disc-total",
]

INPUT_IDS = [
    "field-filename", "field-title", "field-artist", "field-album",
    "field-album-artist", "field-year", "field-track", "field-track-total",
    "field-genre", "field-comment", "field-disc", "field-disc-total",
]


class TagsApplied(Message):
    def __init__(self, songs: list[SongFile], updates: TagData) -> None:
        self.songs = songs
        self.updates = updates
        super().__init__()


class FilenameRenamed(Message):
    def __init__(self, songs: list[SongFile], new_name: str) -> None:
        self.songs = songs
        self.new_name = new_name
        super().__init__()


class BatchReorderRequested(Message):
    def __init__(self, songs: list[SongFile]) -> None:
        self.songs = songs
        super().__init__()


class BatchRenameRequested(Message):
    def __init__(self, songs: list[SongFile]) -> None:
        self.songs = songs
        super().__init__()


class CoverArtRequested(Message):
    def __init__(self, songs: list[SongFile]) -> None:
        self.songs = songs
        super().__init__()


class TagEditor(VerticalScroll):
    """Right pane: tag editing form for selected file(s)."""

    BINDINGS = [
        Binding("enter", "field_submit", "Next Field"),
        Binding("ctrl+s", "apply_tags", "Apply Tags"),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.can_focus = False
        self._songs: list[SongFile] = []
        self._original_filename: str = ""

    def compose(self) -> ComposeResult:
        with Vertical(id="tag-form"):
            yield Label("Tag Editor", id="editor-title")
            yield Label("No files selected", id="selection-info")

            with Vertical(id="tag-fields"):
                yield Label("Filename")
                yield Input(placeholder="filename", id="field-filename")
                yield Label("Title")
                yield Input(placeholder="Title", id="field-title")
                yield Label("Artist")
                yield Input(placeholder="Artist", id="field-artist")
                yield Label("Album")
                yield Input(placeholder="Album", id="field-album")
                yield Label("Album Artist")
                yield Input(placeholder="Album Artist", id="field-album-artist")
                yield Label("Year")
                yield Input(placeholder="Year", id="field-year")
                yield Label("Track (number/total)")
                with Horizontal(id="track-row"):
                    yield Input(placeholder="Track", id="field-track", max_length=3)
                    yield Label("/")
                    yield Input(placeholder="Total", id="field-track-total", max_length=3)
                yield Label("Genre")
                yield Input(placeholder="Genre", id="field-genre")
                yield Label("Comment")
                yield Input(placeholder="Comment", id="field-comment")
                yield Label("Disc (number/total)")
                with Horizontal(id="disc-row"):
                    yield Input(placeholder="Disc", id="field-disc", max_length=3)
                    yield Label("/")
                    yield Input(placeholder="Total", id="field-disc-total", max_length=3)

            with Horizontal(id="cover-section"):
                yield Button("Embed Cover Art", id="btn-cover", variant="default")
                yield Static("No cover", id="cover-preview")

            with Horizontal(id="action-buttons"):
                yield Button("Apply Tags", id="btn-apply", variant="primary")
                yield Button("Reorder Tracks", id="btn-reorder", variant="default")
                yield Button("Rename Files", id="btn-rename", variant="default")

    def on_mount(self) -> None:
        self.query_one("#field-filename", Input).tab_index = 100

    def action_field_submit(self) -> None:
        """Enter: accept current field, move to next."""
        focused = self.app.focused
        if not focused or not isinstance(focused, Input):
            return
        try:
            idx = INPUT_IDS.index(focused.id)
        except ValueError:
            return
        if idx < len(INPUT_IDS) - 1:
            next_id = INPUT_IDS[idx + 1]
            self.query_one(f"#{next_id}", Input).focus()

    def load_songs(self, songs: list[SongFile]) -> None:
        self._songs = songs
        info = self.query_one("#selection-info", Label)
        fn_field = self.query_one("#field-filename", Input)

        if not songs:
            info.update("No files selected — type tags, then select files to apply")
            self._original_filename = ""
            fn_field.value = ""
            fn_field.disabled = False
            return

        if len(songs) == 1:
            info.update(f"1 file: {songs[0].filename}")
            self._original_filename = songs[0].filename
            fn_field.value = songs[0].filename
            fn_field.disabled = False
            self._load_single(songs[0].tags)
        else:
            info.update(f"{len(songs)} files selected")
            self._original_filename = ""
            fn_field.value = "Multiple files"
            fn_field.disabled = True
            self._load_merged(songs)

    def _load_single(self, tags: TagData) -> None:
        self.query_one("#field-title", Input).value = tags.title
        self.query_one("#field-artist", Input).value = tags.artist
        self.query_one("#field-album", Input).value = tags.album
        self.query_one("#field-album-artist", Input).value = tags.album_artist
        self.query_one("#field-year", Input).value = tags.year
        self.query_one("#field-genre", Input).value = tags.genre
        self.query_one("#field-track", Input).value = tags.track
        self.query_one("#field-track-total", Input).value = tags.track_total
        self.query_one("#field-disc", Input).value = tags.disc
        self.query_one("#field-disc-total", Input).value = tags.disc_total
        self.query_one("#field-comment", Input).value = tags.comment

        cover = self.query_one("#cover-preview", Static)
        if tags.cover_data:
            size_kb = len(tags.cover_data) / 1024
            cover.update(f"Cover: {tags.cover_mime} ({size_kb:.0f} KB)")
        else:
            cover.update("No cover")

    def _load_merged(self, songs: list[SongFile]) -> None:
        common = songs[0].tags
        for song in songs[1:]:
            common = common.common(song.tags)
        self._load_single(common)

    def _clear_fields(self) -> None:
        for field_id in FIELD_IDS:
            self.query_one(f"#{field_id}", Input).value = ""
        self.query_one("#field-filename", Input).disabled = False
        self.query_one("#cover-preview", Static).update("No cover")

    def get_updates(self) -> TagData:
        return TagData(
            title=self.query_one("#field-title", Input).value,
            artist=self.query_one("#field-artist", Input).value,
            album=self.query_one("#field-album", Input).value,
            album_artist=self.query_one("#field-album-artist", Input).value,
            year=self.query_one("#field-year", Input).value,
            genre=self.query_one("#field-genre", Input).value,
            track=self.query_one("#field-track", Input).value,
            track_total=self.query_one("#field-track-total", Input).value,
            disc=self.query_one("#field-disc", Input).value,
            disc_total=self.query_one("#field-disc-total", Input).value,
            comment=self.query_one("#field-comment", Input).value,
        )

    def get_new_filename(self) -> str | None:
        """Return the new filename stem if changed, or None."""
        if not self._songs or len(self._songs) != 1:
            return None
        fn = self.query_one("#field-filename", Input).value.strip()
        if fn and fn != self._original_filename:
            return fn
        return None

    def action_apply_tags(self) -> None:
        self.on_apply()

    @on(Button.Pressed, "#btn-apply")
    def on_apply(self) -> None:
        if not self._songs:
            return
        new_fn = self.get_new_filename()
        if new_fn:
            self.post_message(FilenameRenamed(self._songs, new_fn))
        self.post_message(TagsApplied(self._songs, self.get_updates()))

    @on(Button.Pressed, "#btn-reorder")
    def on_reorder(self) -> None:
        if self._songs:
            self.post_message(BatchReorderRequested(self._songs))

    @on(Button.Pressed, "#btn-rename")
    def on_rename(self) -> None:
        if self._songs:
            self.post_message(BatchRenameRequested(self._songs))

    @on(Button.Pressed, "#btn-cover")
    def on_cover(self) -> None:
        if self._songs:
            self.post_message(CoverArtRequested(self._songs))
