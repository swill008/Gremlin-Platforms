# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Export / Import Device writes and reads .gmap only (D-FIXLIST-B2).

Export goes through device_zip.build_gmap (Made by, Note, the chosen
modes); no .zip pack is written or read. Import takes a target: "existing"
(today's merge) or "new" (a new device folder, device_zip.import_device),
and Undo Import covers both. Runs through the HardwareProfile slots the
window calls.
"""

# The pack fixture is shared with test_device_pack_import (F811: its
# name is the test argument).
# ruff: noqa: F811

from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path

import pytest

from gremlin import shared_state
from gremlin.modules import store as module_store
from gremlin.ui import device_pack
from gremlin.ui.hardware_profile import HardwareProfile
from test.unit.test_device_pack_import import _targets, pack  # noqa: F401


def _items(described: dict) -> dict:
    items, outputs = [], {}
    for section in described.get("sections") or []:
        if str(section.get("id", "")).startswith("out:"):
            outputs[str(section["id"])[4:]] = section.get("target") or ""
        for item in section.get("items") or []:
            if item.get("checked") is not False:
                items.append(item["id"])
    return {"items": items, "outputs": outputs}


def test_export_writes_gmap_with_made_by_note_and_modes(
    pack: dict, tmp_path: Path
) -> None:
    hw = HardwareProfile()
    dest = tmp_path / "out" / "stick.zip"
    dest.parent.mkdir()
    options = json.dumps({"modes": ["Default"], "author": "Sam", "note": "F-16"})
    result = json.loads(hw.exportPack(pack["name"], dest.as_uri(), options))
    assert result["ok"], result
    written = Path(result["path"])
    assert written.suffix == ".gmap"
    assert not dest.exists()
    with zipfile.ZipFile(written) as zf:
        names = zf.namelist()
        label = json.loads(zf.read("gmap.json"))
    assert "map.json" not in names
    assert label["madeBy"] == "Sam"
    assert label["note"] == "F-16"
    assert label["modes"] == ["Default"]
    described = json.loads(hw.peekPackZip(written.as_uri()))
    assert described["ok"], described
    assert described["notes"]["author"] == "Sam"
    assert described["madeBy"] == "Sam"
    assert described["note"] == "F-16"


def test_old_zip_pack_is_not_read(tmp_path: Path) -> None:
    path = tmp_path / "old.zip"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("map.json", json.dumps({"device": "pJoy Pro", "nodes": []}))
    described = device_pack.describe_zip(path)
    assert isinstance(described, str)
    assert "gmap.json" in described


def test_peek_says_whether_the_device_has_a_folder(pack: dict) -> None:
    hw = HardwareProfile()
    described = json.loads(hw.peekPackZip(pack["zip"].as_uri()))
    assert described["deviceHasFolder"] is True
    shutil.rmtree(module_store.device_dir(pack["name"]))
    described = json.loads(hw.peekPackZip(pack["zip"].as_uri()))
    assert described["deviceHasFolder"] is False


def test_import_as_new_device_and_undo(pack: dict) -> None:
    hw = HardwareProfile()
    folder = module_store.device_dir(pack["name"])
    shutil.rmtree(folder)
    assert not folder.exists()
    described = json.loads(hw.peekPackZip(pack["zip"].as_uri()))
    selection = _items(described)
    selection["target"] = "new"
    preview = json.loads(
        hw.previewPackImport(pack["zip"].as_uri(), "", json.dumps(selection))
    )
    assert preview["ok"], preview
    assert preview["target"] == "new"
    result = json.loads(hw.importPack(pack["zip"].as_uri(), "", json.dumps(selection)))
    assert result["ok"], result
    made = module_store.device_dir(pack["name"])
    assert module_store.module_file_in(made).is_file()
    doc = json.loads(module_store.module_file_in(made).read_text(encoding="utf-8"))
    assert doc["claim"]["buttons"] == [1, 2]
    profile = shared_state.current_profile
    assert 1 in _targets(profile, pack["uid"], "Default")
    assert hw.canUndoPackImport()
    undone = json.loads(hw.undoPackImport(True))
    assert undone["ok"], undone
    assert not module_store.module_file_in(made).exists()
    assert not made.exists()
    assert 1 not in _targets(profile, pack["uid"], "Default")


def test_import_as_new_device_refused_when_its_id_has_a_folder(pack: dict) -> None:
    hw = HardwareProfile()
    own = module_store.module_file(pack["name"])
    before = own.read_bytes()
    folders = sorted(p.name for p in module_store.folder().iterdir())
    described = json.loads(hw.peekPackZip(pack["zip"].as_uri()))
    selection = _items(described)
    selection["target"] = "new"
    result = json.loads(hw.importPack(pack["zip"].as_uri(), "", json.dumps(selection)))
    assert not result["ok"]
    assert "already has a device folder" in result["error"]
    assert own.read_bytes() == before
    assert sorted(p.name for p in module_store.folder().iterdir()) == folders


def _twin_file(pack: dict, tmp_path: Path) -> Path:
    """The pack as if exported from another stick of the same name."""
    other = "{99999999-8888-7777-6666-555555555555}"
    path = tmp_path / "twin.gmap"
    with zipfile.ZipFile(pack["zip"]) as src, zipfile.ZipFile(path, "w") as out:
        for name in src.namelist():
            data = src.read(name)
            if name == "gmap.json":
                label = json.loads(data)
                label["id"] = other.strip("{}").replace("-", "").upper()
                data = json.dumps(label).encode("utf-8")
            out.writestr(name, data)
    return path


def test_a_twin_file_has_no_folder_here_and_comes_in_as_2_with_its_wires(
    pack: dict, tmp_path: Path
) -> None:
    hw = HardwareProfile()
    twin = _twin_file(pack, tmp_path)
    described = json.loads(hw.peekPackZip(twin.as_uri()))
    assert described["deviceHasFolder"] is False
    selection = _items(described)
    selection["target"] = "new"
    result = json.loads(hw.importPack(twin.as_uri(), "", json.dumps(selection)))
    assert result["ok"], result
    assert result["folder"] == f"{pack['name']} (2)"
    assert "no device id" not in result["report"]
    made = module_store.folder() / result["folder"]
    assert module_store.module_file_in(made).is_file()
    assert json.loads(hw.undoPackImport(True))["ok"]
    assert not made.exists()


def test_import_onto_existing_device_still_merges(pack: dict) -> None:
    hw = HardwareProfile()
    described = json.loads(hw.peekPackZip(pack["zip"].as_uri()))
    selection = _items(described)
    selection["target"] = "existing"
    result = json.loads(
        hw.importPack(pack["zip"].as_uri(), pack["name"], json.dumps(selection))
    )
    assert result["ok"], result
    assert hw.canUndoPackImport()
    assert json.loads(hw.undoPackImport(True))["ok"]


@pytest.mark.parametrize("given", ["pack.zip", "pack", "pack.gmap"])
def test_export_destination_is_gmap(tmp_path: Path, given: str) -> None:
    dest = HardwareProfile._pack_dest((tmp_path / given).as_uri())
    assert isinstance(dest, Path)
    assert dest.suffix == ".gmap"


def test_default_export_name_is_gmap() -> None:
    url = HardwareProfile().defaultExportUrl("pJoy Pro")
    assert url.endswith(".gmap")
    assert "_map" not in url
