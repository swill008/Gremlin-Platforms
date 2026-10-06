# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Plain remaps: buttons, axes and hats follow their input.

A held button is held for a comfortably long time and the test waits for
its release instead of a fixed time (GL-001, AU-119).
"""

from __future__ import annotations

from pathlib import Path

from gremlin.types import HatDirection

from . import input_definitions as inout
from .conftest import JoystickGremlinBot
from .waits import wait_until

# Comfortably longer than the check made while it is held.
HOLD = 2.0


def test_simple(jgbot: JoystickGremlinBot, profile_dir: Path) -> None:
    jgbot.load_profile(profile_dir / "remap_basic.xml")

    jgbot.press_button(inout.IN_BUTTON_1)
    assert jgbot.button(inout.OUT_BUTTON_1)
    jgbot.release_button(inout.IN_BUTTON_1)
    assert not jgbot.button(inout.OUT_BUTTON_1)

    jgbot.set_axis_absolute(inout.IN_AXIS_1, 0.5)
    assert jgbot.axis(inout.OUT_AXIS_1) == 0.5
    jgbot.set_axis_absolute(inout.IN_AXIS_1, -0.5)
    assert jgbot.axis(inout.OUT_AXIS_1) == -0.5

    jgbot.set_hat_direction(inout.IN_HAT_1, HatDirection.NorthWest)
    assert jgbot.hat(inout.OUT_HAT_1) == HatDirection.NorthWest
    jgbot.set_hat_direction(inout.IN_HAT_1, HatDirection.SouthEast)
    assert jgbot.hat(inout.OUT_HAT_1) == HatDirection.SouthEast


def test_button_advanced(jgbot: JoystickGremlinBot, profile_dir: Path) -> None:
    jgbot.load_profile(profile_dir / "remap_basic.xml")

    jgbot.tap_button(inout.IN_BUTTON_1)
    assert not jgbot.button(inout.OUT_BUTTON_1)

    jgbot.hold_button(inout.IN_BUTTON_1, HOLD)
    assert jgbot.button(inout.OUT_BUTTON_1)
    jgbot.wait(0.4)  # well inside the hold
    assert jgbot.button(inout.OUT_BUTTON_1)
    wait_until(jgbot, lambda: not jgbot.button(inout.OUT_BUTTON_1))


def test_remap_inverse(jgbot: JoystickGremlinBot, profile_dir: Path) -> None:
    jgbot.load_profile(profile_dir / "remap_invert.xml")

    jgbot.press_button(inout.IN_BUTTON_1)
    assert not jgbot.button(inout.OUT_BUTTON_1)
    jgbot.release_button(inout.IN_BUTTON_1)
    assert jgbot.button(inout.OUT_BUTTON_1)
