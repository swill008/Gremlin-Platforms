# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Test script: a stick button changes the mode.

Pressing the button (in the mode "Works in") switches to the mode
"Switch to", through user_script.switch_mode (04 S99).
"""

from gremlin import types, user_script

works_in = user_script.ModeVariable("Works in", "Mode the button works in", True)
target = user_script.ModeVariable("Switch to", "Mode to switch to", False)

button = user_script.PhysicalInputVariable(
    "Button",
    "The stick button that changes the mode",
    is_optional=False,
    valid_types=[types.InputType.JoystickButton],
)


@button.decorator(works_in)
def on_button(event: types.Event) -> None:
    """On press only: switch to the target mode."""
    if not event.is_pressed:
        return
    user_script.switch_mode(target.value)
