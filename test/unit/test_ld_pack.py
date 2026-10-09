# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Device Pack and the Logical Device's own module file (D-04-LD-FILE,
08 S64, S72, S80).

Missing Logical Device inputs used to be created in the open profile's own
rows, found by number only; a profile that isn't open was checked against
its own (now gone) rows. Now every profile uses the module file: the pack
carries each target's permanent id, an import creates what is missing in
the file (under the pack's id), and Undo Import takes it out of the file.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from pathlib import Path
from xml.etree import ElementTree

import pytest

from gremlin import library_profiles, logical_device_file, shared_state
from gremlin.logical_device import LogicalDevice
from gremlin.profile import Profile
from gremlin.types import InputType
from gremlin.ui import device_pack
from test.unit.test_device_pack_import import (  # noqa: F401
    _import,
    _logical_link,
    pack,
)
from test.unit.test_ld_profile import _v14, modules  # noqa: F401


@pytest.fixture
def empty_logical() -> Iterator[LogicalDevice]:
    rows = LogicalDevice()
    before = rows.to_dict()
    rows.reset()
    rows.mark_saved()
    yield rows
    rows.load_dict(before)
    rows.mark_saved()


def _action(number: int, uid: str = "") -> str:
    node = ElementTree.Element(
        "action", {"id": "a" * 32, "type": "map-to-logical-device"}
    )
    props = [
        ("logical-input-id", "int", str(number)),
        ("logical-input-type", "input_type", "button"),
    ]
    if uid:
        props.append(("logical-input-uid", "string", uid))
    for name, kind, value in props:
        prop = ElementTree.SubElement(node, "property", {"type": kind})
        ElementTree.SubElement(prop, "name").text = name
        ElementTree.SubElement(prop, "value").text = value
    return ElementTree.tostring(node, encoding="unicode")


def _file_controls() -> list[dict]:
    return list(logical_device_file.read_layout().get("controls") or [])


def test_the_export_carries_the_permanent_id(empty_logical: LogicalDevice) -> None:
    made = empty_logical.create(InputType.JoystickButton, input_id=7)
    profile = Profile()
    shared_state.current_profile = profile
    try:
        guid = "11111111-2222-3333-4444-555555555555"
        _logical_link(profile, uuid.UUID(guid), 5, 7)
        wires = device_pack._collect_wires(guid, profile=profile)
    finally:
        shared_state.current_profile = None
    targets = device_pack._logical_targets(wires["actions"])
    assert targets == [("button", 7, made.uid)]


def test_a_target_is_found_by_its_id(empty_logical: LogicalDevice) -> None:
    mine = empty_logical.create(InputType.JoystickButton, input_id=7)
    # The same id under another number: found (the number is a name only).
    assert device_pack._missing_logical([_action(3, mine.uid)]) == []
    # An id the file doesn't have: missing, even where button 7 exists
    # (decision 4: never re-targeted by number).
    other = "b" * 32
    assert device_pack._missing_logical([_action(7, other)]) == [("button", 7, other)]
    # An older pack, no id: by type and number.
    assert device_pack._missing_logical([_action(7)]) == []
    assert device_pack._missing_logical([_action(9)]) == [("button", 9, "")]


def test_a_saved_profile_is_checked_against_the_file(
    empty_logical: LogicalDevice,
) -> None:
    """A version 15 profile that isn't open has no rows of its own: the
    module file says what is missing (it used to be its empty rows)."""
    empty_logical.create(InputType.JoystickButton, input_id=7)
    other = Profile(bind=False)
    rows = device_pack._rows_of(other)
    assert device_pack._missing_logical([_action(7)], rows) == []


def test_missing_inputs_go_into_the_file_and_undo_takes_them_out(
    pack: dict, empty_logical: LogicalDevice  # noqa: F811
) -> None:
    result = _import(pack, ["wire:Default"], createLogical=True)
    assert result["ok"], result
    made = [
        c for c in _file_controls() if c.get("type") in ("button", "JoystickButton")
    ]
    assert [int(c["id"]) for c in made] == [7], _file_controls()
    uid = made[0]["uid"]
    assert empty_logical.by_uid(uid) is not None
    assert device_pack.undo_import()["ok"]
    assert empty_logical.by_uid(uid) is None
    assert all(c.get("uid") != uid for c in _file_controls())


def test_an_id_from_the_pack_is_kept_under_the_lowest_free_number(
    pack: dict, empty_logical: LogicalDevice  # noqa: F811
) -> None:
    """The pack's button 7 has an id the file lacks, and this PC's button 7
    is another control: the import adds it under the lowest free number
    (06 S78), button 1, with the pack's id."""
    plan = {
        "modes": ["Default"],
        "counts": {"Default": 0},
        "inputs": [],
        "actions": [],
        "leftOut": [],
        "missingLogical": [("button", 7, "c" * 32)],
    }
    empty_logical.create(InputType.JoystickButton, input_id=7)
    notes, undo = device_pack._apply_wires(
        plan, {}, str(pack["uid"]), pack["name"], {}, True, pack["profile"]
    )
    assert undo is not None, notes
    row = empty_logical.by_uid("c" * 32)
    assert row is not None and row.id == 1, notes
    assert "Created on the Logical Device: Button 1." in notes
    assert any(c.get("uid") == "c" * 32 for c in _file_controls())


def test_saving_a_saved_v14_profile_keeps_its_logical_rows(
    modules: Path,  # noqa: F811
    xml_dir: Path,
) -> None:
    """Copy and Swap save a profile that isn't open through save_profile:
    a version 14 profile's rows go into the module file then (they used to
    be dropped: the file is written as version 15 without them)."""
    # The file has another button (a file with none: reading the profile's
    # Map to Logical Device makes a default Button 1 in the shown rows).
    other = LogicalDevice()
    other.load_dict({"controls": [], "groups": []})
    other.create(InputType.JoystickButton, input_id=5, label="Other")
    logical_device_file.save()
    path = _v14(xml_dir)
    read = library_profiles.read_profile(path)
    assert not isinstance(read, str), read
    labels = [c["label"] for c in logical_device_file.read_layout()["controls"]]
    assert labels == ["Other"]
    library_profiles.save_profile(read, path)
    labels = [c["label"] for c in logical_device_file.read_layout()["controls"]]
    assert sorted(labels) == ["Button 1", "Other"]
    assert path.with_name(path.name + ".v14.bak").is_file()
    assert ElementTree.parse(path).getroot().get("version") == "15"

