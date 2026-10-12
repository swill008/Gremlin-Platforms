# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Which device folder a device uses (audit 3, D-03-DEVICE-FOLDERS).

A renamed stick opens its folder (found by its id, 03 S130), but its Button
Map photo, "not saved yet" label, Delete Module File and Delete Device went
by its new name. An old second file marked output naming a stick blocked
it at Run. A module file that isn't UTF-8 stopped Home. The Home card order
kept a deleted device's place for good, put a renamed stick last, and a
drag dropped hidden cards' places. History recorded a delete before it
happened.
"""

from __future__ import annotations

import json
import pathlib
import shutil
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6 import QtCore

from gremlin import device_initialization, history, util
from gremlin.modules import calibration, registry
from gremlin.modules import store as module_store
from gremlin.modules.ids import guid_key, stored_guid_key
from gremlin.types import InputType
from gremlin.ui import hardware_profile, module_model

_APPS: list[QtCore.QCoreApplication] = []
_CLAIM = {"buttons": [1], "axes": [], "hats": [], "keys": []}


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


@pytest.fixture
def folder(tmp_path: Path) -> Iterator[Path]:
    """The modules folder, empty of device folders (those other tests left
    are put aside), put back as it was afterwards."""
    path = util.modules_dir()
    path.mkdir(parents=True, exist_ok=True)
    aside = tmp_path / "aside"
    aside.mkdir()
    for old in list(path.iterdir()):
        shutil.move(str(old), str(aside / old.name))
    module_store._dirs_changed()
    order = module_model._order_slugs()
    hidden = module_model._hidden_slugs()
    yield path
    for extra in list(path.iterdir()):
        if extra.is_dir():
            shutil.rmtree(extra, ignore_errors=True)
        else:
            extra.unlink(missing_ok=True)
    for old in aside.iterdir():
        shutil.move(str(old), str(path / old.name))
    module_store._dirs_changed()
    module_model._set_order(order)
    module_model._set_hidden(hidden)


def _pjoy_guid() -> str:
    dev = next(
        d for d in device_initialization.physical_devices() if d.name == "pJoy Pro"
    )
    return str(dev.device_guid)


def _write(folder: Path, name: str, doc: dict, ident: str = "") -> Path:
    """<folder>/<name>/module.json, its device.json holding ident (the
    device's id key; by default the doc's boundGuidLocal, else name:<slug>)."""
    base = folder / name
    base.mkdir(parents=True, exist_ok=True)
    key = ident or stored_guid_key(doc.get("boundGuidLocal") or "")
    if not key:
        key = "name:" + registry.plain_slug(name)
    (base / "device.json").write_text(
        json.dumps({"format": 1, "id": key, "name": name}), encoding="utf-8"
    )
    path = base / "module.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    module_store._dirs_changed()
    return path


def _renamed(folder: Path) -> str:
    """pJoy Pro was "Old Name": its folder is Old Name, holding its id."""
    guid = _pjoy_guid()
    _write(
        folder,
        "Old Name",
        {
            "kind": "control.hardware",
            "device": "Old Name",
            "direction": "source",
            "boundGuidLocal": guid,
            "claim": _CLAIM,
        },
    )
    assert module_store.device_dir("pJoy Pro", guid) == folder / "Old Name"
    return guid


# --- Item 7: a renamed stick ------------------------------------------------


def test_renamed_sticks_photo_goes_with_the_file_its_device_mapping_editor_opens(
    folder: Path, tmp_path: Path
) -> None:
    guid = _renamed(folder)
    own = folder / "Old Name"
    picture = tmp_path / "shot.jpg"
    picture.write_bytes(b"\xff\xd8\xff\xd9")
    hw = hardware_profile.HardwareProfile()
    hw.setDeviceGuid(guid)

    hw.beginEdit("pJoy Pro")
    rel = hw.copyImage(picture.as_uri(), "pJoy Pro")
    assert rel == "pictures/photo.jpg"
    # 07 S107: it waits in the edit's temporary folder until Save; the
    # device's folder and its module file are untouched (07 Q2, GL-174).
    assert not (own / "pictures" / "photo.jpg").exists()
    assert module_store.device_photo_ref(
        json.loads((own / "module.json").read_text())) == ""
    assert hw.editActive("pJoy Pro")
    # Cancel drops it: no photo.
    assert hw.cancelEdit("pJoy Pro")
    assert not (own / "pictures" / "photo.jpg").exists()
    assert not hw.editActive("pJoy Pro")

    # Saved: it goes into the folder the Device Mapping Editor opens. Old: pjoy_pro/,
    # which the Device Mapping Editor (old_name.json) never read.
    hw.beginEdit("pJoy Pro")
    assert hw.copyImage(picture.as_uri(), "pJoy Pro") == "pictures/photo.jpg"
    assert hw.commitEditFor("pJoy Pro", "") == ""
    assert (own / "pictures" / "photo.jpg").is_file()
    # Module Setup's Save makes it the bottom background picture (07 S127).
    saved = json.loads((own / "module.json").read_text())
    assert module_store.device_photo_ref(saved) == "pictures/photo.jpg"
    assert "image" not in saved
    assert "Old%20Name/pictures/photo.jpg" in hw.profilePhotoUrl("pJoy Pro")
    assert not (folder / "pJoy Pro").exists()


def test_renamed_sticks_saved_photo_is_shown(folder: Path) -> None:
    guid = _renamed(folder)
    (folder / "Old Name" / "pictures").mkdir()
    (folder / "Old Name" / "pictures" / "photo.jpg").write_bytes(b"\xff\xd8\xff\xd9")
    hw = hardware_profile.HardwareProfile()
    hw.setDeviceGuid(guid)
    # Old: looked in pjoy_pro/ and threw the file's own photo away.
    assert "Old%20Name/pictures/photo.jpg" in hw.profilePhotoUrl("pJoy Pro")


def test_renamed_sticks_file_counts_as_saved_and_is_the_one_deleted(
    folder: Path,
) -> None:
    guid = _renamed(folder)
    model = module_model.ModuleListModel()
    assert model.moduleFileFor(guid, "pJoy Pro") == "Old Name"
    # Old: looked for pjoy_pro.json ("not saved yet").
    assert model.moduleFileExists(guid, "pJoy Pro")

    # Old: deleted the missing pjoy_pro.json and said it worked.
    assert hardware_profile.delete_module_file("pJoy Pro", guid) == ""
    assert not (folder / "Old Name" / "module.json").exists()
    assert not model.moduleFileExists(guid, "pJoy Pro")


def test_delete_device_removes_a_renamed_sticks_file(folder: Path) -> None:
    guid = _renamed(folder)
    (folder / "Old Name" / "pictures").mkdir()
    (folder / "Old Name" / "pictures" / "photo.jpg").write_bytes(b"\xff\xd8\xff\xd9")
    preview = json.loads(hardware_profile.delete_preview("pJoy Pro", guid))
    assert preview["canPack"]

    result = json.loads(hardware_profile.delete_device("pJoy Pro", guid))
    assert result["ok"], result
    # Old: removed pjoy_pro.json (none) and kept old_name.json and its photo.
    assert not (folder / "Old Name" / "module.json").exists()
    assert not (folder / "Old Name").exists()
    assert result["stub"] and not result["keptFile"]


def test_calibration_and_auto_mapping_tool_open_on_the_cards_file(folder: Path) -> None:
    guid = _renamed(folder)
    # The window's rows are named by device folder.
    assert calibration.module_for_slug("Old Name") is not None
    assert calibration.module_for_slug("pJoy Pro") is None
    main = (pathlib.Path(__file__).parents[2] / "qml" / "Main.qml").read_text(
        encoding="utf-8"
    )
    for window in ("DialogAutoMappingTool.qml", "DialogCalibration.qml"):
        start = main.find(f'createComponent("{window}"')
        call = main[start : main.find("})", start)]
        # Old: "initialSlug": card.slug (pjoy_pro): another device was shown.
        assert "moduleFileFor(card.guid" in call
    assert module_model.ModuleListModel().moduleFileFor(guid, "pJoy Pro") == "Old Name"


# --- Item 8: the Run gate -----------------------------------------------------


def test_old_output_file_bound_to_a_stick_does_not_block_it_at_run(
    folder: Path,
) -> None:
    from gremlin.modules.runtime import InputModuleRuntime

    guid = _pjoy_guid()
    _write(
        folder,
        "pJoy Pro",
        {
            "device": "pJoy Pro",
            "direction": "source",
            "boundGuidLocal": guid,
            "claim": _CLAIM,
        },
    )
    # Another folder whose file still names the stick's id (an old copy).
    _write(
        folder,
        "Old Stick",
        {
            "device": "Old Stick",
            "direction": "dest",
            "boundGuidLocal": guid,
            "claim": _CLAIM,
        },
        "name:old_stick",
    )
    assert module_store.device_dir("pJoy Pro", guid) == folder / "pJoy Pro"
    gate = InputModuleRuntime()
    try:
        gate.reload()
        # Old: the stick's id was put with the outputs: nothing got through.
        assert guid_key(guid) not in gate._dest_guids
        assert gate.allows(guid, InputType.JoystickButton, 1)
        assert not gate.allows(guid, InputType.JoystickButton, 2)
        assert calibration.module_for_slug("pJoy Pro") is not None
    finally:
        shutil.rmtree(folder / "Old Stick")
        module_store._dirs_changed()
        gate.reload()


def test_stick_whose_file_is_an_output_gets_no_claim_from_another_file(
    folder: Path,
) -> None:
    from gremlin.modules.runtime import InputModuleRuntime

    guid = _pjoy_guid()
    # The stick's own file marked output (Run blocks it), and an old input
    # file naming its id with claims.
    _write(
        folder,
        "pJoy Pro",
        {
            "device": "pJoy Pro",
            "direction": "dest",
            "boundGuidLocal": guid,
            "claim": _CLAIM,
        },
    )
    _write(
        folder,
        "Old Stick",
        {
            "device": "Old Stick",
            "direction": "source",
            "boundGuidLocal": guid,
            "claim": _CLAIM,
        },
        "name:old_stick",
    )
    gate = InputModuleRuntime()
    try:
        gate.reload()
        assert not gate.allows(guid, InputType.JoystickButton, 1)
        # Old: Calibration showed (and saved) old_stick.json for it.
        assert calibration.module_for_slug("Old Stick") is None
    finally:
        shutil.rmtree(folder / "Old Stick")
        shutil.rmtree(folder / "pJoy Pro")
        module_store._dirs_changed()
        gate.reload()


def test_one_vjoy_never_opens_another_vjoys_file(folder: Path) -> None:
    vjoy = next(iter(device_initialization.vjoy_devices()))
    guid = str(vjoy.device_guid)
    _write(folder, "vJoy 2", {"device": "vJoy 2", "direction": "dest", "claim": _CLAIM})
    # A vJoy's folder is found by its number (name:vjoy_N), never another's.
    assert module_store.device_dir("vJoy 1", guid) == folder / "vJoy 1"
    assert module_store.module_file("vJoy 1", guid) == folder / "vJoy 1" / "module.json"


def test_a_vjoy_with_no_id_does_not_open_a_file_bound_to_another_device(
    folder: Path,
) -> None:
    from gremlin.ui import device_pack

    vjoy = next(iter(device_initialization.vjoy_devices()))
    assert vjoy.name == "vJoy Device"
    # A folder holding another vJoy's file.
    _write(
        folder,
        "Throttle Out",
        {
            "device": "Throttle Out",
            "direction": "dest",
            "boundGuidLocal": "{11111111-2222-3333-4444-555555555555}",
            "claim": _CLAIM,
        },
    )
    # Old: throttle_out.json (no id, so the file's binding wasn't checked).
    # A Device Pack never has a vJoy's id: it reports "vJoy Device".
    assert module_store.module_file("vJoy 1", "") == folder / "vJoy 1" / "module.json"
    assert device_pack._device_path("vJoy 1") == folder / "vJoy 1" / "module.json"
    assert registry._guid_for_name("vJoy 1") == stored_guid_key(vjoy.device_guid)
    # Its own folder is still found.
    _write(
        folder,
        "vJoy 1",
        {
            "device": "vJoy 1",
            "direction": "dest",
            "boundGuidLocal": str(vjoy.device_guid),
            "claim": _CLAIM,
        },
        "name:vjoy_1",
    )
    assert module_store.device_dir("vJoy 1", "") == folder / "vJoy 1"


# --- Item 9: a module file that isn't UTF-8 -----------------------------------


def test_a_module_file_that_is_not_utf8_doesnt_stop_home(folder: Path) -> None:
    guid = _pjoy_guid()
    path = _write(folder, "pJoy Pro", {}, stored_guid_key(guid))
    path.write_bytes(b'{"device": "pJoy Pro", "x": "\xff\xfe"}')
    # Old: each of these raised UnicodeDecodeError.
    assert module_model._load_module_doc("pJoy Pro", guid) == {}
    model = module_model.ModuleListModel()
    assert model.claimedCount("pJoy Pro") == 0
    assert json.loads(model.viewConfigJson("pJoy Pro", guid))["layout"]
    assert calibration._load(path) == {}
    hw = hardware_profile.HardwareProfile()
    assert hw.load("pJoy Pro") == ""
    row = next(r for r in model._rows if r.slug == "pjoy_pro")
    assert row.damaged


# --- Item 23: Home card order -------------------------------------------------


def test_a_deleted_devices_place_in_the_card_order_goes(folder: Path) -> None:
    _write(
        folder,
        "Gone Stick",
        {
            "kind": "control.hardware",
            "device": "Gone Stick",
            "direction": "source",
            "claim": _CLAIM,
        },
    )
    model = module_model.ModuleListModel()
    module_model._set_order(["gone_stick"] + [r.slug for r in model._rows])
    raw = json.loads(model.deleteDevice("Gone Stick", ""))
    assert raw["ok"], raw
    # Old: "gone_stick" stayed in the order for good.
    assert "gone_stick" not in module_model._order_slugs()


def test_a_drag_keeps_hidden_cards_places(folder: Path) -> None:
    model = module_model.ModuleListModel()
    showing = [r.slug for r in model._rows]
    assert len(showing) >= 2
    module_model._set_order([showing[0], "hidden_one"] + showing[1:])
    module_model._set_hidden({"hidden_one"})
    model.moveSlugBefore(showing[-1], showing[0])
    order = module_model._order_slugs()
    # Old: the hidden card's place was dropped.
    assert "hidden_one" in order
    assert order.index("hidden_one") == 1


def test_a_renamed_stick_keeps_its_cards_place(folder: Path) -> None:
    _renamed(folder)
    model = module_model.ModuleListModel()
    others = [r.slug for r in model._rows if r.slug != "pjoy_pro"]
    module_model._set_order([others[0], "old_name"] + others[1:])
    model._reload()
    order = module_model._order_slugs()
    # Old: old_name stayed, and pjoy_pro went last.
    assert "old_name" not in order
    assert order.index("pjoy_pro") == 1
    assert [r.slug for r in model._rows].index("pjoy_pro") == 1


# --- History: a delete is recorded once it went through -----------------------


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Path]:
    path = tmp_path / "history"
    monkeypatch.setattr(history, "folder", lambda: path)
    monkeypatch.setattr(history, "_pruned", True)
    yield path
    _settle()


def _settle() -> list[dict]:
    deadline = time.monotonic() + 5
    while history._writer is not None and time.monotonic() < deadline:
        time.sleep(0.02)
    return history.entries()


def test_a_delete_module_file_that_failed_is_no_history_entry(
    folder: Path, store: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    guid = _pjoy_guid()
    locked = _write(
        folder,
        "pJoy Pro",
        {
            "device": "pJoy Pro",
            "direction": "source",
            "boundGuidLocal": guid,
            "claim": _CLAIM,
        },
    )
    _settle()
    real = pathlib.Path.unlink

    def unlink(self: Path, missing_ok: bool = False) -> None:
        if self == locked:
            raise PermissionError("in use")
        real(self, missing_ok)

    monkeypatch.setattr(pathlib.Path, "unlink", unlink)
    try:
        message = hardware_profile.delete_module_file("pJoy Pro", guid)
        # Said, not raised (the store reports a delete that failed).
        assert message.startswith("The module file could not be deleted.")
    finally:
        monkeypatch.setattr(pathlib.Path, "unlink", real)
    assert locked.is_file()
    # Old: "Deleted the module file" was recorded before the delete.
    assert [e for e in _settle() if e["kind"] == "delete"] == []
