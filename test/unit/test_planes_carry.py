# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The background plane travels with the map (D-07-BACKGROUND-PLANES).

Until the device's background picture (pictures/device-photo.png, 07 S157)
is made, the device's photo shown is the bottom background picture (07
S127, the fallback; none of these folders has the file): a map saved in
today's layout has no top-level "image". Device Pack export shows it as
the Device photo and in its preview, and carries every background layer and
its pictures (08 S113); Import's Device photo tick takes the pack's photo
where it was shown (08 S75) and the Map tick the pack's background layers;
a saved setup shows its photo and Copy to Another Stick carries every
background layer (10 S11, S62); the Logical Device card's Add Image and
Module Setup's Save set that same layer (03 S52, S88). The real store,
Device Pack and Device Library in an empty modules folder.
"""

from __future__ import annotations

import json
import struct
import zipfile
import zlib
from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6 import QtCore

from gremlin import device_initialization, library_copy, logical_device_file
from gremlin import device_library as library
from gremlin.logical_device import LogicalDevice
from gremlin.modules import ids, module_file, store
from gremlin.ui import device_pack, module_model
from test.unit.test_stage1_modules import (  # noqa: F401  # pyright: ignore[reportMissingImports]
    folder,
)


def _png(width: int, height: int) -> bytes:
    """A small grey PNG (its size is read for the photo frame fit)."""

    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(
            ">I", zlib.crc32(body) & 0xFFFFFFFF
        )

    rows = b"".join(b"\x00" + b"\x80" * width for _ in range(height))
    header = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(rows))
        + chunk(b"IEND", b"")
    )


PNG = _png(4, 2)
OTHER_PNG = PNG + b"other"
NAME, GUID = "Stick A", "{6C3D1E20-1111-2222-3333-444455556666}"

_APPS: list[QtCore.QCoreApplication] = []


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


@pytest.fixture
def modules(request: pytest.FixtureRequest) -> Path:
    return request.getfixturevalue(folder.__name__)


def _photo(ref: str = "pictures/photo.png", node_id: str = "bg_photo") -> dict:
    return {
        "kind": "draw", "shape": "image", "id": node_id, "src": ref,
        "plane": "background", "fx": 0.2, "fy": 0.1, "fw": 0.6, "fh": 0.3,
        "rot": 12, "opacity": 0.8, "look": {"bright": 0.2},
    }  # fmt: skip


def _bg_shape(node_id: str = "bg_rect") -> dict:
    return {
        "kind": "draw", "shape": "rect", "id": node_id, "plane": "background",
        "fx": 0, "fy": 0, "fw": 1, "fh": 1,
    }  # fmt: skip


def _chip(hw: int = 1) -> dict:
    return {"kind": "btn", "id": f"b{hw}", "hwId": hw}


def _doc(name: str, guid: str, nodes: list[dict]) -> dict:
    return {
        "kind": "control.hardware",
        "device": name,
        "direction": "source",
        "boundGuidLocal": guid,
        "claim": {"buttons": [1, 2], "axes": [], "hats": [], "friendly": {}},
        "nodes": nodes,
    }


def _put(name: str, guid: str, doc: dict, pictures: dict[str, bytes]) -> Path:
    where = store.ensure_device_dir(name, guid)
    for file, data in pictures.items():
        dest = where / store.PICTURES / file
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    module_file.write_bytes(store.module_file_in(where), json.dumps(doc).encode())
    return where


def _read(where: Path) -> dict:
    return store.read_path(store.module_file_in(where))


def _plugged_stick() -> tuple[str, str]:
    for dev in device_initialization.physical_devices():
        if dev.name == "pJoy Pro":
            return dev.name, store.guid_text(dev.device_guid)
    pytest.skip("the fake stick is not there")


# --- Device Pack export (07 S127, 08 S113) ---------------------------------------


def test_export_shows_the_bottom_background_picture_as_the_device_photo(
    modules: Path, tmp_path: Path
) -> None:
    where = _put(
        NAME, GUID, _doc(NAME, GUID, [_photo(), _bg_shape(), _chip()]),
        {"photo.png": PNG},
    )  # fmt: skip

    def resolve(ref: str) -> Path | None:
        return store.find_picture(where, ref)

    plan = device_pack.plan_pack(NAME, resolve, guid=GUID)
    assert isinstance(plan, dict), plan
    # The preview's picture (packExportPhoto) is the bottom background picture.
    assert plan["photoPath"] and Path(plan["photoPath"]).read_bytes() == PNG
    data, _info = device_pack.build_pack(plan)
    path = tmp_path / "pack.gmap"
    path.write_bytes(data)
    with zipfile.ZipFile(path) as zf:
        packed = json.loads(zf.read("module.json"))
        assert "image" not in packed and "photo" not in packed
        bg = [n for n in packed["nodes"] if store.is_background(n)]
        assert [n["id"] for n in bg] == ["bg_photo", "bg_rect"]
        assert bg[0]["look"] == {"bright": 0.2} and bg[0]["rot"] == 12
        assert zf.read(bg[0]["src"]) == PNG
    described = device_pack.describe_zip(path)
    assert isinstance(described, dict), described
    assert described["photoUrl"]
    titles = [i["title"] for s in described["sections"] for i in s["items"]]
    # Old: a "Device photo" row; it is gone (D-03-DEVICE-IMAGE 1a): the bottom
    # background picture travels with the Map tick as a map picture.
    assert "Device photo" not in titles
    assert "Map picture 1" in titles


def test_export_of_an_old_map_carries_its_photo_as_a_layer(
    modules: Path, tmp_path: Path
) -> None:
    """OT-2: a map saved before the planes is read in today's layout when
    its .gmap is imported (the .gmap carries the module file as it is)."""
    old = _doc(NAME, GUID, [_chip()])
    old["image"] = "pictures/photo.png"
    old["photo"] = {"scale": 1.0, "fade": 0.25}
    where = _put(NAME, GUID, old, {"photo.png": PNG})
    plan = device_pack.plan_pack(
        NAME, lambda ref: store.find_picture(where, ref), guid=GUID
    )
    assert isinstance(plan, dict), plan
    assert plan["photoPath"]
    path = tmp_path / "old.gmap"
    path.write_bytes(device_pack.build_pack(plan)[0])
    loaded = device_pack._read_zip(path)
    assert isinstance(loaded, dict), loaded
    packed = loaded["doc"]
    assert "image" not in packed and "photo" not in packed
    first = packed["nodes"][0]
    assert store.is_background(first) and first["shape"] == "image"
    assert first["opacity"] == pytest.approx(0.75)


# --- Device Pack import (08 S75, S113) -------------------------------------------


def _mine() -> dict:
    """This device's map: its photo, a background layer and a chip."""
    nodes = [_photo("pictures/mine.png"), _bg_shape("mine_rect"), _chip(2)]
    return _doc(NAME, "", nodes)


def _incoming() -> dict:
    return {
        "nodes": [
            _photo("photo.png", "in_photo"),
            _bg_shape("in_rect"),
            _chip(1),
        ]
    }


def test_the_photo_tick_takes_the_packs_photo_where_it_was_shown() -> None:
    """Old: a Device photo tick alone put the pack's photo in place of this
    one. That row is gone (D-03-DEVICE-IMAGE 1a): the pack's bottom picture
    comes with the Map tick and its picture's tick, where it was shown."""
    alone, _notes = device_pack._merge_module(
        _mine(), _incoming(), {"pic:photo.png"}, "in.", NAME, ""
    )
    # The picture's tick on its own changes nothing of the map.
    assert [n["id"] for n in alone["nodes"]] == ["bg_photo", "mine_rect", "b2"]
    assert store.device_photo_ref(alone) == "pictures/mine.png"
    merged, notes = device_pack._merge_module(
        _mine(), _incoming(), {"in.layout", "pic:photo.png"}, "in.", NAME, ""
    )
    nodes = merged["nodes"]
    assert [n["id"] for n in nodes][:2] == ["in_photo", "in_rect"]
    assert nodes[0]["fx"] == 0.2 and nodes[0]["look"] == {"bright": 0.2}
    assert store.device_photo_ref(merged) == "pictures/photo.png"
    assert not notes


def test_the_map_tick_takes_the_packs_background_and_keeps_this_photo() -> None:
    base = _mine()
    merged, _notes = device_pack._merge_module(
        base, _incoming(), {"in.layout"}, "in.", NAME, ""
    )
    ids_ = [n["id"] for n in merged["nodes"]]
    # Background first. Old: this device's photo was kept (the Device photo
    # row decided it); now the Map tick takes the pack's whole background,
    # its bottom picture too (D-03-DEVICE-IMAGE 1a).
    assert ids_[:2] == ["in_photo", "in_rect"]
    assert "mine_rect" not in ids_ and "bg_photo" not in ids_
    assert set(ids_[2:]) == {"b1", "b2"}
    # Its picture was not ticked: left out, and said so.
    assert not merged["nodes"][0].get("src")
    assert store.device_photo_ref(merged) == ""
    assert any("not ticked" in note for note in _notes)


def test_a_pack_without_background_keeps_this_devices_background() -> None:
    base = _mine()
    merged, _notes = device_pack._merge_module(
        base, {"nodes": [_chip(1)]}, {"in.layout"}, "in.", NAME, ""
    )
    ids_ = [n["id"] for n in merged["nodes"]]
    assert ids_[:2] == ["bg_photo", "mine_rect"]


def test_import_writes_the_background_pictures_into_the_device_folder(
    modules: Path, tmp_path: Path
) -> None:
    target, target_guid = _plugged_stick()
    source = _put(
        NAME, GUID, _doc(NAME, GUID, [_photo(), _chip()]), {"photo.png": PNG}
    )
    plan = device_pack.plan_pack(
        NAME, lambda ref: store.find_picture(source, ref), guid=GUID
    )
    assert isinstance(plan, dict), plan
    path = tmp_path / "pack.gmap"
    path.write_bytes(device_pack.build_pack(plan)[0])
    items = device_pack.pack_item_ids(path)
    assert isinstance(items, dict), items
    assert any(i.startswith("pic:") for i in items["input"])
    out = device_pack.apply_zip(
        path, target, {"items": items["input"]}, record_undo=False,
        target_guid=target_guid,
    )  # fmt: skip
    assert out.get("ok"), out
    there = store.device_dir(target, target_guid)
    doc = _read(there)
    assert "image" not in doc
    ref = store.device_photo_ref(doc)
    assert ref.startswith("pictures/"), ref
    assert store.picture_path(there, ref).read_bytes() == PNG


# --- Device Library (10 S11, S62) ------------------------------------------------


def test_a_saved_setup_shows_its_bottom_background_picture(modules: Path) -> None:
    _put(NAME, GUID, _doc(NAME, GUID, [_photo(), _chip()]), {"photo.png": PNG})
    out = library.save_setup(NAME, GUID, [])
    assert out["ok"], out
    setup = out["setup"]
    assert "device_map" in setup["holds"]
    shown = library.photo(setup["key"])
    assert shown and Path(shown).read_bytes() == PNG


def test_copy_to_another_stick_carries_every_background_layer(modules: Path) -> None:
    target, target_guid = _plugged_stick()
    _put(
        NAME, GUID, _doc(NAME, GUID, [_photo(), _bg_shape(), _chip()]),
        {"photo.png": PNG},
    )  # fmt: skip
    there = _put(
        target, target_guid,
        _doc(target, target_guid, [_photo("pictures/own.png", "own_photo"),
                                   _bg_shape("own_rect")]),
        {"own.png": OTHER_PNG},
    )  # fmt: skip
    saved = library.save_setup(NAME, GUID, [])
    assert saved["ok"], saved
    out = library_copy.copy(
        saved["setup"]["key"], target, target_guid, ["setup", "device_map"], [], []
    )
    assert out["ok"], out
    doc = _read(there)
    bg = [n["id"] for n in doc["nodes"] if store.is_background(n)]
    assert bg == ["bg_photo", "bg_rect"]
    assert all(store.is_background(n) for n in doc["nodes"][: len(bg)])
    ref = store.device_photo_ref(doc)
    assert store.picture_path(there, ref).read_bytes() == PNG


# --- The Logical Device card's Add Image (03 S88, 07 S127) -----------------------


@pytest.fixture
def ld(modules: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[LogicalDevice]:
    monkeypatch.setattr(library, "_connected", lambda: [])
    device = LogicalDevice()
    kept = device.to_dict()
    layout = {"controls": [], "groups": []}
    doc = {
        "kind": "control.hardware",
        "device": "Logical Device",
        "boundGuidLocal": "{" + str(ids.LOGICAL_DEVICE).upper() + "}",
        "nodes": [_chip()],
        "claim": {},
        logical_device_file.KEY: layout,
    }
    store.ensure_device_dir("Logical Device", str(ids.LOGICAL_DEVICE))
    module_file.write_bytes(logical_device_file.path(), json.dumps(doc).encode())
    device.load_dict(layout)
    yield device
    device.load_dict(kept)


def test_add_image_on_the_logical_device_card_sets_the_bottom_background_picture(
    ld: LogicalDevice, tmp_path: Path
) -> None:
    source = tmp_path / "card.png"
    source.write_bytes(PNG)
    model = module_model.ModuleListModel()
    assert model.setCardImage("logical", source.as_uri())
    doc = json.loads(logical_device_file.path().read_text(encoding="utf-8-sig"))
    assert "image" not in doc
    assert store.device_photo_ref(doc) == "pictures/photo.png"
    assert store.is_background(doc["nodes"][0])
    assert model.removeCardImage("logical")
    doc = json.loads(logical_device_file.path().read_text(encoding="utf-8-sig"))
    assert store.device_photo_ref(doc) == ""
    assert [n["id"] for n in doc["nodes"]] == ["b1"]
