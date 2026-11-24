# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Test script: a stick button presses vJoy 1 button 1.

The button is required: until it is set, the script is not configured and
Run skips it. The callback uses the "vjoy" object the program gives it, so
the write goes through the vJoy output module (only claimed outputs pass).
"""

from gremlin import types, user_script

mode = user_script.ModeVariable("Mode", "The mode the button works in", True)

button = user_script.PhysicalInputVariable(
    "Button",
    "The stick button to watch",
    is_optional=False,
    valid_types=[types.InputType.JoystickButton],
)

# Every press and release seen, for tests.
presses: list[bool] = []


@button.decorator(mode)
def on_button(event: types.Event, vjoy: object) -> None:
    """Pressed or released: vJoy 1 button 1 follows."""
    presses.append(bool(event.is_pressed))
    vjoy[1].button(1).is_pressed = event.is_pressed
