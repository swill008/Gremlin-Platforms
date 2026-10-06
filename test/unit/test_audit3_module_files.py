# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Which module file a device uses (audit 3).

A renamed stick opens its old file (bound to its id), but its Button Map
photo, "not saved yet" label, Delete Module File and Delete Device went by
its new name. Two identical sticks in an old state both opened one file. An
old second file marked output and bound to a stick blocked it at Run. A
module file that isn't UTF-8 stopped Home. The Home card order kept a
deleted device's place for good, put a renamed stick last, and a drag
dropped hidden cards' places. History recorded a delete before it happened.
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
from test.unit.test_twin_devices import (  # noqa: F401
    _first_guid,
    _names,
    _twin_guid,
    twins,
)

_APPS: list[QtCore.QCoreApplication] = []
_CLAIM = {"buttons": [1], "axes": [], "hats": [], "keys": []}


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


@pytest.fixture
def folder(tmp_path: Path) -> Iterator[Path]:
    """The modules folder, empty of module files and bindings (files other
    tests left are put aside), put back as it was afterwards."""
    path = util.modules_dir()
    aside = tmp_path / "aside"
    aside.mkdir()
    for old in path.glob("*.json"):
        shutil.move(str(old), str(aside / old.name))
    before = {p.name for p in path.iterdir()}
    bindings = module_store.bindings()
    module_store.set_bindings({})
    order = module_model._order_slugs()
    hidden = module_model._hidden_slugs()
    yield path
    for extra in path.iterdir():
        if extra.name in before:
            continue
        if extra.is_dir():
            shutil.rmtree(extra, ignore_errors=True)
        else:
            extra.unlink(missing_ok=True)
    for old in aside.iterdir():
        shutil.move(str(old), str(path / old.name))
    module_store.set_bindings(bindings)
    module_model._set_order(order)
    module_model._set_hidden(hidden)


def _pjoy_guid() -> str:
    dev = next(
        d for d in device_initialization.physical_devices() if d.name == "pJoy Pro"
    )
    return str(dev.device_guid)


def _write(folder: Path, slug: str, doc: dict) -> Path:
    path = folder / f"{slug}.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def _renamed(folder: Path) -> str:
    """pJoy Pro was "Old Name": its file is old_name.json, bound to it."""
    guid = _pjoy_guid()
    _write(
        folder,
        "old_name",
        {
            "kind": "control.hardware",
            "device": "Old Name",
            "direction": "source",
            "boundGuidLocal": guid,
            "claim": _CLAIM,
        },
    )
    assert registry.resolve_module_slug("pJoy Pro", guid) == "old_name"
    return guid


# --- Item 7: a renamed stick ------------------------------------------------


def test_renamed_sticks_photo_goes_with_the_file_its_button_map_opens(
    folder: Path, tmp_path: Path
) -> None:
    guid = _renamed(folder)
    picture = tmp_path / "shot.jpg"
    picture.write_bytes(b"\xff\xd8\xff\xd9")
    hw = hardware_profile.HardwareProfile()
    hw.setDeviceGuid(guid)

    hw.stashPhoto("pJoy Pro")
    rel = hw.copyImage(picture.as_uri(), "pJoy Pro")
    # Old: pjoy_pro/photo.jpg, which the Button Map (old_name.json) never
    # reads, and old_name.json kept no picture.
    assert rel == "old_name/photo.jpg"
    assert (folder / "old_name" / "photo.jpg").is_file()
    assert json.loads((folder / "old_name.json").read_text())["image"] == rel
    assert hw.hasPhotoStash("pJoy Pro")
    assert "old_name/photo.jpg" in hw.profilePhotoUrl("pJoy Pro")

    # Cancel puts the session's start back: no photo.
    assert hw.restorePhoto("pJoy Pro")
    assert not (folder / "old_name" / "photo.jpg").exists()
    assert "image" not in json.loads((folder / "old_name.json").read_text())
    assert not hw.hasPhotoStash("pJoy Pro")


def test_renamed_sticks_saved_photo_is_shown(folder: Path) -> None:
    guid = _renamed(folder)
    (folder / "old_name").mkdir()
    (folder / "old_name" / "photo.jpg").write_bytes(b"\xff\xd8\xff\xd9")
    hw = hardware_profile.HardwareProfile()
    hw.setDeviceGuid(guid)
    # Old: looked in pjoy_pro/ and threw the file's own photo away.
    assert "old_name/photo.jpg" in hw.profilePhotoUrl("pJoy Pro")
    assert hw.clearImage("pJoy Pro")
    assert not (folder / "old_name" / "photo.jpg").exists()


def test_renamed_sticks_file_counts_as_saved_and_is_the_one_deleted(
    folder: Path,
) -> None:
    guid = _renamed(folder)
    model = module_model.ModuleListModel()
    assert model.moduleFileFor(guid, "pJoy Pro") == "old_name"
    # Old: looked for pjoy_pro.json ("not saved yet").
    assert model.moduleFileExists(guid, "pJoy Pro")

    # Old: deleted the missing pjoy_pro.json and said it worked.
    assert hardware_profile.delete_module_file("pJoy Pro", guid) == ""
    assert not (folder / "old_name.json").exists()
    assert registry.resolve_module_slug("pJoy Pro", guid) == "pjoy_pro"
    assert not model.moduleFileExists(guid, "pJoy Pro")


def test_delete_device_removes_a_renamed_sticks_file(folder: Path) -> None:
    guid = _renamed(folder)
    (folder / "old_name").mkdir()
    (folder / "old_name" / "photo.jpg").write_bytes(b"\xff\xd8\xff\xd9")
    preview = json.loads(hardware_profile.delete_preview("pJoy Pro", guid))
    assert preview["canPack"] and not preview["shared"]

    result = json.loads(hardware_profile.delete_device("pJoy Pro", guid, False))
    assert result["ok"], result
    # Old: removed pjoy_pro.json (none) and kept old_name.json and its photo.
    assert not (folder / "old_name.json").exists()
    assert not (folder / "old_name").exists()
    assert result["stub"] and not result["keptFile"]


def test_a_file_another_stick_uses_is_not_deleted(folder: Path) -> None:
    guid = _renamed(folder)
    data = module_store.bindings()
    data["{11111111-2222-3333-4444-555555555555}"] = "old_name"
    module_store.set_bindings(data)
    assert hardware_profile.delete_module_file("pJoy Pro", guid) == (
        "Another stick is using this file."
    )
    assert (folder / "old_name.json").is_file()


def test_calibration_and_auto_mapper_open_on_the_cards_file(folder: Path) -> None:
    guid = _renamed(folder)
    # The window's rows are named by module file.
    assert calibration.module_for_slug("old_name") is not None
    assert calibration.module_for_slug("pjoy_pro") is None
    main = (pathlib.Path(__file__).parents[2] / "qml" / "Main.qml").read_text(
        encoding="utf-8"
    )
    for window in ("DialogAutoMapper.qml", "DialogCalibration.qml"):
        start = main.find(f'createComponent("{window}"')
        call = main[start : main.find("})", start)]
        # Old: "initialSlug": card.slug (pjoy_pro): another device was shown.
        assert "moduleFileFor(card.guid" in call
    assert module_model.ModuleListModel().moduleFileFor(guid, "pJoy Pro") == "old_name"


# --- Item 8: twins in an old state, and the Run gate --------------------------


def test_twins_that_both_saved_into_one_file_each_get_their_own(
    twins: list,  # noqa: F811
    folder: Path,
) -> None:
    _write(
        folder,
        "pjoy_pro",
        {"device": "pJoy Pro", "direction": "source", "claim": _CLAIM},
    )
    device_initialization.joystick_devices_initialization()
    names = _names()
    assert sorted(guid_key(g) for g in names) == sorted(
        guid_key(g) for g in (_first_guid(), _twin_guid())
    )
    first = next(g for g, n in names.items() if n == "pJoy Pro")
    second = next(g for g, n in names.items() if n == "pJoy Pro (2)")
    module_store.set_bindings(
        {stored_guid_key(first): "pjoy_pro", stored_guid_key(second): "pjoy_pro"}
    )
    assert registry.resolve_module_slug(names[first], first) == "pjoy_pro"
    # Old: pjoy_pro too (both twins one file).
    assert registry.resolve_module_slug(names[second], second) == "pjoy_pro_2"
    assert (
        module_store.path_for(names[second], second).name
        == "pjoy_pro_2.json"
    )


def test_plain_file_bound_to_the_second_twin_stays_the_first_ones(
    twins: list,  # noqa: F811
    folder: Path,
) -> None:
    device_initialization.joystick_devices_initialization()
    names = _names()
    plain = next(g for g, n in names.items() if n == "pJoy Pro")
    second = next(g for g, n in names.items() if n == "pJoy Pro (2)")
    # Old state: "(2)" saved into the plain-named file, bound to it.
    _write(
        folder,
        "pjoy_pro",
        {
            "device": "pJoy Pro",
            "direction": "source",
            "boundGuidLocal": second,
            "claim": _CLAIM,
        },
    )
    module_store.set_bindings({stored_guid_key(second): "pjoy_pro"})
    # Old: both resolved to pjoy_pro.
    assert registry.resolve_module_slug("pJoy Pro (2)", second) == "pjoy_pro_2"
    assert registry.resolve_module_slug("pJoy Pro", plain) == "pjoy_pro"


def test_old_output_file_bound_to_a_stick_does_not_block_it_at_run(
    folder: Path,
) -> None:
    from gremlin.modules.runtime import InputModuleRuntime

    guid = _pjoy_guid()
    _write(
        folder,
        "pjoy_pro",
        {
            "device": "pJoy Pro",
            "direction": "source",
            "boundGuidLocal": guid,
            "claim": _CLAIM,
        },
    )
    _write(
        folder,
        "old_stick",
        {
            "device": "Old Stick",
            "direction": "dest",
            "boundGuidLocal": guid,
            "claim": _CLAIM,
        },
    )
    assert registry.resolve_module_slug("pJoy Pro", guid) == "pjoy_pro"
    gate = InputModuleRuntime()
    try:
        gate.reload()
        # Old: the stick's id was put with the outputs: nothing got through.
        assert guid_key(guid) not in gate._dest_guids
        assert gate.allows(guid, InputType.JoystickButton, 1)
        assert not gate.allows(guid, InputType.JoystickButton, 2)
        assert calibration.module_for_slug("pjoy_pro") is not None
    finally:
        (folder / "old_stick.json").unlink()
        gate.reload()


def test_stick_whose_file_is_an_output_gets_no_claim_from_another_file(
    folder: Path,
) -> None:
    from gremlin.modules.runtime import InputModuleRuntime

    guid = _pjoy_guid()
    # The stick's own file marked output (Run blocks it), and an old input
    # file bound to it with claims.
    _write(
        folder,
        "pjoy_pro",
        {
            "device": "pJoy Pro",
            "direction": "dest",
            "boundGuidLocal": guid,
            "claim": _CLAIM,
        },
    )
    _write(
        folder,
        "old_stick",
        {
            "device": "Old Stick",
            "direction": "source",
            "boundGuidLocal": guid,
            "claim": _CLAIM,
        },
    )
    gate = InputModuleRuntime()
    try:
        gate.reload()
        assert not gate.allows(guid, InputType.JoystickButton, 1)
        # Old: Calibration showed (and saved) old_stick.json for it.
        assert calibration.module_for_slug("old_stick") is None
    finally:
        (folder / "old_stick.json").unlink()
        (folder / "pjoy_pro.json").unlink()
        gate.reload()


def test_device_pack_and_output_view_use_the_one_rule(folder: Path) -> None:
    guid = _pjoy_guid()
    _write(
        folder,
        "chosen",
        {"device": "Some Other", "direction": "source", "claim": _CLAIM},
    )
    module_store.set_bindings({stored_guid_key(guid): "chosen"})
    assert registry.resolve_module_slug("pJoy Pro", guid) == "chosen"
    # Old: pjoy_pro.json (its own fallback rule).
    assert module_store.path_for("pJoy Pro", guid).name == "chosen.json"


def test_one_vjoy_never_opens_another_vjoys_file(folder: Path) -> None:
    vjoy = next(iter(device_initialization.vjoy_devices()))
    guid = str(vjoy.device_guid)
    _write(folder, "vjoy_2", {"device": "vJoy 2", "direction": "dest", "claim": _CLAIM})
    module_store.set_bindings({stored_guid_key(guid): "vjoy_2"})
    assert registry.resolve_module_slug("vJoy 1", guid) == "vjoy_1"
    assert module_store.path_for("vJoy 1", guid).name == "vjoy_1.json"


def test_a_vjoy_with_no_id_does_not_open_a_file_bound_to_another_device(
    folder: Path,
) -> None:
    from gremlin.ui import device_pack

    vjoy = next(iter(device_initialization.vjoy_devices()))
    assert vjoy.name == "vJoy Device"
    # A file bound to another vJoy, and a leftover name binding to it.
    _write(
        folder,
        "throttle_out",
        {
            "device": "Throttle Out",
            "direction": "dest",
            "boundGuidLocal": "{11111111-2222-3333-4444-555555555555}",
            "claim": _CLAIM,
        },
    )
    module_store.set_bindings({"name:vjoy_1": "throttle_out"})
    # Old: throttle_out.json (no id, so the file's binding wasn't checked).
    # A Device Pack never has a vJoy's id: it reports "vJoy Device".
    assert module_store.path_for("vJoy 1", "").name == "vjoy_1.json"
    assert device_pack._device_path("vJoy 1").name == "vjoy_1.json"
    assert registry._guid_for_name("vJoy 1") == stored_guid_key(vjoy.device_guid)
    # Its own file bound to it is still found.
    _write(
        folder,
        "vjoy_1",
        {
            "device": "vJoy 1",
            "direction": "dest",
            "boundGuidLocal": str(vjoy.device_guid),
            "claim": _CLAIM,
        },
    )
    assert registry.resolve_module_slug("vJoy 1", "") == "vjoy_1"


# --- Item 9: a module file that isn't UTF-8 -----------------------------------


def test_a_module_file_that_is_not_utf8_doesnt_stop_home(folder: Path) -> None:
    guid = _pjoy_guid()
    path = folder / "pjoy_pro.json"
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
        "gone_stick",
        {
            "kind": "control.hardware",
            "device": "Gone Stick",
            "direction": "source",
            "claim": _CLAIM,
        },
    )
    model = module_model.ModuleListModel()
    module_model._set_order(["gone_stick"] + [r.slug for r in model._rows])
    raw = json.loads(model.deleteDevice("Gone Stick", "", False))
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


def test_a_file_chosen_for_a_stick_does_not_take_another_sticks_place(
    folder: Path,
) -> None:
    guid = _pjoy_guid()
    # Unplugged Stick A's file (saved before files were bound to a stick);
    # pJoy Pro set to use it in Module Setup.
    _write(
        folder,
        "stick_a",
        {
            "kind": "control.hardware",
            "device": "Stick A",
            "direction": "source",
            "claim": _CLAIM,
        },
    )
    module_store.bind("pJoy Pro", guid, "stick_a")
    assert registry.resolve_module_slug("pJoy Pro", guid) == "stick_a"
    model = module_model.ModuleListModel()
    others = [r.slug for r in model._rows if r.slug != "pjoy_pro"]
    assert "stick_a" not in others
    module_model._set_order([others[0], "stick_a"] + others[1:])
    model._reload()
    order = module_model._order_slugs()
    # Old: pjoy_pro took Stick A's place, and Stick A's card lost it.
    assert order.index("stick_a") == 1
    assert order[-1] == "pjoy_pro"


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
        "pjoy_pro",
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
