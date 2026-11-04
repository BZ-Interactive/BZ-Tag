# BZ Tag — Project requirements and development plan

Proposed project specification v1.0

BZ Tag will be a Python-based terminal MP3 tag editor with a three-column Urwid interface, built-in batch editing, automatic track numbering, and album artwork management.

The application will have two ways of operating:

- Interactive: Launch the TUI to browse, select, edit, preview, and apply changes.
- Command-line: Pass a directory and editing parameters to perform operations without opening the TUI.

Both will use the same underlying editing engine.

# 1. Core requirements

## File management

- Open the current working directory by default.
- Accept an optional directory argument.
- Discover MP3 files.
- Display file information and existing metadata.
- Select individual files or multiple files.
- Select all / deselect all.
- Support recursive directory scanning.
- Sort files naturally by filename.
- Support manual file ordering.
- Filter files using filename patterns.

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

Use Mutagen for ID3 reading and writing.

Preserve unknown and unsupported frames whenever possible.

## Artwork management

- Extract embedded album covers.
- Display covers in the TUI.
- Import JPG, PNG, and other supported image formats.
- Resize and convert images when needed.
- Embed artwork into MP3 files.
- Replace front covers without deleting unrelated artwork.
- Support files with no existing ID3 tags.

Initial rendering approach: Pillow + Unicode half-blocks, with optional terminal image protocols later.

## Track and disc numbering

Automatic track numbering is an initial-release feature.

- Natural filename sorting.
- Number according to the current visible file order.
- Start number configuration.
- Increment configuration.
- Track number and total count (`1/12`).
- Disc number and total count (`1/2`).
- Manual file reordering.
- Number selected files only.
- Preview before applying.

Example:

```
01.Intro.mp3       → TRCK 1/4
02.Track One.mp3   → TRCK 2/4
03.Track Two.mp3   → TRCK 3/4
04.Outro.mp3       → TRCK 4/4
```

The filename provides the initial ordering, but the actual result is written to the ID3 metadata. Renaming files is not required.

# 2. Application architecture

The application should have four main layers.

User interfaces

Urwid TUI

Interactive editing

CLI

Arguments and operations

Application layer

Selection, editing sessions, change plans, validation

Core editing engine

Scanning, metadata, artwork, sorting, numbering, saving

External libraries and filesystem

Mutagen · Pillow · term-image · pathlib

### Core engine

Responsible for:

- Reading and writing metadata.
- Artwork extraction and insertion.
- Directory scanning.
- Natural sorting.
- Track numbering.
- File validation.
- Safe saving.

No Urwid dependencies here.

### Application layer

Responsible for:

- Selected files.
- Pending changes.
- Mixed metadata values.
- Change plans.
- Preview generation.
- Validation.
- Coordinating saving.

### TUI

Responsible for presenting application state and handling user interaction.

### CLI

Responsible for argument parsing and invoking application operations. Batch operations use the same application and core functionality as the TUI.

# 3. Three-column TUI

The primary interface will consist of three columns.

BZ Tag

\~/Music/My Album

Files

12 files · 3 selected

☑ 01.Intro.mp3

☑ 02.Track.mp3

☑ 03.Theme.mp3

☐ 04.Outro.mp3

☐ 05.Bonus.mp3

...

Properties

3 selected

Album

My Album

Artist

Example Artist

Year

2026

Track

1/3 – 3/3

Artwork

cover.jpg

Changes

3 files

Album

My Album

Artist

Example Artist

Track numbers

1/3 – 3/3

Artwork

Replace front cover

Changes not yet saved

Cancel

Apply

Illustrative layout, not a functional editor.

| Column | Responsibilities                           |
| ------ | ------------------------------------------ |
| Left   | File browser, selection, sorting, ordering |
| Center | Metadata and artwork editor                |
| Right  | Pending changes, preview, Apply/Cancel     |

### Selection behavior

- One selected file: show its actual metadata.
- Multiple selected files: show common values or `<mixed>`.
- Editing a property: apply that change to the selected files.
- Selecting a different file: don't silently discard pending changes.
- Applying: save all pending changes.
- Cancelling: discard pending changes.

There is no separate per-file override mechanism. Selecting one file is how you edit it individually.

# 4. CLI design

This is the revised command-line convention.

The directory is always the first positional argument when supplied. Without editing parameters, the application launches the TUI.

`--all` means all discovered matching files in the specified directory are targets for the requested operations.

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
bztag ~/Music --all --set-cover cover.jpg

# Automatically number tracks
bztag ~/Music --all --auto-track

# Recursive processing
bztag ~/Music --all --recursive --auto-track

# Preview changes
bztag ~/Music --all --dry-run \
    --set-album "My Album"
```

## Proposed arguments

| Argument             | Purpose                                    |
| -------------------- | ------------------------------------------ |
| `directory`          | Optional target directory; defaults to CWD |
| `--all`              | Target every discovered matching file      |
| `-r`, `--recursive`  | Include subdirectories                     |
| `--pattern`          | Filter filenames                           |
| `--set-title`        | Set title                                  |
| `--set-artist`       | Set artist                                 |
| `--set-album`        | Set album                                  |
| `--set-album-artist` | Set album artist                           |
| `--set-year`         | Set year                                   |
| `--set-genre`        | Set genre                                  |
| `--set-cover`        | Assign artwork                             |
| `--auto-track`       | Generate track numbering                   |
| `--dry-run`          | Preview without writing                    |
| `--yes`              | Skip confirmation prompts                  |
| `--help`             | Show usage                                 |
| `--version`          | Show version                               |

Additional metadata arguments can be added later.

### CLI behavior rules

1. `bztag` launches the TUI in the current directory.
2. `bztag ~/Music` launches the TUI in that directory.
3. `bztag ~/Music --all --set-album "Album"` performs a non-interactive batch operation.
4. `--all` without an operation must not modify anything.
5. Batch mode must report how many files were found, changed, skipped, and failed.
6. `--dry-run` must never modify files.
7. `--pattern` filters the discovered files before `--all` selects them.

I'd use `argparse`, which is already included in Python.

# 5. Project file structure

This is the structure I'd settle on for the rewrite.

```
bz-tag/
│
├── pyproject.toml
├── README.md
├── LICENSE
├── .gitignore
│
├── src/
│   └── bz_tag/
│       │
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       ├── app.py
│       │
│       ├── core/
│       │   ├── __init__.py
│       │   ├── scanner.py
│       │   ├── metadata.py
│       │   ├── artwork.py
│       │   ├── sorting.py
│       │   ├── numbering.py
│       │   └── editor.py
│       │
│       ├── batch/
│       │   ├── __init__.py
│       │   └── processor.py
│       │
│       ├── ui/
│       │   ├── __init__.py
│       │   ├── app.py
│       │   ├── layout.py
│       │   ├── screens.py
│       │   ├── widgets.py
│       │   └── renderer.py
│       │
│       └── utils/
│           ├── __init__.py
│           ├── paths.py
│           └── logging.py
│
└── tests/
    ├── test_scanner.py
    ├── test_metadata.py
    ├── test_artwork.py
    ├── test_sorting.py
    ├── test_numbering.py
    ├── test_editor.py
    └── test_batch.py
```

### Module responsibilities

| Module         | Responsibility                           |
| -------------- | ---------------------------------------- |
| `cli.py`       | Parse command-line arguments             |
| `app.py`       | Application orchestration                |
| `scanner.py`   | Discover MP3 files                       |
| `metadata.py`  | Read and write ID3 tags                  |
| `artwork.py`   | Extract, process and embed artwork       |
| `sorting.py`   | Natural sorting and file ordering        |
| `numbering.py` | Track and disc numbering                 |
| `editor.py`    | Pending changes, change plans and saving |
| `processor.py` | Execute batch operations                 |
| `layout.py`    | Three-column Urwid layout                |
| `screens.py`   | TUI screens                              |
| `widgets.py`   | Reusable Urwid widgets                   |
| `renderer.py`  | Terminal image rendering                 |
| `paths.py`     | Path validation and handling             |
| `logging.py`   | Logging configuration                    |

# 6. Dependencies

| Package      | Purpose                    |
| ------------ | -------------------------- |
| `urwid`      | TUI framework              |
| `mutagen`    | MP3 and ID3 handling       |
| `Pillow`     | Image processing           |
| `term-image` | Terminal artwork rendering |
| `pytest`     | Testing                    |
| `build`      | Python package building    |

Python 3.11+ is my recommendation.

## Proposed `pyproject.toml`

```
[build-system]
requires = ["setuptools>=75"]
build-backend = "setuptools.build_meta"

[project]
name = "bz-tag"
version = "0.1.0"
description = "A terminal-based MP3 tag editor"
requires-python = ">=3.11"
dependencies = [
    "urwid",
    "mutagen",
    "Pillow",
    "term-image",
]

[project.scripts]
bztag = "bz_tag.cli:main"

[tool.setuptools.packages.find]
where = ["src"]
```

This supports both:

```
bztag
python -m bz_tag
```

# 7. Safety and reliability

These should be part of the core design rather than postponed until distribution.

- Never write changes immediately when a property is edited.
- Validate files before applying changes.
- Preserve unknown ID3 frames.
- Preserve unrelated artwork.
- Offer backups before modification.
- Report individual file failures.
- Avoid overwriting files changed externally since they were loaded.
- Support dry-run for batch operations.
- Don't promise atomic multi-file transactions; use backups and per-file success/failure reporting instead.

I'd also keep a clear distinction between a pending edit and a saved edit. The application should always know which state each file is in.

# 8. Development roadmap

I'd implement the project in this order:

1. Foundation and packaging
   - Create project structure.
   - Configure `pyproject.toml`.
   - Implement `cli.py` and `__main__.py`.
   - Get `bztag` working.
   - Test directory argument and current-directory behavior.
2. MP3 backend
   - Scan directories.
   - Read ID3 tags.
   - Modify common metadata.
   - Save tags.
   - Preserve unsupported frames.
3. Artwork handling
   - Extract embedded covers.
   - Load external images.
   - Resize and convert artwork.
   - Embed and replace front covers.
   - Preserve other APIC frames.
4. Editing engine
   - File selection model.
   - Multi-file editing.
   - Mixed property values.
   - Pending change plans.
   - Preview and Apply/Cancel.
5. Batch processing
   - `--all` operations.
   - Directory and recursive scanning.
   - Filename filtering.
   - Automatic track numbering.
   - Dry-run and reporting.
6. Urwid interface
   - Three-column layout.
   - File browser and selection.
   - Metadata editor.
   - Artwork preview.
   - Pending changes preview.
   - Keyboard navigation and shortcuts.
7. Testing and distribution
   - Test malformed and partially tagged MP3s.
   - Test artwork and numbering.
   - Test batch failures and recovery.
   - Publish to PyPI.
   - Install through pipx.
   - Consider PyInstaller binaries later.

# 9. Final project decisions

| Category           | Decision                          |
| ------------------ | --------------------------------- |
| Language           | Python                            |
| Minimum Python     | 3.11                              |
| TUI                | Urwid                             |
| Metadata           | Mutagen                           |
| Image processing   | Pillow                            |
| Image rendering    | term-image / half-block           |
| CLI                | argparse                          |
| Architecture       | Shared editing engine             |
| Main interface     | Three-column TUI                  |
| Batch editing      | Built-in CLI operations           |
| Default directory  | Current working directory         |
| Target selection   | `--all`                           |
| Recursive scanning | `--recursive`                     |
| Track ordering     | Natural filename order by default |
| Track numbering    | Automatic and previewable         |
| Package name       | `bz-tag`                          |
| Import name        | `bz_tag`                          |
| Executable         | `bztag`                           |
| Distribution       | PyPI + pipx                       |

## My recommended starting point

Don't implement the entire structure immediately. Start with these files:

```
bz-tag/
├── pyproject.toml
└── src/
    └── bz_tag/
        ├── __init__.py
        ├── __main__.py
        ├── cli.py
        └── core/
            ├── __init__.py
            ├── scanner.py
            └── metadata.py
```

Get directory scanning and metadata reading/writing working first. Add modules as their responsibilities become necessary.

This is the foundation I'd use for the full BZ Tag rewrite: a reliable MP3 editing engine first, a batch-capable CLI, and the three-column Urwid interface on top.
