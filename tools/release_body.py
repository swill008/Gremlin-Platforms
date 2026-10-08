# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Builds a GitHub release's text from release-notes/<version>.md.

Usage: python tools/release_body.py <version> [--out FILE] [--notes-dir DIR]

The text is the notes file followed by "## How to install". Exits 1 with a
message when the notes file is missing or doesn't start with
"## What's new in <version>" (D-REL-NOTES-FILES). Used by
.github/workflows/release-exe.yml.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

NOTES_DIR = Path(__file__).resolve().parent.parent / "release-notes"


class ReleaseNotesError(Exception):
    """The notes file for a version is missing or malformed."""


def install_text(version: str) -> str:
    name = f"Gremlin-Platforms-R1-{version}"
    return (
        "## How to install\n"
        "\n"
        f"- Installer: run {name}-Setup.exe. It installs for your Windows user"
        " only (no administrator rights) and installed copies update themselves"
        " from Help -> Check for Updates.\n"
        f"- Portable: unzip {name}.zip anywhere (Documents, Desktop, etc), not"
        " in Program Files, and run gremlin_platforms.exe. A portable copy"
        " tells you about new versions but does not update itself.\n"
        "- Requires vJoy already installed.\n"
        "- Unsigned build: SmartScreen may warn on first run"
        " (More info -> Run anyway).\n"
    )


def build_body(version: str, notes_dir: Path = NOTES_DIR) -> str:
    path = Path(notes_dir) / f"{version}.md"
    if not path.is_file():
        raise ReleaseNotesError(
            f"No release notes for {version}: add release-notes/{version}.md"
            f" (looked for {path})."
        )
    notes = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    heading = f"## What's new in {version}"
    first = notes.lstrip("\n").split("\n", 1)[0].rstrip()
    if first != heading:
        raise ReleaseNotesError(
            f"release-notes/{version}.md must start with '{heading}' (found '{first}')."
        )
    return notes.strip() + "\n\n" + install_text(version)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("version")
    parser.add_argument("--out", type=Path, help="write here instead of stdout")
    parser.add_argument("--notes-dir", type=Path, default=NOTES_DIR)
    args = parser.parse_args(argv)
    try:
        body = build_body(args.version, args.notes_dir)
    except ReleaseNotesError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    if args.out:
        args.out.write_text(body, encoding="utf-8", newline="\n")
    else:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        sys.stdout.write(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
