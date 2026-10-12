# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Damaged Device Library entries and device files (.gmap; SHAKE-DAMAGE-03,
-04; D-FIXLIST-B2):
a bad library.json row is left out with a warning and the rest is listed;
a pack with wrong types, a broken outputs file or too much to unpack is
refused with a message that names the part, nothing is written and nothing
raises; a very long exported name still imports. On the real store in a
temporary library and modules folder (the LS fixture)."""

from __future__ import annotations

import io
import json
import logging
import zipfile
from collections.abc import Mapping
from pathlib import Path

import pytest

from gremlin import device_library as library
from gremlin.ui import device_pack
from test.unit import test_device_library_LS_store as _ls

lib = _ls.lib  # the LS fixture

_MAP = {
    "device": "pJoy Pro",
    "pack": {
        "exportedName": "pJoy Pro",
        "exportedGuid": "",
        "author": "me",
        "format": 1,
    },
}
_GOOD_WIRES = {"modes": [{"name": "D", "lines": ["Button 1 → vJoy 1 Button 1"]}]}


def _zip(files: Mapping[str, str | bytes]) -> bytes:
    """A device file (.gmap, D-FIXLIST-B2) from a pack's parts: map.json
    becomes gmap.json (the device, its id, Made by) and module.json,
    wires.json and outputs/ go under bindings/."""
    blob = io.BytesIO()
    with zipfile.ZipFile(blob, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in files.items():
            if name == "map.json":
                doc = json.loads(data)
                label = doc.pop("pack", None) or {}
                device = label.get("exportedName") or doc.get("device") or ""
                head = {
                    "format": "gremlin-device",
                    "version": 1,
                    "device": device,
                    "deviceName": device,
                    "id": label.get("exportedGuid") or "name:pjoy_pro",
                    "madeBy": label.get("author", ""),
                }
                zf.writestr("gmap.json", json.dumps(head))
                zf.writestr("module.json", json.dumps(doc))
            elif name == "wires.json" or name.startswith("outputs/"):
                zf.writestr("bindings/" + name, data)
            else:
                zf.writestr(name, data)
    return blob.getvalue()


def _snapshot(*roots: Path) -> dict[str, bytes]:
    out: dict[str, bytes] = {}
    for root in roots:
        if root.is_dir():
            for path in root.rglob("*"):
                if path.is_file():
                    out[str(path)] = path.read_bytes()
    return out


# --- library.json: one bad row ------------------------------------------------------


def _record(key: str, name: str, setups: object) -> dict:
    return {
        "key": key,
        "name": name,
        "ownName": name,
        "description": "",
        "guid": "",
        "kind": "pack",
        "seen": "",
        "setups": setups,
    }


def _setup(key: str, file: object) -> dict:
    return {
        "key": key,
        "name": key,
        "created": "2026-10-10T12:00:00",
        "origin": "pack",
        "holds": ["setup"],
        "file": file,
    }


def test_a_bad_library_row_is_left_out_and_the_rest_is_listed(
    lib: dict, caplog: pytest.LogCaptureFixture
) -> None:
    lib["folder"].mkdir(parents=True, exist_ok=True)
    doc = {
        "format": 1,
        "devices": [
            _record(
                "dev-a",
                "Stick A",
                [_setup("set-bad", 12345), _setup("set-a", "Stick A/a.zip")],
            ),
            _record("dev-b", "Stick B", [_setup("set-b", "Stick B/b.zip")]),
            {"key": 7, "name": ["x"], "setups": "abc"},
            _record("dev-c", "Stick C", "not a list"),
        ],
    }
    path = lib["folder"] / library.LIST_NAME
    path.write_text(json.dumps(doc), encoding="utf-8")
    before = path.read_bytes()
    with caplog.at_level(logging.WARNING, logger="system"):
        rows = library.devices()
    by_name = {row["name"]: row for row in rows}
    assert {"Stick A", "Stick B", "Stick C"} <= set(by_name)
    assert [s["key"] for s in by_name["Stick A"]["setups"]] == ["set-a"]
    assert [s["key"] for s in by_name["Stick B"]["setups"]] == ["set-b"]
    assert by_name["Stick C"]["setups"] == []
    warned = " ".join(r.getMessage() for r in caplog.records)
    assert "Device Library" in warned and "set-bad" in warned
    # Reading never rewrites the list: the bad rows stay as they were.
    assert path.read_bytes() == before


def test_a_deeply_nested_library_list_reads_as_damaged(
    lib: dict, caplog: pytest.LogCaptureFixture
) -> None:
    lib["folder"].mkdir(parents=True, exist_ok=True)
    path = lib["folder"] / library.LIST_NAME
    path.write_text("[" * 100_000 + "]" * 100_000, encoding="utf-8")
    before = path.read_bytes()
    with caplog.at_level(logging.WARNING, logger="system"):
        assert [r for r in library.devices() if not r["builtIn"]] == []
    assert "Device Library" in " ".join(r.getMessage() for r in caplog.records)
    assert path.read_bytes() == before


# --- Device Packs: wrong types, broken outputs, too big -------------------------------

_BAD_PACKS = {
    "wires-lines-int": (
        {
            "map.json": json.dumps(_MAP),
            "wires.json": json.dumps({"modes": [{"name": "D", "lines": 5}]}),
        },
        "wires.json",
    ),
    "wires-modes-string": (
        {"map.json": json.dumps(_MAP), "wires.json": json.dumps({"modes": "abc"})},
        "wires.json",
    ),
    "wires-list": ({"map.json": json.dumps(_MAP), "wires.json": "[1]"}, "wires.json"),
    "wires-mode-not-dict": (
        {"map.json": json.dumps(_MAP), "wires.json": json.dumps({"modes": [5]})},
        "wires.json",
    ),
    "wires-tree-list": (
        {
            "map.json": json.dumps(_MAP),
            "wires.json": json.dumps({**_GOOD_WIRES, "tree": [1]}),
        },
        "wires.json",
    ),
    "wires-bad-block": (
        {
            "map.json": json.dumps(_MAP),
            "wires.json": json.dumps(
                {"modes": [{"name": "D", "lines": ["x"], "inputs": ["<input"]}]}
            ),
        },
        "wires.json",
    ),
    "wires-deep-nesting": (
        {"map.json": json.dumps(_MAP), "wires.json": "[" * 100_000 + "]" * 100_000},
        "wires.json",
    ),
    "wires-invalid-json": (
        {"map.json": json.dumps(_MAP), "wires.json": "{bad"},
        "wires.json",
    ),
    "output-broken": (
        {"map.json": json.dumps(_MAP), "outputs/bad.json": "{bad"},
        "outputs/bad.json",
    ),
    "output-not-document": (
        {"map.json": json.dumps(_MAP), "outputs/vjoy_1.json": "[1]"},
        "outputs/vjoy_1.json",
    ),
}


@pytest.mark.parametrize("variant", sorted(_BAD_PACKS))
def test_a_bad_pack_is_refused_naming_the_part(lib: dict, variant: str) -> None:
    files, part = _BAD_PACKS[variant]
    pack = lib["tmp"] / f"pack_{variant}.gmap"
    pack.write_bytes(_zip(files))
    before = _snapshot(lib["modules"], lib["folder"])

    described = device_pack.describe_zip(pack)
    assert isinstance(described, str) and part in described, described
    applied = device_pack.apply_zip(
        pack, "pJoy Pro", {"items": ["wire:D"], "outputs": {}}
    )
    assert applied["ok"] is False and part in applied["error"], applied
    previewed = device_pack.preview_import(pack, "pJoy Pro", {"items": ["wire:D"]})
    assert previewed["ok"] is False and part in previewed["error"], previewed
    ids = device_pack.pack_item_ids(pack)
    assert isinstance(ids, str) and part in ids, ids
    imported = library.import_pack(pack)
    assert imported["ok"] is False and part in imported["error"], imported

    assert _snapshot(lib["modules"], lib["folder"]) == before


def test_a_pack_too_big_to_unpack_is_refused(
    lib: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin.modules import pack_checks

    monkeypatch.setattr(pack_checks, "MAX_UNPACKED", 64 * 1024)
    pack = lib["tmp"] / "big.gmap"
    pack.write_bytes(
        _zip({"map.json": json.dumps({**_MAP, "pad": "A" * (200 * 1024)})})
    )
    before = _snapshot(lib["modules"], lib["folder"])
    described = device_pack.describe_zip(pack)
    assert isinstance(described, str) and "too big" in described, described
    applied = device_pack.apply_zip(pack, "pJoy Pro", {"items": ["in.checks"]})
    assert applied["ok"] is False and "too big" in applied["error"]
    imported = library.import_pack(pack)
    assert imported["ok"] is False and "too big" in imported["error"], imported
    assert _snapshot(lib["modules"], lib["folder"]) == before


def test_a_good_pack_still_reads(lib: dict) -> None:
    pack = lib["tmp"] / "good.gmap"
    pack.write_bytes(
        _zip({"map.json": json.dumps(_MAP), "wires.json": json.dumps(_GOOD_WIRES)})
    )
    described = device_pack.describe_zip(pack)
    assert isinstance(described, dict) and described["ok"], described
    imported = library.import_pack(pack)
    assert imported["ok"], imported
    assert (
        imported["setup"]["holds"] == ["bindings"]
        or "bindings" in imported["setup"]["holds"]
    )


def test_a_very_long_exported_name_imports_into_a_short_folder(lib: dict) -> None:
    long_name = "N" * 5000
    pack = lib["tmp"] / "long.gmap"
    pack.write_bytes(
        _zip(
            {
                "map.json": json.dumps(
                    {"device": long_name, "pack": {"exportedName": long_name}}
                )
            }
        )
    )
    imported = library.import_pack(pack)
    assert imported["ok"], imported
    written = Path(imported["setup"]["pack"])
    assert written.is_file()
    assert len(str(written.relative_to(lib["folder"]))) < 200
    assert library.find_device(long_name) is not None
