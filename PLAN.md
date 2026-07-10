# BZ-Tag — MP3 Tag Editor

A 3-pane TUI MP3 tag editor in Python using **Textual** + **Mutagen**. Single focus: MP3 files. Multi-file package structure.

## UI Layout

```
+--------------+-------------------+-----------------------+
|  Tree View   |    File List      |     Tag Editor        |
|              |                   |                       |
| ~/Music/     | [x] song1.mp3    | Title:  [________]    |
|   +-- Rock/  | [x] song2.mp3    | Artist: [________]    |
|   +-- Pop/ <-| [ ] song3.mp3    | Album:  [________]    |
|   +-- Jazz/  |   song4.mp3      | Year:   [____]        |
|              |                   | Genre:  [________]    |
|              |                   | Track:  [_/_]         |
|              |                   | Disc:   [_/_]         |
|              |                   | Comment:[________]    |
|              |                   | +--------------+      |
|              |                   | | [Cover Art]  |      |
|              |                   | +--------------+      |
|              |                   |                       |
|              |                   | [Apply] [Batch...]    |
+--------------+-------------------+-----------------------+
 Status: 2 files selected | Folder: ~/Music/Rock/
```

## Rename Pattern

Default: `{track}-{title}.mp3` (e.g., `01-Bohemian Rhapsody.mp3`)

Configurable via pattern field in UI. Tokens: `{track}`, `{title}`, `{artist}`, `{album}`, `{year}`, `{genre}`

## Track Ordering

Auto-number by filename sort order. Sequential numbering (01, 02, 03...). Configurable starting number.

## File Structure

```
BZ-Tag/
├── main.py                 # Entry point
├── requirements.txt        # textual, mutagen
└── bztag/
    ├── __init__.py
    ├── app.py              # Main App, 3-pane layout, keybindings
    ├── models.py           # SongFile, TagData dataclasses
    ├── tree_view.py        # Left: directory tree
    ├── file_list.py        # Center: MP3 list with checkboxes
    ├── tag_editor.py       # Right: tag form + cover art + actions
    ├── batch.py            # Batch logic: reorder, rename, bulk edit
    ├── cover_art.py        # Embed cover art into MP3
    └── utils.py            # Mutagen read/write helpers, pattern parser
```

## Tag Data Model

```python
@dataclass
class TagData:
    title: str
    artist: str
    album: str
    album_artist: str
    year: str
    genre: str
    track: str
    track_total: str
    disc: str
    disc_total: str
    comment: str
    cover_data: bytes | None
    cover_mime: str | None
```

## Implementation Phases

| #  | Phase           | Key Files             | What It Does                                      |
|----|-----------------|-----------------------|---------------------------------------------------|
| 1  | Setup           | requirements.txt, __init__, models | Package skeleton, data models        |
| 2  | Tag I/O         | utils.py              | Read/write ID3 tags with Mutagen, pattern parser  |
| 3  | App Shell       | app.py                | Textual app with 3-pane CSS layout                |
| 4  | Tree View       | tree_view.py          | Directory browser, selects working folder         |
| 5  | File List       | file_list.py          | Lists MP3s in folder, multi-select checkboxes     |
| 6  | Tag Editor      | tag_editor.py         | Shows/edits tags, cover art display               |
| 7  | Tag Writing     | app.py + utils.py     | Apply button writes changes back to files         |
| 8  | Batch Edit      | batch.py              | Set same tag value across multiple files          |
| 9  | Track Ordering  | batch.py              | Auto-number tracks by filename sort               |
| 10 | Rename Files    | batch.py + utils.py   | Rename MP3s from tag pattern, preview before      |
| 11 | Cover Art       | cover_art.py          | Pick image, embed into selected MP3s              |
| 12 | Preview Modal   | app.py                | Before/after confirmation for batch ops           |
| 13 | Polish          | all                   | Keyboard shortcuts, error handling, status bar    |

## UX Details

- **Single file selected**: form shows that file's tags, editable
- **Multiple files selected**: common values shown, blank = differs. Editing applies to all selected.
- **Rename preview**: modal showing old name -> new name per file
- **Track reorder preview**: modal showing current order -> new numbered order
- **All batch ops**: confirmation dialog before writing
