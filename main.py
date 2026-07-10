#!/usr/bin/env python3
"""BZ-Tag: MP3 Tag Editor - Entry point."""

import argparse
import sys
from pathlib import Path

from bztag.app import BZTagApp

BASE_DIR = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="bztag",
        description="BZ-Tag: MP3 Tag Editor",
    )
    parser.add_argument(
        "path", nargs="?", default=None,
        help="Directory to open on launch",
    )
    parser.add_argument(
        "-f", "--file", default=None, metavar="FILE",
        help="MP3 file to select on launch",
    )
    parser.add_argument(
        "-d", "--debug", action="store_true",
        help="Show debug console",
    )
    parser.add_argument(
        "-l", "--license", action="store_true",
        help="Print MIT license and exit",
    )
    parser.add_argument(
        "--logo", "--splash", action="store_true",
        help="Print ASCII art logo and exit",
    )
    args = parser.parse_args()

    if args.license:
        license_path = BASE_DIR / "LICENSE"
        if license_path.exists():
            print(license_path.read_text())
        else:
            print("LICENSE file not found.")
        sys.exit(0)

    if args.logo:
        logo_path = BASE_DIR / "bz-tag_logo.ansi"
        if logo_path.exists():
            print(logo_path.read_text())
        else:
            print("Logo file not found.")
        sys.exit(0)

    app = BZTagApp(debug=args.debug, path=args.path, file_path=args.file)
    app.run()


if __name__ == "__main__":
    main()
