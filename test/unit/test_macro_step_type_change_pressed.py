# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""An existing macro step whose input or type is changed to a button starts
on Pressed, like a new one (05 S116, widened 2026-11-23, D-05-UPSTREAM-B2;
upstream 07eae856)."""

from __future__ import annotations

import sys
import uuid
from collections.abc import Iterator

sys.path.append(".")

import pytest
from PySide6 import QtCore

from gremlin.logical_device import LogicalDevice
from gremlin.types import Event, InputType
from gremlin.ui.device import InputIdentifier

A = InputType.JoystickAxis
B = InputType.JoystickButton
_KEEP: list[object] = []


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    yield QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])


def test_joystick_step_changed_to_a_button_is_pressed() -> None:
    from action_plugins.macro import JoystickActionModel
    from gremlin.macro import JoystickAction

    action = JoystickAction(uuid.uuid4(), A, 1, 0.5)
    model = JoystickActionModel(action)
    _KEEP.append(model)
    model.updateJoystick([Event(B, 4, uuid.uuid4(), "Default", is_pressed=True)])
    assert action.input_type == B
    assert action.value is True


def test_vjoy_step_changed_from_axis_to_button_is_pressed() -> None:
    from action_plugins.macro import VJoyActionModel
    from gremlin.macro import VJoyAction

    action = VJoyAction(1, A, 1, 0.0)
    model = VJoyActionModel(action)
    _KEEP.append(model)
    model._set_input_type(InputType.to_string(B))
    assert action.input_type == B
    assert action.value is True


def test_logical_device_step_changed_to_a_button_is_pressed() -> None:
    from action_plugins.macro import LogicalDeviceActionModel
    from gremlin.macro import LogicalDeviceAction

    logical = LogicalDevice()
    logical.reset()
    try:
        axis = logical.create(A, label="Axis")
        button = logical.create(B, label="Button")
        action = LogicalDeviceAction(A, axis.id, 0.0)
        model = LogicalDeviceActionModel(action)
        _KEEP.append(model)
        model.logicalInputIdentifier = InputIdentifier(
            LogicalDevice.device_guid, B, button.id
        )
        assert action.input_type == B
        assert action.value is True
    finally:
        logical.reset()
