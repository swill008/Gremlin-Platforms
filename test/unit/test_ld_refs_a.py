# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Map to Logical Device and the Logical Device condition point at the
control's permanent id, not its number (decision D-04-LD-FILE; 06 S78)."""

from __future__ import annotations

import sys
import uuid
from unittest import mock

sys.path.append(".")

import pytest

from gremlin import util
from gremlin.base_classes import Value
from gremlin.event_handler import Event
from gremlin.logical_device import LogicalDevice
from gremlin.types import InputType, PropertyType

B = InputType.JoystickButton
_GUID = uuid.UUID(int=7)


@pytest.fixture(autouse=True)
def reset_logical() -> None:
    LogicalDevice().reset()


def _press(data: object) -> None:
    from action_plugins.map_to_logical_device import MapToLogicalDeviceFunctor

    functor = MapToLogicalDeviceFunctor(data)  # type: ignore[arg-type]
    functor._event_listener = mock.MagicMock()
    with mock.patch(
        "action_plugins.map_to_logical_device.mode_manager.ModeManager"
    ):
        functor(Event(B, 1, _GUID, "Default", is_pressed=True), Value(True))


def _reload(data: object) -> object:
    from action_plugins.map_to_logical_device import MapToLogicalDeviceData

    node = data.to_xml()  # type: ignore[attr-defined]
    fresh = MapToLogicalDeviceData(B)
    fresh.from_xml(node, mock.MagicMock())
    return fresh


def test_a_deleted_control_s_number_reused_is_not_driven_by_the_old_action() -> None:
    from action_plugins.map_to_logical_device import MapToLogicalDeviceData

    logical = LogicalDevice()
    old = logical.create(B, label="Fire")
    data = MapToLogicalDeviceData(B)
    assert data.logical_input_id == old.id
    node = data.to_xml()

    logical.delete(old.identifier)
    new = logical.create(B, label="Brake")
    assert new.id == old.id  # the number is reused

    loaded = MapToLogicalDeviceData(B)
    loaded.from_xml(node, mock.MagicMock())
    _press(loaded)
    # It used to press "Brake" (same number).
    assert logical[new.identifier].is_pressed is False


def test_the_action_follows_its_control_when_the_number_changes() -> None:
    from action_plugins.map_to_logical_device import MapToLogicalDeviceData

    logical = LogicalDevice()
    fire = logical.create(B, label="Fire")
    data = MapToLogicalDeviceData(B)
    node = data.to_xml()
    uid = util.read_property(node, "logical-input-uid", PropertyType.String)
    assert uid == fire.uid

    # Same uid, now under number 4: the reference follows it.
    logical.delete(fire.identifier)
    other = logical.create(B, label="Other")
    moved = logical.create(B, input_id=4, label="Fire", uid=uid)
    loaded = MapToLogicalDeviceData(B)
    loaded.from_xml(node, mock.MagicMock())
    assert loaded.logical_input_id == 4
    assert loaded.logical_missing is False
    _press(loaded)
    assert logical[moved.identifier].is_pressed is True
    assert logical[other.identifier].is_pressed is False


def test_a_missing_uid_is_kept_flagged_and_does_nothing() -> None:
    from action_plugins.map_to_logical_device import MapToLogicalDeviceData

    logical = LogicalDevice()
    logical.create(B, label="Fire")
    data = MapToLogicalDeviceData(B)
    node = data.to_xml()
    logical.reset()
    logical.create(B, label="Brake")

    loaded = MapToLogicalDeviceData(B)
    loaded.from_xml(node, mock.MagicMock())
    assert loaded.logical_missing is True
    _press(loaded)  # no error, nothing pressed
    assert logical.button(1).is_pressed is False
    # Saved again with the same uid, not re-targeted.
    again = loaded.to_xml()
    assert util.read_property(
        again, "logical-input-uid", PropertyType.String
    ) == util.read_property(node, "logical-input-uid", PropertyType.String)


def test_old_data_without_a_uid_resolves_by_remap_then_number() -> None:
    from action_plugins.map_to_logical_device import MapToLogicalDeviceData

    logical = LogicalDevice()
    first = logical.create(B, label="One")
    second = logical.create(B, label="Two")
    data = MapToLogicalDeviceData(B)
    data.logical_input_id = first.id
    node = data.to_xml()
    for prop in node.findall("./property"):
        if prop.findtext("name") == "logical-input-uid":
            node.remove(prop)

    loaded = MapToLogicalDeviceData(B)
    loaded.from_xml(node, mock.MagicMock())
    assert loaded.logical_input_uid == first.uid  # by number

    import gremlin.logical_device_file as ldf

    with mock.patch.object(
        ldf,
        "current_uid_map",
        {(InputType.to_string(B), first.id): second.uid},
        create=True,
    ):
        remapped = MapToLogicalDeviceData(B)
        remapped.from_xml(node, mock.MagicMock())
    assert remapped.logical_input_uid == second.uid
    assert remapped.logical_input_id == second.id


def test_the_editor_choice_writes_the_chosen_control_s_uid() -> None:
    from action_plugins.map_to_logical_device import MapToLogicalDeviceData

    logical = LogicalDevice()
    logical.create(B, label="One")
    two = logical.create(B, label="Two")
    data = MapToLogicalDeviceData(B)
    data.logical_input_id = two.id
    assert data.logical_input_uid == two.uid
    assert _reload(data).logical_input_uid == two.uid  # type: ignore[attr-defined]


def test_condition_on_a_deleted_control_whose_number_is_reused_is_false() -> None:
    from action_plugins.condition import condition as ca

    logical = LogicalDevice()
    old = logical.create(B, label="Fire")
    cond = ca.LogicalDeviceCondition()
    # Asks "released" (new conditions ask Pressed, 05 S116).
    cond._comparator.is_pressed = False
    node = cond.to_xml()
    assert util.read_property(node, "uid", PropertyType.String) == old.uid

    logical.delete(old.identifier)
    logical.create(B, label="Brake")

    loaded = ca.LogicalDeviceCondition()
    loaded.from_xml(node)
    # It asks for "released": it used to read "Brake" (same number), true.
    assert loaded(Value(True)) is False
    assert loaded._states[0].display_name() == "(missing)"
    again = loaded.to_xml()
    assert util.read_property(again, "uid", PropertyType.String) == old.uid


def test_condition_follows_its_control_by_uid() -> None:
    from action_plugins.condition import condition as ca

    logical = LogicalDevice()
    fire = logical.create(B, label="Fire")
    cond = ca.LogicalDeviceCondition()
    # Asks "released" (new conditions ask Pressed, 05 S116).
    cond._comparator.is_pressed = False
    node = cond.to_xml()
    logical.delete(fire.identifier)
    logical.create(B, label="Other")
    logical.create(B, input_id=5, label="Fire", uid=fire.uid)

    loaded = ca.LogicalDeviceCondition()
    loaded.from_xml(node)
    assert loaded._states[0].input_id == 5
    assert loaded(Value(True)) is True
