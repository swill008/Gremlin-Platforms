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
    from gremlin.modules.claim import claim_ids

    assert claim_ids({"buttons": [3, 1, 1, "2"]}, "button") == [1, 2, 3]
    assert claim_ids({"axes": []}, "axis") == []
    assert claim_ids({"hats": ["nope"]}, "hat") == []


def test_named_vjoy_cannot_be_a_source_module() -> None:
    from gremlin.modules.registry import module_direction

    assert module_direction({"direction": "source"}, name="vJoy 1") == "dest"
    source = {"direction": "source"}
    assert module_direction(source, name="VKBsim Gladiator EVO R") == "source"


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


def test_hide_system_name_shows_only_the_typed_name() -> None:
    logical = LogicalDevice()
    item = logical.create(InputType.JoystickButton)
    logical.set_user_label(item.identifier, "Trigger")
    item.hide_system = True
    assert item.row_title == "Trigger"
    logical.set_user_label(item.identifier, "")
    assert item.hide_system is False
    assert item.row_title == "Button 1"


def test_hide_system_name_is_saved(tmp_path) -> None:
    profile = Profile()
    logical = LogicalDevice()
    item = logical.create(InputType.JoystickButton)
    logical.set_user_label(item.identifier, "Trigger")
    item.hide_system = True
    path = tmp_path / "hide.xml"
    profile.to_xml(path)
    LogicalDevice().reset()
    Profile().from_xml(path)
    restored = LogicalDevice().button(1)
    assert restored.second_name == "Trigger"
    assert restored.hide_system is True
    assert restored.row_title == "Trigger"


def _button_one(profile: Profile):
    logical = LogicalDevice()
    logical.create(InputType.JoystickButton)
    return logical, lambda: profile.get_input_item(
        logical.device_guid, InputType.JoystickButton, 1, "Default",
        create_if_missing=False,
    )


def test_add_action_then_cancel_writes_nothing(qapp) -> None:
    from gremlin import shared_state
    from gremlin.ui.logical_layout import LogicalLayoutModel

    profile = Profile()
    shared_state.current_profile = profile
    try:
        _logical, real = _button_one(profile)
        model = LogicalLayoutModel()
        model.beginNewAction("parent:button:1")
        model._pane_shadow.add_item_binding()
        assert model.paneDirty()
        model.discardPane()
        model.endPane()
        item = real()
        assert item is None or item.action_sequences == []
        model.deleteLater()
    finally:
        shared_state.current_profile = None


def test_new_action_is_appended_on_ok_and_undoable(qapp) -> None:
    from gremlin import shared_state
    from gremlin.ui.logical_layout import LogicalLayoutModel

    profile = Profile()
    shared_state.current_profile = profile
    try:
        _logical, real = _button_one(profile)
        existing = profile.get_input_item(
            LogicalDevice().device_guid, InputType.JoystickButton, 1, "Default",
            create_if_missing=True,
        ).add_item_binding()
        model = LogicalLayoutModel()
        model.beginNewAction("parent:button:1")
        # The new action edits one blank sequence, not the existing one.
        assert len(model._pane_shadow.action_sequences) == 1
        model._pane_shadow.add_item_binding()
        # OK tells the cards' Driven by to check again.
        from gremlin.signal import signal

        told = []

        def tell() -> None:
            told.append(1)

        signal.actionsChanged.connect(tell)
        try:
            index = model.commitPane()
        finally:
            signal.actionsChanged.disconnect(tell)
        assert told == [1]
        assert index == 1
        assert len(real().action_sequences) == 2
        assert real().action_sequences[0] is existing
        model.endPane()
        model.undo()
        assert real().action_sequences == [existing]
        model.redo()
        assert len(real().action_sequences) == 2
        model.deleteLater()
    finally:
        shared_state.current_profile = None


def test_delete_one_action_and_undo_puts_it_back(qapp) -> None:
    from gremlin import shared_state
    from gremlin.ui.logical_layout import LogicalLayoutModel

    profile = Profile()
    shared_state.current_profile = profile
    try:
        _logical, real = _button_one(profile)
        item = profile.get_input_item(
            LogicalDevice().device_guid, InputType.JoystickButton, 1, "Default",
            create_if_missing=True,
        )
        first = item.add_item_binding()
        second = item.add_item_binding()
        third = item.add_item_binding()
        model = LogicalLayoutModel()
        assert model.deleteAction("parent:button:1", 1)
        assert real().action_sequences == [first, third]
        model.undo()
        assert real().action_sequences == [first, second, third]
        model.redo()
        assert real().action_sequences == [first, third]
        assert not model.deleteAction("parent:button:1", 5)
        model.deleteLater()
    finally:
        shared_state.current_profile = None


def test_typed_group_name_joins_the_existing_group() -> None:
    logical = LogicalDevice()
    logical.ensure_group("Device 2")
    assert logical.ensure_group("device 2") == "Device 2"
    assert logical.ensure_group("  Device   2 ") == "Device 2"
    assert logical.group_names() == ["Device 2"]
    made = logical.create_many(InputType.JoystickButton, 1, "DEVICE 2")
    assert made[0].group == "Device 2"
    logical.place(made[0].identifier, "device 2")
    assert made[0].group == "Device 2"
    assert logical.ensure_group("Device 3") == "Device 3"
    assert logical.group_names() == ["Device 2", "Device 3"]
    assert logical.ensure_group("   ") == ""


def test_rename_refuses_a_look_alike_but_allows_recasing_itself() -> None:
    logical = LogicalDevice()
    logical.ensure_group("Device 2")
    logical.ensure_group("Device 3")
    for look_alike in ("device 2", "Device 2 ", "DEVICE  2"):
        with pytest.raises(GremlinError):
            logical.rename_group("Device 3", look_alike)
    logical.rename_group("Device 3", "device 3")
    assert logical.group_names() == ["Device 2", "device 3"]

def test_delete_removes_every_selected_row_in_one_undo_step(qapp) -> None:
    from gremlin import shared_state
    from gremlin.ui.logical_layout import LogicalLayoutModel

    profile = Profile()
    shared_state.current_profile = profile
    try:
        logical = LogicalDevice()
        for _ in range(3):
            logical.create(InputType.JoystickButton)
        model = LogicalLayoutModel()
        model.deleteParents(["parent:button:1", "parent:button:3"])
        left = [i.id for i in logical.inputs_of_type([InputType.JoystickButton])]
        assert left == [2]
        model.undo()
        left = [i.id for i in logical.inputs_of_type([InputType.JoystickButton])]
        assert left == [1, 2, 3]
        model.deleteLater()
    finally:
        shared_state.current_profile = None
