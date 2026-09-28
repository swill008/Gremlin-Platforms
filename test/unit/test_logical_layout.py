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
