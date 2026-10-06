# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""A device's module file (its Button Map, claims, calibration and layout):
read it to change it, and write it safely.

A file that can't be read is never treated as empty: a save that would
replace it with a nearly empty file is refused (ModuleFileDamaged) and the
user is told. "Start Fresh" moves a damaged file aside, so nothing is lost.
Writes go to a temporary file that then replaces the real one, so a crash
or a full disk can't leave half a file.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from gremlin.error import GremlinError


class ModuleFileDamaged(GremlinError):
    """The module file exists but can't be read; it is left untouched."""

    def __init__(self, path: Path, reason: str) -> None:
        super().__init__(f"{path}: {reason}")
        self.path = Path(path)
        self.reason = reason


def damage_reason(path: Path) -> str:
    """Why the module file can't be read, or "" (missing or fine)."""
    path = Path(path)
    if not path.is_file():
        return ""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        return f"it can't be read ({e})"
    try:
        doc = json.loads(text)
    except ValueError as e:
        return f"it is not valid JSON ({e})"
    if not isinstance(doc, dict):
        return "it is not a module file"
    return ""


def load_for_update(path: Path) -> dict:
    """The module file's content to change and write back: {} when there is
    no file yet. Raises ModuleFileDamaged when it exists but can't be read."""
    path = Path(path)
    if not path.is_file():
        return {}
    reason = damage_reason(path)
    if reason:
        raise ModuleFileDamaged(path, reason)
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(
    path: Path, text: str, encoding: str = "utf-8", newline: str | None = None
) -> None:
    """Writes the whole file safely: a temporary file, then a swap. A crash
    mid-write leaves the old file whole. Also used for profiles (with a BOM
    and their line ends kept: encoding "utf-8-sig", newline "")."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Tools > History: a module file's save is kept (other files are not).
    from gremlin import history_modules

    old = history_modules.text_before(path)
    temporary = path.with_name(path.name + ".tmp")
    try:
        temporary.write_text(text, encoding=encoding, newline=newline)
    except OSError:
        # The new text couldn't be written (a full disk): the file stays as
        # it was. Writing it directly would only cut it short.
        try:
            temporary.unlink()
        except OSError:
            pass
        raise
    try:
        os.replace(temporary, path)
    except OSError:
        # Windows refuses the swap while another program (antivirus, an
        # indexer) has the file open: write it directly instead. The
        # temporary copy goes too.
        try:
            path.write_text(text, encoding=encoding, newline=newline)
        finally:
            try:
                temporary.unlink()
            except OSError:
                pass
    history_modules.note_write(path, text, old)


def write_json(path: Path, doc: dict, indent: int = 2) -> None:
    write_text(path, json.dumps(doc, indent=indent) + "\n")


def start_fresh(path: Path) -> Path:
    """Moves a damaged module file aside as <name>.json.bad-<date> (nothing
    is deleted) so the device can be set up again. Returns the copy's path."""
    path = Path(path)
    copy = path.with_name(f"{path.name}.bad-{time.strftime('%Y%m%d-%H%M%S')}")
    os.replace(path, copy)
    return copy


def refused_message(error: ModuleFileDamaged) -> str:
    """What the user is told when a save into a damaged file is refused."""
    return (
        f"Nothing was saved: the module file {error.path.name} is damaged "
        f"({error.reason}). Its device's inputs are blocked until it is fixed. "
        "Restore the file, fix it, or choose Start Fresh on the device's card "
        "(the damaged file is kept)."
    )


def report_refused(error: ModuleFileDamaged) -> None:
    """Shows the refused-save message in the program's error dialog."""
    from gremlin import signal as gremlin_signal

    gremlin_signal.display_error(refused_message(error), str(error.path))
