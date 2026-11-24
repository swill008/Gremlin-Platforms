# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Test script: a stick button queues a macro.

The macro presses vJoy 1 button "Macro button", waits 0.05 s and releases
it. It is run by the program's macro scheduler (MacroManager), as a Macro
action's macro is. It uses only vJoy steps, never keys. Written for this
suite.
"""

from gremlin import macro, types, user_script

mode = user_script.ModeVariable("Mode", "The mode the button works in", True)

button = user_script.PhysicalInputVariable(
    "Button", "The stick button", False, [types.InputType.JoystickButton]
)
target = user_script.IntegerVariable(
    "Macro button", "vJoy 1 button the macro taps", True, 7, 1, 32
)


@button.decorator(mode)
def on_button(event: types.Event) -> None:
    if not event.is_pressed:
        return
    tap = macro.Macro()
    btn = types.InputType.JoystickButton
    tap.add_action(macro.VJoyAction(1, btn, target.value, True))
    tap.add_action(macro.PauseAction(0.05))
    tap.add_action(macro.VJoyAction(1, btn, target.value, False))
    macro.MacroManager().queue_macro(tap)
