# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Test script: a rotary encoder, paced by a periodic callback.

Each click of the encoder (its two stick buttons, one per direction) adds a
step; a periodic callback sends one step per tick as a tap of vJoy 1
button 1 (clockwise) or button 2 (counter-clockwise), so fast turns are not
lost or sent faster than a game reads them. Written for this suite.
"""

import threading

from gremlin import types, user_script

mode = user_script.ModeVariable("Mode", "The mode the encoder works in", True)

clockwise = user_script.PhysicalInputVariable(
    "Clockwise", "Encoder button, clockwise", False, [types.InputType.JoystickButton]
)
counter = user_script.PhysicalInputVariable(
    "Counter-clockwise",
    "Encoder button, counter-clockwise",
    False,
    [types.InputType.JoystickButton],
)

# vJoy buttons still to tap, oldest first.
pending: list[int] = []
_lock = threading.Lock()


@clockwise.decorator(mode)
def on_clockwise(event: types.Event) -> None:
    if event.is_pressed:
        with _lock:
            pending.append(1)


@counter.decorator(mode)
def on_counter(event: types.Event) -> None:
    if event.is_pressed:
        with _lock:
            pending.append(2)


@user_script.periodic(0.02)
def send_step(vjoy: object) -> None:
    with _lock:
        if not pending:
            return
        number = pending.pop(0)
    vjoy[1].button(number).is_pressed = True
    vjoy[1].button(number).is_pressed = False
