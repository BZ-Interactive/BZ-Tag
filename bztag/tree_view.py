from __future__ import annotations

from pathlib import Path

from textual import on
from textual.message import Message
from textual.widgets import DirectoryTree


class FolderSelected(Message):
    def __init__(self, path: Path) -> None:
        self.path = path
        super().__init__()


class TreeView(DirectoryTree):
    """Directory tree that emits FolderSelected when a folder is chosen."""

    def filter_paths(self, paths: list[Path]) -> list[Path]:
        """Hide directories/files starting with a dot."""
        return [p for p in paths if not p.name.startswith(".")]

    @on(DirectoryTree.DirectorySelected)
    def on_directory_selected(self, event: DirectoryTree.DirectorySelected) -> None:
        self.post_message(FolderSelected(Path(event.path)))
