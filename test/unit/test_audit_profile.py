# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Profile fixes from the code audit (AU-01, 02, 14, 18, 19, 20)."""

from __future__ import annotations

import sys
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

sys.path.append(".")

import pytest

from gremlin import error, plugin_manager, shared_state
from gremlin.profile import Profile
from gremlin.types import InputType

_STICK = uuid.UUID("55555555-6666-7777-8888-999999999999")


@pytest.fixture
def profile() -> Iterator[Profile]:
    p = Profile()
    shared_state.current_profile = p
    yield p
    shared_state.current_profile = None


def _create(name: str) -> Any:  # noqa: ANN401
    return plugin_manager.PluginManager().create_instance(
        name, InputType.JoystickButton
    )


def _vjoy(out: int) -> Any:  # noqa: ANN401
    action = _create("Map to vJoy")
    action.vjoy_device_id = 1
    action.vjoy_input_id = out
    action.vjoy_input_type = InputType.JoystickButton
    return action


def test_deleting_a_mode_keeps_every_child(profile: Profile) -> None:
    modes = profile.modes
    modes.add_mode("Parent")
    for child in ("A", "B", "C", "D"):
        modes.add_mode(child)
        modes.set_parent(child, "Parent")
    modes.delete_mode("Parent")
    assert modes.mode_names() == ["A", "B", "C", "D", "Default"]


def test_the_last_mode_stays(profile: Profile) -> None:
    with pytest.raises(error.GremlinError):
        profile.modes.delete_mode("Default")
    assert profile.modes.mode_names() == ["Default"]


def test_renaming_a_mode_updates_change_mode(profile: Profile) -> None:
    profile.modes.add_mode("Combat")
    item = profile.get_input_item(
        _STICK, InputType.JoystickButton, 1, "Default", create_if_missing=True
    )
    change = _create("Change Mode")
    change.target_modes = ["Combat"]
    item.add_item_binding().root_action.insert_action(change, "children")
    profile.modes.rename_mode("Combat", "Fight")
    assert change.target_modes == ["Fight"]


def test_snapshot_puts_back_an_unfinished_action(profile: Profile) -> None:
    item = profile.get_input_item(
        _STICK, InputType.JoystickButton, 1, "Default", create_if_missing=True
    )
    root = item.add_item_binding().root_action
    root.insert_action(_vjoy(3), "children")
    root.insert_action(_create("Play Sound"), "children")  # no file chosen yet
    snapshot = profile.input_snapshot(item)
    profile.put_input(_STICK, InputType.JoystickButton, 1, "Default", snapshot)
    back = profile.get_input_item(_STICK, InputType.JoystickButton, 1, "Default")
    assert back is not None
    tags = [a.tag for a in back.action_sequences[0].root_action.get_actions()[0]]
    assert tags == ["map-to-vjoy", "play-sound"]


def test_a_snapshot_that_cannot_be_read_changes_nothing(profile: Profile) -> None:
    item = profile.get_input_item(
        _STICK, InputType.JoystickButton, 1, "Default", create_if_missing=True
    )
    item.add_item_binding().root_action.insert_action(_vjoy(3), "children")
    broken = {"input": profile.input_snapshot(item)["input"], "actions": []}
    with pytest.raises(error.ProfileError):
        profile.put_input(_STICK, InputType.JoystickButton, 1, "Default", broken)
    still = profile.get_input_item(_STICK, InputType.JoystickButton, 1, "Default")
    assert still is item and len(still.action_sequences) == 1


def test_a_missing_load_profile_file_still_loads(
    profile: Profile, tmp_path: Path
) -> None:
    target = tmp_path / "other.xml"
    target.write_text("<profile/>")
    item = profile.get_input_item(
        _STICK, InputType.JoystickButton, 1, "Default", create_if_missing=True
    )
    action = _create("Load Profile")
    action.profile_filename = str(target)
    item.add_item_binding().root_action.insert_action(action, "children")
    path = tmp_path / "p.xml"
    profile.to_xml(path)
    target.unlink()
    loaded = Profile()
    loaded.from_xml(str(path))
    back = loaded.get_input_item(_STICK, InputType.JoystickButton, 1, "Default")
    kept = back.action_sequences[0].root_action.get_actions()[0][0]
    assert kept.profile_filename == str(target)
    # A warning, not an error: saving keeps it.
    assert kept.is_valid()


def test_a_mode_with_an_unknown_parent_is_kept(profile: Profile) -> None:
    root = ElementTree.fromstring(
        '<profile><modes><mode>Default</mode><mode parent="Gone">Child</mode>'
        "</modes></profile>"
    )
    profile.modes.from_xml(root)
    assert profile.modes.mode_names() == ["Child", "Default"]


def test_hat_buttons_with_a_bad_count_says_so(profile: Profile) -> None:
    from action_plugins.hat_buttons import HatButtonsData

    node = ElementTree.fromstring(
        f'<action id="{uuid.uuid4()}" type="hat-buttons"><property type="int">'
        "<name>button-count</name><value>3</value></property></action>"
    )
    with pytest.raises(error.ProfileError, match="must be 4 or 8"):
        HatButtonsData()._from_xml(node, profile.library)
