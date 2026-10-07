# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Input state as the input modules pass it.

Actions and scripts that read the current value of some other input (Merge
Axis, Dual Axis Deadzone, the Condition action, the script "joy" and
"keyboard" objects) read it here. An input its input module does not claim
reads as neutral: axis centred, button released, hat centred, key up. An
unplugged stick's axes read centred too (its buttons and hats were let go).
"""

from __future__ import annotations

from typing import Any

import dill
from gremlin import device_initialization, input_cache, keyboard
from gremlin.types import HatDirection, InputType


def _allows(device_guid: object, input_type: InputType, identifier: object) -> bool:
    from gremlin.modules.runtime import InputModuleRuntime

    return InputModuleRuntime().allows(device_guid, input_type, identifier)


def _unplugged(device_guid: object) -> bool:
    """A stick read before that is not in the device list now. Its cache
    keeps the last values (02 S28); only a stick the cache holds can be one
    (the logical device never is)."""
    if not isinstance(
        input_cache.Joystick.devices.get(device_guid), input_cache.JoystickWrapper
    ):
        return False
    return all(
        dev.device_guid.uuid != device_guid
        for dev in device_initialization.joystick_devices()
    )


def axis_value(device_guid: Any, axis_id: int) -> float:  # noqa: ANN401
    """An unplugged stick's axis reads centred (05 S105, D-05-UNPLUG-CENTRE)."""
    if not _allows(device_guid, InputType.JoystickAxis, axis_id):
        return 0.0
    if _unplugged(device_guid):
        return 0.0
    return float(input_cache.Joystick()[device_guid].axis(axis_id).value)


def button_pressed(device_guid: Any, button_id: int) -> bool:  # noqa: ANN401
    if not _allows(device_guid, InputType.JoystickButton, button_id):
        return False
    return bool(input_cache.Joystick()[device_guid].button(button_id).is_pressed)


def hat_direction(device_guid: Any, hat_id: int) -> HatDirection:  # noqa: ANN401
    if not _allows(device_guid, InputType.JoystickHat, hat_id):
        return HatDirection.Center
    return input_cache.Joystick()[device_guid].hat(hat_id).direction


def key_pressed(key: keyboard.Key | str) -> bool:
    if isinstance(key, str):
        key = keyboard.key_from_name(key)
    ident = (key.scan_code, key.is_extended)
    if not _allows(dill.UUID_Keyboard, InputType.Keyboard, ident):
        return False
    return bool(input_cache.Keyboard().is_pressed(key))


# --- what user scripts get ---------------------------------------------------


class _ScriptAxis:
    def __init__(self, device_guid: Any, axis_id: int) -> None:  # noqa: ANN401
        self._guid, self._id = device_guid, axis_id

    @property
    def value(self) -> float:
        return axis_value(self._guid, self._id)


class _ScriptButton:
    def __init__(self, device_guid: Any, button_id: int) -> None:  # noqa: ANN401
        self._guid, self._id = device_guid, button_id

    @property
    def is_pressed(self) -> bool:
        return button_pressed(self._guid, self._id)


class _ScriptHat:
    def __init__(self, device_guid: Any, hat_id: int) -> None:  # noqa: ANN401
        self._guid, self._id = device_guid, hat_id

    @property
    def direction(self) -> HatDirection:
        return hat_direction(self._guid, self._id)


class _ScriptDevice:
    """One device as a script sees it: claimed inputs only. Anything else
    (axis_count, name, ...) comes from the device unchanged."""

    def __init__(self, device_guid: Any) -> None:  # noqa: ANN401
        self._guid = device_guid
        self._device = input_cache.Joystick()[device_guid]

    def axis(self, index: int) -> _ScriptAxis:
        return _ScriptAxis(self._guid, int(index))

    def button(self, index: int) -> _ScriptButton:
        return _ScriptButton(self._guid, int(index))

    def hat(self, index: int) -> _ScriptHat:
        return _ScriptHat(self._guid, int(index))

    def __getattr__(self, name: str) -> Any:  # noqa: ANN401
        return getattr(self._device, name)


class ScriptJoystick:
    """The "joy" object user scripts get: joy[guid].button(3).is_pressed."""

    def __getitem__(self, device_guid: Any) -> _ScriptDevice:  # noqa: ANN401
        return _ScriptDevice(device_guid)


class ScriptKeyboard:
    """The "keyboard" object user scripts get: keyboard.is_pressed("a")."""

    def is_pressed(self, key: keyboard.Key | str) -> bool:
        return key_pressed(key)
