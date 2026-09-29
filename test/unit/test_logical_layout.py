# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import sys

sys.path.append(".")

import pytest

from gremlin.common import InputType
from gremlin.error import GremlinError
from gremlin.logical_device import LogicalDevice
from gremlin.profile import Profile


@pytest.fixture(autouse=True)
def reset_logical() -> None:
    LogicalDevice().reset()


def test_system_name_stays_when_the_user_renames() -> None:
    logical = LogicalDevice()
    made = logical.create_many(InputType.JoystickButton, 2, "Device 2", "")
    assert made[0].system_name == "Button 1"
    assert made[1].system_name == "Button 2"
    assert made[0].group == "Device 2"
    logical.set_user_label(made[0].identifier, "Trigger")
    assert made[0].system_name == "Button 1"
    assert made[0].second_name == "Trigger"
    assert made[0].row_title.startswith("Button 1")
    logical.set_user_label(made[0].identifier, "Button 1")
    assert made[0].second_name == ""
    assert made[0].label == "Button 1"


def test_groups_and_order() -> None:
    logical = LogicalDevice()
    logical.create_many(InputType.JoystickButton, 3, "Device 2")
    logical.create_many(InputType.JoystickAxis, 1, "Device 2")
    logical.ensure_group("Device 3")
    first = logical.button(1)
    logical.place(first.identifier, "Device 3")
    assert first.group == "Device 3"
    logical.sort_within("system")
    ordered = [item.id for item in logical.ordered() if item.type == InputType.JoystickButton and item.group == "Device 2"]
    assert ordered == [2, 3]
    logical.sort_groups()
    assert logical.group_names() == ["Device 2", "Device 3"]
    logical.delete_group("Device 2")
    assert logical.button(2).group == ""
    assert "Device 2" not in logical.group_names()
    assert logical.button(1).group == "Device 3"


def test_delete_group_keeps_the_parents() -> None:
    logical = LogicalDevice()
    logical.create_many(InputType.JoystickHat, 2, "Hats")
    logical.delete_group("Hats")
    assert logical.hat_count == 2
    assert logical.hat(1).group == ""


def test_rename_group_rejects_a_duplicate() -> None:
    logical = LogicalDevice()
    logical.ensure_group("Device 2")
    logical.ensure_group("Device 3")
    with pytest.raises(GremlinError):
        logical.rename_group("Device 2", "Device 3")


def test_memento_roundtrip() -> None:
    logical = LogicalDevice()
    logical.create_many(InputType.JoystickButton, 2, "Device 2", "Stick")
    memo = logical.memento()
    logical.delete(logical.button(1).identifier)
    logical.restore(memo)
    assert logical.button(1).group == "Device 2"
    assert logical.button(1).second_name == "Stick"
    assert logical.button(1).system_name == "Button 1"


def test_profile_saves_group_name_and_user_name(tmp_path) -> None:
    profile = Profile()
    logical = LogicalDevice()
    logical.ensure_group("Device 3")
    logical.create_many(InputType.JoystickButton, 1, "Device 2", "Trigger")
    path = tmp_path / "logical.xml"
    profile.to_xml(path)
    again = Profile()
    again.from_xml(path)
    restored = LogicalDevice()
    assert restored.group_names() == ["Device 3", "Device 2"]
    button = restored.button(1)
    assert button.system_name == "Button 1"
    assert button.second_name == "Trigger"
    assert button.group == "Device 2"
    assert button.label == "Button 1"


def test_two_rows_can_share_a_user_name() -> None:
    logical = LogicalDevice()
    made = logical.create_many(InputType.JoystickButton, 2)
    logical.set_user_label(made[0].identifier, "Fire")
    logical.set_user_label(made[1].identifier, "Fire")
    assert made[0].second_name == "Fire"
    assert made[1].second_name == "Fire"
    assert made[0].system_name == "Button 1"
    assert made[1].system_name == "Button 2"


def test_create_one_starts_ungrouped() -> None:
    logical = LogicalDevice()
    item = logical.create(InputType.JoystickAxis)
    assert item.group == ""
    assert item.second_name == ""
    assert item.system_name == "Axis 1"


def test_move_group_up_and_down() -> None:
    logical = LogicalDevice()
    logical.ensure_group("A")
    logical.ensure_group("B")
    logical.ensure_group("C")
    logical.move_group_before("C", "A")
    assert logical.group_names() == ["C", "A", "B"]
    logical.move_group_before("C", None)
    assert logical.group_names() == ["A", "B", "C"]
    logical.move_group_before("B", "A")
    assert logical.group_names() == ["B", "A", "C"]


def test_old_profile_label_becomes_user_name(tmp_path) -> None:
    profile = Profile()
    logical = LogicalDevice()
    logical.create(InputType.JoystickButton, 1, "Trigger")
    path = tmp_path / "old.xml"
    profile.to_xml(path)
    LogicalDevice().reset()
    again = Profile()
    again.from_xml(path)
    restored = LogicalDevice()
    button = restored.button(1)
    assert button.system_name == "Button 1"
    assert button.second_name == "Trigger"
    assert button.group == ""


def test_claimed_ids_are_sorted_and_unique() -> None:
    from gremlin.ui.logical_layout import _claimed_ids

    assert _claimed_ids({"buttons": [3, 1, 1, "2"]}, "button") == [1, 2, 3]
    assert _claimed_ids({"axes": []}, "axis") == []
    assert _claimed_ids({"hats": ["nope"]}, "hat") == []


def test_named_vjoy_cannot_be_a_source_module() -> None:
    from gremlin.ui.logical_layout import _module_direction

    assert _module_direction({"direction": "source"}, "vJoy 1") == "dest"
    assert _module_direction({"direction": "source"}, "VKBsim Gladiator EVO R") == "source"


def test_ok_on_one_sequence_keeps_the_pane_on_that_sequence(qapp) -> None:
    from gremlin import shared_state
    from gremlin.ui.logical_layout import LogicalLayoutModel

    profile = Profile()
    shared_state.current_profile = profile
    try:
        logical = LogicalDevice()
        logical.create(InputType.JoystickButton)
        real = profile.get_input_item(
            logical.device_guid,
            InputType.JoystickButton,
            1,
            "Default",
            create_if_missing=True,
        )
        real.add_item_binding()
        real.add_item_binding()
        model = LogicalLayoutModel()
        model.beginPane("parent:button:1", 0)
        assert len(model._pane_shadow.action_sequences) == 1
        model._pane_shadow.add_item_binding()
        assert model.paneDirty()
        model.commitPane()
        assert len(real.action_sequences) == 2
        assert len(model._pane_shadow.action_sequences) == 1
        assert model._pane_whole is False
        model.deleteLater()
    finally:
        shared_state.current_profile = None


def test_group_as_moves_every_selected_row(qapp) -> None:
    from gremlin import shared_state
    from gremlin.ui.logical_layout import LogicalLayoutModel

    profile = Profile()
    shared_state.current_profile = profile
    try:
        logical = LogicalDevice()
        logical.create(InputType.JoystickButton)
        logical.create(InputType.JoystickButton)
        model = LogicalLayoutModel()
        model.setSelection(["parent:button:1", "parent:button:2"])
        model.moveSelected("Stick")
        assert logical.button(1).group == "Stick"
        assert logical.button(2).group == "Stick"
        assert logical.group_names() == ["Stick"]
        model.deleteLater()
    finally:
        shared_state.current_profile = None


def test_drag_places_a_button_before_after_and_into_a_group(qapp) -> None:
    from gremlin import shared_state
    from gremlin.ui.logical_layout import LogicalLayoutModel

    profile = Profile()
    shared_state.current_profile = profile
    try:
        logical = LogicalDevice()
        logical.create(InputType.JoystickButton)
        logical.create(InputType.JoystickButton)
        logical.create(InputType.JoystickButton)
        model = LogicalLayoutModel()
        model.moveParent("parent:button:2", "group:Stick", "into")
        model.moveParent("parent:button:3", "group:Stick", "into")
        model.moveParent("parent:button:1", "parent:button:3", "before")
        assert logical.button(1).group == "Stick"
        order = [item.id for item in logical.ordered() if item.group == "Stick"]
        assert order == [2, 1, 3]
        model.moveParent("parent:button:1", "parent:button:3", "after")
        order = [item.id for item in logical.ordered() if item.group == "Stick"]
        assert order == [2, 3, 1]
        model.deleteLater()
    finally:
        shared_state.current_profile = None
