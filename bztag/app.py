from __future__ import annotations

from pathlib import Path

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, Label, Static

from bztag.batch import (
    ReorderChange,
    RenameChange,
    build_batch_edit_preview,
    build_reorder_preview,
    build_rename_preview,
    execute_batch_edit,
    execute_reorders,
    execute_renames,
)
from bztag.cover_art import SUPPORTED_EXTENSIONS, embed_cover
from bztag.file_list import FileFocused, FileList, FilesSelected
from bztag.models import SongFile, TagData
from bztag.tag_editor import (
    BatchReorderRequested,
    BatchRenameRequested,
    CoverArtRequested,
    FilenameRenamed,
    TagEditor,
    TagsApplied,
)
from bztag.tree_view import FolderSelected, TreeView

CSS = """
Screen {
    layout: horizontal;
}

#tree-pane {
    width: 50;
    min-width: 20;
    height: 100%;
    border-right: solid $accent;
}

#list-pane {
    width: 1fr;
    min-width: 30;
    height: 100%;
    border-right: solid $accent;
}

#editor-pane {
    width: 1fr;
    min-width: 40;
    height: 100%;
    overflow-y: auto;
}

#tag-form {
    height: auto;
}

#tag-fields {
    height: auto;
    margin: 0 1;
}

#tag-fields Input {
    margin: 0 0 1 0;
}

#tag-fields Label {
    height: 1;
}

#track-row, #disc-row {
    height: 3;
}

#track-row Input, #disc-row Input {
    width: 10;
}

#track-row Label, #disc-row Label {
    width: 10;
    content-align: center middle;
}

#cover-section {
    height: 3;
    margin: 1 1;
    align: left middle;
}

#cover-preview {
    margin-left: 1;
    width: 1fr;
}

#action-buttons {
    height: 3;
    margin: 1 1;
    align: left middle;
}

#action-buttons Button {
    margin-right: 1;
}

#editor-title {
    text-style: bold;
    margin: 1 1 0 1;
}

#selection-info {
    margin: 0 1 1 1;
    color: $text-muted;
}

#rename-pattern-row {
    height: 3;
    margin: 0 1 1 1;
    align: left middle;
}

#rename-pattern-row Label {
    margin-right: 1;
}

#rename-pattern-row Input {
    width: 1fr;
}

#start-number-row {
    height: 3;
    margin: 0 1 1 1;
    align: left middle;
}

#start-number-row Label {
    margin-right: 1;
}

#start-number-row Input {
    width: 5;
}

#confirm-buttons {
    height: 3;
    margin: 1;
    align: center middle;
}

#confirm-buttons Button {
    margin: 0 1;
}

#preview-text {
    margin: 0 1 1 1;
    height: 1fr;
    overflow-y: auto;
}

#status-bar {
    height: 1;
    dock: bottom;
    padding: 0 1;
    background: $accent;
    color: $text;
}

#debug-log {
    height: 12;
    dock: bottom;
    border-top: solid $accent;
    padding: 0 1;
    overflow-y: auto;
    background: $surface;
}
"""


class BZTagApp(App):
    """BZ-Tag: MP3 Tag Editor"""

    CSS = CSS
    TITLE = "BZ-Tag"
    SUB_TITLE = "MP3 Tag Editor"

    BINDINGS = [
        Binding("ctrl+a", "select_all", "Select All"),
        Binding("ctrl+d", "deselect_all", "Deselect All"),
        Binding("ctrl+q", "quit", "Quit"),
        Binding("alt+up", "pane_left", "Prev Pane"),
        Binding("alt+down", "pane_right", "Next Pane"),
    ]

    PANE_IDS = ["dir-tree", "file-list", "tag-editor"]

    def __init__(self, debug: bool = False, path: str | None = None, file_path: str | None = None) -> None:
        super().__init__()
        self._debug = debug
        self._initial_path = Path(path).expanduser().resolve() if path else None
        self._initial_file = Path(file_path).expanduser().resolve() if file_path else None

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical(id="tree-pane"):
                yield TreeView(Path.home(), id="dir-tree")
            with Vertical(id="list-pane"):
                yield FileList(id="file-list")
                if self._debug:
                    yield Static("No file focused", id="debug-log")
            with Vertical(id="editor-pane"):
                yield TagEditor(id="tag-editor")
        yield Footer()
        yield Static("Ready", id="status-bar")

    def on_mount(self) -> None:
        file_list = self.query_one("#file-list", FileList)
        tag_editor = self.query_one("#tag-editor", TagEditor)

        if self._initial_file:
            parent = self._initial_file.parent
            if parent.is_dir():
                tree = self.query_one("#dir-tree", TreeView)
                tree.path = parent
                file_list.load_directory(parent)
                self.set_status(f"Folder: {parent}")
                self._select_file(file_list, tag_editor, self._initial_file.name)
        elif self._initial_path and self._initial_path.is_dir():
            tree = self.query_one("#dir-tree", TreeView)
            tree.path = self._initial_path
            file_list.load_directory(self._initial_path)
            self.set_status(f"Folder: {self._initial_path}")

    def _select_file(self, file_list: FileList, tag_editor: TagEditor, filename: str) -> None:
        for i, song in enumerate(file_list._songs):
            if song.path.name == filename:
                file_list.cursor_row = i
                file_list.action_toggle_selection()
                tag_editor.load_songs([song])
                tag_editor.query_one("#field-title", Input).focus()
                return

    def action_select_all(self) -> None:
        self.query_one("#file-list", FileList).select_all()

    def action_deselect_all(self) -> None:
        self.query_one("#file-list", FileList).deselect_all()

    def action_pane_left(self) -> None:
        focused = self.app.focused
        if focused is None:
            idx = 0
        else:
            try:
                idx = self.PANE_IDS.index(focused.id)
            except ValueError:
                idx = 0
        idx = (idx - 1) % len(self.PANE_IDS)
        self.query_one(f"#{self.PANE_IDS[idx]}").focus()

    def action_pane_right(self) -> None:
        focused = self.app.focused
        if focused is None:
            idx = 0
        else:
            try:
                idx = self.PANE_IDS.index(focused.id)
            except ValueError:
                idx = 0
        idx = (idx + 1) % len(self.PANE_IDS)
        self.query_one(f"#{self.PANE_IDS[idx]}").focus()

    def set_status(self, text: str) -> None:
        self.query_one("#status-bar", Static).update(text)

    @on(FolderSelected)
    def on_folder_selected(self, event: FolderSelected) -> None:
        file_list = self.query_one("#file-list", FileList)
        file_list.load_directory(event.path)
        self.set_status(f"Folder: {event.path}")
        tag_editor = self.query_one("#tag-editor", TagEditor)
        tag_editor._songs = []
        tag_editor._clear_fields()
        tag_editor.query_one("#selection-info", Label).update("No files selected")

    @on(FilesSelected)
    def on_files_selected(self, event: FilesSelected) -> None:
        tag_editor = self.query_one("#tag-editor", TagEditor)
        tag_editor.load_songs(event.songs)
        count = len(event.songs)
        self.set_status(f"{count} file(s) selected")

    @on(FileFocused)
    def on_file_focused(self, event: FileFocused) -> None:
        tag_editor = self.query_one("#tag-editor", TagEditor)
        tag_editor.load_songs([event.song])
        if self._debug:
            s = event.song.tags
            debug = self.query_one("#debug-log", Static)
            debug.update(
                f"File: {event.song.filename}\n"
                f"  title={s.title!r}  artist={s.artist!r}  album={s.album!r}\n"
                f"  year={s.year!r}  genre={s.genre!r}\n"
                f"  track={s.track!r}  track_total={s.track_total!r}\n"
                f"  disc={s.disc!r}  disc_total={s.disc_total!r}\n"
                f"  comment={s.comment!r}\n"
                f"  cover={'yes' if s.cover_data else 'no'}"
            )

    @on(TagsApplied)
    def on_tags_applied(self, event: TagsApplied) -> None:
        self._show_confirm_modal(
            "Apply Tags",
            self._build_tag_preview_text(event.songs, event.updates),
            lambda: self._execute_tag_apply(event.songs, event.updates),
        )

    @on(BatchReorderRequested)
    def on_batch_reorder(self, event: BatchReorderRequested) -> None:
        self._show_reorder_modal(event.songs)

    @on(BatchRenameRequested)
    def on_batch_rename(self, event: BatchRenameRequested) -> None:
        self._show_rename_modal(event.songs)

    @on(CoverArtRequested)
    def on_cover_art(self, event: CoverArtRequested) -> None:
        self._show_cover_art_modal(event.songs)

    @on(FilenameRenamed)
    def on_filename_renamed(self, event: FilenameRenamed) -> None:
        for song in event.songs:
            new_name = event.new_name
            if not new_name.lower().endswith(".mp3"):
                new_name += ".mp3"
            new_path = song.path.with_name(new_name)
            counter = 1
            while new_path.exists() and new_path != song.path:
                stem = new_path.stem
                new_path = song.path.with_name(f"{stem} ({counter}).mp3")
                counter += 1
            if new_path != song.path:
                song.path.rename(new_path)
                song.path = new_path
        self._refresh_current_dir()
        self.set_status(f"Renamed {len(event.songs)} file(s)")

    def _show_confirm_modal(
        self, title: str, text: str, on_confirm: callable
    ) -> None:
        modal = ConfirmModal(title, text, on_confirm)
        self.push_screen(modal)

    def _build_tag_preview_text(
        self, songs: list[SongFile], updates: TagData
    ) -> str:
        preview = build_batch_edit_preview(songs, updates)
        lines = []
        for change in preview:
            lines.append(f"=== {change.old_filename} ===")
            fields = [
                ("Title", change.old_tags.title, change.new_tags.title),
                ("Artist", change.old_tags.artist, change.new_tags.artist),
                ("Album", change.old_tags.album, change.new_tags.album),
                ("Year", change.old_tags.year, change.new_tags.year),
                ("Genre", change.old_tags.genre, change.new_tags.genre),
                ("Track", change.old_tags.track, change.new_tags.track),
            ]
            for name, old, new in fields:
                if old != new:
                    lines.append(f"  {name}: '{old}' -> '{new}'")
            lines.append("")
        return "\n".join(lines)

    def _execute_tag_apply(
        self, songs: list[SongFile], updates: TagData
    ) -> None:
        preview = build_batch_edit_preview(songs, updates)
        execute_batch_edit(preview)
        self.set_status(f"Tags applied to {len(songs)} file(s)")
        self._refresh_current_dir()

    def _show_reorder_modal(self, songs: list[SongFile]) -> None:
        modal = ReorderModal(songs)
        self.push_screen(modal)

    def _show_rename_modal(self, songs: list[SongFile]) -> None:
        modal = RenameModal(songs)
        self.push_screen(modal)

    def _show_cover_art_modal(self, songs: list[SongFile]) -> None:
        modal = CoverArtModal(songs)
        self.push_screen(modal)

    def _refresh_current_dir(self) -> None:
        tree = self.query_one("#dir-tree", TreeView)
        file_list = self.query_one("#file-list", FileList)
        try:
            selected = tree.cursor_node
            if selected:
                path = tree.get_node_at(selected).data.path
                if path.is_dir():
                    file_list.load_directory(path)
        except Exception:
            pass


from textual.screen import ModalScreen
from textual.widgets import Button, TextArea


class ConfirmModal(ModalScreen[bool]):
    """Modal to confirm a batch operation."""

    CSS = """
    ConfirmModal {
        align: center middle;
    }
    #confirm-container {
        width: 70;
        max-width: 90%;
        height: auto;
        max-height: 80%;
        border: thick solid $accent;
        background: $surface;
        padding: 1 2;
    }
    #confirm-title {
        text-style: bold;
        margin-bottom: 1;
    }
    #confirm-text {
        height: auto;
        max-height: 40;
        margin-bottom: 1;
        overflow-y: auto;
    }
    #confirm-buttons {
        height: 3;
        align: center middle;
    }
    #confirm-buttons Button {
        margin: 0 1;
    }
    """

    def __init__(self, title: str, text: str, on_confirm: callable) -> None:
        super().__init__()
        self._title = title
        self._text = text
        self._on_confirm = on_confirm

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-container"):
            yield Label(self._title, id="confirm-title")
            yield Static(self._text, id="confirm-text")
            with Horizontal(id="confirm-buttons"):
                yield Button("Confirm", variant="primary", id="btn-confirm")
                yield Button("Cancel", variant="default", id="btn-cancel")

    @on(Button.Pressed, "#btn-confirm")
    def on_confirm(self) -> None:
        self._on_confirm()
        self.dismiss(True)

    @on(Button.Pressed, "#btn-cancel")
    def on_cancel(self) -> None:
        self.dismiss(False)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(False)


class ReorderModal(ModalScreen[bool]):
    """Modal for track reordering with start number input."""

    CSS = """
    ReorderModal {
        align: center middle;
    }
    #reorder-container {
        width: 70;
        max-width: 90%;
        height: auto;
        max-height: 80%;
        border: thick solid $accent;
        background: $surface;
        padding: 1 2;
    }
    #reorder-title {
        text-style: bold;
        margin-bottom: 1;
    }
    #start-number-row {
        height: 3;
        margin-bottom: 1;
        align: left middle;
    }
    #start-number-row Label {
        margin-right: 1;
    }
    #reorder-preview {
        height: 1fr;
        max-height: 30;
        overflow-y: auto;
        margin-bottom: 1;
    }
    #reorder-buttons {
        height: 3;
        align: center middle;
    }
    #reorder-buttons Button {
        margin: 0 1;
    }
    """

    def __init__(self, songs: list[SongFile]) -> None:
        super().__init__()
        self._songs = songs

    def compose(self) -> ComposeResult:
        with Vertical(id="reorder-container"):
            yield Label("Reorder Tracks", id="reorder-title")
            with Horizontal(id="start-number-row"):
                yield Label("Start number:")
                yield Input("1", id="start-number", max_length=3)
            yield Static("", id="reorder-preview")
            with Horizontal(id="reorder-buttons"):
                yield Button("Apply", variant="primary", id="btn-reorder-apply")
                yield Button("Cancel", variant="default", id="btn-reorder-cancel")

    def on_mount(self) -> None:
        self._update_preview()

    @on(Input.Changed, "#start-number")
    def on_start_changed(self) -> None:
        self._update_preview()

    def _update_preview(self) -> None:
        try:
            start = int(self.query_one("#start-number", Input).value or "1")
        except ValueError:
            start = 1

        preview = build_reorder_preview(self._songs, start)
        lines = []
        for change in preview:
            lines.append(
                f"{change.song.filename}: {change.old_track} -> {change.new_track}"
            )
        self.query_one("#reorder-preview", Static).update("\n".join(lines))

    @on(Button.Pressed, "#btn-reorder-apply")
    def on_apply(self) -> None:
        try:
            start = int(self.query_one("#start-number", Input).value or "1")
        except ValueError:
            start = 1

        preview = build_reorder_preview(self._songs, start)
        execute_reorders(preview)
        self.dismiss(True)

    @on(Button.Pressed, "#btn-reorder-cancel")
    def on_cancel(self) -> None:
        self.dismiss(False)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(False)


class RenameModal(ModalScreen[bool]):
    """Modal for file renaming with pattern input."""

    CSS = """
    RenameModal {
        align: center middle;
    }
    #rename-container {
        width: 70;
        max-width: 90%;
        height: auto;
        max-height: 80%;
        border: thick solid $accent;
        background: $surface;
        padding: 1 2;
    }
    #rename-title {
        text-style: bold;
        margin-bottom: 1;
    }
    #rename-pattern-row {
        height: 3;
        margin-bottom: 1;
        align: left middle;
    }
    #rename-pattern-row Label {
        margin-right: 1;
    }
    #rename-pattern-row Input {
        width: 1fr;
    }
    #rename-preview {
        height: 1fr;
        max-height: 30;
        overflow-y: auto;
        margin-bottom: 1;
    }
    #rename-buttons {
        height: 3;
        align: center middle;
    }
    #rename-buttons Button {
        margin: 0 1;
    }
    """

    DEFAULT_PATTERN = "{track}-{title}"

    def __init__(self, songs: list[SongFile]) -> None:
        super().__init__()
        self._songs = songs

    def compose(self) -> ComposeResult:
        with Vertical(id="rename-container"):
            yield Label("Rename Files", id="rename-title")
            with Horizontal(id="rename-pattern-row"):
                yield Label("Pattern:")
                yield Input(self.DEFAULT_PATTERN, id="rename-pattern")
            yield Static(
                "Tokens: {track} {title} {artist} {album} {year} {genre}",
                id="rename-help",
            )
            yield Static("", id="rename-preview")
            with Horizontal(id="rename-buttons"):
                yield Button("Apply", variant="primary", id="btn-rename-apply")
                yield Button("Cancel", variant="default", id="btn-rename-cancel")

    def on_mount(self) -> None:
        self._update_preview()

    @on(Input.Changed, "#rename-pattern")
    def on_pattern_changed(self) -> None:
        self._update_preview()

    def _update_preview(self) -> None:
        pattern = self.query_one("#rename-pattern", Input).value
        preview = build_rename_preview(self._songs, pattern)
        lines = []
        for change in preview:
            lines.append(f"{change.old_name}  ->  {change.new_name}")
        self.query_one("#rename-preview", Static).update("\n".join(lines))

    @on(Button.Pressed, "#btn-rename-apply")
    def on_apply(self) -> None:
        pattern = self.query_one("#rename-pattern", Input).value
        preview = build_rename_preview(self._songs, pattern)
        execute_renames(preview)
        self.dismiss(True)

    @on(Button.Pressed, "#btn-rename-cancel")
    def on_cancel(self) -> None:
        self.dismiss(False)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(False)


class CoverArtModal(ModalScreen[bool]):
    """Modal for selecting and embedding cover art."""

    CSS = """
    CoverArtModal {
        align: center middle;
    }
    #cover-container {
        width: 50;
        max-width: 90%;
        height: auto;
        border: thick solid $accent;
        background: $surface;
        padding: 1 2;
    }
    #cover-title {
        text-style: bold;
        margin-bottom: 1;
    }
    #cover-info {
        margin-bottom: 1;
        color: $text-muted;
    }
    #cover-path-row {
        height: 3;
        margin-bottom: 1;
        align: left middle;
    }
    #cover-path-row Label {
        margin-right: 1;
    }
    #cover-path-row Input {
        width: 1fr;
    }
    #cover-buttons {
        height: 3;
        align: center middle;
    }
    #cover-buttons Button {
        margin: 0 1;
    }
    """

    def __init__(self, songs: list[SongFile]) -> None:
        super().__init__()
        self._songs = songs

    def compose(self) -> ComposeResult:
        with Vertical(id="cover-container"):
            yield Label("Embed Cover Art", id="cover-title")
            yield Label(
                f"Will embed into {len(self._songs)} file(s)", id="cover-info"
            )
            with Horizontal(id="cover-path-row"):
                yield Label("Image path:")
                yield Input(placeholder="/path/to/cover.jpg", id="cover-path")
            with Horizontal(id="cover-buttons"):
                yield Button("Embed", variant="primary", id="btn-cover-embed")
                yield Button("Cancel", variant="default", id="btn-cover-cancel")

    @on(Button.Pressed, "#btn-cover-embed")
    def on_embed(self) -> None:
        path_str = self.query_one("#cover-path", Input).value.strip()
        if not path_str:
            return

        image_path = Path(path_str)
        if not image_path.exists():
            self.notify(f"File not found: {image_path}", severity="error")
            return

        if image_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            self.notify(
                f"Unsupported format: {image_path.suffix}",
                severity="error",
            )
            return

        for song in self._songs:
            embed_cover(song.path, image_path)

        self.notify(f"Cover art embedded in {len(self._songs)} file(s)")
        self.dismiss(True)

    @on(Button.Pressed, "#btn-cover-cancel")
    def on_cancel(self) -> None:
        self.dismiss(False)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(False)
