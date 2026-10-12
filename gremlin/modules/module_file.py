# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""A device's module file (<Device Folder>/module.json: its device map,
claims, calibration and layout, D-03-DEVICE-FOLDERS): read it to change it,
and write it safely. Where it is belongs to gremlin.modules.store.

A file that can't be read is never treated as empty: a save that would
replace it with a nearly empty file is refused (ModuleFileDamaged) and the
user is told. "Start Fresh" moves a damaged file aside, so nothing is lost.
Writes go to a temporary file that then replaces the real one, so a crash
or a full disk can't leave half a file.
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

from gremlin import clock
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
    except (ValueError, RecursionError) as e:
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
    mid-write leaves the old file whole; a swap refused every time raises
    OSError with the old file untouched (never written in place). No
    History here: module files are written through gremlin.modules.store,
    the one place History is hooked."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # A name of its own, so two writes of the same file never share one.
    temporary = path.with_name(f"{path.name}.{uuid.uuid4().hex[:8]}.tmp")
    try:
        temporary.write_bytes(data)
        _swap(temporary, path)
    except BaseException:
        # The new data couldn't be written (a full disk) or the swap was
        # refused every time: the file stays as it was. Writing it directly
        # would only risk cutting it short.
        try:
            temporary.unlink()
        except OSError:
            pass
        raise


# Waits between swap attempts (seconds): about 0.75 s in all.
_SWAP_WAITS = (0.05, 0.1, 0.2, 0.4)


def _swap(temporary: Path, path: Path) -> None:
    """Windows refuses the swap while another program (antivirus, an
    indexer) has the file open for a moment: tried again after a short wait,
    then the last refusal is raised."""
    for wait in _SWAP_WAITS:
        try:
            os.replace(temporary, path)
            return
        except OSError:
            clock.sleep(wait)
    os.replace(temporary, path)


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
    """Moves a damaged module file aside as module.json.bad-<date> in its
    device folder (nothing is deleted) so the device can be set up again,
    with a History entry. Returns the copy's path. New callers use store.move_aside."""
    from gremlin.modules import store

    return store.move_aside_path(Path(path))


def _shown_path(path: Path) -> str:
    """A module file as the user is told it: <device folder>\\module.json."""
    path = Path(path)
    if not path.parent.name:
        return path.name
    return path.parent.name + "\\" + path.name


def refused_message(error: ModuleFileDamaged) -> str:
    """What the user is told when a save into a damaged file is refused."""
    return (
        f"Nothing was saved: the module file {_shown_path(error.path)} is damaged "
        f"({error.reason}). Its device's inputs are blocked until it is fixed. "
        "Restore the file, fix it, or choose Start Fresh on the device's card "
        "(the damaged file is kept)."
    )


def report_refused(error: ModuleFileDamaged) -> None:
    """Shows the refused-save message in the program's error dialog."""
    from gremlin import signal as gremlin_signal

    gremlin_signal.display_error(refused_message(error), str(error.path))
