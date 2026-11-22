# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
"""Fixing a binding from Search (01 S195, D-01-SEARCH-FIX-BINDING):
gremlin.binding_edit removes a binding or changes a Map to vJoy's target
on the open profile, for a device that isn't plugged in, marks the profile
changed and announces it; undo puts the profile back exactly."""

from __future__ import annotations

import sys
import uuid
from collections.abc import Iterator

sys.path.append(".")

import pytest

from gremlin import binding_edit, search_index, shared_state
from gremlin.modules import output
from gremlin.profile import DeviceInfo
from gremlin.types import InputType

B = InputType.JoystickButton
A = InputType.JoystickAxis
# Not connected: the tests have no devices.
_STICK = uuid.UUID("{7E1D2C3B-0000-11EB-8003-444553540000}")


@pytest.fixture(autouse=True)
def _outputs_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(output, "cant_send_text", lambda *a, **k: None)
    monkeypatch.setattr(output, "xbox_cant_send_text", lambda *a, **k: None)
    monkeypatch.setattr(output, "osc_cant_send_text", lambda *a, **k: None)


def _vjoy(vjoy_id: int, control: int) -> object:
    from action_plugins.map_to_vjoy import MapToVjoyData

    action = MapToVjoyData(B)
    action.vjoy_device_id = vjoy_id
    action.vjoy_input_type = B
    action.vjoy_input_id = control
    return action


def _bind(
    profile: object, input_id: int, *actions: object, mode: str = "Default"
) -> None:
    from action_plugins.root import RootData
    from gremlin.profile import InputItemBinding

    item = profile.get_input_item(_STICK, B, input_id, mode, True)  # type: ignore[attr-defined]
    root = RootData(B)
    root.children = list(actions)
    binding = InputItemBinding(item)
    binding.root_action = root
    binding.behavior = B
    item.action_sequences.append(binding)
    for each in (root, *actions):
        profile.library.add_action(each)  # type: ignore[attr-defined]


@pytest.fixture
def profile(monkeypatch: pytest.MonkeyPatch) -> Iterator[object]:
    """Button 1 sends vJoy 1 Button 5 then vJoy 1 Button 6; Button 2 sends
    vJoy 3 Button 1 (no such vJoy); Button 3 sends vJoy 1 Button 7."""
    from gremlin.profile import Profile

    p = Profile()
    monkeypatch.setattr(shared_state, "current_profile", p)
    _bind(p, 1, _vjoy(1, 5), _vjoy(1, 6))
    _bind(p, 2, _vjoy(3, 1))
    _bind(p, 3, _vjoy(1, 7))
    p.device_database.devices[_STICK] = DeviceInfo(_STICK, "HID Remapper 2DGG")
    p.mark_clean()
    yield p
    monkeypatch.setattr(shared_state, "current_profile", None)


@pytest.fixture
def notices() -> Iterator[list[int]]:
    from gremlin.signal import signal

    seen: list[int] = []

    def note() -> None:
        seen.append(1)

    signal.actionsChanged.connect(note)
    yield seen
    signal.actionsChanged.disconnect(note)


def _rows(p: object) -> list[search_index.SearchRow]:
    return search_index.profile_rows(p, "open", "test", "", lambda g, n: False)


def _row(p: object, input_id: int, vjoy: int, control: int) -> search_index.SearchRow:
    want = (("vjoy", vjoy, B.value, control),)
    return next(r for r in _rows(p) if r.input_id == input_id and r.target_keys == want)


def test_describe_names_the_unplugged_device(profile: object) -> None:
    row = _row(profile, 2, 3, 1)
    assert row.plugged is False
    assert binding_edit.describe(row) == (
        "the Map to vJoy binding from Button 2 of HID Remapper 2DGG (Default mode)"
    )


def test_device_name_falls_back_to_the_stored_name_then_the_id(profile: object) -> None:
    assert binding_edit.device_name(_STICK) == "HID Remapper 2DGG"
    assert binding_edit.device_name(str(_STICK)) == "HID Remapper 2DGG"
    other = uuid.UUID("{11111111-2222-3333-4444-555555555555}")
    assert binding_edit.device_name(other) == str(other)


def test_remove_one_action_and_undo_round_trips(
    profile: object, notices: list[int]
) -> None:
    before = profile._xml_text()  # type: ignore[attr-defined]
    row = _row(profile, 1, 1, 6)
    first = _row(profile, 1, 1, 5)
    record = binding_edit.remove_binding(row)
    assert record.kind == "remove-action"
    keys = [r.target_keys for r in _rows(profile) if r.input_id == 1]
    assert keys == [first.target_keys]
    assert profile.has_unsaved_changes()  # type: ignore[attr-defined]
    assert notices
    removed_id = record.action.id
    binding_edit.undo(record)
    assert profile._xml_text() == before  # type: ignore[attr-defined]
    assert not profile.has_unsaved_changes()  # type: ignore[attr-defined]
    again = [r for r in _rows(profile) if r.input_id == 1]
    assert [r.target_keys for r in again] == [first.target_keys, row.target_keys]
    assert profile.library.has_action(removed_id)  # type: ignore[attr-defined]
    with pytest.raises(binding_edit.EditError):
        binding_edit.undo(record)


def test_remove_only_action_removes_the_binding_and_undo_restores(
    profile: object,
) -> None:
    before = profile._xml_text()  # type: ignore[attr-defined]
    row = _row(profile, 2, 3, 1)
    record = binding_edit.remove_binding(row)
    assert record.kind == "remove-binding"
    assert not [r for r in _rows(profile) if r.input_id == 2]
    assert profile.has_unsaved_changes()  # type: ignore[attr-defined]
    binding_edit.undo(record)
    assert profile._xml_text() == before  # type: ignore[attr-defined]
    item = profile.get_input_item(_STICK, B, 2, "Default", False)  # type: ignore[attr-defined]
    assert item.action_sequences[0] is record.binding


def test_change_target_and_undo(profile: object, notices: list[int]) -> None:
    before = profile._xml_text()  # type: ignore[attr-defined]
    row = _row(profile, 2, 3, 1)
    record = binding_edit.change_vjoy_target(row, 1, "axis", 2)
    action = record.action
    assert (action.vjoy_device_id, action.vjoy_input_type, action.vjoy_input_id) == (
        1,
        A,
        2,
    )
    assert [r.target_keys for r in _rows(profile) if r.input_id == 2] == [
        (("vjoy", 1, A.value, 2),)
    ]
    assert profile.has_unsaved_changes()  # type: ignore[attr-defined]
    assert notices
    binding_edit.undo(record)
    assert profile._xml_text() == before  # type: ignore[attr-defined]
    assert not profile.has_unsaved_changes()  # type: ignore[attr-defined]


def test_change_target_refuses_other_kinds(profile: object) -> None:
    row = _row(profile, 2, 3, 1)
    with pytest.raises(binding_edit.EditError):
        binding_edit.change_vjoy_target(row, 1, "key", 2)


def test_a_gone_binding_says_so(profile: object) -> None:
    row = _row(profile, 3, 1, 7)
    binding_edit.remove_binding(row)
    with pytest.raises(binding_edit.EditError, match="no longer in the profile"):
        binding_edit.remove_binding(row)


def test_running_profile_refuses_edits(
    profile: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin.ui import binding_catalog

    monkeypatch.setattr(binding_catalog, "editing_locked", lambda: True)
    before = profile._xml_text()  # type: ignore[attr-defined]
    with pytest.raises(binding_edit.EditError, match="running"):
        binding_edit.remove_binding(_row(profile, 2, 3, 1))
    assert profile._xml_text() == before  # type: ignore[attr-defined]
