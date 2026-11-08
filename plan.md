# BZ Tag — Project specification and development plan

Specification v2.0

BZ Tag is a Python-based MP3 metadata editor. The editing engine is the product; the
CLI, batch driver, and TUI are adapters around it. The same engine must be usable
without a terminal UI.

The application has two ways of operating:

- **Interactive**: launch the TUI to browse, select, edit, preview, and apply changes.
- **Command-line**: pass a directory and editing parameters to perform operations
  without opening the TUI.

Both use the same application layer and core editing engine.

# 1. Core requirements

## File management

- Open the current working directory by default.
- Accept an optional directory argument.
- Discover MP3 files in that directory.
- Display file information and existing metadata.
- Select individual files or multiple files.
- Select all / deselect all.
- Sort files by filename or by ID3 track number.
- Support manual file ordering.
- Filter files using filename patterns.
- Recursive scanning is **not** supported. Only the target directory is scanned.

## Sorting

Sorting is intentionally simple. There are two plain sort keys:

- **Filename**: case-insensitive comparison of the filename. Zero-padded names such
  as `01.name.mp3` and `02.other.mp3` sort as expected.
- **Track number**: read `TRCK` from ID3 and compare the `N` part of `N/T`.

Files with a missing or unparseable `TRCK` are sorted after tagged files, then by
filename. There is no natural sort, locale-aware ordering, or tag-based fallback.

Filename order is the default. The TUI can switch to track order later using the same
two core sorting functions. There is no `--sort` CLI flag.

## Metadata editing

Support the most popular ID3 properties:

| Property     | ID3 frame | Priority  |
| ------------ | --------- | --------- |
| Title        | `TIT2`    | Essential |
| Artist       | `TPE1`    | Essential |
| Album        | `TALB`    | Essential |
| Album Artist | `TPE2`    | Essential |
| Track Number | `TRCK`    | Essential |
| Disc Number  | `TPOS`    | Essential |
| Year / Date  | `TDRC`    | Essential |
| Genre        | `TCON`    | Essential |
| Composer     | `TCOM`    | Useful    |
| Comment      | `COMM`    | Useful    |
| Lyrics       | `USLT`    | Later     |
| Copyright    | `TCOP`    | Later     |
| Publisher    | `TPUB`    | Later     |
| BPM          | `TBPM`    | Later     |
| Artwork      | `APIC`    | Essential |

Use Mutagen for ID3 reading and writing. Preserve unknown and unsupported frames
whenever possible.

### Track and disc number values

Track and disc numbers are always expressed as `N/T` (number over total).

- `TRCK` and `TPOS` values must include both parts, for example `3/12`.
- A bare number such as `3` is not accepted.
- Automatic numbering writes `N/T` using the target file count as `T`.

## Artwork management

- Extract embedded album covers.
- Display covers in the TUI.
- Import JPG, PNG, and other supported image formats.
- Resize and convert images when needed.
- Embed artwork into MP3 files.
- Replace front covers without deleting unrelated artwork.
- Support files with no existing ID3 tags.

Initial rendering approach: Pillow + Unicode half-blocks, with optional terminal
image protocols later.

## Track and disc numbering

Automatic track numbering is an initial-release feature.

- Number according to the current visible file order (filename or track).
- Start number configuration.
- Increment configuration.
- Track number and total count always written as `N/T`.
- Disc number and total count always written as `N/T`.
- Manual file reordering.
- Number selected files only.
- Preview before applying.

### Filename padding

Track numbers used in filenames are zero-padded according to the highest generated
number:

```python
width = len(str(start + (count - 1) * increment))
label = str(number).zfill(width)
```

| Files | Start | Increment | Highest | Width | Names              |
| ----- | ----- | --------- | ------- | ----- | ------------------ |
| 9     | 1     | 1         | 9       | 1     | `1` ... `9`        |
| 11    | 1     | 1         | 11      | 2     | `01` ... `11`      |
| 100   | 1     | 1         | 100     | 3     | `001` ... `100`    |
| 4     | 8     | 1         | 11      | 2     | `08`, `09`, `10`, `11` |

Padding applies to filenames only. `TRCK` and `TPOS` remain unpadded `N/T` values such
as `1/11` and `2/11`.

Example:

```
1.Intro.mp3       → TRCK 1/4
2.Track One.mp3   → TRCK 2/4
3.Track Two.mp3   → TRCK 3/4
4.Outro.mp3       → TRCK 4/4
```

The filename provides the initial ordering, but the result is written to the ID3
metadata. Renaming files is not required.

# 2. Architecture

BZ Tag is an MP3 metadata editor first. The terminal interface is one adapter among
several.

```
cli.py ─────────────┐
ui/tui.py ──────────┼─→ app.py ─→ core/
batch driver ───────┘        ↑
                    models.py
```

Dependency direction is always inward: frontends depend on the application layer,
the application layer depends on the core, and `models.py` is the shared dependency
root with no imports from the rest of the package.

- `core/` never imports `app`, `cli`, `ui`, or any frontend code.
- `ui/` never imports Mutagen and never performs edits.
- `app.py` owns application decisions: selected files, pending changes, apply/cancel,
  and which frontend runs.
- `cli.py` maps argv to an `EditRequest`; it does not decide what happens next.

## Layers

| Layer | Responsibility |
| ----- | -------------- |
| Frontends | `cli.py` argument parsing; `ui/` rendering and key handling |
| Application | `app.py`: request building, `EditorSession`, apply/cancel, dispatch |
| Shared models | `models.py`: request and result dataclasses |
| Core engine | scanning, sorting, metadata, numbering, artwork, per-file editing |
| External | Mutagen, Pillow, term-image, filesystem |

## Application flow

```
bztag [args]
  → cli.parse_args(argv) → Namespace
  → app.main(argv)
      → app.build_request(namespace) → EditRequest
      → session = app.EditorSession(request)
      → if request.is_batch: session.apply() + report results
      → else: ui.tui.run(session)
```

Batch mode is not a separate layer. It is the same `EditorSession.apply()` loop used
by the TUI's Apply action:

```python
for path in session.files():
    results.append(core.editor.apply(path, request))
```

## Shared application object

`app.EditorSession` is used by both batch and TUI:

```python
class EditorSession:
    def __init__(self, request: EditRequest): ...
    def files(self) -> list[Path]: ...
    def selected(self) -> set[Path]: ...
    def select(...): ...
    def select_all(self): ...
    def clear_selection(self): ...
    def set_changes(self, changes: MetadataChanges) -> None: ...
    def preview(self) -> list[FileResult]: ...
    def apply(self) -> list[FileResult]: ...
    def cancel(self) -> None: ...
```

`ui.tui.run(session)` only renders session state and calls these methods. It makes no
file or metadata decisions.

## Shared models

`models.py` contains immutable request and result types:

- `FileTargets`: directory, `--all`, explicit files, pattern.
- `MetadataChanges`: title, artist, album, album artist, track, disc, year, genre,
  composer, comment, art.
- `NumberingOptions`: enabled, start, increment.
- `RenameOptions`: template.
- `EditRequest`: the complete UI-independent request.
- `FileResult`: path, status (`changed`, `skipped`, `failed`), message.
- `RequestError`: invalid request/configuration.

## Error handling

`core/errors.py` contains expected, recoverable domain failures. `EditorSession.apply()`
catches `BZTagError` per file and converts it into a `FileResult`; anything not derived
from it is treated as a bug and allowed to propagate.

```python
class BZTagError(Exception):
    """Base for expected domain failures. Carries an optional path."""

class ScanError(BZTagError): ...
class UnsupportedFileError(ScanError): ...
class MetadataError(BZTagError): ...
class TagReadError(MetadataError): ...
class TagWriteError(MetadataError): ...
class ArtworkError(BZTagError): ...
class RenameError(BZTagError): ...
class FileChangedError(BZTagError): ...
```

- CLI usage errors use `argparse` errors, not exceptions from `core`.
- Invalid requests use `models.RequestError`.
- Artwork and file-changed errors are added when those features land.

# 3. CLI design

The directory is always the first positional argument when supplied. Without editing
parameters, the application launches the TUI.

`--all` means all discovered matching files in the specified directory are targets for
the requested operations. Additional files can be targeted explicitly with `--file`.

## Basic usage

```
# TUI in current working directory
bztag

# TUI in a specified directory
bztag ~/Music

# Help and version
bztag --help
bztag --version
```

## Editing all files

```
# Set album
bztag . --all --set-album "My Album"

# Set artist
bztag ~/Music --all --set-artist "Example Artist"

# Multiple properties
bztag ~/Music --all \
    --set-album "My Album" \
    --set-artist "Example Artist" \
    --set-year 2026

# Assign cover artwork
bztag ~/Music --all --set-art cover.jpg

# Automatically number tracks
bztag ~/Music --all --auto-number

# Preview changes
bztag ~/Music --all --dry-run --set-album "My Album"
```

## Target selection

| Argument      | Purpose                                    |
| ------------- | ------------------------------------------ |
| `directory`   | Optional target directory; defaults to CWD |
| `--all`       | Target every discovered matching file      |
| `--file PATH` | Target a specific file; may be repeated    |
| `--pattern`   | Filter filenames used by `--all`           |

Targets are the union of explicit `--file` paths and, when `--all` is set, all
discovered files matching `--pattern`. Recursive scanning is not supported.

## Metadata arguments

| Argument             | Purpose                    |
| -------------------- | -------------------------- |
| `--set-title`        | Set title                  |
| `--set-artist`       | Set artist                 |
| `--set-album`        | Set album                  |
| `--set-album-artist` | Set album artist           |
| `--set-track-number` | Set track number as `N/T`  |
| `--set-disc-number`  | Set disc number as `N/T`   |
| `--set-year`         | Set year                   |
| `--set-genre`        | Set genre                  |
| `--set-composer`     | Set composer               |
| `--set-comment`      | Set comment                |
| `--set-art FILEPATH` | Assign front cover artwork |

## Numbering arguments

| Argument         | Purpose                              |
| ---------------- | ------------------------------------ |
| `--auto-number`  | Generate `N/T` track numbering       |
| `--start-number` | First number used by `--auto-number` |
| `--increment`    | Step between generated numbers       |

## Rename argument

| Argument            | Purpose                                        |
| ------------------- | ---------------------------------------------- |
| `--rename TEMPLATE` | Rename files using a template with placeholders |

Supported tokens: `{track}`, `{disc}`, `{title}`, `{artist}`, `{album}`,
`{album_artist}`, `{year}`, `{genre}`, `{ext}`. Format specifiers such as `:02d` are
not supported; `{track}` always uses the automatic padding width described above.
`{disc}` and `{year}` are not auto-padded. `{ext}` is the extension without the dot.

Renaming happens only when `--rename` is supplied; `--auto-number` does not rename
files on its own. Renaming happens after metadata changes; `.mp3` is appended when the
rendered name has no extension; collisions and invalid names are rejected unless
`--yes` is supplied.

Examples:

```
9 files:   --rename "{track}.{title}" → 1.name.mp3
11 files:  --rename "{track}.{title}" → 01.name.mp3, 02.other.mp3, ... 11.last.mp3
```

Renaming is fully specified here and must be implemented before the first release. The
first implementation pass accepts and validates `--rename`, but applying it returns a
clear `RenameError("renaming is not implemented yet")` instead of silently ignoring the
request.

## Output and safety arguments

| Argument    | Purpose                   |
| ----------- | ------------------------- |
| `--dry-run` | Preview without writing   |
| `--yes`     | Skip confirmation prompts |
| `--quiet`   | Reduce output             |
| `--verbose` | Increase output           |
| `--help`    | Show usage                |
| `--version` | Show version              |

## CLI behavior rules

1. `bztag` launches the TUI in the current directory.
2. `bztag ~/Music` launches the TUI in that directory.
3. `bztag ~/Music --all --set-album "Album"` performs a non-interactive batch operation.
4. `--all` without an operation must not modify anything.
5. A batch operation requires at least one target via `--all` or `--file`.
6. Batch mode reports how many files were found, changed, skipped, and failed.
7. `--dry-run` must never modify files.
8. `--pattern` filters the discovered files before `--all` selects them.
9. Track and disc number arguments accept only `N/T`.
10. `--start-number` and `--increment` require `--auto-number`.
11. `--auto-number` only writes tags; renaming requires `--rename`.

# 4. TUI

The primary interface is a three-column Urwid layout.

| Column | Responsibilities                           |
| ------ | ------------------------------------------ |
| Left   | File browser, selection, sorting, ordering |
| Center | Metadata and artwork editor                |
| Right  | Pending changes, preview, Apply/Cancel     |

`ui/` contains presentation only:

- `tui.py`: event loop and wiring; `run(session)`.
- `layout.py`: three-column layout.
- `screens.py`: screens.
- `widgets.py`: reusable Urwid widgets.
- `renderer.py`: terminal image rendering.

### Selection behavior

- One selected file: show its actual metadata.
- Multiple selected files: show common values or `<mixed>`.
- Editing a property: apply that change to the selected files.
- Selecting a different file: don't silently discard pending changes.
- Applying: save all pending changes through `EditorSession.apply()`.
- Cancelling: discard pending changes through `EditorSession.cancel()`.

There is no separate per-file override mechanism. Selecting one file is how you edit it
individually.

# 5. Project file structure

```
bz-tag/
│
├── pyproject.toml
├── README.md
├── LICENSE
├── .gitignore
│
├── src/
│   └── bztag/
│       ├── __init__.py
│       ├── __main__.py       # raise SystemExit(app.main())
│       ├── cli.py            # argparse adapter only
│       ├── app.py            # main(), build_request(), EditorSession
│       ├── models.py         # shared request/result dataclasses
│       │
│       ├── core/
│       │   ├── __init__.py
│       │   ├── errors.py
│       │   ├── sorting.py
│       │   ├── scanner.py
│       │   ├── metadata.py
│       │   ├── numbering.py
│       │   ├── artwork.py
│       │   └── editor.py
│       │
│       └── ui/
│           ├── __init__.py
│           ├── tui.py
│           ├── layout.py
│           ├── screens.py
│           ├── widgets.py
│           └── renderer.py
│
└── tests/
    ├── test_cli.py
    ├── test_models.py
    ├── test_sorting.py
    ├── test_scanner.py
    ├── test_metadata.py
    └── test_editor.py
```

There is no separate `batch/` package; batch mode is `EditorSession.apply()` plus a
reporting function. There is no `utils/` package until a concrete shared helper exists.

## Module responsibilities

| Module         | Responsibility                                        |
| -------------- | ----------------------------------------------------- |
| `cli.py`       | Build the parser, parse values, return raw arguments  |
| `app.py`       | Entry point, request building, session, dispatch      |
| `models.py`    | Shared dataclasses and request invariants             |
| `errors.py`    | Expected domain exceptions                            |
| `sorting.py`   | Filename and ID3 track-number sorting                 |
| `scanner.py`   | Discover MP3 files, filter patterns, dedupe targets   |
| `metadata.py`  | Read and write ID3 tags, preserve unknown frames      |
| `numbering.py` | Compute track and disc `N/T` assignments              |
| `artwork.py`   | Extract, process and embed artwork                    |
| `editor.py`    | Apply changes to individual files; return `FileResult`|
| `tui.py`       | Terminal event loop and session wiring                |
| `layout.py`    | Three-column Urwid layout                             |
| `screens.py`   | TUI screens                                           |
| `widgets.py`   | Reusable Urwid widgets                                |
| `renderer.py`  | Terminal image rendering                              |

# 6. Dependencies

| Package      | Purpose                    |
| ------------ | -------------------------- |
| `urwid`      | TUI framework              |
| `mutagen`    | MP3 and ID3 handling       |
| `Pillow`     | Image processing           |
| `term-image` | Terminal artwork rendering |

Python 3.10+ is the configured minimum. Tests use the standard library `unittest`
initially; pytest can be added later.

## `pyproject.toml`

```
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "bz-tag"
version = "0.1.0"
description = "A terminal-based MP3 tag editor"
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
    "urwid",
    "mutagen",
    "pillow",
    "term-image",
]

[project.scripts]
bztag = "bztag.app:main"

[tool.hatch.build]
dev-mode-dirs = ["src"]

[tool.hatch.build.targets.wheel]
packages = ["src/bztag"]
```

This supports both:

```
bztag
python -m bztag
```

# 7. Safety and reliability

- Never write changes immediately when a property is edited.
- Validate files before applying changes.
- Preserve unknown ID3 frames.
- Preserve unrelated artwork.
- Offer backups before modification.
- Report individual file failures.
- Avoid overwriting files changed externally since they were loaded.
- Support dry-run for batch operations.
- Don't promise atomic multi-file transactions; use backups and per-file success/failure
  reporting instead.

Keep a clear distinction between a pending edit and a saved edit. The application must
always know which state each file is in.

# 8. Development roadmap

1. **Foundation and separation**
   - Scaffold `core/` and `ui/`.
   - Add `models.py` and `core/errors.py`.
   - Rewrite `cli.py` as a parser-only adapter.
   - Add `app.py` with `main()`, `build_request()`, and `EditorSession`.
   - Switch the executable entry point to `bztag.app:main`.
   - Add unit tests for parsing and models.

2. **Core foundation**
   - Filename and track-number sorting.
   - Directory scanning and pattern filtering.
   - ID3 reading and writing with frame preservation.
   - Track/disc `N/T` numbering.
   - Per-file metadata editing with dry-run.
   - Unit tests for each core module.

3. **Artwork handling**
   - Extract embedded covers.
   - Load external images.
   - Resize and convert artwork.
   - Embed and replace front covers.
   - Preserve other APIC frames.

4. **Rename support (before 1st release)**
   - Rename templates and token rendering.
   - Automatic filename padding.
   - Target planning, collision detection, and invalid-name rejection.
   - `--rename` behavior and tests.
   - `--auto-number` remains tag-only; renaming requires `--rename`.

5. **Batch driver and reporting**
   - `EditorSession.apply()` used from the CLI.
   - Found/changed/skipped/failed counts.
   - `--dry-run` and `--yes` behavior.
   - Per-file failure reporting.

6. **Urwid interface**
   - Three-column layout.
   - File browser and selection.
   - Metadata editor.
   - Artwork preview.
   - Pending changes preview.
   - Keyboard navigation and shortcuts.

7. **Testing and distribution**
   - Test malformed and partially tagged MP3s.
   - Test artwork and numbering.
   - Test batch failures and recovery.
   - Publish to PyPI.
   - Install through pipx.
   - Consider PyInstaller binaries later.

### First implementation pass

The first pass covers steps 1 and 2, excluding artwork and renaming. `--set-art` and
`--rename` parse and validate, but applying them returns clear `ArtworkError` and
`RenameError` results respectively until those features are implemented, rather than
silently ignoring the requests. `ui/tui.py` remains a stub.

# 9. Final project decisions

| Category           | Decision                          |
| ------------------ | --------------------------------- |
| Language           | Python                            |
| Minimum Python     | 3.10                              |
| TUI                | Urwid                             |
| Metadata           | Mutagen                           |
| Image processing   | Pillow                            |
| Image rendering    | term-image / half-block           |
| CLI                | argparse                          |
| Architecture       | Core engine plus thin adapters    |
| Main interface     | Three-column TUI                  |
| Batch editing      | `EditorSession.apply()` loop      |
| Default directory  | Current working directory         |
| Target selection   | `--all` and repeatable `--file`   |
| Recursive scanning | Not supported                     |
| Track ordering     | Filename by default; TRCK order in TUI |
| Number format      | Always `N/T` in tags                |
| Filename padding   | Auto width from highest number      |
| Renaming           | Required before 1st release         |
| Track numbering    | Automatic and previewable         |
| Package name       | `bz-tag`                          |
| Import name        | `bztag`                           |
| Executable         | `bztag`                           |
| Distribution       | PyPI + pipx                       |
