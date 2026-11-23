# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Test script: an R13-style user plugin after the three documented edits.

Written for this suite in the style of Joystick Gremlin R13 user plugins
(button to vJoy button, one decorator made per mode). Upstream's R13 to
R14 notes list the three edits applied here:
  1. `from gremlin.user_script import *` instead of `gremlin.user_plugin`;
  2. every variable takes is_optional as its third argument;
  3. the vJoy output is written with vjoy[var.vjoy_id].button(var.input_id)
     (R13 read var.value["device_id"] / ["input_id"]).
"""

# ruff: noqa: F403, F405
from gremlin.user_script import *

mode = ModeVariable("Mode", "Mode in which to use these settings", True)

physical = PhysicalInputVariable(
    "Physical button", "Button to watch", False, [InputType.JoystickButton]
)
virtual = VirtualInputVariable(
    "Virtual button", "vJoy button to press", True, [InputType.JoystickButton]
)

decorator = physical.create_decorator(mode.value)


@decorator.button(physical.input_id)
def forward(event: object, vjoy: object) -> None:
    vjoy[virtual.vjoy_id].button(virtual.input_id).is_pressed = event.is_pressed
