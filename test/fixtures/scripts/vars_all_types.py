# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Test script: one variable of each of the 11 variable types.

Every variable is optional, so the script counts as configured as soon as
it is added. It registers no callbacks; it only shows that each variable
type appears on the Scripts window with its default and its limits.
"""

from gremlin import types, user_script

flag = user_script.BoolVariable(
    "Flag", "A bool, on by default", is_optional=True, initial_value=True
)

gain = user_script.FloatVariable(
    "Gain",
    "A float from -2.0 to 2.0, 0.5 by default",
    is_optional=True,
    initial_value=0.5,
    min_value=-2.0,
    max_value=2.0,
)

count = user_script.IntegerVariable(
    "Count",
    "An integer from 0 to 10, 3 by default",
    is_optional=True,
    initial_value=3,
    min_value=0,
    max_value=10,
)

hotkey = user_script.KeyboardVariable("Hotkey", "A key, none by default", True)

logical = user_script.LogicalDeviceVariable(
    "Logical button",
    "A Logical Device button",
    is_optional=True,
    valid_types=[types.InputType.JoystickButton],
)

osc_in = user_script.OscInputVariable(
    "OSC input", "An OSC input, none chosen by default", is_optional=True
)

active_mode = user_script.ModeVariable(
    "Active mode", "A mode, the profile's first mode by default", True
)

choice = user_script.SelectionVariable(
    "Choice",
    "One of three options, the second by default",
    is_optional=True,
    option_list=["Low", "Medium", "High"],
    default_index=1,
)

label = user_script.StringVariable(
    "Label", "A text, 'hello' by default", is_optional=True, initial_value="hello"
)

stick_axis = user_script.PhysicalInputVariable(
    "Stick axis",
    "A physical axis, none by default",
    is_optional=True,
    valid_types=[types.InputType.JoystickAxis],
)

vjoy_hat = user_script.VirtualInputVariable(
    "vJoy hat",
    "A vJoy hat, vJoy 1 hat 1 by default",
    is_optional=True,
    valid_types=[types.InputType.JoystickHat],
)
