# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Device Pack import is a working copy of what was exported.

Import is destructive by design (the user is warned first): each ticked mode
replaces the device's wires and actions there. It used to empty the whole
profile's action list instead (every other device lost its actions at the
next save and load), skip controls that already had actions, keep wires on
the exported vJoy when the output was put on another, create modes without
their parent, and leave the replaced actions in the file. Also: Map
settings in two rows, Configuration Appearance, the photo's placement, a
newer pack refused, and Undo Import.

A pack is exported from one profile and imported into another, as on a
second PC.
"""

from __future__ import annotations

import json
import uuid
import zipfile
from pathlib import Path
from xml.etree import ElementTree

import pytest

from gremlin import device_initialization, plugin_manager, shared_state, util
from gremlin.modules import module_file
from gremlin.profile import DeviceInfo, Profile
from gremlin.types import InputType
from gremlin.ui import device_pack, hardware_profile

_OTHER = uuid.UUID("11111111-2222-3333-4444-555555555555")


def _stick() -> tuple[str, uuid.UUID]:
    for dev in device_initialization.physical_devices():
        if dev.name == "pJoy Pro":
            return dev.name, dev.device_guid.uuid
    pytest.skip("the fake stick is not there")


def _map(
    profile: Profile, uid: uuid.UUID, button: int, mode: str, vjoy: int, out: int
) -> None:
    action = plugin_manager.PluginManager().create_instance(
        "Map to vJoy", InputType.JoystickButton
    )
    action.vjoy_device_id = vjoy
    action.vjoy_input_id = out
    action.vjoy_input_type = InputType.JoystickButton
    item = profile.get_input_item(
        uid, InputType.JoystickButton, button, mode, create_if_missing=True
    )
    item.add_item_binding().root_action.insert_action(action, "children")


def _logical_link(profile: Profile, uid: uuid.UUID, button: int, number: int) -> None:
    action = plugin_manager.PluginManager().create_instance(
        "Map to Logical Device", InputType.JoystickButton
    )
    action.logical_input_id = number
    action.logical_input_type = InputType.JoystickButton
    item = profile.get_input_item(
        uid, InputType.JoystickButton, button, "Default", create_if_missing=True
    )
    item.add_item_binding().root_action.insert_action(action, "children")


def _targets(profile: Profile, uid: uuid.UUID, mode: str) -> dict[int, tuple[int, int]]:
    """Button -> (vJoy device, vJoy button) for the device's Map to vJoy."""
    out = {}
    for item in profile.inputs.get(uid, []):
        if item.mode != mode:
            continue
        for binding in item.action_sequences:
            for action in binding.root_action.get_actions()[0]:
                if getattr(action, "tag", "") == "map-to-vjoy":
                    out[item.input_id] = (action.vjoy_device_id, action.vjoy_input_id)
    return out


def _new_profile(name: str, uid: uuid.UUID) -> Profile:
    profile = Profile()
    shared_state.current_profile = profile
    profile.device_database.devices[uid] = DeviceInfo(uid, name)
    profile.device_database.devices[_OTHER] = DeviceInfo(_OTHER, "Other Stick")
    return profile


def _reload(profile: Profile, tmp_path: Path) -> Profile:
    path = tmp_path / "saved.xml"
    profile.to_xml(path)
    again = Profile()
    again.from_xml(path)
    shared_state.current_profile = again
    return again


@pytest.fixture
def pack(tmp_path: Path) -> dict:
    name, uid = _stick()
    modules = util.modules_dir()
    modules.mkdir(parents=True, exist_ok=True)
    module_file.write_json(
        modules / f"{hardware_profile._slug(name)}.json",
        {
            "kind": "control.hardware",
            "device": name,
            "direction": "source",
            "claim": {
                "buttons": [1, 2],
                "axes": [],
                "hats": [],
                "keys": [],
                "friendly": {},
            },
            "catalog": {"rowHeight": 40},
            "photo": {"x": 0.1, "y": 0.2, "scale": 1.5},
            "ui": {
                "viewPct": 80,
                "gridSize": 4,
                "guidesX": [0.5],
                "printArea": {"fx": 0, "fy": 0, "fw": 1, "fh": 1},
            },
            "nodes": [],
        },
    )
    module_file.write_json(
        modules / "vjoy_2.json",
        {
            "kind": "control.hardware",
            "device": "vJoy 2",
            "direction": "dest",
            "claim": {"buttons": [1, 2, 3], "axes": [], "hats": []},
            "nodes": [],
        },
    )
    source = _new_profile(name, uid)
    source.modes.add_mode("Combat")
    source.modes.set_parent("Combat", "Default")
    _map(source, uid, 1, "Default", 2, 1)
    _map(source, uid, 2, "Combat", 2, 2)
    _map(source, uid, 99, "Default", 2, 3)  # the other PC's stick has 64 buttons
    _logical_link(source, uid, 5, 7)
    built = device_pack.assemble(
        name, lambda stored: None, None, {"author": "Sam", "note": "My F-16 setup"}
    )
    assert not isinstance(built, str), built
    zip_path = tmp_path / "pack.zip"
    zip_path.write_bytes(built[0])
    # The second PC: this stick has its own wires in Default and Landing,
    # and another stick has wires too.
    target = _new_profile(name, uid)
    target.modes.add_mode("Landing")
    _map(target, uid, 3, "Default", 1, 3)
    _map(target, uid, 4, "Landing", 1, 4)
    _map(target, _OTHER, 1, "Default", 1, 5)
    yield {"name": name, "uid": uid, "zip": zip_path, "profile": target}
    device_pack.drop_import_undo()
    shared_state.current_profile = None


def _import(pack: dict, items: list[str], **extra: object) -> dict:
    selection = {"items": items, "outputs": {"vjoy_2": "vJoy 1"}, **extra}
    return device_pack.apply_zip(pack["zip"], pack["name"], selection)


def test_other_devices_keep_their_actions(pack: dict, tmp_path: Path) -> None:
    result = _import(pack, ["wire:Default"])
    assert result["ok"], result
    device_pack.drop_import_undo()
    again = _reload(pack["profile"], tmp_path)
    assert _targets(again, _OTHER, "Default") == {1: (1, 5)}


def test_a_ticked_mode_is_replaced_and_others_stay(pack: dict, tmp_path: Path) -> None:
    _import(pack, ["wire:Default"])
    device_pack.drop_import_undo()
    again = _reload(pack["profile"], tmp_path)
    uid = pack["uid"]
    # Button 3 was this PC's; Default is now the pack's (button 99 left out).
    assert set(_targets(again, uid, "Default")) == {1}
    assert _targets(again, uid, "Landing") == {4: (1, 4)}


def test_wires_follow_the_output_they_were_put_on(pack: dict) -> None:
    _import(pack, ["wire:Default"])
    assert _targets(pack["profile"], pack["uid"], "Default")[1] == (1, 1)


def test_modes_keep_their_parent(pack: dict) -> None:
    result = _import(pack, ["wire:Combat"])
    profile = pack["profile"]
    assert profile.modes.mode_exists("Combat")
    assert profile.modes.find_mode("Combat").parent.value == "Default"
    assert "Created Combat." in result["report"]


def test_no_unused_actions_are_saved(pack: dict, tmp_path: Path) -> None:
    _import(pack, ["wire:Default", "wire:Combat"])
    device_pack.drop_import_undo()
    profile = pack["profile"]
    assert set(profile.library._actions) == profile.actions_in_use()
    again = _reload(profile, tmp_path)
    assert set(again.library._actions) == again.actions_in_use()


def test_the_warning_says_what_is_replaced(pack: dict) -> None:
    preview = device_pack.preview_import(
        pack["zip"],
        pack["name"],
        {"items": ["wire:Default", "in.checks"], "outputs": {"vjoy_2": "vJoy 1"}},
    )
    assert preview["ok"], preview
    assert preview["modes"] == [{"name": "Default", "here": 1, "pack": 2}]
    assert preview["missingLogical"] == ["Button 7"]
    assert "Button 99" in preview["leftOut"]
    assert preview["moves"] == [{"from": "vJoy 2", "to": "vJoy 1"}]
    assert preview["hasModuleFile"] is True
    # Wires are in "modes", with their counts, not again in the pieces.
    assert preview["pieces"] == ["Input module: Checked controls"]


def test_missing_logical_inputs_can_be_created(pack: dict) -> None:
    from gremlin.logical_device import LogicalDevice

    ident = LogicalDevice.Input.Identifier(InputType.JoystickButton, 7)
    result = _import(pack, ["wire:Default"], createLogical=True)
    assert LogicalDevice().exists(ident), result
    device_pack.undo_import()
    assert not LogicalDevice().exists(ident)


def test_undo_import_puts_everything_back(pack: dict) -> None:
    name, uid, profile = pack["name"], pack["uid"], pack["profile"]
    path = util.modules_dir() / f"{hardware_profile._slug(name)}.json"
    before_file = path.read_bytes()
    before_actions = set(profile.library._actions)
    _import(pack, ["wire:Default", "wire:Combat", "in.catalog", "in.mapview"])
    assert device_pack.can_undo_import()
    result = device_pack.undo_import()
    assert result["ok"], result
    assert path.read_bytes() == before_file
    assert _targets(profile, uid, "Default") == {3: (1, 3)}
    assert not profile.modes.mode_exists("Combat")
    assert set(profile.library._actions) == before_actions
    assert not device_pack.can_undo_import()


def test_map_settings_rows_import_separately(pack: dict) -> None:
    name = pack["name"]
    path = util.modules_dir() / f"{hardware_profile._slug(name)}.json"
    module_file.write_json(
        path, {"kind": "control.hardware", "device": name, "ui": {"viewPct": 100}}
    )
    _import(pack, ["in.mapview"])
    ui = json.loads(path.read_text(encoding="utf-8"))["ui"]
    assert ui["viewPct"] == 80 and ui["guidesX"] == [0.5]
    assert "printArea" not in ui
    _import(pack, ["in.print"])
    ui = json.loads(path.read_text(encoding="utf-8"))["ui"]
    assert ui["printArea"] == {"fx": 0, "fy": 0, "fw": 1, "fh": 1}


def test_configuration_appearance_comes_with_the_pack(pack: dict) -> None:
    path = util.modules_dir() / f"{hardware_profile._slug(pack['name'])}.json"
    _import(pack, ["in.catalog"])
    assert json.loads(path.read_text(encoding="utf-8"))["catalog"] == {"rowHeight": 40}


def test_the_photo_keeps_its_placement() -> None:
    merged, _notes = device_pack._merge_module(
        {"kind": "control.hardware", "photo": {"x": 0}},
        {"image": "photo.png", "photo": {"x": 0.1, "scale": 1.5}, "nodes": []},
        {"pic:photo.png"},
        "in.",
        "pJoy Pro",
        "",
    )
    assert merged["image"] == "photo.png"
    assert merged["photo"] == {"x": 0.1, "scale": 1.5}


def test_the_rows_and_notes(pack: dict) -> None:
    described = device_pack.describe_zip(pack["zip"])
    titles = {
        section["title"]: [item["title"] for item in section["items"]]
        for section in described["sections"]
    }
    assert "Configuration Appearance" in titles["Input module"]
    assert titles["Map settings"] == ["Map view", "Print area and print settings"]
    assert "Combat (under Default)" in titles["Wires"]
    settings = next(s for s in described["sections"] if s["title"] == "Map settings")
    assert all(item["checked"] is False for item in settings["items"])
    assert described["notes"]["author"] == "Sam"
    assert described["notes"]["note"] == "My F-16 setup"


def test_export_can_take_some_modes(pack: dict, tmp_path: Path) -> None:
    built = device_pack.assemble(pack["name"], lambda stored: None, ["Default"], None)
    zip_path = tmp_path / "default-only.zip"
    zip_path.write_bytes(built[0])
    wires = json.loads(zipfile.ZipFile(zip_path).read("wires.json"))
    assert [mode["name"] for mode in wires["modes"]] == ["Default"]
    assert wires["tree"] == {"Default": ""}


def test_a_newer_pack_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "newer.zip"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(
            "map.json",
            json.dumps(
                {
                    "device": "pJoy Pro",
                    "pack": {
                        "exportedName": "pJoy Pro",
                        "format": 99,
                        "program": "9.0.0",
                    },
                }
            ),
        )
    described = device_pack.describe_zip(path)
    assert (
        isinstance(described, str)
        and "newer Gremlin-Platforms (version 9.0.0)" in described
    )
    result = device_pack.apply_zip(path, "pJoy Pro", {"items": ["in.checks"]})
    assert result["ok"] is False


def test_adding_actions_keeps_the_ones_already_there() -> None:
    profile = Profile()
    shared_state.current_profile = profile
    try:
        uid = uuid.uuid4()
        _map(profile, uid, 1, "Default", 1, 1)
        before = set(profile.library._actions)
        action = next(iter(profile.library._actions.values()))
        node = ElementTree.Element("profile")
        library = ElementTree.SubElement(node, "library")
        block = action.to_xml()
        block.set("id", str(uuid.uuid4()))
        library.append(block)
        profile.library.from_xml(node)
        assert before < set(profile.library._actions)
    finally:
        shared_state.current_profile = None


def _drivers(
    monkeypatch: pytest.MonkeyPatch, vjoy: bool, devices: set[int], xbox: bool
) -> None:
    from gremlin.modules import output

    monkeypatch.setattr(output, "vjoy_driver_found", lambda: vjoy)
    monkeypatch.setattr(output, "vjoy_exists", lambda number: number in devices)
    monkeypatch.setattr(output, "xbox_available", lambda: xbox)
    monkeypatch.setattr(output, "xbox_driver_installed", lambda: False)
    monkeypatch.setattr(output, "xbox_error", lambda: "")


def test_opening_a_pack_says_the_vjoy_driver_is_missing(
    pack: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    _drivers(monkeypatch, vjoy=False, devices=set(), xbox=True)
    drivers = device_pack.describe_zip(pack["zip"])["drivers"]
    assert drivers == [
        "vJoy is not installed or not running: wires to vJoy won't do anything. "
        "Install vJoy, then restart Gremlin-Platforms."
    ]


def test_the_warning_names_a_vjoy_device_that_is_not_set_up(
    pack: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    _drivers(monkeypatch, vjoy=True, devices={1}, xbox=True)
    # Put on vJoy 1 (set up): nothing to say.
    selection = {"items": ["wire:Default"], "outputs": {"vjoy_2": "vJoy 1"}}
    assert (
        device_pack.preview_import(pack["zip"], pack["name"], selection)["drivers"]
        == []
    )
    # Left on vJoy 2 (not set up): said.
    selection["outputs"] = {"vjoy_2": "vJoy 2"}
    drivers = device_pack.preview_import(pack["zip"], pack["name"], selection)[
        "drivers"
    ]
    assert drivers == [
        "vJoy 2 isn't set up in the vJoy driver, so wires to it won't do anything. "
        "Add it in Configure vJoy."
    ]


def test_the_xbox_driver_is_checked_when_wires_send_to_xbox(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _drivers(monkeypatch, vjoy=True, devices={1}, xbox=False)
    xbox = '<action id="a" type="map-to-xbox"></action>'
    vjoy = (
        '<action id="b" type="map-to-vjoy"><property type="int">'
        "<name>vjoy-device-id</name><value>1</value></property></action>"
    )
    assert device_pack._needs([xbox, vjoy]) == ({1}, True)
    notes = device_pack.driver_notes({1}, True)
    assert notes == [
        "ViGEmBus is not installed: wires to Xbox won't do anything. Install "
        "ViGEmBus 1.22 from the Nefarius releases page, then restart "
        "Gremlin-Platforms. This program does not download or bundle that "
        "installer."
    ]
    assert device_pack.driver_notes(set(), False) == []


def test_the_pack_and_the_xbox_viewer_say_the_same(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One wording (the output module's) for every check of a driver."""
    from gremlin.ui.xbox_device_model import XboxDriverStatus

    _drivers(monkeypatch, vjoy=True, devices={1}, xbox=False)
    viewer = XboxDriverStatus()
    note = device_pack.driver_notes(set(), True)[0]
    assert note.startswith(str(viewer.statusText) + ":")
    assert note.endswith(str(viewer.hint))
