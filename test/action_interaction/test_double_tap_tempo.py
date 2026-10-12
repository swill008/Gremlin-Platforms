# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Double Tap with a Tempo on each side: a tap or a hold, single or double.

The thresholds (0.1 s each) run on timers the test steps itself
(virtual_timers), so presses, releases and timers come in the same order
however busy the PC is.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from gremlin.types import InputType

from . import input_definitions as inout
from .conftest import (
    EventSpec,
    JoystickGremlinBot,
)
from .virtual_timers import VirtualTimers, virtual_timers

TAP = 0.05
# Between the two taps of a double tap: both inside the 0.1 s threshold.
GAP = 0.02
HOLD = 0.3
# Long enough for every timer still waiting (thresholds, pulse release).
AFTER = 1.0


@pytest.fixture
def clock() -> Iterator[VirtualTimers]:
    with virtual_timers() as timers:
        yield timers


def _tap(jgbot: JoystickGremlinBot, clock: VirtualTimers) -> None:
    _hold(jgbot, clock, TAP)


def _hold(jgbot: JoystickGremlinBot, clock: VirtualTimers, seconds: float) -> None:
    jgbot.press_button(inout.IN_BUTTON_1)
    clock.advance(seconds)
    jgbot.release_button(inout.IN_BUTTON_1)


def _assert_pressed_then_released(jgbot: JoystickGremlinBot, button: int) -> None:
    """button pressed then released, and nothing else, once every timer ran."""
    assert EventSpec(InputType.JoystickButton, button, True) == jgbot.next_event()
    assert EventSpec(InputType.JoystickButton, button, False) == jgbot.next_event()
    assert jgbot.event_count() == 0


def test_single_tap_short(
    jgbot: JoystickGremlinBot, profile_dir: Path, clock: VirtualTimers
) -> None:
    jgbot.load_profile(profile_dir / "double_tap_tempo.xml")
    _tap(jgbot, clock)
    clock.advance(AFTER)
    _assert_pressed_then_released(jgbot, inout.OUT_BUTTON_1)


def test_single_tap_long(
    jgbot: JoystickGremlinBot, profile_dir: Path, clock: VirtualTimers
) -> None:
    jgbot.load_profile(profile_dir / "double_tap_tempo.xml")
    _hold(jgbot, clock, HOLD)
    clock.advance(AFTER)
    _assert_pressed_then_released(jgbot, inout.OUT_BUTTON_2)


def test_double_tap_short(
    jgbot: JoystickGremlinBot, profile_dir: Path, clock: VirtualTimers
) -> None:
    jgbot.load_profile(profile_dir / "double_tap_tempo.xml")
    _tap(jgbot, clock)
    clock.advance(GAP)
    _tap(jgbot, clock)
    clock.advance(AFTER)
    _assert_pressed_then_released(jgbot, inout.OUT_BUTTON_3)


def test_double_tap_long(
    jgbot: JoystickGremlinBot, profile_dir: Path, clock: VirtualTimers
) -> None:
    jgbot.load_profile(profile_dir / "double_tap_tempo.xml")
    _tap(jgbot, clock)
    clock.advance(GAP)
    _hold(jgbot, clock, HOLD)
    clock.advance(AFTER)
    _assert_pressed_then_released(jgbot, inout.OUT_BUTTON_4)
