from . import __version__
import argparse


def _add_base_args(parser):
    parser.add_argument("directory",
                        nargs="?",
                        default=".",
                        help="Directory containing MP3 files")
    parser.add_argument("--version",
                        action="version",
                        version=f"%(prog)s {__version__}",
                        help="Print installed version.")
    parser.add_argument("--all",
                        action="store_true",
                        help="Select all discovered files")
    parser.add_argument("--auto-number",
                        action="store_true",
                        help="Automatically number tracks")
    parser.add_argument("--dry-run",
                        action="store_true",
                        help="Runs the command without applying changes.")


def _add_edit_args(parser):
    parser.add_argument("--set-filename",
                        metavar="NAME",
                        type=str,
                        help="Sets filename.")
    parser.add_argument("--set-title",
                        metavar="TITLE",
                        type=str,
                        help="Sets track title.")
    parser.add_argument("--set-artist",
                        metavar="ARTIST",
                        type=str,
                        help="Sets artist name.")
    parser.add_argument("--set-album",
                        metavar="ALBUM",
                        type=str,
                        help="Sets album name.")
    parser.add_argument("--set-art",  # gets file path as an argument
                        metavar="FILEPATH",
                        type=str,
                        help="Sets album cover.")
    parser.add_argument("--set-track-number",
                        metavar="NUMBER",
                        type=int,
                        help="Sets track number.")
    parser.add_argument("--set-year",
                        metavar="YEAR",
                        type=int,
                        help="Sets track year.")


def main(args=None):
    parser = argparse.ArgumentParser(
        prog="bztag",
        description="A terminal-based MP3 tag editor"
        )
    _add_base_args(parser)
    _add_edit_args(parser)
    args = parser.parse_args(args)

    if args.all:
        print("All files will be processed.")
    else:
        print("Single selection mode.")
