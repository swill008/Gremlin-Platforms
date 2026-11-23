# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Test script: one stick button, short press and long press.

Released before "Long press (s)" has passed, it taps vJoy 1 button
"Short button"; held longer, it taps "Long button". The time is read from
gremlin.clock on press and release, so no timer thread is needed. Written
for this suite.
"""

from gremlin import clock, event_handler, types, user_script

mode = user_script.ModeVariable("Mode", "The mode the button works in", True)

button = user_script.PhysicalInputVariable(
    "Button", "The stick button", False, [types.InputType.JoystickButton]
)
long_press = user_script.FloatVariable(
    "Long press (s)", "Held this long is a long press", True, 0.5, 0.1, 5.0
)
short_button = user_script.IntegerVariable(
    "Short button", "vJoy 1 button for a short press", True, 1, 1, 32
)
long_button = user_script.IntegerVariable(
    "Long button", "vJoy 1 button for a long press", True, 2, 1, 32
)

# When the button went down (None: up).
pressed_at: list[float | None] = [None]


@button.decorator(mode)
def on_button(event: event_handler.Event, vjoy: object) -> None:
    if event.is_pressed:
        pressed_at[0] = clock.monotonic()
        return
    if pressed_at[0] is None:
        return
    held = clock.monotonic() - pressed_at[0]
    pressed_at[0] = None
    target = long_button if held >= long_press.value else short_button
    vjoy[1].button(target.value).is_pressed = True
    vjoy[1].button(target.value).is_pressed = False
