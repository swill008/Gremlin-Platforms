# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""History of module files: each save or delete of a device's module file.

Only the module file store (gremlin.modules.store) calls these: its writes
call before_change() first (the pictures the file names are kept before
anything replaces them) and note_write() after; its deletes and Start Fresh
go through deleting() (delete_before() before, note_delete() after). An
entry keeps
the file as it was and as it became, and the pictures it uses (kept once
each by content), so it can be put back. A change to the Device Mapping
Editor's view only (zoom, pan, grid, guides, print area) isn't kept: it
changes all the time. A save that changes only the device map is filed
under Device Mapping Editor, others under Module files.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from gremlin import history

# What the Device Mapping Editor writes, and what a change means in words. The
# device's photo is the bottom background picture, inside "nodes" (07
# S127); "photo", "image", "imageWidth" and "imageHeight" are a map saved
# before the planes, dropped by its next Save (OT-2), still a device map
# change. The background's view settings are program settings, never in
# the file (08 S9).
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
    "layout": "Device Bindings layout",
    "calibration": "calibration",
    "view": "Output View Appearance",
    "nodes": "Device Map",
    "photo": "Device Map photo",
    "image": "Device Map photo",
}


# The pictures kept with each file's last save, by file: the next save's
# "before" (by then the pictures on disk may already be the new ones).
_last_pictures: dict[str, list[dict]] = {}
# The save thread sets it (before_change), the History thread reads and
# replaces it (_record): one at a time (GL-187).
_pictures_lock = threading.RLock()


def _modules() -> Path:
    from gremlin.modules import store

    return store.folder().resolve()


def is_module_file(path: Path) -> bool:
    """True for <modules>/<Device Folder>/module.json (not a reserved folder)."""
    from gremlin.modules import store

    path = Path(path)
    try:
        return (
            path.name == store.MODULE_FILE
            and path.parent.parent.resolve() == _modules()
            and path.parent.name.lower() not in store.RESERVED
        )
    except OSError:
        return False


def _doc(text: str | None) -> dict | None:
    if text is None:
        return None
    try:
        doc = json.loads(text)
    except (ValueError, RecursionError):
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


def before_change(path: Path) -> None:
    """Called before a module file or one of its pictures changes: the
    pictures the file names now are kept as the next save's "before" (once
    per file; later saves know them from the save before). The first save
    of a session read them after the write, so a picture replaced under the
    same name was kept as its own "before" (08 S8, GL-082)."""
    path = Path(path)
    with _pictures_lock:
        if str(path) in _last_pictures:
            return
        if not is_module_file(path) or not path.is_file():
            return
        _last_pictures[str(path)] = _keep_pictures(path, _doc(_read(path)))


def note_write(path: Path, text: str, old: str | None) -> None:
    """A module file was written with text (old: text_before() it). Called
    after the write: a write that failed is no History entry."""
    path = Path(path)
    if not is_module_file(path):
        return
    if old == text:
        return
    device_id = _device_id(path)
    history.later(lambda: _record(path, old, text, "save", device_id=device_id))


def delete_before(path: Path) -> dict | None:
    """A module file about to be deleted, as it is (None: not a module file,
    or no file). Its pictures are kept now: they go with it."""
    path = Path(path)
    if not is_module_file(path) or not path.is_file():
        return None
    old = _read(path)
    return {
        "text": old,
        "pictures": _keep_pictures(path, _doc(old)),
        # Read now: a delete of the whole folder takes device.json with it.
        "deviceId": _device_id(path),
    }


# note_delete(path) without before: the old way, called before the delete
# (an entry even when the delete then fails). Use deleting().
_NOW = object()


def note_delete(
    path: Path, before: dict | None | object = _NOW, moved_to: Path | None = None
) -> None:
    """A module file was deleted (before: delete_before() it), or moved
    aside by Start Fresh (moved_to: where it went). Called after the
    delete: a delete that failed is no History entry."""
    path = Path(path)
    if before is _NOW:
        before = delete_before(path)
    if not isinstance(before, dict):
        return
    old, pictures = before.get("text"), list(before.get("pictures") or [])
    device_id = str(before.get("deviceId") or "")
    with _pictures_lock:
        _last_pictures.pop(str(path), None)
    history.later(
        lambda: _record(
            path, old, None, "delete", pictures, moved_to, device_id=device_id
        )
    )


@contextmanager
def deleting(path: Path, moved_to: Path | None = None) -> Iterator[None]:
    """Around a module file's delete: History records it once the delete
    went through (a locked file that stays is no "Deleted" entry)::

        with history_modules.deleting(path):
            path.unlink()

    moved_to: Start Fresh moves the file there instead (kept, not deleted).
    """
    before = delete_before(path)
    yield
    if Path(path).exists():
        return  # the delete or move did not go through
    note_delete(path, before, moved_to)


def _device_id(path: Path) -> str:
    """The id key in the device folder's device.json ("" when none)."""
    from gremlin.modules import store

    doc = _doc(_read(Path(path).parent / store.ID_FILE))
    return str((doc or {}).get("id") or "").strip()


def _picture_refs(doc: dict | None) -> list[str]:
    from gremlin.modules import store

    if not doc:
        return []
    return sorted(
        ref for ref in store.named_refs(doc) if ref and not ref.startswith("file:")
    )


def picture_path(module_path: Path, ref: str) -> Path:
    """Where a picture the module file names is: its ref is relative to the
    file's device folder."""
    from gremlin.modules import store

    return store.picture_path(Path(module_path).parent, str(ref))


def _keep_pictures(module_path: Path, doc: dict | None) -> list[dict]:
    # Every picture the file names, kept or not ("keptFile" ""): Restore
    # then names the ones it can't put back.
    kept = []
    for ref in _picture_refs(doc):
        path = picture_path(module_path, ref)
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
    moved_to: Path | None = None,
    *,
    device_id: str = "",
) -> None:
    old, new = _doc(old_text), _doc(new_text)
    folder = path.parent.name
    changed = _changed_keys(old, new)
    if kind == "save" and changed <= {"ui"}:
        return  # the Device Mapping Editor's view only
    # Spaces as typed in the file ("EVO OT L  ") don't reach the title.
    device = " ".join(str((new or old or {}).get("device") or folder).split())
    if kind == "delete" and moved_to is not None:
        title = (
            f"Started fresh: the damaged module file of {device} was kept "
            f"as {Path(moved_to).name}"
        )
        area = "modules"
    elif kind == "delete":
        title = f"Deleted the module file of {device}"
        area = "modules"
    else:
        words = list(
            dict.fromkeys(word for key, word in _WORDS.items() if key in changed)
        )
        title = f"Saved {device}" + (": " + ", ".join(words) if words else "")
        if old_text is None:
            title = f"Created the module file of {device}"
        area = "device-mapping-editor" if changed <= MAP_KEYS | {"ui"} else "modules"
    with _pictures_lock:
        before = {
            "text": old_text,
            "pictures": old_pictures
            if old_pictures is not None
            else (
                _last_pictures[str(path)]
                if str(path) in _last_pictures
                else _keep_pictures(path, old)
            ),
        }
        after = (
            {"text": new_text, "pictures": _keep_pictures(path, new)}
            if new_text is not None
            else None
        )
        _last_pictures[str(path)] = after["pictures"] if after else []
    subject = {
        "device": device,
        # 08 S43: Restore finds the device's folder by this id.
        "deviceId": device_id,
        "folder": folder,
        "file": str(path),
        "fileName": f"{folder}/{path.name}",
        "parts": sorted(changed),
    }
    if moved_to is not None:
        subject["movedTo"] = str(moved_to)
    history.write_now(
        area,
        title,
        subject,
        before if old_text is not None else None,
        after,
        kind=kind,
    )
