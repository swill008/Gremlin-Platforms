# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Test script: an ON/OFF/ON switch as three vJoy buttons.

The switch is two stick buttons ("Up" and "Down"; neither pressed is the
middle). vJoy 1 buttons 1, 2 and 3 show up, middle and down: exactly one
is pressed. The script sets the start state from the switch when its
top-level code runs. That code runs when the script is added or loaded
(vJoy writes are refused then: no Run) and again at each Run, where the
start state is sent. Written for this suite.
"""

from gremlin import types, user_script

mode = user_script.ModeVariable("Mode", "The mode the switch works in", True)

up = user_script.PhysicalInputVariable(
    "Up", "Stick button for up", False, [types.InputType.JoystickButton]
)
down = user_script.PhysicalInputVariable(
    "Down", "Stick button for down", False, [types.InputType.JoystickButton]
)

_joy = user_script.JoystickPlugin.joystick
_vjoy = user_script.VJoyPlugin.vjoy


def _show(is_up: bool, is_down: bool) -> None:
    """Exactly one of vJoy 1 buttons 1 (up), 2 (middle), 3 (down) pressed."""
    _vjoy[1].button(1).is_pressed = is_up
    _vjoy[1].button(2).is_pressed = not is_up and not is_down
    _vjoy[1].button(3).is_pressed = is_down


def _read(var: user_script.PhysicalInputVariable) -> bool:
    if not var.is_valid():
        return False
    return _joy[var.device_guid].button(var.input_id).is_pressed


# The start state, from the switch as it is now.
_show(_read(up), _read(down))


@up.decorator(mode)
def on_up(event: types.Event) -> None:
    _show(bool(event.is_pressed), _read(down))


@down.decorator(mode)
def on_down(event: types.Event) -> None:
    _show(_read(up), bool(event.is_pressed))
