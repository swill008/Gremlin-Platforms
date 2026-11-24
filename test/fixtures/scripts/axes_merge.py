# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Test script: two stick axes merged into one vJoy axis.

The vJoy axis gets the sum of both axes, held to -1.0..1.0 (for example a
throttle plus a fine-trim axis). Written for this suite; the idea is a
common one in published scripts.
"""

from gremlin import types, user_script

mode = user_script.ModeVariable("Mode", "The mode the axes work in", True)

axis_a = user_script.PhysicalInputVariable(
    "Axis A", "First stick axis", False, [types.InputType.JoystickAxis]
)
axis_b = user_script.PhysicalInputVariable(
    "Axis B", "Second stick axis", False, [types.InputType.JoystickAxis]
)
merged = user_script.VirtualInputVariable(
    "Merged axis", "vJoy axis that gets A + B", True, [types.InputType.JoystickAxis]
)

# The last value of each axis.
values = {"a": 0.0, "b": 0.0}


def _write() -> None:
    merged.remap(user_script.clamp_value(values["a"] + values["b"], -1.0, 1.0))


@axis_a.decorator(mode)
def on_a(event: types.Event) -> None:
    values["a"] = event.value
    _write()


@axis_b.decorator(mode)
def on_b(event: types.Event) -> None:
    values["b"] = event.value
    _write()
