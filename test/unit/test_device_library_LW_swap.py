# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Device Library: Swap with Another Stick (10 S26-S29, S33-S34, S41)."""

from __future__ import annotations

import json
import pathlib
import shutil
import uuid

import pytest

import gremlin.profile
from gremlin import device_library as library
from gremlin import library_swap, shared_state, swap_devices, util
from gremlin.modules import ids, store
from gremlin.types import InputType

LEFT_ID = "97b77b40-07d8-11f0-8028-444553540000"
RIGHT_ID = str(uuid.UUID("12345678-1234-1234-1234-1234567890ab"))
LEFT = ("Left stick", LEFT_ID)
RIGHT = ("Right stick", RIGHT_ID)
ALL = ["setup", "button_map", "appearance", "calibration", "bindings"]

# Left has buttons 1-5, axes 1-3, hat 1; Right has buttons 1-6, axes 1-2, hat 1.
HAS = {
    LEFT_ID: ({1, 2, 3, 4, 5}, {1, 2, 3}, {1}),
    RIGHT_ID: ({1, 2, 3, 4, 5, 6}, {1, 2}, {1}),
}


def _controls(guid: str) -> dict[str, set[int]]:
    buttons, axes, hats = HAS[guid]
    return {"button": buttons, "axis": axes, "hat": hats}


def _where(profile: gremlin.profile.Profile, guid: str) -> set[tuple[str, int]]:
    return {
        (item.input_type.name, int(item.input_id))
        for item in profile.inputs.get(uuid.UUID(guid), [])
        if item.device_id == uuid.UUID(guid)
    }


@pytest.fixture
def sticks(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> dict:
    """Two connected sticks with module files, pictures, and fakes for the
    Library's autosave and last change."""
    modules = tmp_path / "modules"
    modules.mkdir()
    monkeypatch.setattr(util, "modules_dir", lambda: modules)
    slugs = {LEFT_ID: "left", RIGHT_ID: "right"}
    real_path_for = store.path_for

    def path_for(name: str, guid: str = "") -> pathlib.Path:
        # Other sticks (a Home model left by an earlier test may refresh
        # while this one runs) keep the real lookup.
        if guid in slugs:
            return store.path_of(slugs[guid])
        return real_path_for(name, guid)

    monkeypatch.setattr(store, "path_for", path_for)
    monkeypatch.setattr(store, "connected_input_ids", lambda guid: HAS.get(guid))
    (modules / "left").mkdir()
    (modules / "left" / "photo.jpg").write_bytes(b"left photo")
    (modules / "right").mkdir()
    (modules / "right" / "map.png").write_bytes(b"right map")
    left = {
        "kind": "control.hardware",
        "device": "Left stick",
        "claim": {
            "buttons": [1, 2, 5],
            "axes": [3],
            "hats": [],
            "friendly": {"button:1": "Fire", "axis:3": "Throttle"},
        },
        "calibration": {"1": [0, 500, 1000], "3": [10, 20, 30]},
        "view": {"layout": "left view"},
        "image": "left/photo.jpg",
    }
    right = {
        "kind": "control.hardware",
        "device": "Right stick",
        "claim": {
            "buttons": [3, 6],
            "axes": [],
            "hats": [],
            "friendly": {"button:3": "Trigger", "button:6": "Pinkie"},
        },
        "layout": {
            "groups": ["Right"],
            "order": ["button:3"],
            "group_of": {"button:3": "Right"},
        },
        "nodes": [{"id": "n1", "kind": "image", "src": "right/map.png"}],
    }
    store.path_of("left").write_text(json.dumps(left), encoding="utf-8")
    store.path_of("right").write_text(json.dumps(right), encoding="utf-8")
    calls: dict = {"autosave": [], "last": [], "fail": set()}

    def autosave(
        name: str, guid: str, trigger: str, reason: str, profiles: list
    ) -> dict:
        calls["autosave"].append((name, guid, trigger, reason, list(profiles)))
        if name in calls["fail"]:
            return {"ok": False, "error": "disk full", "warnings": [], "notes": []}
        key = "set-" + ("aaaaaaaa" if guid == LEFT_ID else "bbbbbbbb")
        return {
            "ok": True,
            "error": "",
            "warnings": [],
            "notes": [],
            "setups": [{"key": key}],
        }

    monkeypatch.setattr(library, "autosave", autosave)
    monkeypatch.setattr(
        library,
        "set_last_change",
        lambda op, keys, label, detail=None: calls["last"].append((op, keys, label)),
    )
    monkeypatch.setattr(shared_state, "current_profile", None)
    calls["modules"] = modules
    return calls


def _open(
    xml_dir: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> gremlin.profile.Profile:
    profile = gremlin.profile.Profile()
    profile.from_xml(xml_dir / "profile_auto_mapper.xml")
    monkeypatch.setattr(shared_state, "current_profile", profile)
    return profile


def _doc(name: str) -> dict:
    return json.loads(store.path_of(name).read_text(encoding="utf-8"))


# --- swap_devices with limits (the shared owner) ----------------------------------


def test_swap_devices_keeps_inputs_the_other_stick_lacks(xml_dir: pathlib.Path) -> None:
    """S27: a binding on a control the other stick lacks stays where it was."""
    profile = gremlin.profile.Profile()
    profile.from_xml(xml_dir / "profile_auto_mapper.xml")
    result = swap_devices.swap_devices(
        profile,
        uuid.UUID(LEFT_ID),
        uuid.UUID(RIGHT_ID),
        (_controls(LEFT_ID), _controls(RIGHT_ID)),
    )
    assert _where(profile, LEFT_ID) == {("JoystickAxis", 3)}
    assert ("JoystickButton", 5) in _where(profile, RIGHT_ID)
    assert ("JoystickAxis", 3) not in _where(profile, RIGHT_ID)
    assert len(_where(profile, RIGHT_ID)) == 8
    assert result.input_swaps == 8


def test_swap_devices_without_limits_moves_everything(xml_dir: pathlib.Path) -> None:
    profile = gremlin.profile.Profile()
    profile.from_xml(xml_dir / "profile_auto_mapper.xml")
    swap_devices.swap_devices(profile, uuid.UUID(LEFT_ID), uuid.UUID(RIGHT_ID))
    assert _where(profile, LEFT_ID) == set()
    assert len(_where(profile, RIGHT_ID)) == 9


# --- refusals (S29) -----------------------------------------------------------------


@pytest.mark.parametrize(
    "other",
    [
        ("Keyboard", str(ids.KEYBOARD)),
        ("Logical Device", str(ids.LOGICAL_DEVICE)),
        ("OSC", str(ids.OSC)),
        ("Xbox", str(ids.XBOX)),
        LEFT,
        ("Unplugged", str(uuid.uuid4())),
    ],
)
def test_swap_refuses(sticks: dict, other: tuple[str, str]) -> None:
    result = library_swap.swap(LEFT, other, ALL, [])
    assert result["ok"] is False and result["error"]
    assert sticks["autosave"] == []
    assert library_swap.plan_swap(LEFT, other, ALL, [])["ok"] is False


# --- plan (S27) ---------------------------------------------------------------------


def test_plan_warns_both_directions(
    sticks: dict, xml_dir: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    profile = _open(xml_dir, monkeypatch)
    plan = library_swap.plan_swap(LEFT, RIGHT, ALL, [pathlib.Path(profile.fpath)])
    assert plan["ok"] is True
    text = "\n".join(plan["warnings"])
    assert "Right stick has no Axis 3: Left stick's setup" in text
    assert "Left stick has no Button 6: Right stick's setup" in text
    assert (
        "Right stick has no Axis 3: Left stick's bindings on them in "
        "profile_auto_mapper" in text
    )
    assert sticks["autosave"] == []  # a plan changes nothing


# --- the swap (S26, S28, S33) ------------------------------------------------------


def test_swap_exchanges_parts_and_bindings(
    sticks: dict, xml_dir: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    profile = _open(xml_dir, monkeypatch)
    path = pathlib.Path(profile.fpath)
    on_disk = path.read_bytes()
    result = library_swap.swap(LEFT, RIGHT, ALL, [path])
    assert result["ok"] is True, result
    # Both autosaved first, each naming the other (S17, S28).
    assert [c[3] for c in sticks["autosave"]] == [
        "Autosave: before Swap with Right stick",
        "Autosave: before Swap with Left stick",
    ]
    assert all(c[2] == "swap" and c[4] == [path] for c in sticks["autosave"])
    assert sticks["last"] == [
        ("swap", ["set-aaaaaaaa", "set-bbbbbbbb"], "Swap Left stick with Right stick")
    ]
    left, right = _doc("left"), _doc("right")
    # Setup: controls both have trade places; Axis 3 (Right lacks) and
    # Button 6 (Left lacks) stay.
    assert left["claim"]["buttons"] == [3]
    assert left["claim"]["axes"] == [3]
    assert left["claim"]["friendly"] == {"axis:3": "Throttle", "button:3": "Trigger"}
    assert right["claim"]["buttons"] == [1, 2, 5, 6]
    assert right["claim"]["friendly"] == {"button:1": "Fire", "button:6": "Pinkie"}
    # Calibration: axis 1 moves, axis 3 stays.
    assert left["calibration"] == {"3": [10, 20, 30]}
    assert right["calibration"] == {"1": [0, 500, 1000]}
    # The Configuration layout goes with the setup (CF-Q1); Appearance
    # (Output View) and Button Map trade places, pictures with them.
    assert (
        left["layout"]
        == {
            "groups": ["Right"],
            "order": ["button:3"],
            "group_of": {"button:3": "Right"},
        }
        and "view" not in left
    )
    assert right["view"] == {"layout": "left view"} and "layout" not in right
    assert right["image"] == "right/photo.jpg"
    assert (sticks["modules"] / "right" / "photo.jpg").read_bytes() == b"left photo"
    assert left["nodes"][0]["src"] == "left/map.png"
    assert (sticks["modules"] / "left" / "map.png").read_bytes() == b"right map"
    assert "image" not in left and "nodes" not in right
    # Bindings: the open profile changes in memory, unsaved (S33).
    assert _where(profile, LEFT_ID) == {("JoystickAxis", 3)}
    assert len(_where(profile, RIGHT_ID)) == 8
    assert path.read_bytes() == on_disk
    assert profile.has_unsaved_changes()
    assert any("Right stick has no Axis 3" in w for w in result["warnings"])


def test_swap_bindings_only_leaves_module_files(
    sticks: dict, xml_dir: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    profile = _open(xml_dir, monkeypatch)
    before = (store.path_of("left").read_bytes(), store.path_of("right").read_bytes())
    result = library_swap.swap(LEFT, RIGHT, ["bindings"], [pathlib.Path(profile.fpath)])
    assert result["ok"] is True
    assert (
        store.path_of("left").read_bytes(),
        store.path_of("right").read_bytes(),
    ) == before
    assert len(_where(profile, RIGHT_ID)) == 8


def test_swap_saved_profile_and_unreadable_one(
    sticks: dict, xml_dir: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    """S33-S34: a ticked saved profile is changed on disk; one that can't be
    read is named and left as it was, the others still change."""
    saved = tmp_path / "saved.xml"
    shutil.copy(xml_dir / "profile_auto_mapper.xml", saved)
    missing = tmp_path / "missing.xml"
    result = library_swap.swap(LEFT, RIGHT, ["bindings"], [saved, missing])
    assert result["ok"] is True
    assert any("missing.xml" in w for w in result["warnings"])
    assert not missing.exists()
    reread = gremlin.profile.Profile()
    reread.from_xml(saved)
    assert _where(reread, LEFT_ID) == {("JoystickAxis", 3)}
    assert len(_where(reread, RIGHT_ID)) == 8


def test_swap_refused_when_an_autosave_fails(
    sticks: dict, xml_dir: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """S20, S28: no autosave, no swap; nothing changes."""
    profile = _open(xml_dir, monkeypatch)
    sticks["fail"].add("Right stick")
    before = (store.path_of("left").read_bytes(), store.path_of("right").read_bytes())
    text = profile._xml_text()
    result = library_swap.swap(LEFT, RIGHT, ALL, [pathlib.Path(profile.fpath)])
    assert result["ok"] is False
    assert "Right stick" in result["error"] and "nothing was swapped" in result["error"]
    assert (
        store.path_of("left").read_bytes(),
        store.path_of("right").read_bytes(),
    ) == before
    assert profile._xml_text() == text
    assert sticks["last"] == []


def test_swap_refused_on_a_damaged_module_file(
    sticks: dict, xml_dir: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    profile = _open(xml_dir, monkeypatch)
    store.path_of("right").write_text("{ not json", encoding="utf-8")
    text = profile._xml_text()
    left_before = store.path_of("left").read_bytes()
    result = library_swap.swap(LEFT, RIGHT, ALL, [pathlib.Path(profile.fpath)])
    assert result["ok"] is False and "damaged" in result["error"]
    assert store.path_of("left").read_bytes() == left_before
    assert profile._xml_text() == text
    assert sticks["last"] == []


def test_input_types_are_joystick_kinds() -> None:
    assert (
        swap_devices.stays(
            type("I", (), {"input_type": InputType.Keyboard, "input_id": 9})(), {}, {}
        )
        is False
    )


# --- references inside actions (S27, D-10-SWAP-REFS) -------------------------------


def _refer_to_left_axis_3(profile: gremlin.profile.Profile) -> None:
    """A Merge Axis reading Left stick Axis 3 and a Macro (nested data, not
    an action) pressing Right stick Button 6: each a control the other stick
    lacks."""
    from action_plugins.axis_pair import AxisRef
    from gremlin import macro

    merge = profile.library.create("Merge Axis", InputType.JoystickAxis, reuse=False)
    assert merge is not None
    merge.axis_in1 = AxisRef(uuid.UUID(LEFT_ID), InputType.JoystickAxis, 3)  # type: ignore[attr-defined]
    made = profile.library.create("Macro", InputType.JoystickButton)
    assert made is not None
    made.actions.append(  # type: ignore[attr-defined]
        macro.JoystickAction(uuid.UUID(RIGHT_ID), InputType.JoystickButton, 6, True)
    )


def test_plan_lists_references_the_other_stick_lacks(
    sticks: dict, xml_dir: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    profile = _open(xml_dir, monkeypatch)
    _refer_to_left_axis_3(profile)
    plan = library_swap.plan_swap(
        LEFT, RIGHT, ["bindings"], [pathlib.Path(profile.fpath)]
    )
    text = "\n".join(plan["warnings"])
    assert "Merge Axis in profile_auto_mapper refers to Left stick Axis 3" in text
    assert "Macro in profile_auto_mapper refers to Right stick Button 6" in text
    assert "Right stick has no Axis 3" in text and "Left stick has no Button 6" in text


def test_swap_lists_references_and_still_moves_them(
    sticks: dict, xml_dir: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    profile = _open(xml_dir, monkeypatch)
    _refer_to_left_axis_3(profile)
    result = library_swap.swap(LEFT, RIGHT, ["bindings"], [pathlib.Path(profile.fpath)])
    assert result["ok"] is True
    assert any(
        "Merge Axis in profile_auto_mapper refers to Left stick Axis 3" in w
        for w in result["warnings"]
    )
    merges = profile.library.actions_by_predicate(lambda a: a.name == "Merge Axis")
    assert any(
        getattr(m, "axis_in1", None) is not None
        and m.axis_in1.device_guid == uuid.UUID(RIGHT_ID)  # type: ignore[attr-defined]
        and m.axis_in1.input_id == 3  # type: ignore[attr-defined]
        for m in merges
    )


def test_references_found_inside_conditions(xml_dir: pathlib.Path) -> None:
    """A Condition's joystick states (nested in the action) are found."""
    profile = gremlin.profile.Profile()
    profile.from_xml(xml_dir / "action_condition_complex.xml")
    refs = swap_devices.device_references(profile)
    found = {(label, str(device).upper(), kind, n) for label, device, kind, n in refs}
    assert ("Condition", "4DCB3090-97EC-11EB-8003-444553540000", "button", 2) in found
    assert ("Condition", "4DCB3090-97EC-11EB-8003-444553540024", "button", 42) in found


def test_other_sticks_keep_the_real_module_file_lookup(sticks: dict) -> None:
    """A Home model left by an earlier test may refresh while a swap test
    runs: asking about any other stick must not raise (full run seed 752346:
    KeyError in module_model._refresh_inplace failed this file's swap test)."""
    other = "{00000001-0000-0000-0000-000000000000}"
    assert store.path_for("Some other stick", other).name.endswith(".json")
