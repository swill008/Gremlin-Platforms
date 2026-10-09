# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The macro step and script variable editors point a Logical Device
reference at the chosen control's permanent id, so deleting it and creating
another under the same number never re-targets the reference (D-04-LD-FILE;
06 S78)."""

from __future__ import annotations

import sys
from collections.abc import Iterator
from unittest import mock

sys.path.append(".")

import pytest
from PySide6 import QtCore

from gremlin.logical_device import LogicalDevice
from gremlin.types import InputType
from gremlin.ui.device import InputIdentifier

B = InputType.JoystickButton
_APP = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])


@pytest.fixture(autouse=True)
def reset_logical() -> Iterator[None]:
    LogicalDevice().reset()
    yield
    LogicalDevice().reset()


def _pick(number: int) -> InputIdentifier:
    return InputIdentifier(LogicalDevice.device_guid, B, number)


def _step_model() -> tuple[object, object]:
    from action_plugins.macro import LogicalDeviceActionModel
    from gremlin import macro

    action = macro.LogicalDeviceAction(B, None, False)
    return action, LogicalDeviceActionModel(action)


def _variable_model() -> tuple[object, object]:
    from gremlin import user_script
    from gremlin.ui.script import LogicalDeviceModel

    with mock.patch.object(user_script, "_current_script_id", return_value=None):
        variable = user_script.LogicalDeviceVariable("v", "", False, [B])
    return variable, LogicalDeviceModel(variable)


@pytest.mark.parametrize("make", [_step_model, _variable_model])
def test_choosing_a_control_stores_its_uid(make) -> None:  # noqa: ANN001
    logical = LogicalDevice()
    logical.create(B, label="First")
    second = logical.create(B, label="Second")
    data, model = make()
    model.logicalInputIdentifier = _pick(second.id)
    assert data.uid == second.uid
    shown = model.logicalInputIdentifier
    assert (shown.input_type, shown.input_id) == (B, second.id)


@pytest.mark.parametrize("make", [_step_model, _variable_model])
def test_delete_and_recreate_under_the_same_number_does_not_retarget(
    make,  # noqa: ANN001
) -> None:
    logical = LogicalDevice()
    old = logical.create(B, label="Fire")
    data, model = make()
    model.logicalInputIdentifier = _pick(old.id)
    old_uid, number = old.uid, old.id

    logical.delete(old.identifier)
    new = logical.create(B, label="Other")
    assert new.id == number and new.uid != old_uid

    # Still the deleted control: missing, never the new one by number.
    assert data.uid == old_uid
    assert data.is_missing()

    # Choosing the new control on purpose repoints it.
    model.logicalInputIdentifier = _pick(new.id)
    assert data.uid == new.uid
    assert not data.is_missing()
