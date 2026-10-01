# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest import mock

import pytest

import dill
from gremlin.common import InputType
from gremlin.logical_device import LogicalDevice
from gremlin.ui import xbox_device_model
from vigem.xbox import XboxTarget


@pytest.fixture(autouse=True)
def reset_logical() -> None:
    LogicalDevice().reset()
    yield
    LogicalDevice().reset()


def _incoming(device_id: uuid.UUID, item: SimpleNamespace) -> str:
    target = list(XboxTarget)[0]
    profile = SimpleNamespace(inputs={device_id: [item]})
    maps = [(1, target.value)]
    with (
        mock.patch.object(xbox_device_model.shared_state, "current_profile", profile),
        mock.patch.object(xbox_device_model, "xbox_maps_for_item", return_value=maps),
    ):
        return xbox_device_model._incoming_for(1, target)


def test_logical_device_input_shows_its_names() -> None:
    # Used to read "f0af472f-... JoystickButton 1".
    logical = LogicalDevice()
    logical.create(InputType.JoystickButton, user_label="This is a test :)")
    item = SimpleNamespace(input_type=InputType.JoystickButton, input_id=1)

    text = _incoming(dill.UUID_LogicalDevice, item)

    assert text == "Logical Device · Button 1 — This is a test :)"
    assert str(dill.UUID_LogicalDevice) not in text
    assert "JoystickButton" not in text


def test_unnamed_logical_input_shows_the_system_name() -> None:
    LogicalDevice().create(InputType.JoystickHat)
    item = SimpleNamespace(input_type=InputType.JoystickHat, input_id=1)
    assert _incoming(dill.UUID_LogicalDevice, item) == "Logical Device · Hat 1"


def test_hardware_input_uses_the_device_name() -> None:
    guid = uuid.uuid4()
    item = SimpleNamespace(input_type=InputType.JoystickAxis, input_id=3)
    with mock.patch.object(xbox_device_model, "device_label", return_value="Stick"):
        assert _incoming(guid, item) == "Stick · Axis 3"
