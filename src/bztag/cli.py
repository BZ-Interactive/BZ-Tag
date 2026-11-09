import os
import sys
import argparse
from . import __version__
from .engine import Engine
from .core.bztagerror import ActionError, BZTagError


UNIMPLEMENTED_FLAGS = {
    "auto_number": "--auto-number",
    "rename": "--rename",
    "art": "--set-art",
}


def collect_unimplemented(args):
    """Flags parsed but not wired to any behavior yet (phases 3 and 4)."""
    return [flag for attr, flag in UNIMPLEMENTED_FLAGS.items()
            if getattr(args, attr)]


EDIT_DESTS = (
    "title",
    "artist",
    "album_artist",
    "composer",
    "album",
    "track_number",
    "disc_number",
    "year",
    "genre",
    "comment",
    "art",
)


def _add_base_args(parser):
    parser.add_argument("directory",
                        nargs="?",
                        default=".",
                        help="Directory containing MP3 files")
    parser.add_argument("--version", "-v",
                        action="version",
                        version=f"%(prog)s {__version__}",
                        help="Print installed version.")
    parser.add_argument("--tui",
                        action="store_true",
                        help="Starts TUI mode")
    parser.add_argument("--cli",
                        action="store_true",
                        help="Works in cli only mode")
    parser.add_argument("--all", "-a",
                        action="store_true",
                        help="Select all discovered files")
    parser.add_argument("--auto-number",
                        action="store_true",
                        help="Automatically number tracks based on name sort.")
    parser.add_argument("--rename",
                        metavar="FILENAME",
                        help="Sets filename.")
    parser.add_argument("--dry-run",
                        action="store_true",
                        help="Runs the command without applying changes.")


def _add_edit_args(parser):
    parser.add_argument("--set-title",
                        metavar="TITLE",
                        dest="title",
                        type=str,
                        help="Sets track title.")
    parser.add_argument("--set-artist",
                        metavar="ARTIST",
                        dest="artist",
                        type=str,
                        help="Sets artist name.")
    parser.add_argument("--set-album-artist",
                        metavar="ALBUM ARTIST",
                        dest="album_artist",
                        type=str,
                        help="Sets album artist.")
    parser.add_argument("--set-composer",
                        metavar="COMPOSER",
                        dest="composer",
                        type=str,
                        help="Sets composer.")
    parser.add_argument("--set-album",
                        metavar="ALBUM",
                        dest="album",
                        type=str,
                        help="Sets album name.")
    parser.add_argument("--set-track-number",
                        metavar="NUMBER",
                        dest="track_number",
                        type=int,
                        help="Sets track number. Input an int, format: N/T")
    parser.add_argument("--set-disc-number",
                        metavar="NUMBER",
                        dest="disc_number",
                        type=int,
                        help="Sets disc number.")
    parser.add_argument("--set-year",
                        metavar="YEAR",
                        dest="year",
                        type=int,
                        help="Sets track year.")
    parser.add_argument("--set-genre",
                        metavar="GENRE",
                        dest="genre",
                        type=str,
                        help="Sets genre.")
    parser.add_argument("--set-comment",
                        metavar="COMMENT",
                        dest="comment",
                        type=str,
                        help="Sets comment.")
    parser.add_argument("--set-art",  # gets file path as an argument
                        metavar="FILEPATH",
                        dest="art",
                        type=str,
                        help="Sets album cover.")


def resolve_mode(args) -> bool:
    if args.tui:
        print("TUI Mode active.")
        return True
    return False


def collect_edits(args):
    """Pick the --set-* flags that were supplied, as a changes dict."""
    return {dest: getattr(args, dest)
            for dest in EDIT_DESTS
            if getattr(args, dest) is not None}


def resolve_action(args):
    unimplemented = collect_unimplemented(args)
    if unimplemented:
        raise ActionError(f"not implemented yet: {', '.join(unimplemented)}")
    edits = collect_edits(args)
    if not edits:
        raise ActionError("no changes specified (e.g. --set-title)")

    target = args.directory
    is_file = os.path.isfile(target) and target.lower().endswith(".mp3")
    if not is_file and not args.all:
        raise ActionError("editing a directory requires --all")

    engine = Engine(target)
    results = engine.run(edits, select_all=args.all or is_file, dry=args.dry_run)

    tag = "(dry-run) " if args.dry_run else ""
    counts = {}
    for result in results:
        counts[result.status.value] = counts.get(result.status.value, 0) + 1
        print(f"{tag}{result.path}: {result.message}")
    print(f"{len(engine.files())} found, {counts.get('changed', 0)} changed, "
          f"{counts.get('skipped', 0)} skipped, {counts.get('failed', 0)} failed")


def handle_args(args):
    tui_mode = resolve_mode(args)
    if tui_mode:
        # TODO: launch tui here
        pass
    else:  # cli mode
        resolve_action(args)


def main(argv=None):
    supplied = sys.argv[1:] if argv is None else argv

    parser = argparse.ArgumentParser(
        prog="bztag",
        description="A terminal-based MP3 tag editor"
        )
    _add_base_args(parser)
    _add_edit_args(parser)

    args = parser.parse_args(argv)
    if not supplied:
        args.tui = True
    try:
        handle_args(args)
    except BZTagError as e:
        parser.error(str(e))
