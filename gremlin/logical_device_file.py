# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The Logical Device's own module file (decision D-04-LD-FILE).

Every profile uses one Logical Device layout, kept under "logical-device"
in <modules>/logical_device.json; the file's other keys are left as they
are. Writes go through gremlin.modules.store, so module-file History
records them (08 S4, S46).

Version 14 profiles carried their own rows: merge_profile_rows adds them
to the file (decision 3) and gives the uid each old (type, number) now
points at. While such a profile loads, profile.py puts that map in
current_uid_map for readers of references without a uid.

Main thread only.
"""

from __future__ import annotations

import logging
import os
import shutil
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from gremlin.modules import store

if TYPE_CHECKING:
    from gremlin.logical_device import LogicalRows

SLUG = "logical_device"
KEY = "logical-device"
WHO = "Logical Device"

syslog = logging.getLogger("system")

# (type name, number) in the v14 profile being loaded -> uid in the file.
current_uid_map: dict[tuple[str, int], str] | None = None


@dataclass
class MergeResult:
    uid_map: dict[tuple[str, int], str] = field(default_factory=dict)
    added: list[str] = field(default_factory=list)


def path() -> Path:
    return store.path_of(SLUG)


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
        written = store.update_path(path(), change, who or WHO)
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


def _number(value: object) -> int | None:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _origin_uid(kind: str, number: int, label: str) -> str:
    """The uid a v14 control without one gets: the same every time, so a
    dry run (Library browsing) and the later real merge agree."""
    return uuid.uuid5(_ORIGIN, f"{kind}:{number}:{label}").hex


_ORIGIN = uuid.UUID("5c1f3f0e-7d0b-4f43-9a51-6c0d2b9e4a10")


def merge_layout(file_layout: dict, profile_layout: dict) -> tuple[dict, MergeResult]:
    """Decision 3 on plain layouts: a profile control with the same type,
    number and label as one in the file is that control (its uid is kept),
    and so is one whose uid the file already has. Any other is added under
    its own number when free, else the lowest free number of its type, with
    a label made unique and its own uid (the one it carries, else one made
    from its type, number and label). Nothing is removed. Returns the merged
    layout and the uid map / added labels."""
    merged = _clean(file_layout)
    merged["controls"] = [dict(c) for c in merged["controls"]]
    result = MergeResult()
    controls = merged["controls"]
    for entry in controls:
        if not entry.get("uid"):
            entry["uid"] = uuid.uuid4().hex
    used = {(str(c.get("type")), _number(c.get("id"))) for c in controls}
    labels = {str(c.get("label")) for c in controls}
    incoming = _clean(profile_layout)
    for name in incoming["groups"]:
        if name not in merged["groups"]:
            merged["groups"].append(name)
    for entry in incoming["controls"]:
        kind = str(entry.get("type") or "")
        number = _number(entry.get("id"))
        label = str(entry.get("label") or "")
        if not kind or number is None:
            continue
        same = next(
            (
                c
                for c in controls
                if str(c.get("type")) == kind
                and _number(c.get("id")) == number
                and str(c.get("label")) == label
            ),
            None,
        )
        if same is None:
            carried = str(entry.get("uid") or "") or _origin_uid(kind, number, label)
            same = next((c for c in controls if str(c.get("uid")) == carried), None)
        else:
            carried = ""
        if same is not None:
            result.uid_map[(kind, number)] = str(same["uid"])
            continue
        new_number = number
        if (kind, new_number) in used:
            new_number = 1
            while (kind, new_number) in used:
                new_number += 1
        base = label or f"{kind.capitalize()} {new_number}"
        new_label, copy = base, 1
        while new_label in labels:
            copy += 1
            new_label = f"{base} ({copy})"
        added = dict(entry)
        added.update(uid=carried, type=kind, id=new_number, label=new_label)
        group = str(added.get("group") or "").strip()
        if group and group not in merged["groups"]:
            merged["groups"].append(group)
        controls.append(added)
        used.add((kind, new_number))
        labels.add(new_label)
        result.uid_map[(kind, number)] = added["uid"]
        result.added.append(new_label)
    return merged, result


def merge_profile_rows(
    profile_dict: dict, dry_run: bool = False, *, rows: LogicalRows | None = None
) -> MergeResult:
    """Adds a version 14 profile's Logical Device controls (profile_dict, in
    the to_dict layout) to the Logical Device and its file (decision 3).
    The file is written at once when the result differs from it. dry_run gives the
    same result and changes nothing (a profile read without binding, such as
    Library browsing)."""
    target = _rows(rows)
    merged, result = merge_layout(target.to_dict(), profile_dict)
    if dry_run:
        return result
    if result.added:
        if getattr(target, "unreadable", None):
            # The file's unreadable controls stay held for its Save (AD1).
            target.load_dict(merged, keep_unreadable=True)
        else:
            target.load_dict(merged)
    # A matching row only in memory (not saved yet) still reaches the file.
    try:
        on_file = _read_raw()
    except _TooDeep:
        on_file = None
    if _with_unreadable(_clean(target.to_dict()), target) != on_file:
        save(target, WHO)
    return result


def backup_v14(profile_path: Path) -> Path | None:
    """Keeps the version 14 profile as <name>.xml.v14.bak beside it, only if
    there isn't one already. The backup's path, or None when none was made."""
    source = Path(profile_path)
    backup = source.with_name(source.name + ".v14.bak")
    if backup.exists() or not source.is_file():
        return None
    try:
        # A profile copy, not a module file: copy beside it, then rename.
        part = backup.with_name(backup.name + ".part")
        shutil.copyfile(source, part)
        os.replace(part, backup)
    except OSError:
        syslog.exception(
            "The version 14 profile backup could not be written: %s", backup
        )
        return None
    return backup
