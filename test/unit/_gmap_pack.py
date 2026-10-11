# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Writes a hand-made device file (.gmap, 08 S111) for the Device Library
tests: a module file doc (its "pack" label gives the device's name and id,
the maker and the note) and its wires, laid out as device_zip.build_gmap
lays them out (gmap.json, module.json, bindings/wires.json,
bindings/outputs/<name>.json)."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path


def write_gmap(
    path: Path,
    doc: dict,
    wires: dict | None = None,
    *,
    files: dict[str, bytes] | None = None,
    outputs: dict[str, dict] | None = None,
) -> Path:
    """path (".gmap" added when it has another extension) holding doc as
    its module.json, wires as its bindings, files at their place in the
    folder and outputs as bindings/outputs/<name>.json."""
    path = Path(path)
    if path.suffix.lower() != ".gmap":
        path = path.with_name(path.name + ".gmap")
    doc = dict(doc)
    label = doc.pop("pack", None) or {}
    name = str(label.get("exportedName") or doc.get("device") or path.stem)
    guid = str(label.get("exportedGuid") or "")
    head = {
        "format": "gremlin-device",
        "version": 1,
        "device": name,
        "deviceName": name,
        "id": guid or f"name:{name.lower().replace(' ', '_')}",
        "parts": ["folder"] + (["bindings"] if wires else []),
    }
    if label.get("author"):
        head["madeBy"] = label["author"]
    if label.get("note"):
        head["note"] = label["note"]
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("gmap.json", json.dumps(head))
        zf.writestr("module.json", json.dumps(doc))
        if wires:
            zf.writestr("bindings/wires.json", json.dumps(wires))
        for arc, raw in (files or {}).items():
            zf.writestr(arc, raw)
        for slug, out_doc in (outputs or {}).items():
            zf.writestr(f"bindings/outputs/{slug}.json", json.dumps(out_doc))
    return path
