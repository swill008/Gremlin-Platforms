# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Device Mapping Editor in device folders (D-03-DEVICE-FOLDERS, 07 S106-S110).

Pictures added in an edit wait in the edit's temporary folder until Save
(S107), so Cancel leaves nothing; Save removes the pictures the map no
longer names (S106); a missing picture is reported and can be pointed at a
new file (S108); a template is its own folder carried whole by a
".gtemplate" (S80, S110); Copy Device Map from Device copies the pictures
it uses into this device's folder (S109).
"""

from __future__ import annotations

import json
import pathlib

import pytest
from PySide6 import QtGui

from gremlin.modules import store
from gremlin.ui import hardware_profile

DEVICE = "Stick R"
OTHER = "Stick L"


@pytest.fixture
def maps(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> pathlib.Path:
    modules = tmp_path / "modules"
    modules.mkdir()
    monkeypatch.setattr(store, "folder", lambda: modules)
    store._dirs_changed()
    return modules


def _png(path: pathlib.Path, colour: str = "#336699") -> pathlib.Path:
    image = QtGui.QImage(8, 8, QtGui.QImage.Format.Format_RGB32)
    image.fill(QtGui.QColor(colour))
    path.parent.mkdir(parents=True, exist_ok=True)
    assert image.save(str(path))
    return path


def _put_module(name: str, doc: dict) -> pathlib.Path:
    base = store.ensure_device_dir(name)
    path = store.module_file_in(base)
    path.write_text(json.dumps({"device": name, **doc}), encoding="utf-8")
    return base


def _picture_files(root: pathlib.Path) -> list[str]:
    return sorted(
        str(p.relative_to(root)).replace("\\", "/")
        for p in root.rglob("*")
        if p.is_file() and p.suffix.lower() in (".png", ".jpg")
    )


def _payload(image: str = "", nodes: list | None = None) -> str:
    """The editor's Save: the device's photo is the bottom background
    picture, a node like any other (07 S111, S127)."""
    background = [_background_node(image)] if image else []
    return json.dumps({
        "kind": "control.hardware",
        "device": DEVICE,
        "ui": {},
        "nodes": background + (nodes or []),
    })


def _picture_node(ref: str, node_id: str = "p1") -> dict:
    return {"id": node_id, "kind": "draw", "shape": "image", "src": ref}


def _background_node(ref: str) -> dict:
    return {**_picture_node(ref, "bg"), "plane": "background"}


def test_paste_then_cancel_leaves_no_file(maps: pathlib.Path) -> None:
    hp = hardware_profile.HardwareProfile()
    image = QtGui.QImage(8, 8, QtGui.QImage.Format.Format_RGB32)
    image.fill(QtGui.QColor("#993366"))
    ref = hp.savePastedImage(image, DEVICE)
    assert ref == "pictures/pasted.png"
    # It waits in the edit: the device's folder is not touched (S107).
    assert not store.pictures_dir(DEVICE).is_dir()
    assert hp.imageUrl(ref), "the waiting picture shows on the map"
    assert hp.cancelEdit(DEVICE) is True
    assert _picture_files(maps) == []


def test_photo_and_picture_wait_until_save(maps: pathlib.Path) -> None:
    _put_module(DEVICE, {"nodes": []})
    source = _png(maps.parent / "outside" / "red.png", "#993366")
    hp = hardware_profile.HardwareProfile()
    hp.load(DEVICE)
    photo = hp.copyImage(source.as_uri(), DEVICE)
    picture = hp.copyOverlay(source.as_uri(), DEVICE)
    assert photo == "pictures/photo.png"
    assert picture.startswith("pictures/")
    assert not store.pictures_dir(DEVICE).is_dir()
    assert hp.save(DEVICE, _payload(photo, [_picture_node(picture)]))
    names = sorted(p.name for p in store.pictures_dir(DEVICE).iterdir())
    assert names == sorted({"photo.png", picture.split("/")[-1]})
    # The edit ended with the Save: its temporary folder is gone.
    assert not store.edit_temp_dir(DEVICE).exists()


def test_save_removes_an_unused_picture_and_keeps_used_ones(
    maps: pathlib.Path
) -> None:
    base = _put_module(DEVICE, {
        "nodes": [
            _background_node("pictures/photo.png"),
            _picture_node("pictures/a.png"),
            _picture_node("pictures/b.png", "p2"),
        ],
    })
    for name in ("photo.png", "a.png", "b.png"):
        _png(base / "pictures" / name)
    hp = hardware_profile.HardwareProfile()
    hp.load(DEVICE)
    # b.png's picture was deleted from the map in this edit (S106).
    kept = [_picture_node("pictures/a.png")]
    assert hp.save(DEVICE, _payload("pictures/photo.png", kept))
    names = sorted(p.name for p in (base / "pictures").iterdir())
    assert names == ["a.png", "photo.png"]


def test_a_missing_picture_is_reported_and_choose_picture_fixes_it(
    maps: pathlib.Path
) -> None:
    base = _put_module(DEVICE, {"nodes": [_picture_node("pictures/gone.png")]})
    hp = hardware_profile.HardwareProfile()
    hp.load(DEVICE)
    assert hp.pictureMissing("pictures/gone.png") is True
    assert hp.imageUrl("pictures/gone.png") == ""
    new = _png(maps.parent / "outside" / "found.png")
    ref = hp.choosePictureFor("pictures/gone.png", new.as_uri())
    assert ref == "pictures/found.png"
    assert hp.pictureMissing(ref) is False
    assert hp.save(DEVICE, _payload("", [_picture_node(ref)]))
    saved = json.loads((base / "module.json").read_text(encoding="utf-8"))
    assert saved["nodes"][0]["src"] == "pictures/found.png"
    assert (base / "pictures" / "found.png").is_file()


def test_save_keeps_a_missing_picture_named(maps: pathlib.Path) -> None:
    """A missing picture stays named (the placeholder shows it), as
    pictures/<file name>."""
    base = _put_module(DEVICE, {"nodes": []})
    hp = hardware_profile.HardwareProfile()
    hp.load(DEVICE)
    gone = (maps.parent / "elsewhere" / "lost.png").as_uri()
    assert hp.save(DEVICE, _payload("", [_picture_node(gone)]))
    saved = json.loads((base / "module.json").read_text(encoding="utf-8"))
    assert saved["nodes"][0]["src"] == "pictures/lost.png"


def test_copy_device_mapping_editor_from_device_copies_its_pictures(
    maps: pathlib.Path
) -> None:
    other = _put_module(OTHER, {"nodes": [_picture_node("pictures/logo.png")]})
    _png(other / "pictures" / "logo.png", "#00ff00")
    mine = _put_module(DEVICE, {"nodes": []})
    hp = hardware_profile.HardwareProfile()
    hp.load(DEVICE)
    rows = hp.savedLayouts(DEVICE)
    assert [row["slug"] for row in rows] == [other.name]
    nodes = json.loads(hp.layoutNodes(rows[0]["slug"], DEVICE))
    assert nodes[0]["src"] == "pictures/logo.png"
    # Nothing in this device's folder until Save (S109) ...
    assert not (mine / "pictures").is_dir()
    assert hp.save(DEVICE, _payload("", nodes))
    # ... then its own copy: the two devices never share a file (03 S133).
    assert (mine / "pictures" / "logo.png").is_file()
    assert (other / "pictures" / "logo.png").is_file()


def test_copy_then_cancel_leaves_nothing(maps: pathlib.Path) -> None:
    other = _put_module(OTHER, {"nodes": [_picture_node("pictures/logo.png")]})
    _png(other / "pictures" / "logo.png")
    mine = _put_module(DEVICE, {"nodes": []})
    hp = hardware_profile.HardwareProfile()
    hp.load(DEVICE)
    assert hp.layoutNodes(other.name, DEVICE)
    hp.cancelEdit(DEVICE)
    assert not (mine / "pictures").exists()
    assert not store.edit_temp_dir(DEVICE).exists()


def test_a_template_round_trip_carries_its_pictures(
    maps: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    base = _put_module(DEVICE, {"nodes": [_picture_node("pictures/logo.png")]})
    _png(base / "pictures" / "logo.png", "#123456")
    hp = hardware_profile.HardwareProfile()
    hp.load(DEVICE)
    nodes = json.dumps([_picture_node("pictures/logo.png")])
    assert hp.saveTemplate("Flight Deck", nodes, DEVICE)
    folder = store.template_dir("Flight Deck")
    assert (folder / "template.json").is_file()
    assert (folder / "pictures" / "logo.png").is_file()
    # The device can go: the template keeps its own copy (S110).
    out = tmp_path / "shared" / "Flight Deck"
    out.parent.mkdir()
    assert hp.exportTemplate("Flight Deck", out.as_uri()), hp.templateError()
    shared = out.with_name("Flight Deck.gtemplate")
    assert shared.is_file()
    assert hp.deleteTemplate("Flight Deck")
    assert not folder.exists()
    name = hp.importTemplate(shared.as_uri())
    assert name == "Flight Deck"
    assert (store.template_dir(name) / "pictures" / "logo.png").is_file()
    # Applying it to another device copies the picture into that device on Save.
    hp2 = hardware_profile.HardwareProfile()
    hp2.load(OTHER)
    applied = json.loads(hp2.templateNodes(name, OTHER))
    assert applied[0]["src"] == "pictures/logo.png"
    assert hp2.save(OTHER, json.dumps({"nodes": applied}))
    assert (store.pictures_dir(OTHER) / "logo.png").is_file()


def test_rename_template_moves_its_folder(maps: pathlib.Path) -> None:
    _put_module(DEVICE, {"nodes": []})
    hp = hardware_profile.HardwareProfile()
    assert hp.saveTemplate("Old", json.dumps([{"id": "c1", "kind": "chip"}]), DEVICE)
    assert hp.renameTemplate("Old", "New"), hp.templateError()
    assert not store.template_dir("Old").exists()
    assert [row["name"] for row in hp.templates()] == ["New"]


def test_recovery_copy_is_kept_in_the_device_folder(
    maps: pathlib.Path
) -> None:
    base = _put_module(DEVICE, {"nodes": []})
    hp = hardware_profile.HardwareProfile()
    hp.load(DEVICE)
    assert hp.saveRecovery(DEVICE, json.dumps({"nodes": []}))
    assert (base / "recovery.json").is_file()
    assert hp.loadRecovery(DEVICE)
    hp.clearRecovery(DEVICE)
    assert not (base / "recovery.json").exists()
