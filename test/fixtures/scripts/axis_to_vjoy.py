# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Test script: a stick axis drives a vJoy axis, scaled.

The output axis value is the input value times Scale (0.5 by default,
limited to 0.0 to 2.0). The stick axis is required. The output is written
through VirtualInputVariable.remap, which goes through the output module.
"""

from gremlin import event_handler, types, user_script

mode = user_script.ModeVariable("Mode", "The mode the axis works in", True)

stick_axis = user_script.PhysicalInputVariable(
    "Stick axis",
    "The stick axis to read",
    is_optional=False,
    valid_types=[types.InputType.JoystickAxis],
)

vjoy_axis = user_script.VirtualInputVariable(
    "vJoy axis",
    "The vJoy axis to write (vJoy 1 axis 1 by default)",
    is_optional=True,
    valid_types=[types.InputType.JoystickAxis],
)

scale = user_script.FloatVariable(
    "Scale",
    "Output = input x Scale",
    is_optional=True,
    initial_value=0.5,
    min_value=0.0,
    max_value=2.0,
)


@stick_axis.decorator(mode)
def on_axis(event: event_handler.Event) -> None:
    """Writes the scaled axis value to the vJoy axis."""
    vjoy_axis.remap(event.value * scale.value)
