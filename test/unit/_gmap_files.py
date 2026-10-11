# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Hand-made .gmap files for tests (D-FIXLIST-B2: .gmap is the only
Export / Import Device file).

write_gmap takes the members a test used to put in a Device Pack zip
("map.json", "wires.json", "outputs/<slug>.json", "<picture>") and writes
the same content as a .gmap: gmap.json (from map.json's "pack" label),
module.json (its pictures as "pictures/<file>"), pictures/<file>,
bindings/wires.json and bindings/outputs/<slug>.json.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from gremlin.modules import device_zip, store

_PICTURE_EXT = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".svg", ".webp")


def _text(value: object) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        return value.encode("utf-8")
    return (json.dumps(value, indent=2) + "\n").encode("utf-8")


def _folder_refs(doc: dict, pictures: set[str]) -> dict:
    """doc with each picture it names (a plain file name in the old pack)
    as "pictures/<file>"."""
    mapping = {}
    for ref in store.named_refs(doc):
        name = Path(str(ref).replace("\\", "/")).name
        if name in pictures:
            mapping[str(ref)] = "pictures/" + name
    out = device_zip.replace_strings(doc, mapping)
    return out if isinstance(out, dict) else doc


def gmap_label(doc: dict) -> dict:
    """gmap.json for a module document with an old pack label."""
    label = doc.get("pack") if isinstance(doc.get("pack"), dict) else {}
    name = str(label.get("exportedName") or doc.get("device") or "").strip()
    guid = str(label.get("exportedGuid") or "")
    try:
        made = int(label.get("format") or 1)
    except (TypeError, ValueError):
        made = 1
    out = {
        "format": device_zip.GMAP_FORMAT,
        # A pack label from a newer program is a newer .gmap.
        "version": device_zip.GMAP_VERSION + 1 if made > 2 else device_zip.GMAP_VERSION,
        "device": name,
        "deviceName": name,
        "id": guid,
        "direction": doc.get("direction") or "source",
        "exportedAt": str(label.get("exportedOn") or ""),
        "app": str(label.get("program") or ""),
        "parts": ["folder"],
    }
    if label.get("author"):
        out["madeBy"] = label["author"]
    if label.get("note"):
        out["note"] = label["note"]
    return out


def gmap_members(files: dict[str, object]) -> dict[str, bytes]:
    """The .gmap members for an old pack's members."""
    pictures = {
        name
        for name in files
        if Path(name).suffix.lower() in _PICTURE_EXT and "/" not in name
    }
    members: dict[str, bytes] = {}
    doc = files.get("map.json")
    if isinstance(doc, (bytes, str)):
        # A damaged or odd map.json goes in as it is.
        members[device_zip.GMAP_JSON] = _text(
            {"format": device_zip.GMAP_FORMAT, "version": 1, "device": "x",
             "deviceName": "x", "parts": ["folder"]}
        )
        members[store.MODULE_FILE] = _text(doc)
    elif isinstance(doc, dict):
        label = gmap_label(doc)
        module = {k: v for k, v in doc.items() if k != "pack"}
        members[device_zip.GMAP_JSON] = _text(label)
        members[store.MODULE_FILE] = _text(_folder_refs(module, pictures))
    for name, value in files.items():
        if name == "map.json":
            continue
        if name == "wires.json":
            members["bindings/wires.json"] = _text(value)
            if device_zip.GMAP_JSON in members:
                label = json.loads(members[device_zip.GMAP_JSON])
                label["parts"] = [*label["parts"], "bindings"]
                members[device_zip.GMAP_JSON] = _text(label)
        elif name.startswith("outputs/"):
            out = value
            if isinstance(out, dict):
                out = _folder_refs(out, pictures)
            members["bindings/" + name] = _text(out)
        elif name in pictures:
            members["pictures/" + name] = _text(value)
        else:
            members[name] = _text(value)
    return members


def write_gmap(path: Path, files: dict[str, object]) -> Path:
    """Writes an old pack's members as a .gmap at path; returns path."""
    path = Path(path)
    with zipfile.ZipFile(path, "w") as zf:
        for name, data in gmap_members(files).items():
            zf.writestr(name, data)
    return path


def read_module(path: Path) -> tuple[dict, dict, set[str]]:
    """A .gmap's (gmap.json, module.json, member names)."""
    with zipfile.ZipFile(path) as zf:
        names = set(zf.namelist())
        label = json.loads(zf.read(device_zip.GMAP_JSON))
        doc = json.loads(zf.read(store.MODULE_FILE))
    return label, doc, names
