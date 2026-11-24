# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Test script: an OSC button input presses a vJoy button.

The OSC input is chosen by its address on the Scripts window (a new OSC
input variable starts with none chosen, so the script is not configured
until one is picked). The vJoy button is written through remap.
"""

from gremlin import types, user_script

mode = user_script.ModeVariable("Mode", "The mode the OSC input works in", True)

osc_button = user_script.OscInputVariable(
    "OSC button",
    "The OSC button input to watch",
    is_optional=False,
    valid_types=[types.InputType.JoystickButton],
)

vjoy_button = user_script.VirtualInputVariable(
    "vJoy button",
    "The vJoy button to press (vJoy 1 button 1 by default)",
    is_optional=True,
    valid_types=[types.InputType.JoystickButton],
)

# Every press and release seen, for tests.
presses: list[bool] = []


@osc_button.decorator(mode)
def on_osc(event: types.Event) -> None:
    """The OSC input pressed or released: the vJoy button follows."""
    presses.append(bool(event.is_pressed))
    vjoy_button.remap(event.is_pressed)
