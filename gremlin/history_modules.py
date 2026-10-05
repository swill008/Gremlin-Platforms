# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""History of module files: each save or delete of a device's module file.

The module file writers (module_file.write_text, and the import and Device
Pack replace) tell note_write() what they are about to write; deletes tell
note_delete(). An entry keeps the file as it was and as it became, and the
pictures it uses (kept once each by content), so it can be put back. A
change to the Button Map's view only (zoom, pan, grid, guides, print area)
isn't kept: it changes all the time. A save that changes only the Button
Map is filed under Button Map, others under Module files.
"""

from __future__ import annotations

import json
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


def note_write(path: Path, text: str) -> None:
    """A module file is about to be written with text."""
    path = Path(path)
    if not is_module_file(path):
        return
    old = _read(path) if path.is_file() else None
    if old == text:
        return
    history.later(lambda: _record(path, old, text, "save"))


def note_delete(path: Path) -> None:
    """A module file (and its pictures) is about to be deleted. The pictures
    are kept now: they go with it."""
    path = Path(path)
    if not is_module_file(path) or not path.is_file():
        return
    old = _read(path)
    pictures = _keep_pictures(_doc(old))
    history.later(lambda: _record(path, old, None, "delete", pictures))


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


def _keep_pictures(doc: dict | None) -> list[dict]:
    kept = []
    for ref in _picture_refs(doc):
        path = _modules() / ref.replace("\\", "/").lstrip("/")
        name = history.keep_file(path) if path.is_file() else ""
        if name:
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
    device = str((new or old or {}).get("device") or path.stem)
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
