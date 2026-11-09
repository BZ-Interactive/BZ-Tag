"""Shared editing engine for BZ Tag frontends.

Both frontends (cli.py now, ui/tui.py) talk only to Engine;
Engine talks only to core/ functions.
"""

import os
from dataclasses import dataclass
from enum import Enum

from .core.bztagerror import BZTagError, ScanError
from .core.scanner import scan
from .core.sorter import sort
from .core import metadata


class Status(Enum):
    CHANGED = "changed"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class FileResult:
    path: str
    status: Status
    message: str


class Engine:
    """Owns file discovery, selection, and change application."""

    def __init__(self, target="."):
        self.target = target
        if os.path.isfile(target) and target.lower().endswith(".mp3"):
            self._files = [target]
            self._total = len(scan(os.path.dirname(target) or "."))
        elif os.path.isdir(target):
            self._files = scan(target)
            self._total = len(self._files)
        else:
            raise ScanError(f"no such MP3 file or directory: {target}")
        self._selected = set()

    def files(self, sort_how=None):
        """Ordered inventory as a fresh list; with sort_how, a sorted COPY.

        Display concern only — never engine state.
        """
        return sort(self._files, sort_how) if sort_how else list(self._files)

    def selected(self):
        return [p for p in self._files if p in self._selected]

    def select_all(self):
        self._selected = set(self._files)

    def select(self, paths):
        unknown = [p for p in paths if p not in self._files]
        if unknown:
            raise ScanError(f"not in target scope: {unknown}")
        self._selected.update(paths)

    def clear(self):
        self._selected = set()

    def apply(self, changes, dry=False):
        """Apply `changes` to every selected file, one FileResult each.

        With dry=True nothing is written; files whose values already match
        come back as SKIPPED. A failing file never aborts the batch.
        """
        composed = self._compose_changes(changes)
        return [self._process(path, composed, dry) for path in self.selected()]

    def _process(self, path, composed, dry):
        try:
            old = metadata.read_tags(path)
            pending = {k: v for k, v in composed.items() if str(v) != old.get(k)}
            if not pending:
                return FileResult(path, Status.SKIPPED, "no changes needed")
            if not dry:
                metadata.apply_changes(path, pending)
            return FileResult(path, Status.CHANGED, _describe(old, pending))
        except BZTagError as e:
            return FileResult(path, Status.FAILED, str(e))

    def _compose_changes(self, changes):
        """Expand shorthand values before handing strings to core.

        track_number int 3 -> "3/<total>" where <total> is the MP3 count of
        the target directory; disc_number stays bare. The caller's dict is
        never mutated.
        """
        composed = dict(changes)
        if "track_number" in composed and isinstance(composed["track_number"], int):
            composed["track_number"] = f'{composed["track_number"]}/{self._total}'
        return composed


def _describe(old, new):
    """Render 'key: old -> new' lines for FileResult messages."""
    return "; ".join(f"{k}: {old.get(k)!r} -> {v!r}" for k, v in new.items())
