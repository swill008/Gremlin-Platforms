# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""A Condition's check on an unplugged stick counts as false; OSC checks are
not affected; the editor shows the profile's stored name (05 S146, S105,
upstream c479d342)."""

from __future__ import annotations

import uuid

import pytest

import dill
from action_plugins.condition import ConditionData, ConditionFunctor
from action_plugins.condition.comparator import PressedComparator
from action_plugins.condition.condition import JoystickCondition
from gremlin import device_initialization
from gremlin.base_classes import Value
from gremlin.modules import ids, inputs
from gremlin.types import Event, InputType

_STICK = uuid.UUID("5e1f0c2a-0b0b-4c4c-9d9d-111122223333")
_OTHER = uuid.UUID("5e1f0c2a-0b0b-4c4c-9d9d-444455556666")


class _Recorder:
    def __init__(self) -> None:
        self.values: list = []
        self.functors: dict = {}

    def __call__(self, event: Event, value: Value, properties: list = []) -> None:
        self.values.append(value.current)

    def reset(self) -> None:
        pass


def _released_check(device: uuid.UUID) -> JoystickCondition:
    """A Joystick condition: <device> Button 1 is Released."""
    cond = JoystickCondition()
    state = JoystickCondition.State(device, InputType.JoystickButton, 1)
    state.joystick = object()  # seen since start (the cache holds it)
    cond._states = [state]
    cond._comparator = PressedComparator(is_pressed=False)
    return cond


@pytest.fixture
def plugged(monkeypatch: pytest.MonkeyPatch) -> set[uuid.UUID]:
    """The devices the driver lists now; the check reads Button 1 released."""
    present = {_STICK, _OTHER}
    monkeypatch.setattr(
        dill.DILL,
        "device_exists",
        staticmethod(lambda guid: guid.uuid in present),
    )
    monkeypatch.setattr(inputs, "button_pressed", lambda guid, ident: False)
    return present


def test_released_check_true_while_plugged_in(plugged: set[uuid.UUID]) -> None:
    assert _released_check(_STICK)(Value(True)) is True


def test_released_check_false_once_unplugged(plugged: set[uuid.UUID]) -> None:
    plugged.discard(_STICK)
    assert _released_check(_STICK)(Value(True)) is False


def test_never_seen_stick_counts_as_false(plugged: set[uuid.UUID]) -> None:
    # Old code: the missing stick raised, so neither list ran.
    plugged.discard(_STICK)
    cond = _released_check(_STICK)
    cond._states[0].joystick = None
    assert cond(Value(True)) is False


def test_osc_check_not_affected(
    plugged: set[uuid.UUID], monkeypatch: pytest.MonkeyPatch
) -> None:
    # OSC has no driver device; its check must not read as unplugged.
    monkeypatch.setattr(dill.DILL, "device_exists", staticmethod(lambda guid: False))
    cond = JoystickCondition()
    state = JoystickCondition.State(ids.OSC, InputType.JoystickButton, 1)
    state.joystick = object()
    state._refresh_osc = lambda: True  # type: ignore[method-assign]
    cond._states = [state]
    cond._comparator = PressedComparator(is_pressed=False)
    assert cond(Value(True)) is True


def test_unplug_then_press_runs_false_list(plugged: set[uuid.UUID]) -> None:
    """End to end through the functor: a press on another device after the
    stick is unplugged runs the False list; nothing ran at the unplug."""
    data = ConditionData(InputType.JoystickButton)
    data.conditions = [_released_check(_STICK)]
    functor = ConditionFunctor(data)
    true_list, false_list = _Recorder(), _Recorder()
    functor.functors["true"] = [true_list]
    functor.functors["false"] = [false_list]

    def tap() -> None:
        for pressed in (True, False):
            event = Event(
                InputType.JoystickButton, 2, _OTHER, "Default", is_pressed=pressed
            )
            functor(event, Value(pressed))

    tap()
    assert true_list.values == [True, False] and false_list.values == []

    plugged.discard(_STICK)
    assert true_list.values == [True, False] and false_list.values == []
    tap()
    assert false_list.values == [True, False]
    assert true_list.values == [True, False]


def test_shown_name_falls_back_to_stored_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(device_initialization, "device_name", lambda uid: "")
    monkeypatch.setattr(
        device_initialization,
        "_profile_names",
        lambda: {str(_STICK).upper(): "Stored Stick"},
    )
    assert device_initialization.shown_name(_STICK) == "Stored Stick"
    assert device_initialization.shown_name(_OTHER) == ""


def test_editor_label_shows_stored_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(device_initialization, "device_name", lambda uid: "")
    monkeypatch.setattr(
        device_initialization,
        "_profile_names",
        lambda: {str(_STICK).upper(): "Stored Stick"},
    )
    state = JoystickCondition.State(_STICK, InputType.JoystickButton, 1)
    state.joystick = None
    assert state.display_name().startswith("Stored Stick - ")
    other = JoystickCondition.State(_OTHER, InputType.JoystickButton, 1)
    other.joystick = None
    assert other.display_name().startswith("Unknown Joystick - ")


def test_editor_names_follow_device_names_notice() -> None:
    from gremlin.signal import signal

    cond = JoystickCondition()
    seen: list = []
    cond.statesChanged.connect(lambda states: seen.append(states))
    signal.deviceNamesChanged.emit()
    assert seen
