# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Actions and scripts read other inputs through the input modules: an
unclaimed input reads as neutral."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest

from gremlin import keyboard
from gremlin.modules import inputs
from gremlin.types import HatDirection, InputType

_ROOT = Path(__file__).resolve().parents[2]
_STICK = uuid.UUID("87fdb100-a8f5-11f1-8003-444553540000")


class _FakeDevice:
    def axis(self, index: int) -> SimpleNamespace:
        return SimpleNamespace(value=0.75)

    def button(self, index: int) -> SimpleNamespace:
        return SimpleNamespace(is_pressed=True)

    def hat(self, index: int) -> SimpleNamespace:
        return SimpleNamespace(direction=HatDirection.North)

    axis_count = 3


@pytest.fixture
def stick() -> Iterator[list[tuple]]:
    """Axis 1, button 1, hat 1 and key "a" are claimed; nothing else."""
    asked: list[tuple] = []

    def allows(guid: object, input_type: InputType, ident: object) -> bool:
        asked.append((input_type, ident))
        if input_type == InputType.Keyboard:
            return ident == (keyboard.key_from_name("a").scan_code, False)
        return ident == 1

    with (
        mock.patch.object(inputs, "_allows", side_effect=allows),
        mock.patch.object(
            inputs.input_cache.Joystick, "__getitem__", return_value=_FakeDevice()
        ),
        mock.patch.object(
            inputs.input_cache.Keyboard(), "is_pressed", return_value=True
        ),
    ):
        yield asked


def test_claimed_inputs_read_their_value(stick: list[tuple]) -> None:
    assert inputs.axis_value(_STICK, 1) == 0.75
    assert inputs.button_pressed(_STICK, 1) is True
    assert inputs.hat_direction(_STICK, 1) == HatDirection.North
    assert inputs.key_pressed("a") is True


def test_unclaimed_inputs_read_neutral(stick: list[tuple]) -> None:
    assert inputs.axis_value(_STICK, 2) == 0.0
    assert inputs.button_pressed(_STICK, 57) is False
    assert inputs.hat_direction(_STICK, 2) == HatDirection.Center
    assert inputs.key_pressed("b") is False


def test_scripts_get_the_claim_aware_objects(stick: list[tuple]) -> None:
    from gremlin.user_script import JoystickPlugin, KeyboardPlugin

    joy = JoystickPlugin.joystick
    assert isinstance(joy, inputs.ScriptJoystick)
    assert joy[_STICK].button(57).is_pressed is False
    assert joy[_STICK].axis(1).value == 0.75
    assert joy[_STICK].axis_count == 3  # other attributes pass through
    assert isinstance(KeyboardPlugin.keyboard, inputs.ScriptKeyboard)
    assert KeyboardPlugin.keyboard.is_pressed("b") is False


def test_actions_read_other_inputs_through_the_input_modules() -> None:
    for rel in (
        "action_plugins/merge_axis/__init__.py",
        "action_plugins/dual_axis_deadzone/__init__.py",
        "action_plugins/condition/condition.py",
        "gremlin/user_script.py",
    ):
        text = (_ROOT / rel).read_text(encoding="utf-8")
        # No value is read from the raw input cache any more.
        for raw_read in (
            "].axis(",
            "joystick.axis(",
            "joystick.button(",
            "joystick.hat(",
            "keyboard.is_pressed(self",
            " Keyboard()",
        ):
            assert raw_read not in text, (rel, raw_read)
