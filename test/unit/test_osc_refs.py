# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""References to OSC inputs go by their permanent id (D-09-OSC-FILE 2).

OSC's addresses live in its module file, shared by every profile; each row
has a uid and its number is only a display name. Bindings on OSC inputs,
Assign Hardware links and Device Pack wires carry the uid (<osc-uid>); an
unknown uid is missing (flagged by the profile check), never re-targeted by
number. A Device Pack of OSC carries its addresses and server settings in
the one module-file write; wires create missing addresses in the file and
Undo Import removes them. A Library put-back takes OSC's file too.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Iterator
from pathlib import Path
from xml.etree import ElementTree

sys.path.append(".")

import pytest

from gremlin import osc_device_file, plugin_manager, shared_state, validate
from gremlin.osc import OSC_DEVICE_UUID, OscDevice
from gremlin.profile import DeviceInfo, Profile
from gremlin.types import InputType

pytestmark = pytest.mark.validate_off

_UNKNOWN = "f" * 32
_B = InputType.JoystickButton


@pytest.fixture
def modules(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """OSC's (and every) module file in a temporary modules folder."""
    from gremlin.modules import store

    folder = tmp_path / "modules"
    folder.mkdir()
    monkeypatch.setattr(store, "folder", lambda: folder)
    return folder


@pytest.fixture
def rows() -> Iterator[object]:
    """OSC's rows emptied for the test and put back afterwards."""
    shared = OscDevice().rows
    saved = shared.to_dict()
    shared.load_dict({"inputs": []})
    yield shared
    osc_device_file.current_uid_map = None
    shared.load_dict(saved)


@pytest.fixture
def profile() -> Iterator[Profile]:
    old = shared_state.current_profile
    made = Profile()
    made.device_database.devices[OSC_DEVICE_UUID] = DeviceInfo(OSC_DEVICE_UUID, "OSC")
    shared_state.current_profile = made
    yield made
    shared_state.current_profile = old


def _renumber(shared: object, uid: str, new_id: int) -> None:
    data = shared.to_dict()  # type: ignore[attr-defined]
    for row in data["inputs"]:
        if row["uid"] == uid:
            row["id"] = new_id
    shared.load_dict(data)  # type: ignore[attr-defined]


# --- the one resolver ---------------------------------------------------------


def test_the_uid_wins_over_the_number(rows: object) -> None:
    from gremlin.osc_persist import resolve_osc_reference

    first = rows.create(_B, "/a")  # type: ignore[attr-defined]
    second = rows.create(_B, "/b")  # type: ignore[attr-defined]
    _renumber(rows, second.uid, 5)
    ident, uid = resolve_osc_reference(second.uid, _B, 2)
    assert (ident.type, ident.id, uid) == (_B, 5, second.uid)
    # An unknown id is missing, even when its old number is taken.
    assert resolve_osc_reference(_UNKNOWN, _B, 1) == (None, _UNKNOWN)
    # No id (old data): the load map first, then type+number.
    ident, uid = resolve_osc_reference(None, _B, 1)
    assert (ident.id, uid) == (1, first.uid)
    osc_device_file.current_uid_map = {("button", 9): second.uid}
    ident, uid = resolve_osc_reference(None, _B, 9)
    assert (ident.id, uid) == (5, second.uid)
    assert resolve_osc_reference(None, _B, 7) == (None, None)


def test_the_label_is_the_shared_rows_address(rows: object) -> None:
    from gremlin.osc_persist import osc_label
    from gremlin.ui.device import InputIdentifier

    rows.create(_B, "/fire")  # type: ignore[attr-defined]
    assert osc_label(_B, 1) == "OSC - /fire"
    assert osc_label(_B, 4) == "OSC - Button 4"
    ident = InputIdentifier()
    ident.device_guid = OSC_DEVICE_UUID
    ident.input_type = _B
    ident.input_id = 1
    assert ident.label == "OSC - /fire"


# --- the profile check --------------------------------------------------------


def test_the_check_flags_a_binding_on_an_unknown_osc_uid(
    rows: object, profile: Profile
) -> None:
    rows.create(_B, "/a")  # type: ignore[attr-defined]
    item = profile.get_input_item(
        OSC_DEVICE_UUID, _B, 1, "Default", create_if_missing=True
    )
    item.osc_uid = _UNKNOWN  # type: ignore[attr-defined]
    found = [line for line in validate.profile(profile) if "OSC" in line]
    assert any(line.startswith("PROFILE-OSC-MISSING") for line in found), found
    item.osc_uid = rows.uid_of(_B, 1)  # type: ignore[attr-defined]
    assert not [line for line in validate.profile(profile) if "PROFILE-OSC" in line]


def test_the_check_flags_a_binding_on_a_number_osc_lacks(
    rows: object, profile: Profile
) -> None:
    profile.get_input_item(OSC_DEVICE_UUID, _B, 3, "Default", create_if_missing=True)
    found = validate.profile(profile)
    assert any(line.startswith("PROFILE-OSC-MISSING") for line in found), found


# --- Assign Hardware ----------------------------------------------------------


def test_assign_hardware_offers_osc_s_addresses_and_links_by_uid(
    rows: object, profile: Profile, modules: Path
) -> None:
    from gremlin.logical_device import LogicalDevice
    from gremlin.ui.logical_layout import LogicalLayoutModel

    logical = LogicalDevice()
    saved = logical.to_dict()
    logical.load_dict({"controls": [], "groups": []})
    try:
        logical.create(_B)
        made = rows.create(_B, "/fire")  # type: ignore[attr-defined]
        rows.create(InputType.JoystickAxis, "/throttle")  # type: ignore[attr-defined]
        model = LogicalLayoutModel()
        try:
            devices = model.hardware("parent:button:1", "")
            osc = [d for d in devices if d["name"] == "OSC"]
            assert osc, devices
            assert [c["label"] for c in osc[0]["controls"]] == ["/fire"]
            model.setLinks("parent:button:1", [osc[0]["controls"][0]["key"]], True)
            item = profile.get_input_item(
                OSC_DEVICE_UUID, _B, made.input_id, "Default", create_if_missing=False
            )
            assert item is not None and item.action_sequences
            assert getattr(item, "osc_uid", None) == made.uid
        finally:
            model.deleteLater()
    finally:
        logical.load_dict(saved)


# --- Device Pack --------------------------------------------------------------


def _map_vjoy(profile: Profile, number: int, out: int) -> object:
    action = plugin_manager.PluginManager().create_instance("Map to vJoy", _B)
    action.vjoy_device_id = 1
    action.vjoy_input_id = out
    action.vjoy_input_type = _B
    item = profile.get_input_item(
        OSC_DEVICE_UUID, _B, number, "Default", create_if_missing=True
    )
    item.add_item_binding().root_action.insert_action(action, "children")
    return item


def _vjoy_targets(profile: Profile) -> dict[int, int]:
    out = {}
    for item in profile.inputs.get(OSC_DEVICE_UUID, []):
        for binding in item.action_sequences:
            for action in binding.root_action.get_actions()[0]:
                if getattr(action, "tag", "") == "map-to-vjoy":
                    out[int(item.input_id)] = action.vjoy_input_id
    return out


@pytest.fixture
def osc_pack(rows: object, modules: Path, tmp_path: Path) -> Iterator[dict]:
    from gremlin.ui import device_pack

    old = shared_state.current_profile
    fire = rows.create(_B, "/fire", trigger=True)  # type: ignore[attr-defined]
    osc_device_file.save()
    # Its friendly name, by its permanent id (module_model.osc_friendly_key).
    doc = json.loads(osc_device_file.path().read_text("utf-8"))
    doc.setdefault("claim", {}).setdefault("friendly", {})[f"osc:{fire.uid}"] = "Fire"
    osc_device_file.path().write_text(json.dumps(doc), "utf-8")
    source = Profile()
    shared_state.current_profile = source
    _map_vjoy(source, fire.input_id, 7)
    built = device_pack.assemble(
        "OSC", lambda stored: None, None, {}, source, str(OSC_DEVICE_UUID)
    )
    assert not isinstance(built, str), built
    path = tmp_path / "osc.zip"
    path.write_bytes(built[0])
    # The second PC: OSC has another address on button 1.
    rows.load_dict({"inputs": []})  # type: ignore[attr-defined]
    other = rows.create(_B, "/other")  # type: ignore[attr-defined]
    osc_device_file.save()
    target = Profile()
    shared_state.current_profile = target
    yield {"zip": path, "fire": fire.uid, "other": other.uid, "profile": target}
    device_pack.drop_import_undo()
    shared_state.current_profile = old


def test_a_pack_s_wires_carry_the_osc_uid_and_create_the_address(
    osc_pack: dict, rows: object
) -> None:
    from gremlin.ui import device_pack

    result = device_pack.apply_zip(
        osc_pack["zip"], "OSC", {"items": ["wire:Default"]},
        target_guid=str(OSC_DEVICE_UUID),
    )
    assert result["ok"], result
    made = rows.by_uid(osc_pack["fire"])  # type: ignore[attr-defined]
    assert made is not None and made.label == "/fire" and made.trigger is True
    # Button 1 is /other here: the wire follows /fire to its new number.
    assert made.input_id == 2
    assert _vjoy_targets(osc_pack["profile"]) == {2: 7}
    saved = [r["uid"] for r in osc_device_file.read_inputs()]
    assert osc_pack["fire"] in saved
    assert device_pack.undo_import()["ok"]
    assert rows.by_uid(osc_pack["fire"]) is None  # type: ignore[attr-defined]
    assert rows.by_uid(osc_pack["other"]) is not None  # type: ignore[attr-defined]
    assert osc_pack["fire"] not in [r["uid"] for r in osc_device_file.read_inputs()]


def test_a_pack_carries_osc_s_addresses_and_server_in_one_write(
    osc_pack: dict, rows: object
) -> None:
    from gremlin.ui import device_pack

    ids = device_pack.pack_item_ids(osc_pack["zip"])
    assert "in.osc" in ids["input"], ids
    result = device_pack.apply_zip(
        osc_pack["zip"], "OSC", {"items": ["in.osc"]},
        target_guid=str(OSC_DEVICE_UUID),
    )
    assert result["ok"], result
    saved = osc_device_file.read_inputs()
    assert [r["uid"] for r in saved] == [osc_pack["fire"]]
    assert isinstance(osc_device_file.read_server(), dict)


def test_a_library_put_back_takes_osc_s_file() -> None:
    from gremlin import library_copy

    picked = library_copy._module_items(["in.osc", "in.checks"], [], everything=True)
    assert "in.osc" in picked


def test_an_osc_input_block_gets_its_uid_after_the_number(rows: object) -> None:
    from gremlin.ui import device_pack

    made = rows.create(_B, "/a")  # type: ignore[attr-defined]
    block = (
        f"<input><device-id>{OSC_DEVICE_UUID}</device-id>"
        "<input-type>button</input-type><mode>Default</mode>"
        "<input-id>1</input-id></input>"
    )
    modes = [{"name": "Default", "inputs": [block]}]
    carried = device_pack._with_osc_uids(modes)
    node = ElementTree.fromstring(modes[0]["inputs"][0])
    tags = [child.tag for child in node]
    assert tags.index("osc-uid") == tags.index("input-id") + 1
    assert node.findtext("osc-uid") == made.uid
    assert [r["uid"] for r in carried] == [made.uid]


def test_osc_friendly_names_travel_by_uid(osc_pack: dict) -> None:
    from gremlin.ui import device_pack

    ids = device_pack.pack_item_ids(osc_pack["zip"])
    assert "in.names" in ids["input"], ids
    result = device_pack.apply_zip(
        osc_pack["zip"], "OSC", {"items": ["in.names"]},
        target_guid=str(OSC_DEVICE_UUID),
    )
    assert result["ok"], result
    doc = json.loads(osc_device_file.path().read_text("utf-8"))
    assert doc["claim"]["friendly"].get(f"osc:{osc_pack['fire']}") == "Fire"


def test_a_saved_older_profile_s_own_osc_rows_count_and_are_not_merged(
    osc_pack: dict, rows: object
) -> None:
    """A saved older profile read without opening it keeps its OSC rows in
    pending_osc_rows: wires on /fire land on its row, nothing is added to
    OSC's file from here (D-09-OSC-FILE 3)."""
    from gremlin.ui import device_pack

    into = Profile()
    into.pending_osc_rows = {  # type: ignore[attr-defined]
        "inputs": [
            {"uid": osc_pack["fire"], "type": "button", "id": 4, "label": "/fire"}
        ]
    }
    loaded = device_pack._read_zip(osc_pack["zip"])
    plan = device_pack._plan_wires(
        loaded["wires"], {"wire:Default"}, None,
        device_pack._rows_of(into), device_pack._osc_rows_of(into),
    )
    assert plan["missingOsc"] == []
    result = device_pack.apply_zip(
        osc_pack["zip"], "OSC", {"items": ["wire:Default"]}, into,
        target_guid=str(OSC_DEVICE_UUID),
    )
    assert result["ok"], result
    assert rows.by_uid(osc_pack["fire"]) is None  # type: ignore[attr-defined]
    assert _vjoy_targets(into) == {4: 7}
