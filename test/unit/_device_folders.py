# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Device folders for tests (D-03-DEVICE-FOLDERS, 03 S128-S134).

A module file lives in its device's folder: <modules>/<Device Folder>/
module.json, with device.json naming the device's id and its pictures in
pictures/. Tests write one the way the program does:

    put_module(modules, "pJoy Pro", stick_doc())      -> .../pJoy Pro/module.json
    module_path(modules, "vJoy 1")                     -> .../vJoy 1/module.json
    put_picture(modules, "pJoy Pro", "photo.jpg", b"") -> "pictures/photo.jpg"

When modules is the program's modules folder (store.folder(), which tests
point at tmp), the store itself picks and makes the folder
(store.ensure_device_dir), so a test sees exactly what the program would.
For any other folder the same rules are applied here: the folder name from
store.folder_name_for, the id from store.id_key, and "<name> (2)" when a
folder of that name already holds another device (S132).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

MODULE_FILE = "module.json"
ID_FILE = "device.json"
PICTURES = "pictures"

# Fallbacks used only until the store has the new functions (contract §1).
_BAD_CHARS = re.compile(r'[\\/:*?"<>|\x00-\x1f]')
_RESERVED = {
    "con", "prn", "aux", "nul",
    *(f"com{n}" for n in range(1, 10)),
    *(f"lpt{n}" for n in range(1, 10)),
    "cache", "templates", "library", "recovery", "imported", "backup",
}  # fmt: skip
_BUILT_IN_SHOWN = {
    "keyboard": "Keyboard",
    "osc": "OSC",
    "logical_device": "Logical Device",
    "logical": "Logical Device",
    "xbox": "Xbox 360 Controller",
    "xbox_360_controller": "Xbox 360 Controller",
}


def _store() -> Any:  # noqa: ANN401
    from gremlin.modules import store

    return store


def _has(name: str) -> bool:
    return hasattr(_store(), name)


def _guid_text(guid: object) -> str:
    if guid is None or guid == "":
        return ""
    from gremlin.modules.ids import stored_guid_key

    return stored_guid_key(guid)


def folder_name_for(shown: str) -> str:
    """The folder name for a shown name (store.folder_name_for)."""
    if _has("folder_name_for"):
        return _store().folder_name_for(shown)
    name = " ".join(str(shown or "").split())
    name = _BAD_CHARS.sub("_", name)
    name = re.sub(r"[. ]+$", lambda m: "_" * len(m.group()), name)[:80]
    if name.casefold() in _RESERVED:
        name += "_"
    return name or "Device"


def id_key(name: str, guid: object = "") -> str:
    """The device's id key, as device.json holds it (store.id_key)."""
    text = _guid_text(guid)
    if _has("id_key"):
        return _store().id_key(name, text)
    if text:
        return text
    from gremlin.modules import device_class
    from gremlin.modules.ids import guid_key
    from gremlin.modules.registry import plain_slug

    slug = plain_slug(name)
    fixed = device_class.guid_of_kind(
        {"logical": "logical_device", "xbox_360_controller": "xbox"}.get(slug, slug)
    )
    if fixed is not None:
        return guid_key(fixed)
    return "name:" + slug


def shown_name(name: str, guid: object = "") -> str:
    """The device's shown name (store.shown_name_of)."""
    text = _guid_text(guid)
    if _has("shown_name_of"):
        return _store().shown_name_of(name, text)
    from gremlin.modules.registry import plain_slug

    return _BUILT_IN_SHOWN.get(plain_slug(name), name)


def _is_program_folder(modules: Path) -> bool:
    if not _has("ensure_device_dir"):
        return False
    try:
        return Path(modules).resolve() == Path(_store().folder()).resolve()
    except OSError:
        return False


def _id_in(folder: Path) -> str:
    try:
        doc = json.loads((folder / ID_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    return str(doc.get("id", "")) if isinstance(doc, dict) else ""


def _find_dir(modules: Path, name: str, guid: object) -> Path:
    """Where the device's folder is (or goes) under modules: the folder that
    already holds its id, else the name's folder when free or the device's
    own, else "<name> (n)"."""
    key = id_key(name, guid)
    base = folder_name_for(shown_name(name, guid))
    modules = Path(modules)
    if modules.is_dir():
        for sub in sorted(modules.iterdir()):
            if sub.is_dir() and _id_in(sub) == key:
                return sub
    n = 1
    while True:
        if n == 1:
            candidate = base
        else:
            suffix = f" ({n})"
            candidate = base[: 80 - len(suffix)] + suffix
        existing = [
            sub
            for sub in (modules.iterdir() if modules.is_dir() else [])
            if sub.name.casefold() == candidate.casefold()
        ]
        if not existing:
            return modules / candidate
        held = _id_in(existing[0])
        if held in ("", key):
            return existing[0]
        n += 1


def device_dir(modules: Path, name: str, guid: object = "") -> Path:
    """The device's folder under modules (may not exist yet)."""
    if _is_program_folder(modules):
        return Path(_store().device_dir(name, _guid_text(guid)))
    return _find_dir(Path(modules), name, guid)


def ensure_dir(modules: Path, name: str, guid: object = "") -> Path:
    """The device's folder, made, with its device.json."""
    if _is_program_folder(modules):
        return Path(_store().ensure_device_dir(name, _guid_text(guid)))
    folder = _find_dir(Path(modules), name, guid)
    folder.mkdir(parents=True, exist_ok=True)
    ident = folder / ID_FILE
    if not ident.is_file():
        ident.write_text(
            json.dumps(
                {"format": 1, "id": id_key(name, guid), "name": shown_name(name, guid)}
            ),
            encoding="utf-8",
        )
    return folder


def module_path(modules: Path, name: str, guid: object = "") -> Path:
    """<modules>/<Device Folder>/module.json (may not exist yet)."""
    return device_dir(modules, name, guid) / MODULE_FILE


def _guid_of(doc: dict, guid: object) -> object:
    if guid not in (None, ""):
        return guid
    return doc.get("boundGuidLocal", "") if isinstance(doc, dict) else ""


def put_module(
    modules: Path, name: str, doc: dict | str | bytes, guid: object = ""
) -> Path:
    """Writes the device's module.json (and device.json) as the program lays
    them out; returns the module.json path. doc may be raw text or bytes
    (a damaged file). guid defaults to the doc's boundGuidLocal."""
    guid = _guid_of(doc if isinstance(doc, dict) else {}, guid)
    folder = ensure_dir(modules, name, guid)
    path = folder / MODULE_FILE
    if isinstance(doc, bytes):
        path.write_bytes(doc)
    elif isinstance(doc, str):
        path.write_text(doc, encoding="utf-8")
    else:
        path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    return path


def put_picture(
    modules: Path, name: str, file: str, data: bytes = b"", guid: object = ""
) -> str:
    """Writes a picture into the device's pictures/ folder; returns the ref
    a module file names it by ("pictures/<file>")."""
    folder = ensure_dir(modules, name, guid) / PICTURES
    folder.mkdir(parents=True, exist_ok=True)
    (folder / file).write_bytes(data)
    return f"{PICTURES}/{file}"


def picture_file(modules: Path, name: str, file: str, guid: object = "") -> Path:
    """Where a picture of the device is on disk."""
    return device_dir(modules, name, guid) / PICTURES / file
