# BZ Tag — Project plan (v3, simplified)

BZ Tag is a Python MP3 metadata editor. Editing work flows through one shared
`Engine`; both the CLI and the future TUI call into it. The spec favors a
simple, plain-function design over a heavy layered architecture.

# 1. Core requirements

## File management

- Target is a directory (recursive scanning is NOT supported) or a single MP3 file.
- Target may be omitted; it defaults to the current working directory.
- Discover `*.mp3` files in the target directory.
- Select one file, several files, or all files (`--all`).
- Sort by filename only (case-insensitive) for now; sort styles live in
  `core/sorter.py` so new ones (e.g. track number) can be added later.

## Metadata editing

Use Mutagen for ID3 reading and writing. Preserve unknown and unsupported frames.

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
| Artwork      | `APIC`    | Later     |

Changes are a plain dict of `{"album": "...", "track_number": 3, ...}`; only
keys present are written. `--dry-run` never writes; it shows old → new per file.

### Track and disc numbers

Users always type plain integers: `--set-track-number 3`, `--set-disc-number 2`.

- The Engine composes the ID3 values at apply time — users never type `N/T`.
- `track_number` int `3` → `TRCK = "3/T"`, where `T` is the total number of
  MP3 files in the target directory (deduced from the scan). For a single-file
  target, `T` is deduced by scanning that file's parent directory.
- `disc_number` int `2` → `TPOS = "2"` (bare number, no total part).
- `--auto-number` (later) writes `N/T` per file with the target count as `T`.
- Values in the `changes` dict stay plain ints; `metadata.apply_changes` only
  ever receives ready-to-write strings composed by the Engine.

# 2. Architecture

```
cli.py ──────→ engine.py ───────→ core/
  TUI later ──┘                   scanner.py  scan(directory) -> list[str]
                                  sorter.py   registered sort styles ("filename",
                                              "track_number" once metadata exists)
                                  metadata.py read_tags / apply_changes (mutagen)
                                  bztagerror.py BZTagError base + subclasses
```

- Frontends (cli, later ui/) only talk to `Engine`.
- `Engine` only talks to `core` functions.
- Core contains no frontend logic and is plain, importable, testable code.
- NO models.py, NO app.py, NO EditorSession — until the TUI actually needs them.

## engine.py

```python
@dataclass
class FileResult:
    path: str
    status: "Status"  # Status.CHANGED | SKIPPED | FAILED (enum in engine.py)
    message: str

class Engine:
    def __init__(self, target)                # directory or single .mp3
    def files(self, sort_how=None) -> list    # inventory copy; sorted copy for display
    def select_all() / select(paths) / clear()
    def apply(changes, dry=False) -> list[FileResult]
                                              # dry=True writes nothing;
                                              # one bad file does not stop the rest
```

- `changes` is a plain dict; FileResult is the only shared result type.
- Before delegating to `core.metadata`, `Engine` composes `track_number` int
  → `N/T` (string) using the deduced total; disc stays bare.
- Ordering: `apply()` always walks inventory (filename) order. `files(sort_how)`
  is a display-sorted COPY — sorting is visual only, never engine state.
- CLI creates an Engine per invocation and calls `apply(edits, dry=--dry-run)`
  immediately; the TUI will hold one Engine open, call `apply(..., dry=True)`
  for preview and `apply(...)` on confirmation.

## Error style

One base `BZTagError` (core/bztagerror.py) with a few subclasses as needed
(`ScanError`, `MetadataError`). Frontends catch it and report per file.

# 3. CLI design

## Mode resolution (the "user picks" rules)

| Invocation                        | Behavior                          |
| --------------------------------- | --------------------------------- |
| `bztag`                           | TUI in cwd                        |
| `bztag ~/Music`                   | TUI in ~/Music                    |
| `bztag ~/Music --all --set-*`     | batch: all MP3s in ~/Music        |
| `bztag song.mp3 --set-*`          | single-file edit                  |
| `bztag song.mp3` (no edits)       | error: "no changes specified"     |
| `bztag dir --set-*` (no --all)    | error: "editing a directory requires --all" |
| `--tui`                           | force TUI, even with editing args |

The `directory` positional is polymorphic: a directory (default `.`) or a
path ending in an MP3 file. Mode is `--tui` if forced, else batch when an
MP3 file or `--all` + edits are given, else TUI. Invalid/nonexistent targets
are argparse-level errors.

## Arguments

| Argument             | Purpose                    |
| -------------------- | -------------------------- |
| `directory`          | dir or .mp3 path (default `.`) |
| `--all`              | Target every discovered file (required for dir batch) |
| `--tui`              | Force interactive mode     |
| `--dry-run`          | Show old → new, write nothing |
| `--version` / `--help` | Meta                     |
| `--set-title`        | Title                      |
| `--set-artist`       | Artist                     |
| `--set-album`        | Album                      |
| `--set-album-artist` | Album artist               |
| `--set-track-number` | Track number (int; `N/T` composed by Engine) |
| `--set-disc-number`  | Disc number (int, written bare)            |
| `--set-year`         | Year (int)                 |
| `--set-genre`        | Genre                      |
| `--set-composer`     | Composer                   |
| `--set-comment`      | Comment                    |

Batch mode reports found / changed / skipped / failed counts and per-file
failures. Later: `--file`, `--pattern`, `--start-number` / `--increment`,
`--rename TEMPLATE`, `--set-art`, `--yes` / `--quiet` / `--verbose`.

## Deferred features (each = one core module + engine method later)

- `--auto-number` — track numbering, `N` part only, zero-padded in filenames
  only if `--rename` is used. Numbering order is ALWAYS the inventory
  (filename) order — deterministic, never the TUI's display sort; no
  `--sort` CLI flag.
- `--rename TEMPLATE` — tokens `{track} {disc} {title} {artist} {album} {ext}`;
  happens after metadata writes.
- `--set-art` / artwork — embed and replace front covers, preserve others.
- Sorting via `core/sorter.py`: `filename` (case-insensitive) is the only active
  style; `track_number` is registered as a skeleton until metadata exists.
  Filters and recursion — not planned.

# 4. TUI (later, after the CLI works)

Three-column layout, Urwid. Up to spec change; it only needs the Engine API
above: `files(sort_how=...)` for display (visual only), `selected()`,
`select*/clear`, and `apply(changes, dry=...)` for preview/confirmation.
Not designed in this plan.

# 5. Development phases

1. **Batch CLI slice (current)**
   - `core/bztagerror.py`, `core/scanner.py`, `core/metadata.py`, `engine.py`
   - `cli.py` mode dispatch + batch flow + dry-run + reports
   - tests: scanner + sorter, metadata round-trip + `N/T` validation,
     engine (selection/apply/dry/failure isolation), CLI flow + mode errors
2. **Polish** — malformed/partially tagged MP3s, failure reporting.
3. **Artwork** (`--set-art`) — extract, resize, embed, preserve others.
4. **Numbering + rename** — `--auto-number`, `--rename` with padding.
5. **TUI** — Urwid three-column, reusing `Engine`.

# 6. Dependencies

| Package   | Purpose              |
| --------- | -------------------- |
| `mutagen` | MP3 / ID3 handling   |
| `urwid`   | TUI (phase 5)        |
| `Pillow`  | artwork (phase 3)    |

Python 3.10+. Stdlib `unittest` for tests. Entry point stays
`bztag = "bztag.cli:main"`; supports `bztag` and `python -m bztag`.
Re-point the entry point only when the TUI lands and a shared layer is needed.

# 7. Safety and reliability

- `--dry-run` never writes.
- Per-file success/failure reporting; one bad file never aborts the batch.
- Preserve unknown ID3 frames and unrelated artwork.
- Keep pending edits distinct from saved edits (TUI concern, later).

| Decision         | Choice                  |
| ---------------- | ----------------------- |
| Language         | Python                  |
| CLI              | argparse                |
| Metadata         | Mutagen                 |
| Import / exe     | `bztag` / `bztag`       |
| Distribution     | PyPI later              |
