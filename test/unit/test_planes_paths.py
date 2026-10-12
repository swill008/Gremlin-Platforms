# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The background travels through every path that carries a map
(D-07-BACKGROUND-PLANES; CLAUDE.md working standard 4).

A map's background is its nodes with "plane": "background" (07 S111), the
bottom background picture is the device's photo (07 S127). Each path puts
back every background node as it was (its plane key, its place in the
order) and every picture it names:

- History: a Device Mapping Editor Save is an entry; Restore puts the background
  layers and their pictures back (08 S114).
- Device folder file (.gmap): export, then import into an empty modules
  folder (08 S111, S113).
- Device Library: save a setup, change the background, Restore to This
  Stick / Restore (10 S11, S48).
- Device Pack: export, change the background, import with every item
  ticked (Map and Device photo): the pack's background in its order (08
  S75, S113).

The real store, History, Device Library, Device Pack and Device Mapping Editor Save
(HardwareProfile.save) in an empty modules folder; the fake stick.
"""

from __future__ import annotations

import copy
import json
import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6 import QtCore

from gremlin import device_initialization, history, library_copy
from gremlin import device_library as library
from gremlin.modules import device_zip, module_file, store
from gremlin.ui import device_pack, hardware_profile, history_model
from test.unit.test_planes_carry import _png  # pyright: ignore[reportMissingImports]
from test.unit.test_stage1_modules import (  # noqa: F401  # pyright: ignore[reportMissingImports]
    folder,
    settle_history,
)

pytestmark = pytest.mark.validate_off

PHOTO = _png(4, 2)
KNOB = _png(3, 3)
NEW_PHOTO = _png(5, 1)

_APPS: list[QtCore.QCoreApplication] = []


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


@pytest.fixture
def stick(request: pytest.FixtureRequest) -> tuple[str, str]:
    """The fake plugged-in stick, in an empty modules folder."""
    request.getfixturevalue(folder.__name__)
    for dev in device_initialization.physical_devices():
        if dev.name == "pJoy Pro":
            return dev.name, store.guid_text(dev.device_guid)
    pytest.skip("the fake stick is not there")


# --- the maps ---------------------------------------------------------------------


def _background_a() -> list[dict]:
    """Three background layers, bottom first: the photo, a shape, a second
    picture; each with its own look so a swap or a loss shows."""
    return [
        {"kind": "draw", "shape": "image", "id": "bg_photo", "plane": "background",
         "src": "pictures/photo.png", "fx": 0.2, "fy": 0.1, "fw": 0.6, "fh": 0.3,
         "rot": 12, "opacity": 0.8, "look": {"bright": 0.2}},
        {"kind": "draw", "shape": "rect", "id": "bg_rect", "plane": "background",
         "fx": 0, "fy": 0, "fw": 1, "fh": 1},
        {"kind": "draw", "shape": "image", "id": "bg_knob", "plane": "background",
         "src": "pictures/knob.png", "fx": 0.5, "fy": 0.5, "fw": 0.1, "fh": 0.1,
         "look": {"grey": 1}},
    ]  # fmt: skip


def _foreground() -> list[dict]:
    return [
        {"kind": "draw", "shape": "rect", "id": "fg_rect", "fx": 0.1, "fy": 0.1,
         "fw": 0.2, "fh": 0.2},
        {"kind": "btn", "id": "b1", "hwId": 1},
    ]  # fmt: skip


def _background_b() -> list[dict]:
    """What the background is changed to: one other picture."""
    return [
        {"kind": "draw", "shape": "image", "id": "bg_new", "plane": "background",
         "src": "pictures/new.png", "fx": 0, "fy": 0, "fw": 1, "fh": 1},
    ]  # fmt: skip


_PICTURES_A = {"photo.png": PHOTO, "knob.png": KNOB}


def _map(name: str, guid: str, nodes: list[dict]) -> dict:
    return {
        "kind": "control.hardware",
        "device": name,
        "direction": "source",
        "boundGuidLocal": guid,
        "claim": {"buttons": [1, 2], "axes": [], "hats": [], "friendly": {}},
        "nodes": nodes,
    }


def _put(name: str, guid: str, doc: dict, pictures: dict[str, bytes]) -> Path:
    """The device folder with its pictures and module file (one store write)."""
    where = store.ensure_device_dir(name, guid)
    for file, data in pictures.items():
        store.put_picture_at(where / store.PICTURES / file, data)
    module_file.write_bytes(store.module_file_in(where), json.dumps(doc).encode())
    return where


def _read(where: Path) -> dict:
    return store.read_path(store.module_file_in(where))


def _device_map_save(name: str, guid: str, nodes: list[dict]) -> None:
    """The Device Mapping Editor's Save (07 S12), not in an edit: the pictures are in
    the device's folder already."""
    hw = hardware_profile.HardwareProfile()
    hw.setDeviceGuid(guid)
    assert hw.save(name, json.dumps({"nodes": nodes}))


def _change_background(name: str, guid: str, where: Path) -> None:
    """Background B instead of A; A's pictures are no longer named, so the
    save removes them from the folder (07 S106)."""
    store.put_picture_at(where / store.PICTURES / "new.png", NEW_PHOTO)
    _device_map_save(name, guid, _background_b() + _foreground())
    doc = _read(where)
    assert [n["id"] for n in doc["nodes"] if store.is_background(n)] == ["bg_new"]
    assert not (where / store.PICTURES / "photo.png").exists()


def check_background(
    doc: dict, where: Path, expected: list[dict], pictures: dict[str, bytes]
) -> None:
    """The map's background is exactly expected (every key, the plane key
    too, in order, at the bottom of the nodes) and every picture it names
    is in the device's folder with its bytes."""
    nodes = doc.get("nodes") or []
    background = [n for n in nodes if store.is_background(n)]
    assert background == expected
    assert nodes[: len(background)] == background, "background not at the bottom"
    assert "image" not in doc and "photo" not in doc
    assert store.device_photo_ref(doc) == expected[0]["src"]
    for node in background:
        if node.get("shape") != "image":
            continue
        ref = str(node["src"])
        path = store.picture_path(where, ref)
        assert path.is_file(), f"{ref} is missing"
        assert path.read_bytes() == pictures[Path(ref).name], f"{ref} differs"


# --- the check fails when the plane key or a picture is dropped --------------------


def test_the_check_fails_when_the_plane_key_or_a_picture_is_dropped(
    tmp_path: Path,
) -> None:
    """Every path below ends in check_background: a copy with one plane key
    dropped, or a picture missing, must not pass it."""
    where = tmp_path / "dev"
    (where / store.PICTURES).mkdir(parents=True)
    for file, data in _PICTURES_A.items():
        (where / store.PICTURES / file).write_bytes(data)
    doc = _map("X", "", _background_a() + _foreground())
    check_background(doc, where, _background_a(), _PICTURES_A)

    for index in range(len(_background_a())):
        dropped = copy.deepcopy(doc)
        del dropped["nodes"][index]["plane"]
        with pytest.raises(AssertionError):
            check_background(dropped, where, _background_a(), _PICTURES_A)
    moved = copy.deepcopy(doc)
    moved["nodes"][0], moved["nodes"][2] = moved["nodes"][2], moved["nodes"][0]
    with pytest.raises(AssertionError):
        check_background(moved, where, _background_a(), _PICTURES_A)
    for file in _PICTURES_A:
        aside = tmp_path / file
        shutil.move(str(where / store.PICTURES / file), str(aside))
        with pytest.raises(AssertionError):
            check_background(doc, where, _background_a(), _PICTURES_A)
        shutil.move(str(aside), str(where / store.PICTURES / file))


# --- 1. History (08 S114) ---------------------------------------------------------


def test_history_restore_puts_the_background_and_its_pictures_back(
    stick: tuple[str, str],
) -> None:
    name, guid = stick
    where = _put(name, guid, _map(name, guid, _foreground()), _PICTURES_A)
    _device_map_save(name, guid, _background_a() + _foreground())
    saved_a = _read(where)
    check_background(saved_a, where, _background_a(), _PICTURES_A)
    settle_history()
    before = {str(e.get("id")) for e in history.entries()}

    _change_background(name, guid, where)
    settle_history()
    file_name = f"{where.name}/{store.MODULE_FILE}"
    new = [
        e
        for e in history.entries()
        if str(e.get("id")) not in before
        and (e.get("subject") or {}).get("fileName") == file_name
    ]
    assert len(new) == 1, new
    entry = new[0]
    assert entry["area"] == "device-mapping-editor"
    kept = {p["ref"] for p in entry["before"]["pictures"] if p["keptFile"]}
    assert kept >= {"pictures/photo.png", "pictures/knob.png"}

    out = history_model.restore(str(entry["id"]), "before")
    assert out["ok"], out
    doc = _read(where)
    check_background(doc, where, _background_a(), _PICTURES_A)
    assert doc["nodes"] == saved_a["nodes"]


# --- 2. Device folder file .gmap (08 S111, S113) ----------------------------------


def test_gmap_export_then_import_keeps_every_background_layer(
    stick: tuple[str, str], tmp_path: Path
) -> None:
    name, guid = stick
    where = _put(
        name, guid, _map(name, guid, _background_a() + _foreground()), _PICTURES_A
    )
    out = tmp_path / "out" / "stick.gmap"
    out.parent.mkdir()
    assert device_zip.export_device(name, guid, out, None) == ""

    # An empty modules folder: the device's folder is gone.
    shutil.rmtree(where)
    assert not any(store.folder().iterdir())
    done = device_zip.import_device(out)
    key, problem = done["key"], done["error"]
    assert problem == "", problem
    assert key == store.id_key(name, guid)
    there = store.device_dir(name, guid)
    doc = _read(there)
    check_background(doc, there, _background_a(), _PICTURES_A)
    assert doc["nodes"] == _background_a() + _foreground()


# --- 3. Device Library (10 S11, S48) ----------------------------------------------


@pytest.mark.parametrize("how", ["restore_to_stick", "restore"])
def test_library_restore_puts_the_background_back(
    stick: tuple[str, str], how: str
) -> None:
    name, guid = stick
    where = _put(
        name, guid, _map(name, guid, _background_a() + _foreground()), _PICTURES_A
    )
    saved = library.save_setup(name, guid, [])
    assert saved["ok"], saved
    _change_background(name, guid, where)

    out = getattr(library_copy, how)(saved["setup"]["key"])
    assert out["ok"], out
    doc = _read(where)
    check_background(doc, where, _background_a(), _PICTURES_A)
    assert [n["id"] for n in doc["nodes"]] == [
        "bg_photo", "bg_rect", "bg_knob", "fg_rect", "b1",
    ]  # fmt: skip


# --- 4. Device Pack round trip, Map and Device photo ticked (08 S75, S113) ---------


def test_device_pack_round_trip_keeps_the_background_in_order(
    stick: tuple[str, str], tmp_path: Path
) -> None:
    """test_planes_carry checks each tick on its own (_merge_module) and that
    an import writes the photo; this is the whole round trip onto the same
    stick with every item ticked: all three layers, in their order."""
    name, guid = stick
    where = _put(
        name, guid, _map(name, guid, _background_a() + _foreground()), _PICTURES_A
    )
    plan = device_pack.plan_pack(
        name, lambda ref: store.find_picture(where, ref), guid=guid
    )
    assert isinstance(plan, dict), plan
    path = tmp_path / "pack.zip"
    path.write_bytes(device_pack.build_pack(plan)[0])
    _change_background(name, guid, where)

    items = device_pack.pack_item_ids(path)
    assert isinstance(items, dict), items
    ticked = items["input"]
    assert any(i.startswith("pic:") for i in ticked), ticked
    assert any(i.endswith(".layout") for i in ticked), ticked
    out = device_pack.apply_zip(
        path, name, {"items": ticked}, record_undo=False, target_guid=guid
    )
    assert out.get("ok"), out
    doc = _read(where)
    background = [n for n in doc["nodes"] if store.is_background(n)]
    # The pack's pictures may be renamed on the way in; everything else of
    # each layer, its plane key and its place are kept.
    assert [n["id"] for n in background] == ["bg_photo", "bg_rect", "bg_knob"]
    renamed = {n["id"]: n.get("src") for n in background}
    expected = [
        n | ({"src": renamed[n["id"]]} if "src" in n else {}) for n in _background_a()
    ]
    pictures = {
        Path(str(renamed[n["id"]])).name: _PICTURES_A[Path(n["src"]).name]
        for n in _background_a()
        if "src" in n
    }
    check_background(doc, where, expected, pictures)
