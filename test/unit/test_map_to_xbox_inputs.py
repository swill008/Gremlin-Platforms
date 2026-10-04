# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Map to Xbox with each kind of input.

Before: a button or key on a trigger rested at 50% (False read as the axis
middle), a hat on a stick raised an error on every event, and every target
was offered for every input.
"""

from __future__ import annotations

import sys

sys.path.append(".")

from types import SimpleNamespace
from unittest import mock

import pytest

from action_plugins.map_to_xbox import (
    TRIGGER_FULL,
    TRIGGER_UPPER,
    MapToXboxData,
    MapToXboxFunctor,
    MapToXboxModel,
    _stick_value,
    _trigger_value,
    targets_for,
)
from gremlin.types import HatDirection, InputType
from vigem.xbox import XboxTarget


def _byte(axis: float) -> int:
    """What the pad's trigger byte becomes for this axis value (XboxPad.apply)."""
    return round((axis + 1.0) * 0.5 * 255)


@pytest.mark.parametrize("trigger_range", [TRIGGER_FULL, TRIGGER_UPPER])
def test_button_on_a_trigger_is_full_or_nothing(trigger_range: str) -> None:
    assert _byte(_trigger_value(True, trigger_range)) == 255
    assert _byte(_trigger_value(False, trigger_range)) == 0  # was 128 (50%)


def test_an_axis_on_a_trigger_is_unchanged() -> None:
    assert _trigger_value(0.25, TRIGGER_FULL) == 0.25
    assert _trigger_value(0.5, TRIGGER_UPPER) == 0.0
    assert _trigger_value(-0.5, TRIGGER_UPPER) == -1.0


@pytest.mark.parametrize(
    ("hat", "target", "expected"),
    [
        (HatDirection.North, XboxTarget.LEFT_STICK_Y, 1.0),
        (HatDirection.South, XboxTarget.RIGHT_STICK_Y, -1.0),
        (HatDirection.West, XboxTarget.LEFT_STICK_X, -1.0),
        (HatDirection.East, XboxTarget.RIGHT_STICK_X, 1.0),
        (HatDirection.North, XboxTarget.LEFT_STICK_X, 0.0),
        (HatDirection.Center, XboxTarget.LEFT_STICK_Y, 0.0),
    ],
)
def test_a_hat_moves_a_stick(
    hat: HatDirection, target: XboxTarget, expected: float
) -> None:
    assert _stick_value(hat, target) == expected


def test_hat_on_a_stick_writes_without_error() -> None:
    action = MapToXboxData(InputType.JoystickHat)
    action.xbox_target = XboxTarget.LEFT_STICK_Y
    functor = MapToXboxFunctor(action)
    value = SimpleNamespace(current=HatDirection.North)
    with (
        mock.patch.object(functor, "_should_execute", return_value=True),
        mock.patch("action_plugins.map_to_xbox.output.write_xbox") as write,
        mock.patch("action_plugins.map_to_xbox._LOG.error") as logged,
    ):
        functor(mock.Mock(), value)
    write.assert_called_once_with(1, XboxTarget.LEFT_STICK_Y, 1.0)
    logged.assert_not_called()  # was: "Map to Xbox failed" on every event


def test_targets_offered_for_each_input() -> None:
    def kinds(behavior: InputType) -> set[str]:
        return {t.kind for t in targets_for(behavior)}

    assert kinds(InputType.JoystickAxis) == {"stick", "trigger"}
    assert kinds(InputType.JoystickButton) == {"button", "trigger"}
    assert kinds(InputType.Keyboard) == {"button", "trigger"}
    assert kinds(InputType.JoystickHat) == {"hat", "button", "stick"}


def test_a_saved_target_outside_the_list_stays_listed() -> None:
    action = MapToXboxData(InputType.JoystickButton)
    action.xbox_target = XboxTarget.LEFT_STICK_X  # saved before the list
    choices = MapToXboxModel._get_target_choices(SimpleNamespace(_data=action))
    values = [c["value"] for c in choices]
    assert XboxTarget.LEFT_STICK_X.value in values
    assert XboxTarget.A.value in values
    assert XboxTarget.RIGHT_STICK_Y.value not in values
