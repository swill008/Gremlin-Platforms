# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Unused actions don't reach the profile file (G-LIBLEAK).

Some edits dropped an input's link to its actions but kept the actions, and
saving wrote every action: a user's profile held 1,172 actions, 408 of them
used. Now the file gets only what an input uses (deleted and replaced ones
stay in memory, so Undo still works), the leaks are closed where no Undo
needs the actions (Auto Mapper Overwrite, Delete Mode, Keyboard, OSC,
Configuration Delete, the live editor's Remove), and remove_unused keeps an
action another input still uses.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from pathlib import Path
from unittest import mock
from xml.etree import ElementTree

import pytest

from gremlin import auto_mapper, plugin_manager, shared_state
from gremlin.auto_mapper import AutoMapper, AutoMapperOptions
from gremlin.profile import Profile
from gremlin.types import InputType

_STICK = uuid.UUID("22222222-3333-4444-5555-666666666666")


@pytest.fixture
def profile() -> Iterator[Profile]:
    made = Profile()
    shared_state.current_profile = made
    yield made
    shared_state.current_profile = None


def _map(profile: Profile, button: int, mode: str = "Default") -> object:
    action = plugin_manager.PluginManager().create_instance(
        "Map to vJoy", InputType.JoystickButton
    )
    action.vjoy_device_id = 1
    action.vjoy_input_id = button
    action.vjoy_input_type = InputType.JoystickButton
    item = profile.get_input_item(
        _STICK, InputType.JoystickButton, button, mode, create_if_missing=True
    )
    item.add_item_binding().root_action.insert_action(action, "children")
    return action


def _in_file(path: Path) -> set[str]:
    root = ElementTree.parse(path).getroot()
    return {node.get("id") for node in root.findall("./library/action")}


def test_the_file_gets_only_what_inputs_use(profile: Profile, tmp_path: Path) -> None:
    _map(profile, 1)
    item = profile.get_input_item(_STICK, InputType.JoystickButton, 2, "Default", True)
    _map(profile, 2)
    dropped = item.action_sequences[0]
    # Unlinked but kept, as a Logical Device Delete keeps it for Undo.
    item.remove_item_binding(dropped)
    path = tmp_path / "p.xml"
    profile.to_xml(path)
    assert _in_file(path) == {str(a) for a in profile.actions_in_use()}
    assert dropped.root_action.id in profile.library._actions


def test_undo_after_a_save_keeps_the_action(profile: Profile, tmp_path: Path) -> None:
    _map(profile, 1)
    item = profile.get_input_item(_STICK, InputType.JoystickButton, 1, "Default")
    binding = item.action_sequences[0]
    item.remove_item_binding(binding)
    profile.to_xml(tmp_path / "p.xml")
    # Undo puts the binding back; the next save writes its actions again.
    item.action_sequences.append(binding)
    profile.to_xml(tmp_path / "p.xml")
    again = Profile()
    again.from_xml(tmp_path / "p.xml")
    restored = again.get_input_item(_STICK, InputType.JoystickButton, 1, "Default")
    assert restored is not None and len(restored.action_sequences) == 1
    shared_state.current_profile = profile


def test_an_open_draft_is_not_unsaved_work(profile: Profile, tmp_path: Path) -> None:
    _map(profile, 1)
    profile.to_xml(tmp_path / "p.xml")
    # A draft action, in the library but on no input (an editor pane is open).
    plugin_manager.PluginManager().create_instance(
        "Map to vJoy", InputType.JoystickButton
    )
    assert not profile.has_unsaved_changes()


def test_a_shared_action_stays_while_an_input_uses_it(profile: Profile) -> None:
    shared = _map(profile, 1)
    other = profile.get_input_item(_STICK, InputType.JoystickButton, 2, "Default", True)
    other.add_item_binding().root_action.insert_action(shared, "children")
    first = profile.get_input_item(_STICK, InputType.JoystickButton, 1, "Default")
    root = first.action_sequences[0].root_action
    first.action_sequences.clear()
    profile.library.remove_unused(root)
    assert root.id not in profile.library._actions
    assert shared.id in profile.library._actions


def test_delete_mode_takes_the_actions_with_it(profile: Profile) -> None:
    profile.modes.add_mode("Combat")
    _map(profile, 1)
    _map(profile, 2, "Combat")
    profile.modes.delete_mode("Combat")
    assert set(profile.library._actions) == profile.actions_in_use()


def test_drop_inputs_takes_their_actions(profile: Profile) -> None:
    _map(profile, 1)
    _map(profile, 2)
    item = profile.get_input_item(_STICK, InputType.JoystickButton, 2, "Default")
    profile.drop_inputs(_STICK, [item])
    assert [i.input_id for i in profile.inputs[_STICK]] == [1]
    assert set(profile.library._actions) == profile.actions_in_use()


def test_auto_mapper_overwrite_leaves_nothing_behind(profile: Profile) -> None:
    source = {"slug": "nxt", "name": "NXT", "claim": {"buttons": [1, 2]}}
    dest = {
        "slug": "vjoy_1",
        "name": "vJoy 1",
        "vjoyId": 1,
        "claim": {"buttons": [1, 2]},
    }
    limits = {"axes": set(), "buttons": {1, 2}, "hats": set()}
    with (
        mock.patch.object(auto_mapper.auto_map, "input_modules", return_value=[source]),
        mock.patch.object(auto_mapper.auto_map, "output_modules", return_value=[dest]),
        mock.patch.object(AutoMapper, "_vjoy_limits", return_value=limits),
        mock.patch.object(AutoMapper, "_get_used_vjoy_inputs", return_value=[]),
        mock.patch.object(AutoMapper, "_source_uuid", return_value=_STICK),
    ):
        options = AutoMapperOptions(overwrite_used_inputs=True)
        AutoMapper(profile).generate_module_mappings(["nxt"], ["vjoy_1"], options)
        AutoMapper(profile).generate_module_mappings(["nxt"], ["vjoy_1"], options)
    assert len(profile.actions_in_use()) == 4  # two inputs: a root and a map each
    assert set(profile.library._actions) == profile.actions_in_use()
