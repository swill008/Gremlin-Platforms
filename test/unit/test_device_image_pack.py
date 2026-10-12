# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The device image travels with the Device Pack and the Device Library
(D-03-DEVICE-IMAGE; 03 S52, 08 S75, 10 S62, 07 S127).

Export / Import list it as its own "Device image" row in the Input module
section, ticked by default; the old "Device photo" row is gone (the bottom
background picture goes with the Map tick). Ticked, the pack's image
replaces this device's; unticked, this device's stays; Restore Import puts
it back. A Device Library Restore brings it; Copy to Another Stick leaves
each stick's image with that stick. device_library.device_photo(folder)
gives the Device Library's thumbnail. The real store, Device Pack and
Device Library in an empty modules folder.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import url2pathname

import pytest
from PySide6 import QtCore

from gremlin import device_initialization, library_copy
from gremlin import device_library as library
from gremlin.modules import module_file, store
from gremlin.ui import device_pack
from test.unit.test_stage1_modules import (  # noqa: F401  # pyright: ignore[reportMissingImports]
    folder,
)

NAME, GUID = "Stick A", "{6C3D1E20-1111-2222-3333-444455556666}"
IMAGE = "pictures/device-image.png"
PACK_IMG = b"\x89PNG pack image"
OWN_IMG = b"\x89PNG own image"
PHOTO = b"\x89PNG bottom background picture"

_APPS: list[QtCore.QCoreApplication] = []


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


@pytest.fixture
def modules(request: pytest.FixtureRequest) -> Path:
    return request.getfixturevalue(folder.__name__)


def _chip(hw: int = 1) -> dict:
    return {"kind": "btn", "id": f"b{hw}", "hwId": hw}


def _photo(ref: str = "pictures/photo.png", node_id: str = "bg_photo") -> dict:
    return {
        "kind": "draw", "shape": "image", "id": node_id, "src": ref,
        "plane": "background", "fx": 0, "fy": 0, "fw": 1, "fh": 1,
    }  # fmt: skip


def _doc(name: str, guid: str, nodes: list[dict], image: str = "") -> dict:
    doc = {
        "kind": "control.hardware",
        "device": name,
        "direction": "source",
        "boundGuidLocal": guid,
        "claim": {"buttons": [1, 2], "axes": [], "hats": [], "friendly": {}},
        "nodes": nodes,
    }
    if image:
        doc[store.DEVICE_IMAGE_KEY] = image
    return doc


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


def _image_bytes(where: Path) -> bytes | None:
    ref = store.device_image_ref(_read(where))
    if not ref:
        return None
    found = store.find_picture(where, ref)
    return found.read_bytes() if found else None


def _plugged_stick() -> tuple[str, str]:
    for dev in device_initialization.physical_devices():
        if dev.name == "pJoy Pro":
            return dev.name, store.guid_text(dev.device_guid)
    pytest.skip("the fake stick is not there")


def _source() -> Path:
    return _put(
        NAME, GUID, _doc(NAME, GUID, [_chip()], IMAGE),
        {"device-image.png": PACK_IMG},
    )  # fmt: skip


def _export(where: Path, dest: Path) -> Path:
    plan = device_pack.plan_pack(
        NAME, lambda ref: store.find_picture(where, ref), guid=GUID
    )
    assert isinstance(plan, dict), plan
    dest.write_bytes(device_pack.build_pack(plan)[0])
    return dest


def _own(target: str, target_guid: str) -> Path:
    return _put(
        target, target_guid,
        _doc(target, target_guid, [_chip(2)], IMAGE),
        {"device-image.png": OWN_IMG},
    )  # fmt: skip


# --- Export / Import window rows (08 S75) -------------------------------------


def test_the_pack_lists_a_ticked_device_image_row_in_the_input_module_section(
    modules: Path, tmp_path: Path
) -> None:
    path = _export(_source(), tmp_path / "pack.gmap")
    described = device_pack.describe_zip(path)
    assert isinstance(described, dict), described
    rows = {
        item["id"]: (section["id"], item)
        for section in described["sections"]
        for item in section["items"]
    }
    assert "in.image" in rows, rows.keys()
    section, row = rows["in.image"]
    assert section == "input"
    assert row["title"] == "Device image"
    assert row["checked"] is True and row["kind"] == "image"
    url = row["url"]
    assert url and Path(url2pathname(urlsplit(url).path)).read_bytes() == PACK_IMG
    # The preview shows the device image (07 S127 precedence).
    assert described["photoUrl"] == url
    ids = device_pack.pack_item_ids(path)
    assert isinstance(ids, dict), ids
    assert "in.image" in ids["input"]


def test_the_bottom_background_picture_is_a_map_picture_not_a_device_photo_row(
    modules: Path, tmp_path: Path
) -> None:
    where = _put(
        NAME, GUID, _doc(NAME, GUID, [_photo(), _chip()]), {"photo.png": PHOTO}
    )
    path = _export(where, tmp_path / "pack.gmap")
    described = device_pack.describe_zip(path)
    assert isinstance(described, dict), described
    items = [i for s in described["sections"] for i in s["items"]]
    titles = [i["title"] for i in items]
    assert "Device photo" not in titles
    assert "in.image" not in [i["id"] for i in items]
    layout = next(i for i in items if i["id"] == "in.layout")
    assert layout["needs"] == ["pic:photo.png"]


def test_the_map_tick_takes_the_packs_bottom_background_picture() -> None:
    mine = _doc(NAME, "", [_photo("pictures/mine.png", "mine_photo"), _chip(2)])
    incoming = {"nodes": [_photo("photo.png", "in_photo"), _chip(1)]}
    merged, notes = device_pack._merge_module(
        mine, incoming, {"in.layout", "pic:photo.png"}, "in.", NAME, ""
    )
    assert merged["nodes"][0]["id"] == "in_photo", merged["nodes"]
    assert not notes
    kept, _ = device_pack._merge_module(mine, incoming, {"in.checks"}, "in.", NAME, "")
    assert kept["nodes"][0]["id"] == "mine_photo"


# --- Import onto an existing device (08 S75, S80) ------------------------------


def test_ticked_the_packs_image_replaces_this_devices_and_restore_import_puts_it_back(
    modules: Path, tmp_path: Path
) -> None:
    target, target_guid = _plugged_stick()
    path = _export(_source(), tmp_path / "pack.gmap")
    there = _own(target, target_guid)
    out = device_pack.apply_zip(
        path, target, {"items": ["in.checks", "in.image"]},
        target_guid=target_guid,
    )  # fmt: skip
    assert out.get("ok"), out
    assert store.device_image_ref(_read(there)).startswith("pictures/")
    assert _image_bytes(there) == PACK_IMG
    back = device_pack.undo_import(force=True)
    assert back.get("ok"), back
    assert _image_bytes(there) == OWN_IMG


def test_unticked_this_devices_image_stays(modules: Path, tmp_path: Path) -> None:
    target, target_guid = _plugged_stick()
    path = _export(_source(), tmp_path / "pack.gmap")
    there = _own(target, target_guid)
    out = device_pack.apply_zip(
        path, target, {"items": ["in.checks"]}, record_undo=False,
        target_guid=target_guid,
    )  # fmt: skip
    assert out.get("ok"), out
    assert store.device_image_ref(_read(there)) == IMAGE
    assert _image_bytes(there) == OWN_IMG


def test_import_onto_a_device_without_an_image_takes_the_packs(
    modules: Path, tmp_path: Path
) -> None:
    target, target_guid = _plugged_stick()
    path = _export(_source(), tmp_path / "pack.gmap")
    ids = device_pack.pack_item_ids(path)
    assert isinstance(ids, dict), ids
    out = device_pack.apply_zip(
        path, target, {"items": ids["input"]}, record_undo=False,
        target_guid=target_guid,
    )  # fmt: skip
    assert out.get("ok"), out
    assert _image_bytes(store.device_dir(target, target_guid)) == PACK_IMG


def test_history_text_names_the_device_image() -> None:
    text = device_pack.module_text(
        {store.DEVICE_IMAGE_KEY: IMAGE}, [store.DEVICE_IMAGE_KEY]
    )
    assert "Device image:\ndevice-image.png" in text
    assert "Other settings" not in text


# --- Device Library (10 S11, S62) -----------------------------------------------


def test_a_saved_setup_with_only_an_image_holds_the_setup(modules: Path) -> None:
    _put(NAME, GUID, {**_doc(NAME, GUID, [], IMAGE), "claim": {}},
         {"device-image.png": PACK_IMG})  # fmt: skip
    out = library.save_setup(NAME, GUID, [])
    assert out["ok"], out
    assert "setup" in out["setup"]["holds"]
    shown = library.photo(out["setup"]["key"])
    assert shown and Path(shown).read_bytes() == PACK_IMG


def test_a_library_restore_brings_the_image_back(modules: Path) -> None:
    target, target_guid = _plugged_stick()
    there = _own(target, target_guid)
    saved = library.save_setup(target, target_guid, [])
    assert saved["ok"], saved
    store.update_path(
        store.module_file_in(there),
        lambda doc: doc.pop(store.DEVICE_IMAGE_KEY, None),
        "Test",
    )
    assert _image_bytes(there) is None
    out = library_copy.restore_to_stick(saved["setup"]["key"])
    assert out.get("ok"), out
    assert _image_bytes(there) == OWN_IMG


def test_the_librarys_put_back_takes_the_image_and_copy_does_not() -> None:
    ids = ["in.checks", "in.image", "in.layout"]
    assert "in.image" in library_copy._module_items(ids, ["setup"], everything=True)
    assert "in.image" in library_copy._module_items(ids, ["setup"], image=True)
    assert "in.image" not in library_copy._module_items(ids, ["setup", "device_map"])


def test_copy_to_another_stick_leaves_each_sticks_image(modules: Path) -> None:
    target, target_guid = _plugged_stick()
    _source()
    there = _own(target, target_guid)
    saved = library.save_setup(NAME, GUID, [])
    assert saved["ok"], saved
    out = library_copy.copy(
        saved["setup"]["key"], target, target_guid, ["setup", "device_map"], [], []
    )
    assert out["ok"], out
    assert store.device_image_ref(_read(there)) == IMAGE
    assert _image_bytes(there) == OWN_IMG


def test_device_photo_gives_the_shown_photo_of_a_folder(modules: Path) -> None:
    assert library.device_photo("") == ""
    empty = store.ensure_device_dir("Nothing", "")
    assert library.device_photo(str(empty)) == ""
    where = _put(
        NAME, GUID, _doc(NAME, GUID, [_photo(), _chip()], IMAGE),
        {"device-image.png": PACK_IMG, "photo.png": PHOTO},
    )  # fmt: skip
    url = library.device_photo(str(where))
    file_url, _, stamp = url.partition("?t=")
    assert stamp.isdigit()
    assert Path(url2pathname(urlsplit(file_url).path)).read_bytes() == PACK_IMG
    # No device image: the bottom background picture (no generated one here).
    store.update_path(
        store.module_file_in(where),
        lambda doc: doc.pop(store.DEVICE_IMAGE_KEY, None),
        "Test",
    )
    url = library.device_photo(str(where))
    file_url = url.partition("?t=")[0]
    assert Path(url2pathname(urlsplit(file_url).path)).read_bytes() == PHOTO
