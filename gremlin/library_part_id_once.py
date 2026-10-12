# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""ONE-TIME (tracker OT-4): the Device Library's part id "button_map"
becomes "device_map" (the Device Mapping Editor rename). Removed before
release with OT-1, OT-2 and OT-3.

Part ids are stored only in library.json (the .gmap files hold none): the
default parts (settings.default_parts), each saved setup's "holds" and
"covers", the last change's detail (a swap's "parts") and any other list.
The move renames the id wherever it is a value in the document (a list
item or a field's value), so no list is missed. At start, when library.json holds
the old id, a copy of it goes to <data folder>/backup/<date> library part
id move/ and library.json is written with the new id. Once moved, no old id
is left, which is the marker: the move never runs again. No History entry
(a rename, not a change).
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

syslog = logging.getLogger("system")

# ONE-TIME (tracker OT-4): the old and new part id.
OLD_ID = "button_map"
NEW_ID = "device_map"
REFUSED = "refused: tests"

# ONE-TIME (tracker OT-4): the user's own Gremlin Platforms folder, read from
# the environment when this module loads (tests patch the library folder).
_REAL_DATA = [
    Path(base) / "Gremlin Platforms"
    for base in (
        os.environ.get("USERPROFILE", ""),
        os.environ.get("HOMEDRIVE", "") + os.environ.get("HOMEPATH", ""),
    )
    if base
]


def _inside(path: Path, parent: Path) -> bool:
    """ONE-TIME (tracker OT-4): path is parent or under it."""
    try:
        Path(path).resolve().relative_to(Path(parent).resolve())
    except (ValueError, OSError):
        return False
    return True


def refuses_real_library(path: Path) -> bool:
    """ONE-TIME (tracker OT-4): True in a test run (GREMLIN_TESTS=1, or
    pytest loaded) when library.json is in the user's real Gremlin Platforms
    folder: a test never changes the user's library."""
    testing = os.environ.get("GREMLIN_TESTS") == "1" or "pytest" in sys.modules
    return testing and any(_inside(path, real) for real in _REAL_DATA)


def _renamed(ids: object) -> tuple[object, int]:
    """ONE-TIME (tracker OT-4): a list of part ids with the old id renamed
    (dropped when the new one is there already), and how many were."""
    if not isinstance(ids, list) or OLD_ID not in ids:
        return ids, 0
    out: list = []
    for each in ids:
        value = NEW_ID if each == OLD_ID else each
        if value == NEW_ID and NEW_ID in out:
            continue
        out.append(value)
    return out, ids.count(OLD_ID)


def _walk(value: object) -> tuple[object, int]:
    """ONE-TIME (tracker OT-4): the old id renamed wherever it is a value
    inside value: in every list (holds, covers, default parts, a change's
    parts) and as a field's value."""
    if value == OLD_ID:
        return NEW_ID, 1
    if isinstance(value, list):
        renamed, moved = _renamed(value)
        out = []
        for each in renamed if isinstance(renamed, list) else value:
            item, count = _walk(each)
            out.append(item)
            moved += count
        return out, moved
    if isinstance(value, dict):
        moved = 0
        result = {}
        for key, each in value.items():
            result[key], count = _walk(each)
            moved += count
        return result, moved
    return value, 0


def migrate(doc: dict) -> int:
    """ONE-TIME (tracker OT-4): renames the old id in a library.json document
    in place, wherever it is a value: default parts, every setup's holds and
    covers, the last change and any other list. Returns how many were
    renamed."""
    moved = 0
    for key in list(doc):
        doc[key], count = _walk(doc[key])
        moved += count
    return moved


def _backup(path: Path, data_dir: Path) -> Path:
    """ONE-TIME (tracker OT-4): library.json copied to <data>/backup/<date>
    library part id move/ and checked; returns the copy."""
    base = data_dir / "backup" / f"{datetime.now():%Y-%m-%d} library part id move"
    target = base
    number = 2
    while target.exists():
        target = base.with_name(f"{base.name} ({number})")
        number += 1
    target.mkdir(parents=True)
    copy = target / path.name
    shutil.copy2(path, copy)
    if copy.read_bytes() != path.read_bytes():
        raise OSError(f"The backup of {path.name} does not match it.")
    return copy


def run(path: Path | None = None, data_dir: Path | None = None) -> str:
    """ONE-TIME (tracker OT-4): moves the old id in library.json (default:
    the Library's own). Returns a summary ("" when nothing was to do);
    REFUSED in a test run on the real library."""
    from gremlin import device_library, util
    from gremlin.modules import module_file

    path = Path(path or device_library._list_path())  # noqa: SLF001 - the one list file
    if refuses_real_library(path):
        syslog.warning(f"Library part id move {REFUSED} ({path})")
        return REFUSED
    if not path.is_file():
        return ""
    with device_library._LOCK:  # noqa: SLF001 - one-time rewrite of the list
        text = path.read_text(encoding="utf-8")
        if f'"{OLD_ID}"' not in text:
            return ""
        doc = json.loads(text)
        if not isinstance(doc, dict):
            return ""
        moved = migrate(doc)
        if not moved:
            return ""
        copy = _backup(path, Path(data_dir or util.data_folder()))
        data = (json.dumps(doc, indent=2) + "\n").encode("utf-8")
        module_file.write_bytes(path, data)
    summary = f"Library part id move: {moved} renamed; backup in {copy.parent}"
    syslog.info(summary)
    return summary


def run_if_needed() -> str:
    """ONE-TIME (tracker OT-4): the start's entry point (joystick_gremlin):
    "" when done or nothing to do, else the reason (logged; the start goes
    on and the next start tries again)."""
    try:
        return REFUSED if run() == REFUSED else ""
    except Exception as exc:  # noqa: BLE001 - logged, retried next start
        syslog.exception("Library part id move failed")
        return str(exc) or type(exc).__name__
