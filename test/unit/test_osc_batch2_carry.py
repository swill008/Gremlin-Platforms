# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""OSC batch 2's new parts of OSC's module file travel like the rest of it
(09 S147-S158): a pattern input (/fader/*), a feedback row with an
action_state source and a "Show under this input" key (`input`), and one
with an osc_input source on the pattern input, come back whole through
Save to Device Library and Restore, Export (current and saved), a Device
Pack import ("OSC addresses and server": osc.json comes back key for key)
and History restore.

Feedback rows name an action by its id, and that id lives in the profile,
not in osc.json. So the action ids are checked too: a Device Pack's wires
keep the Smart Toggle's id when imported into a profile that doesn't hold
it (a fresh profile, or the same profile where the import replaces the
mode), so the row still finds its action; where the profile already holds
that id elsewhere the import gives the action a new id and the feedback rows
that come in the same pack follow it (D-09-OSC-ACTSTATE: the owner keeps the
reference; nothing re-links rows later).

The real store, Library, Device Pack and History in an empty modules
folder; no network."""

from __future__ import annotations

import copy
import json
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest

from gremlin import device_library as library
from gremlin import library_copy, osc_device_file, plugin_manager, shared_state
from gremlin.osc import OSC_DEVICE_UUID, OscDevice
from gremlin.profile import DeviceInfo, Profile
from gremlin.types import InputType
from gremlin.ui import history_model
from test.unit import (
    test_osc_features_carry as _carry,  # pyright: ignore[reportMissingImports]
)

# The OSC features batch's fixtures: an empty modules folder, OSC's rows
# emptied and put back, the osc.json write / History watcher.
_app = _carry._app
folder = _carry.folder
modules = _carry.modules
rows = _carry.rows
watch_maker = _carry.watch_maker
_osc_doc_in = _carry._osc_doc_in
_save = _carry._save

pytestmark = pytest.mark.validate_off

_A = InputType.JoystickAxis
_B = InputType.JoystickButton
PATTERN = "/fader/*"
BUTTON = "/btn"
ACT = "3c1e2f4a-5b6c-4d7e-8f90-a1b2c3d4e5f6"


def _feedback(uids: dict) -> list[dict]:
    return [
        {
            "id": "a1" * 16,
            "enabled": True,
            "source": {
                "kind": "action_state",
                "device": None,
                "input": None,
                "action": ACT,
            },
            "target": "reply",
            "address": "/fb/toggle",
            "min": 0.0,
            "max": 7.0,
            "type": "int",
            "on_value": 5,
            "off_value": 1,
            "input": uids[BUTTON],
        },
        {
            "id": "a2" * 16,
            "enabled": False,
            "source": {"kind": "osc_input", "device": None, "input": uids[PATTERN]},
            "target": "reply",
            "address": "/fb/fader",
            "min": 0.0,
            "max": 1.0,
            "type": "float",
        },
    ]


@pytest.fixture
def state_a(rows: object) -> dict:
    """OSC's file as saved: a pattern axis, an exact button and the two
    feedback rows."""
    fader = rows.create(_A, PATTERN, range_min=0.0, range_max=1.0)  # type: ignore[attr-defined]
    btn = rows.create(_B, BUTTON)  # type: ignore[attr-defined]
    uids = {PATTERN: fader.uid, BUTTON: btn.uid}
    assert osc_device_file.save()
    feedback = _feedback(uids)
    assert osc_device_file.write_feedback(feedback)
    # Cleaning keeps the new keys as written.
    assert osc_device_file.clean_feedback(feedback) == feedback
    return {"uids": uids, "feedback": feedback, "doc": _doc()}


def _doc() -> dict:
    return json.loads(osc_device_file.path().read_text(encoding="utf-8-sig"))


def _change_to_b(rows: object) -> None:
    """After saving: the pattern input gone, other feedback."""
    data = rows.to_dict()  # type: ignore[attr-defined]
    data["inputs"] = [r for r in data["inputs"] if r["label"] != PATTERN]
    rows.load_dict(data)  # type: ignore[attr-defined]
    assert osc_device_file.save()
    assert osc_device_file.write_feedback([])
    assert PATTERN not in [r.get("label") for r in _doc().get("inputs") or []]


def _assert_carries(doc: dict, state: dict) -> None:
    """A document (the file or one in a zip) holds A's pattern input and
    feedback rows, ids and keys as written."""
    inputs = {r.get("label"): r for r in doc.get("inputs") or []}
    assert PATTERN in inputs, list(inputs)
    assert inputs[PATTERN]["uid"] == state["uids"][PATTERN]
    assert inputs[BUTTON]["uid"] == state["uids"][BUTTON]
    feedback = osc_device_file.clean_feedback(doc.get("feedback"))
    assert feedback == state["feedback"], doc.get("feedback")
    assert feedback[0]["source"]["action"] == ACT
    assert feedback[0]["input"] == state["uids"][BUTTON]


def _assert_state_a(state: dict) -> None:
    _assert_carries(_doc(), state)
    assert osc_device_file.read_feedback() == state["feedback"]
    row = OscDevice().rows.by_uid(state["uids"][PATTERN])
    assert row is not None and row.label == PATTERN and row.is_pattern
    # The pattern answers again at run time (the index was rebuilt).
    assert [r.uid for r in OscDevice().rows.matches("/fader/2", (0.5,))] == [
        state["uids"][PATTERN]
    ]


# --- (1) Save to Device Library, then Restore --------------------------------


@pytest.mark.parametrize("how", ["restore_to_stick", "restore"])
def test_library_restore_brings_back_pattern_and_feedback_rows(
    how: str, state_a: dict, rows: object, watch_maker: object
) -> None:
    setup = _save()
    _change_to_b(rows)
    watch = watch_maker()  # type: ignore[operator]
    out = getattr(library_copy, how)(setup["key"])
    assert out["ok"], out
    _assert_state_a(state_a)
    assert len(watch.writes) == 1, watch.writes


# --- (2) Export current / saved ------------------------------------------------


def test_export_current_carries_pattern_and_feedback_rows(
    state_a: dict, tmp_path: Path
) -> None:
    row = next(r for r in library.devices() if r["name"] == "OSC")
    dest = tmp_path / "out" / "now.zip"
    assert library.export_current(row["key"], dest)["ok"]
    _assert_carries(_osc_doc_in(dest), state_a)


def test_export_saved_setup_carries_pattern_and_feedback_rows(
    state_a: dict, rows: object, tmp_path: Path
) -> None:
    setup = _save()
    _change_to_b(rows)
    dest = tmp_path / "out" / "saved.zip"
    assert library.export_setup(setup["key"], dest)["ok"]
    _assert_carries(_osc_doc_in(dest), state_a)


# --- (3) Device Pack: osc.json travels whole ----------------------------------


@pytest.fixture
def profile() -> Iterator[Profile]:
    old = shared_state.current_profile
    made = _osc_profile()
    shared_state.current_profile = made
    yield made
    from gremlin.ui import device_pack

    device_pack.drop_import_undo()
    shared_state.current_profile = old


def _osc_profile() -> Profile:
    made = Profile()
    made.device_database.devices[OSC_DEVICE_UUID] = DeviceInfo(OSC_DEVICE_UUID, "OSC")
    return made


def _pack(profile: Profile, tmp_path: Path, name: str = "osc.zip") -> Path:
    from gremlin.ui import device_pack

    built = device_pack.assemble(
        "OSC", lambda stored: None, None, {}, profile, str(OSC_DEVICE_UUID)
    )
    assert not isinstance(built, str), built
    path = tmp_path / name
    path.write_bytes(built[0])
    return path


def test_device_pack_carries_osc_json_whole(
    state_a: dict, rows: object, profile: Profile, tmp_path: Path
) -> None:
    from gremlin.ui import device_pack

    path = _pack(profile, tmp_path)
    packed = _osc_doc_in(path)
    _assert_carries(packed, state_a)
    _change_to_b(rows)
    result = device_pack.apply_zip(
        path, "OSC", {"items": ["in.osc"]}, target_guid=str(OSC_DEVICE_UUID)
    )
    assert result["ok"], result
    _assert_state_a(state_a)
    # Whole: every part of the file as saved comes back as it was.
    # The device's GUID comes back lower-case (same GUID).
    now = _doc()

    def same(key: str) -> bool:
        old, new = state_a["doc"][key], now.get(key)
        if key == "boundGuidLocal":
            return str(old).lower() == str(new).lower()
        return old == new

    differ = [k for k in state_a["doc"] if not same(k)]
    assert differ == [], {k: (state_a["doc"][k], now.get(k)) for k in differ}


# --- (4) History restore ------------------------------------------------------


@pytest.mark.parametrize("part", ["feedback", "inputs"])
def test_history_restore_brings_back_pattern_or_feedback_rows(
    part: str, state_a: dict, rows: object, watch_maker: object
) -> None:
    watch = watch_maker()  # type: ignore[operator]
    if part == "feedback":
        assert osc_device_file.write_feedback([], "OSC page")
    else:
        data = rows.to_dict()  # type: ignore[attr-defined]
        data["inputs"] = [r for r in data["inputs"] if r["label"] != PATTERN]
        rows.load_dict(data)  # type: ignore[attr-defined]
        assert osc_device_file.save()
    entries = watch.entries()
    assert len(entries) == 1, entries
    before = json.loads((entries[0].get("before") or {}).get("text") or "{}")
    _assert_carries(before, state_a)
    out = history_model.restore(str(entries[0]["id"]), "before")
    assert out["ok"], out
    _assert_state_a(state_a)


# --- (5) Action ids through a Device Pack's wires -----------------------------


def _smart_toggle(action_id: str) -> object:
    manager = plugin_manager.PluginManager()
    toggle = manager.create_instance("Smart Toggle", _B)
    toggle._id = uuid.UUID(action_id)
    child = manager.create_instance("Map to vJoy", _B)
    child.vjoy_device_id = 1
    child.vjoy_input_id = 4
    child.vjoy_input_type = _B
    toggle.insert_action(child, "children")
    return toggle


def _bind_toggle(profile: Profile, number: int) -> None:
    item = profile.get_input_item(
        OSC_DEVICE_UUID, _B, number, "Default", create_if_missing=True
    )
    item.add_item_binding().root_action.insert_action(_smart_toggle(ACT), "children")


def _toggle_ids(profile: Profile) -> list[str]:
    from gremlin.profile import reachable

    return [
        str(action.id)
        for item in profile.inputs.get(OSC_DEVICE_UUID, [])
        for binding in item.action_sequences
        for action in reachable([binding.root_action])
        if action.name == "Smart Toggle"
    ]


def _placement(profile: Profile) -> str | None:
    """Where the action_state row shows on the page: its action's OSC input
    (09 S153, osc_feedback_model.action_inputs)."""
    from gremlin.ui import osc_feedback_model

    return osc_feedback_model.action_inputs(profile).get(ACT)


@pytest.fixture
def wired(state_a: dict, profile: Profile, tmp_path: Path) -> dict:
    """The profile's /btn has a Smart Toggle with id ACT; a pack of OSC
    with its wires."""
    btn = OscDevice().rows.by_uid(state_a["uids"][BUTTON])
    _bind_toggle(profile, btn.input_id)
    assert _toggle_ids(profile) == [ACT]
    assert _placement(profile) == state_a["uids"][BUTTON]
    return {"zip": _pack(profile, tmp_path, "wires.zip"), **state_a}


def _import_wires(path: Path) -> dict:
    from gremlin.ui import device_pack

    return device_pack.apply_zip(
        path,
        "OSC",
        {"items": ["in.osc", "wire:Default"]},
        target_guid=str(OSC_DEVICE_UUID),
    )


def test_pack_wires_keep_the_action_id_in_a_fresh_profile(wired: dict) -> None:
    target = _osc_profile()
    shared_state.current_profile = target
    result = _import_wires(wired["zip"])
    assert result["ok"], result
    assert _toggle_ids(target) == [ACT]
    # The feedback row (from the same pack) still finds its action.
    assert osc_device_file.read_feedback() == wired["feedback"]
    assert _placement(target) == wired["uids"][BUTTON]


def test_pack_wires_keep_the_action_id_when_replacing_the_same_mode(
    wired: dict, profile: Profile
) -> None:
    result = _import_wires(wired["zip"])
    assert result["ok"], result
    assert _toggle_ids(profile) == [ACT]
    assert _placement(profile) == wired["uids"][BUTTON]


def test_pack_wires_get_a_new_action_id_and_the_pack_s_row_follows_it(
    wired: dict,
) -> None:
    """A profile that already holds the action id elsewhere gets a new id
    for the imported action; the action_state row that came in the same
    pack (its osc.json) names the new id, in the same write."""
    target = _osc_profile()
    clash = copy.copy(_smart_toggle(ACT))
    target.library.add_action(clash)  # type: ignore[arg-type]
    shared_state.current_profile = target
    result = _import_wires(wired["zip"])
    assert result["ok"], result
    ids = _toggle_ids(target)
    assert len(ids) == 1 and ids[0] != ACT, ids
    feedback = osc_device_file.read_feedback()
    assert feedback[0]["source"]["action"] == ids[0]
    # Only the action id moved; the rest of the rows is as packed.
    expected = copy.deepcopy(wired["feedback"])
    expected[0]["source"]["action"] = ids[0]
    assert feedback == expected
    assert osc_device_file.read_feedback() == _doc()["feedback"]


def test_pack_wires_without_osc_json_leave_the_target_s_rows(
    wired: dict,
) -> None:
    """Wires only (no "OSC addresses and server"): the rows already in the
    target's osc.json belong to the action that kept the id; untouched."""
    from gremlin.ui import device_pack

    target = _osc_profile()
    clash = copy.copy(_smart_toggle(ACT))
    target.library.add_action(clash)  # type: ignore[arg-type]
    shared_state.current_profile = target
    result = device_pack.apply_zip(
        wired["zip"],
        "OSC",
        {"items": ["wire:Default"]},
        target_guid=str(OSC_DEVICE_UUID),
    )
    assert result["ok"], result
    ids = _toggle_ids(target)
    assert len(ids) == 1 and ids[0] != ACT, ids
    assert osc_device_file.read_feedback() == wired["feedback"]
    assert osc_device_file.read_feedback()[0]["source"]["action"] == ACT


def test_library_restore_leaves_action_ids_and_the_row_s_reference(
    wired: dict, profile: Profile, rows: object
) -> None:
    """A Library put-back writes only osc.json; the profile's action keeps
    its id and the restored row still names it."""
    setup = _save()
    _change_to_b(rows)
    assert library_copy.restore_to_stick(setup["key"])["ok"]
    assert _toggle_ids(profile) == [ACT]
    assert osc_device_file.read_feedback()[0]["source"]["action"] == ACT
    assert _placement(profile) == wired["uids"][BUTTON]
