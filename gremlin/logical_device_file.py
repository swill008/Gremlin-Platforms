# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The Logical Device's own module file (decision D-04-LD-FILE).

Every profile uses one Logical Device layout, kept under "logical-device"
in its module file, <modules>/Logical Device/module.json (its own folder,
03 S128; found by its id); the file's other keys are left as they
are. Writes go through gremlin.modules.store, so module-file History
records them (08 S4, S46).

A version 14 profile's own rows are not read (D-04-LD-NOLEGACY): its
references find their control by uid, else by type and number.

Main thread only.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from gremlin.modules import store

if TYPE_CHECKING:
    from gremlin.logical_device import LogicalRows

KEY = "logical-device"
WHO = "Logical Device"

syslog = logging.getLogger("system")

def _guid() -> str:
    from gremlin.modules import ids

    return str(ids.LOGICAL_DEVICE)


def path() -> Path:
    """The module file in the Logical Device's folder (may not exist yet)."""
    return store.module_file(WHO, _guid())


def _write_path() -> Path:
    """path(), its folder made first (with its device.json) for a write."""
    store.ensure_device_dir(WHO, _guid())
    return path()


def _identity() -> dict:
    from gremlin.modules import ids

    return {
        "kind": "control.hardware",
        "device": WHO,
        "direction": "source",
        "boundName": WHO,
        "boundGuidLocal": str(ids.LOGICAL_DEVICE).upper(),
    }


def _rows(rows: LogicalRows | None) -> LogicalRows:
    if rows is not None:
        return rows
    from gremlin.logical_device import LogicalDevice

    return LogicalDevice()


def _clean(layout: object, *, every_control: bool = False) -> dict:
    """A layout with a controls list and a groups list, whatever was read.
    every_control keeps controls that aren't objects too (for loading: the
    rows skip and keep them, AD1)."""
    if not isinstance(layout, dict):
        layout = {}
    controls = layout.get("controls")
    if not isinstance(controls, list):
        controls = []
    if not every_control:
        controls = [c for c in controls if isinstance(c, dict)]
    groups = layout.get("groups")
    if not isinstance(groups, list):
        groups = []
    groups = [str(g) for g in groups if str(g or "").strip()]
    return {"controls": controls, "groups": groups}


class _TooDeep(Exception):
    """The file exists but can't be read (bad text, not UTF-8 or nested too
    deeply); the reason is the exception's text."""


def _read_raw() -> dict:
    """The file's layout as it is; raises _TooDeep when it can't be read
    for its nesting."""
    reason = store.damage_of(path())
    if reason:
        raise _TooDeep(reason)
    try:
        return _clean(store.read_path(path()).get(KEY), every_control=True)
    except RecursionError:
        raise _TooDeep("it is nested too deeply") from None


def read_layout() -> dict:
    """The file's layout; empty when the file is missing or damaged."""
    try:
        return _clean(_read_raw())
    except _TooDeep:
        return _clean({})


def _with_unreadable(layout: dict, rows: object) -> dict:
    """layout with the controls the rows couldn't read put back in their
    places (AD1), so a Save never drops a row of the file."""
    kept = getattr(rows, "unreadable", None) or []
    controls = list(layout["controls"])
    for index, entry in sorted(kept, key=lambda pair: pair[0]):
        controls.insert(min(index, len(controls)), entry)
    return {**layout, "controls": controls}


def load(rows: LogicalRows | None = None) -> list[str]:
    """Fills the Logical Device (or rows) from the file. A missing file is an
    empty layout; the file is made on the first save. A control that can't
    be read is skipped and kept for Save (AD1). Returns a warning for the
    user per skipped control (also in the log); [] when all were read."""
    target = _rows(rows)
    try:
        layout = _read_raw()
    except _TooDeep as damaged:
        target.load_dict(_clean({}))
        target.mark_saved()
        warning = (
            f"The Logical Device file can't be read ({damaged}): "
            f"{path()}. It was left as it is and won't be saved over."
        )
        syslog.warning(warning)
        return [warning]
    target.load_dict(layout)
    target.mark_saved()
    warnings = list(getattr(target, "load_warnings", []) or [])
    for warning in warnings:
        syslog.warning(warning)
    return warnings


def save(rows: LogicalRows | None = None, who: str = "") -> bool:
    """Writes the layout into the file, keeping its other keys and the
    controls the last load couldn't read (AD1). False when a damaged file
    was refused (said in the error dialog) or can't be read for its nesting
    (logged; nothing written); raises OSError when the write failed."""
    source = _rows(rows)
    layout = _with_unreadable(_clean(source.to_dict()), source)

    def change(doc: dict) -> None:
        # What makes it the Logical Device's module file for the Library
        # and Import; kept as they are when already there.
        for key, value in _identity().items():
            if not doc.get(key):
                doc[key] = value
        doc[KEY] = layout

    try:
        written = store.update_path(_write_path(), change, who or WHO)
    except RecursionError:
        syslog.warning(
            "Nothing was saved: the Logical Device file is nested too deeply "
            "to read: %s",
            path(),
        )
        return False
    if not written:
        return False
    source.mark_saved()
    return True


def save_if_dirty(who: str = "") -> bool:
    """Saves the Logical Device when it changed; True when written."""
    rows = _rows(None)
    if not rows.dirty:
        return False
    return save(rows, who)
