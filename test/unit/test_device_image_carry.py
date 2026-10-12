# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The Device Image travels with its device (D-03-DEVICE-IMAGE; 03 S52,
08 S8, S43, S49, S75, S80, S113, 10 S11, S18, S22, S26, S61, S62).

Each image is set the way the user sets it (the Home card's Add Image…,
ModuleListModel.setCardImage, or store.set_device_image under it) and then
carried by the real owner of each path:
- History keeps it with the entry; restoring that entry brings the key and
  the file back after a Remove Image.
- A .gmap export holds the file at pictures/<file> and names it.
- Import as a new device takes it; Import onto an existing device takes it
  with the "Device image" row ticked (its default), keeps this device's own
  unticked, and Restore Import puts the old one back.
- A Device Library saved setup holds it and Restore to This Stick brings it.
- Copy Setup to Another Stick and Swap with Another Stick leave each stick's
  own image with that stick.
- The Device Library's device row thumbnail (device_library.device_photo,
  the model's photo field) shows it.
The real store, Device Pack, History, Device Library and its model in an
empty modules folder.
"""

from __future__ import annotations

import json
import time
import zipfile
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import unquote, urlsplit
from urllib.request import url2pathname

import pytest
from PySide6 import QtCore, QtGui

from gremlin import device_initialization, history, library_copy, library_swap
from gremlin import device_library as library
from gremlin.modules import module_file, store
from gremlin.ui import device_pack, history_model, module_model
from test.unit.test_device_library_LW_swap import (  # noqa: F401  # pyright: ignore[reportMissingImports]
    LEFT,
    RIGHT,
    sticks,
)
from test.unit.test_stage1_modules import (  # noqa: F401  # pyright: ignore[reportMissingImports]
    folder,
)

NAME, GUID = "Stick A", "{6C3D1E20-1111-2222-3333-444455556666}"
NEW_NAME, NEW_GUID = "Stick B", "{6C3D1E20-9999-2222-3333-444455556666}"
KEY = "deviceImage"

_APPS: list[QtCore.QCoreApplication] = []


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtGui.QGuiApplication.instance() or QtGui.QGuiApplication([])
    _APPS.append(app)
    yield app


@pytest.fixture
def modules(request: pytest.FixtureRequest) -> Path:
    return request.getfixturevalue(folder.__name__)


def _png(path: Path, color: QtGui.QColor) -> bytes:
    image = QtGui.QImage(8, 4, QtGui.QImage.Format.Format_RGB32)
    image.fill(color)
    path.parent.mkdir(parents=True, exist_ok=True)
    assert image.save(str(path), "PNG")
    return path.read_bytes()


@pytest.fixture
def picks(tmp_path: Path) -> dict[str, Path]:
    where = tmp_path / "picks"
    out = {}
    for name, color in (
        ("red", QtGui.QColor(255, 0, 0)),
        ("blue", QtGui.QColor(0, 0, 255)),
        ("green", QtGui.QColor(0, 255, 0)),
    ):
        path = where / f"{name}.png"
        _png(path, color)
        out[name] = path
    return out


def _settle() -> None:
    for _ in range(6):
        QtCore.QCoreApplication.processEvents()
        time.sleep(0.01)


def _doc(name: str, guid: str, hw: int = 1) -> dict:
    return {
        "kind": "control.hardware",
        "device": name,
        "direction": "source",
        "boundGuidLocal": guid,
        "claim": {"buttons": [1, 2], "axes": [], "hats": [], "friendly": {}},
        "nodes": [{"kind": "btn", "id": f"b{hw}", "hwId": hw}],
    }


def _put(name: str, guid: str, hw: int = 1) -> Path:
    where = store.ensure_device_dir(name, guid)
    module_file.write_bytes(
        store.module_file_in(where), json.dumps(_doc(name, guid, hw)).encode()
    )
    return where


def _read(where: Path) -> dict:
    return store.read_path(store.module_file_in(where))


def _image(where: Path) -> bytes | None:
    """The image file the device's module file names, None when none."""
    ref = str(_read(where).get(KEY) or "")
    if not ref:
        return None
    found = store.find_picture(where, ref)
    return found.read_bytes() if found else None


def _set(name: str, guid: str, src: Path) -> str:
    ref = store.set_device_image(name, guid, src, "Home")
    assert ref.startswith("pictures/device-image"), ref
    return ref


def _plugged_stick() -> tuple[str, str]:
    for dev in device_initialization.physical_devices():
        if dev.name == "pJoy Pro":
            return dev.name, store.guid_text(dev.device_guid)
    pytest.skip("the fake stick is not there")


def _export(where: Path, name: str, guid: str, dest: Path) -> Path:
    plan = device_pack.plan_pack(
        name, lambda ref: store.find_picture(where, ref), guid=guid
    )
    assert isinstance(plan, dict), plan
    dest.write_bytes(device_pack.build_pack(plan)[0])
    return dest


def _pack_rows(path: Path) -> dict[str, dict]:
    described = device_pack.describe_zip(path)
    assert isinstance(described, dict), described
    return {i["id"]: i for s in described["sections"] for i in s["items"]}


def _ticked(path: Path) -> list[str]:
    """The rows Import ticks by default (the user's untouched choice)."""
    return [i for i, row in _pack_rows(path).items() if row.get("checked")]


# --- The Home card writes it (the path every other test starts from) -----------------


def test_the_home_card_writes_the_image_into_the_device_folder(
    modules: Path, picks: dict[str, Path]
) -> None:
    target, target_guid = _plugged_stick()
    there = _put(target, target_guid)
    model = module_model.ModuleListModel()
    try:
        model.reload()
        slug = next(r.slug for r in model._rows if (r.raw_name or r.name) == target)
        assert model.setCardImage(slug, picks["red"].as_uri())
        assert model.cardMap(slug)["hasImage"] is True
    finally:
        model.deleteLater()
    assert _read(there)[KEY] == "pictures/device-image.png"
    assert _image(there) == picks["red"].read_bytes()


# --- History (08 S8, S43) -------------------------------------------------------------


def _history_entries() -> list[dict]:
    deadline = time.monotonic() + 5
    while history._writer is not None and time.monotonic() < deadline:
        time.sleep(0.02)
    return history.entries()


def test_history_keeps_the_image_and_a_restore_brings_it_back(
    modules: Path, picks: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(history_model, "_changed_everywhere", lambda: None)
    where = _put(NAME, GUID)
    ref = _set(NAME, GUID, picks["red"])
    assert store.remove_device_image(NAME, GUID, "Home")
    assert _image(where) is None
    assert not (where / ref).exists()
    entry = next(
        e for e in _history_entries()
        if e.get("kind") == "save"
        and KEY in str((e.get("after") or {}).get("text") or "")
        and KEY not in str((e.get("before") or {}).get("text") or "")
    )  # fmt: skip
    ok, message = history_model._restore_module(entry, entry["after"])
    assert ok, message
    _settle()
    assert _read(where)[KEY] == ref
    assert _image(where) == picks["red"].read_bytes()


# --- .gmap export (08 S49, S113) ------------------------------------------------------


def test_the_gmap_export_holds_the_image(
    modules: Path, picks: dict[str, Path], tmp_path: Path
) -> None:
    where = _put(NAME, GUID)
    ref = _set(NAME, GUID, picks["red"])
    path = _export(where, NAME, GUID, tmp_path / "pack.gmap")
    with zipfile.ZipFile(path) as zf:
        assert ref in zf.namelist(), zf.namelist()
        assert zf.read(ref) == picks["red"].read_bytes()
        module = next(n for n in zf.namelist() if n.endswith(".json") and "module" in n)
        assert json.loads(zf.read(module))[KEY] == ref
    row = _pack_rows(path)["in.image"]
    assert row["title"] == "Device image" and row["checked"] is True


# --- Import (08 S75, S80) -------------------------------------------------------------


def test_import_as_new_takes_the_image(
    modules: Path, picks: dict[str, Path], tmp_path: Path
) -> None:
    where = _put(NAME, GUID)
    _set(NAME, GUID, picks["red"])
    path = _export(where, NAME, GUID, tmp_path / "pack.gmap")
    out = device_pack.import_as_new(
        path, NEW_NAME, {"items": _ticked(path), "targetGuid": NEW_GUID}
    )
    assert out.get("ok"), out
    there = store.device_dir(NEW_NAME, NEW_GUID)
    assert _image(there) == picks["red"].read_bytes()


def _onto_existing(
    picks: dict[str, Path], tmp_path: Path
) -> tuple[Path, Path, str, str]:
    target, target_guid = _plugged_stick()
    where = _put(NAME, GUID)
    _set(NAME, GUID, picks["red"])
    there = _put(target, target_guid, 2)
    _set(target, target_guid, picks["blue"])
    path = _export(where, NAME, GUID, tmp_path / "pack.gmap")
    return path, there, target, target_guid


def test_import_onto_a_device_ticked_takes_the_image_and_restore_import_puts_it_back(
    modules: Path, picks: dict[str, Path], tmp_path: Path
) -> None:
    path, there, target, target_guid = _onto_existing(picks, tmp_path)
    items = _ticked(path)
    assert "in.image" in items, items
    out = device_pack.apply_zip(path, target, {"items": items}, target_guid=target_guid)
    assert out.get("ok"), out
    assert _image(there) == picks["red"].read_bytes()
    back = device_pack.undo_import(force=True)
    assert back.get("ok"), back
    assert _image(there) == picks["blue"].read_bytes()


def test_import_onto_a_device_unticked_keeps_its_own_image(
    modules: Path, picks: dict[str, Path], tmp_path: Path
) -> None:
    path, there, target, target_guid = _onto_existing(picks, tmp_path)
    items = [i for i in _ticked(path) if i != "in.image"]
    out = device_pack.apply_zip(
        path, target, {"items": items}, record_undo=False, target_guid=target_guid
    )
    assert out.get("ok"), out
    assert _image(there) == picks["blue"].read_bytes()


# --- Device Library (10 S11, S18, S22, S26, S61, S62) ---------------------------------


def test_a_library_save_and_restore_to_this_stick_brings_the_image(
    modules: Path, picks: dict[str, Path]
) -> None:
    target, target_guid = _plugged_stick()
    there = _put(target, target_guid)
    _set(target, target_guid, picks["red"])
    saved = library.save_setup(target, target_guid, [])
    assert saved["ok"], saved
    shown = library.photo(saved["setup"]["key"])
    assert shown and Path(shown).read_bytes() == picks["red"].read_bytes()
    assert store.remove_device_image(target, target_guid, "Home")
    assert _image(there) is None
    out = library_copy.restore_to_stick(saved["setup"]["key"])
    assert out.get("ok"), out
    assert _image(there) == picks["red"].read_bytes()


def test_copy_setup_to_another_stick_leaves_each_sticks_image(
    modules: Path, picks: dict[str, Path]
) -> None:
    target, target_guid = _plugged_stick()
    _put(NAME, GUID)
    _set(NAME, GUID, picks["red"])
    there = _put(target, target_guid, 2)
    _set(target, target_guid, picks["blue"])
    saved = library.save_setup(NAME, GUID, [])
    assert saved["ok"], saved
    out = library_copy.copy(
        saved["setup"]["key"], target, target_guid,
        ["setup", "device_map", "appearance", "calibration"], [], [],
    )  # fmt: skip
    assert out["ok"], out
    assert _image(there) == picks["blue"].read_bytes()


def test_swap_with_another_stick_leaves_each_sticks_image(
    modules: Path, picks: dict[str, Path], request: pytest.FixtureRequest
) -> None:
    request.getfixturevalue(sticks.__name__)
    left = store.module_file(*LEFT).parent
    right = store.module_file(*RIGHT).parent
    _set(*LEFT, picks["red"])
    _set(*RIGHT, picks["blue"])
    out = library_swap.swap(
        LEFT, RIGHT, ["setup", "device_map", "appearance", "calibration"], []
    )
    assert out["ok"], out
    assert _image(left) == picks["red"].read_bytes()
    assert _image(right) == picks["blue"].read_bytes()


def _url_file(url: str) -> Path:
    return Path(url2pathname(unquote(urlsplit(url.partition("?t=")[0]).path)))


def test_the_library_row_thumbnail_shows_the_image(
    modules: Path, picks: dict[str, Path]
) -> None:
    from gremlin.ui.device_library_model import DeviceLibraryModel

    where = _put(NAME, GUID)
    _set(NAME, GUID, picks["green"])
    url = library.device_photo(str(where))
    assert url, url
    assert _url_file(url).read_bytes() == picks["green"].read_bytes()
    model = DeviceLibraryModel(watch_devices=False)
    try:
        model.refresh()
        rows = [
            r for r in model.rows if r.get("kind") == "device" and r.get("name") == NAME
        ]
        assert rows, [r.get("name") for r in model.rows]
        assert rows[0]["photo"], rows[0]
        assert _url_file(rows[0]["photo"]).read_bytes() == picks["green"].read_bytes()
    finally:
        model.deleteLater()
