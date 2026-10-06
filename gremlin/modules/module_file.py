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


def write_bytes(path: Path, data: bytes) -> None:
    """Writes the whole file safely: a temporary file, then a swap. A crash
    mid-write leaves the old file whole. No History here: module files are
    written through gremlin.modules.store, the one place History is hooked."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    try:
        temporary.write_bytes(data)
    except OSError:
        # The new data couldn't be written (a full disk): the file stays as
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
            path.write_bytes(data)
        finally:
            try:
                temporary.unlink()
            except OSError:
                pass


def encode(text: str, encoding: str = "utf-8", newline: str | None = None) -> bytes:
    """text as a text file is written: newline None turns line ends into
    the system's, "" keeps them as they are, anything else uses it."""
    if newline is None:
        text = text.replace("\r\n", "\n").replace("\n", os.linesep)
    elif newline:
        text = text.replace("\r\n", "\n").replace("\n", newline)
    return text.encode(encoding)


def write_text(
    path: Path, text: str, encoding: str = "utf-8", newline: str | None = None
) -> None:
    """write_bytes for text. Also used for profiles and settings (with a BOM
    and their line ends kept: encoding "utf-8-sig", newline ""). A module
    file goes through the module file store, so History keeps it; program
    code writes module files with the store itself."""
    data = encode(text, encoding, newline)
    from gremlin import history_modules

    if history_modules.is_module_file(Path(path)):
        from gremlin.modules import store

        store.write_file(Path(path), data)
        return
    write_bytes(path, data)


def write_json(path: Path, doc: dict, indent: int = 2) -> None:
    write_text(path, json.dumps(doc, indent=indent) + "\n")


def start_fresh(path: Path) -> Path:
    """Moves a damaged module file aside as <name>.json.bad-<date> (nothing
    is deleted) so the device can be set up again, with a History entry.
    Returns the copy's path. New callers use store.move_aside."""
    from gremlin.modules import store

    return store.move_aside_path(Path(path))


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
