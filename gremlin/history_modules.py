# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""History of module files: each save or delete of a device's module file.

The module file writers (module_file.write_text, and the import and Device
Pack replace) tell note_write() what they wrote; deletes go through
deleting() (delete_before() before, note_delete() after). An entry keeps
the file as it was and as it became, and the pictures it uses (kept once
each by content), so it can be put back. A change to the Button Map's view
only (zoom, pan, grid, guides, print area) isn't kept: it changes all the
time. A save that changes only the Button Map is filed under Button Map,
others under Module files.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from gremlin import history

# What the Button Map writes, and what a change means in words.
MAP_KEYS = {
    "nodes",
    "photo",
    "image",
    "imageWidth",
    "imageHeight",
    "space",
    "page",
    "pageW",
    "pageH",
    "photoWell",
    "kind",
    "device",
}
_WORDS = {
    "claim": "checked controls and names",
    "calibration": "calibration",
    "view": "Output View Appearance",
    "catalog": "Configuration Appearance",
    "nodes": "Button Map",
    "photo": "Button Map photo",
    "image": "Button Map photo",
}


# The pictures kept with each file's last save, by file: the next save's
# "before" (by then the pictures on disk may already be the new ones).
_last_pictures: dict[str, list[dict]] = {}


def _modules() -> Path:
    from gremlin import util

    return util.modules_dir().resolve()


def is_module_file(path: Path) -> bool:
    path = Path(path)
    try:
        return path.suffix.lower() == ".json" and path.parent.resolve() == _modules()
    except OSError:
        return False


def _doc(text: str | None) -> dict | None:
    if text is None:
        return None
    try:
        doc = json.loads(text)
    except ValueError:
        return None
    return doc if isinstance(doc, dict) else None


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def text_before(path: Path) -> str | None:
    """A module file's text before it is written (None: no file yet)."""
    path = Path(path)
    if not is_module_file(path) or not path.is_file():
        return None
    return _read(path)


def note_write(path: Path, text: str, old: str | None) -> None:
    """A module file was written with text (old: text_before() it). Called
    after the write: a write that failed is no History entry."""
    path = Path(path)
    if not is_module_file(path):
        return
    if old == text:
        return
    history.later(lambda: _record(path, old, text, "save"))


def delete_before(path: Path) -> dict | None:
    """A module file about to be deleted, as it is (None: not a module file,
    or no file). Its pictures are kept now: they go with it."""
    path = Path(path)
    if not is_module_file(path) or not path.is_file():
        return None
    old = _read(path)
    return {"text": old, "pictures": _keep_pictures(_doc(old))}


# note_delete(path) without before: the old way, called before the delete
# (an entry even when the delete then fails). Use deleting().
_NOW = object()


def note_delete(path: Path, before: dict | None | object = _NOW) -> None:
    """A module file was deleted (before: delete_before() it). Called after
    the delete: a delete that failed is no History entry."""
    path = Path(path)
    if before is _NOW:
        before = delete_before(path)
    if not isinstance(before, dict):
        return
    old, pictures = before.get("text"), list(before.get("pictures") or [])
    history.later(lambda: _record(path, old, None, "delete", pictures))


@contextmanager
def deleting(path: Path) -> Iterator[None]:
    """Around a module file's delete: History records it once the delete
    went through (a locked file that stays is no "Deleted" entry)::

        with history_modules.deleting(path):
            path.unlink()
    """
    before = delete_before(path)
    yield
    note_delete(path, before)


def _picture_refs(doc: dict | None) -> list[str]:
    if not doc:
        return []
    refs = [str(doc.get("image") or "")]
    for node in doc.get("nodes") or []:
        if isinstance(node, dict) and (
            node.get("kind") == "image" or node.get("shape") == "image"
        ):
            refs.append(str(node.get("src") or ""))
    return [ref for ref in dict.fromkeys(refs) if ref and not ref.startswith("file:")]


def picture_path(ref: str) -> Path:
    """Where a picture the file names is ("qml/maps/..." as the Button Map
    finds it: in the modules folder)."""
    from gremlin.ui.hardware_profile import _module_relative

    return _modules() / _module_relative(str(ref))


def _keep_pictures(doc: dict | None) -> list[dict]:
    # Every picture the file names, kept or not ("keptFile" ""): Restore
    # then names the ones it can't put back.
    kept = []
    for ref in _picture_refs(doc):
        path = picture_path(ref)
        name = history.keep_file(path) if path.is_file() else ""
        kept.append({"ref": ref, "keptFile": name})
    return kept


def _changed_keys(old: dict | None, new: dict | None) -> set[str]:
    old, new = old or {}, new or {}
    return {key for key in set(old) | set(new) if old.get(key) != new.get(key)}


def _record(
    path: Path,
    old_text: str | None,
    new_text: str | None,
    kind: str,
    old_pictures: list[dict] | None = None,
) -> None:
    old, new = _doc(old_text), _doc(new_text)
    changed = _changed_keys(old, new)
    if kind == "save" and changed <= {"ui"}:
        return  # the Button Map's view only
    # Spaces as typed in the file ("EVO OT L  ") don't reach the title.
    device = " ".join(str((new or old or {}).get("device") or path.stem).split())
    if kind == "delete":
        title = f"Deleted the module file of {device}"
        area = "modules"
    else:
        words = list(
            dict.fromkeys(word for key, word in _WORDS.items() if key in changed)
        )
        title = f"Saved {device}" + (": " + ", ".join(words) if words else "")
        if old_text is None:
            title = f"Created the module file of {device}"
        area = "button-map" if changed <= MAP_KEYS | {"ui"} else "modules"
    before = {
        "text": old_text,
        "pictures": old_pictures
        if old_pictures is not None
        else (
            _last_pictures[str(path)]
            if str(path) in _last_pictures
            else _keep_pictures(old)
        ),
    }
    after = (
        {"text": new_text, "pictures": _keep_pictures(new)}
        if new_text is not None
        else None
    )
    _last_pictures[str(path)] = after["pictures"] if after else []
    history.write_now(
        area,
        title,
        {
            "device": device,
            "file": str(path),
            "fileName": path.name,
            "parts": sorted(changed),
        },
        before if old_text is not None else None,
        after,
        kind=kind,
    )
