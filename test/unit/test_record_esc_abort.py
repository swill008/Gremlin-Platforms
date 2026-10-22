# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Holding Esc to stop "Listen for input" keeps what was recorded before.

Page 02: Esc held 1 s ends listening with no inputs (`_abort_listening`
emits an empty list). Every recorder fed by it must treat that as "cancel":
Map to Mouse and Script crashed with IndexError; Map to Keyboard, Macro
steps and Conditions wiped what was set.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any, cast

import pytest
from PySide6 import QtCore

from gremlin import keyboard
from gremlin.types import InputType, MouseButton

_KEEP: list[object] = []


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    yield app


class _Binding(QtCore.QObject):
    behaviorChanged = QtCore.Signal()


def _esc_held(slot: Any) -> None:  # noqa: ANN401
    """Starts the real listener feeding `slot`, then aborts it as Esc does."""
    from gremlin.ui.util import InputListenerModel

    listener = InputListenerModel()
    _KEEP.append(listener)
    listener.listeningTerminated.connect(slot)
    listener._abort_listening()


def _action(model_cls: Any, data: Any) -> Any:  # noqa: ANN401
    binding = _Binding()
    _KEEP.append(binding)
    model = model_cls(data, cast(Any, binding), cast(Any, None),
                      cast(Any, None), cast(Any, None))
    _KEEP.append(model)
    return model


def test_map_to_mouse_keeps_button_on_esc() -> None:
    from action_plugins.map_to_mouse import MapToMouseData, MapToMouseModel

    data = MapToMouseData(InputType.JoystickButton)
    data.button = MouseButton.Right
    _esc_held(_action(MapToMouseModel, data).updateInputs)
    assert data.button == MouseButton.Right


def test_map_to_keyboard_keeps_keys_on_esc() -> None:
    from action_plugins.map_to_keyboard import MapToKeyboardData, MapToKeyboardModel

    data = MapToKeyboardData(InputType.JoystickButton)
    keys = [keyboard.key_from_name("leftshift"), keyboard.key_from_name("a")]
    data.keys = list(keys)
    _esc_held(_action(MapToKeyboardModel, data).updateInputs)
    assert data.keys == keys


def test_script_keyboard_keeps_key_on_esc() -> None:
    from gremlin.ui.script import KeyboardVariableModel

    key = keyboard.key_from_name("a")
    variable = SimpleNamespace(value=key)
    model = KeyboardVariableModel(cast(Any, variable))
    _KEEP.append(model)
    _esc_held(model.updateKeyboard)
    assert variable.value == key


def test_script_joystick_keeps_input_on_esc() -> None:
    from gremlin.ui.script import PhysicalInputVariableModel

    chosen = (uuid.uuid4(), InputType.JoystickButton, 3)
    variable = SimpleNamespace(value=chosen)
    model = PhysicalInputVariableModel(cast(Any, variable))
    _KEEP.append(model)
    _esc_held(model.updateJoystick)
    assert variable.value == chosen


def test_macro_joystick_step_keeps_input_on_esc() -> None:
    from action_plugins.macro import JoystickActionModel
    from gremlin.macro import JoystickAction

    guid = uuid.uuid4()
    action = JoystickAction(guid, InputType.JoystickButton, 7, True)
    model = JoystickActionModel(action)
    _KEEP.append(model)
    _esc_held(model.updateJoystick)
    assert (action.device_guid, action.input_type, action.input_id) == (
        guid, InputType.JoystickButton, 7
    )
    assert action.value is True


def test_macro_key_step_keeps_key_on_esc() -> None:
    from action_plugins.macro import KeyActionModel
    from gremlin.macro import KeyAction

    key = keyboard.key_from_name("a")
    action = KeyAction(key, True)
    model = KeyActionModel(action)
    _KEEP.append(model)
    _esc_held(model.updateKey)
    assert action.key == key


def test_macro_mouse_step_keeps_button_on_esc() -> None:
    from action_plugins.macro import MouseButtonActionModel
    from gremlin.macro import MouseButtonAction

    action = MouseButtonAction(MouseButton.Middle, True)
    model = MouseButtonActionModel(action)
    _KEEP.append(model)
    _esc_held(model.updateButton)
    assert action.button == MouseButton.Middle


def _event(kind: InputType, identifier: Any, guid: uuid.UUID) -> Any:  # noqa: ANN401
    from gremlin import event_handler

    return event_handler.Event(kind, identifier, guid, "Default", is_pressed=True)


def test_joystick_condition_keeps_input_on_esc() -> None:
    from action_plugins.condition import condition as cond_mod

    cond = cond_mod.JoystickCondition()
    _KEEP.append(cond)
    guid = uuid.uuid4()
    cond.updateFromUserInput([_event(InputType.JoystickButton, 4, guid)])
    states, comparator = list(cond._states), cond._comparator
    assert comparator is not None
    _esc_held(cond.updateFromUserInput)
    assert cond._states == states
    assert cond._comparator is comparator


def test_keyboard_condition_keeps_keys_on_esc() -> None:
    import dill
    from action_plugins.condition import condition as cond_mod

    cond = cond_mod.KeyboardCondition()
    _KEEP.append(cond)
    key = keyboard.key_from_name("a")
    code = (key.scan_code, key.is_extended)
    cond.updateFromUserInput([_event(InputType.Keyboard, code, dill.UUID_Keyboard)])
    states, comparator = list(cond._states), cond._comparator
    assert comparator is not None
    _esc_held(cond.updateFromUserInput)
    assert cond._states == states
    assert cond._comparator is comparator
