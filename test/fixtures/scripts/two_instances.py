# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Test script: meant to be added twice ("Instance 1" and "Instance 2").

Each instance has its own settings: its own stick button and its own vJoy
button number. Pressing an instance's stick button presses its vJoy button
on vJoy 1 (and only that one).
"""

from gremlin import event_handler, types, user_script

mode = user_script.ModeVariable("Mode", "The mode the button works in", True)

button = user_script.PhysicalInputVariable(
    "Button",
    "The stick button to watch",
    is_optional=False,
    valid_types=[types.InputType.JoystickButton],
)

vjoy_button = user_script.IntegerVariable(
    "vJoy button",
    "The vJoy 1 button this instance presses",
    is_optional=True,
    initial_value=1,
    min_value=1,
    max_value=32,
)


@button.decorator(mode)
def on_button(event: event_handler.Event, vjoy: object) -> None:
    """This instance's vJoy button follows its stick button."""
    vjoy[1].button(vjoy_button.value).is_pressed = event.is_pressed
