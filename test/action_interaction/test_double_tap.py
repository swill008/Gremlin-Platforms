# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Double Tap: one action for a single tap, another for a double tap.

The double-tap time in the test profile is made comfortably large (1 s) so
two quick taps stay a double tap on a busy PC; the tests wait for the
single-tap result or for the double-tap timer itself instead of a fixed
time (GL-001, AU-119).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from action_plugins.double_tap import DoubleTapFunctor
from gremlin.types import InputType

from . import input_definitions as inout
from .conftest import (
    EventSpec,
    JoystickGremlinBot,
)
from .waits import assert_no_event_for, next_event, profile_with, wait_until

THRESHOLD = 1.0
_EXCLUSIVE = "12f4d060-51ca-4b73-853c-497430730d07"  # button 1
_COMBINED = "cf19460e-4bed-4451-8d62-407ebd429585"  # button 2


@pytest.fixture
def double_tap_profile(profile_dir: Path, tmp_path: Path) -> Path:
    return profile_with(
        profile_dir / "double_tap.xml",
        tmp_path,
        {tap: {"threshold": str(THRESHOLD)} for tap in (_EXCLUSIVE, _COMBINED)},
    )


@pytest.fixture
def timeouts(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """Counts the double-tap timers that ran out."""
    fired: list[int] = []
    original: Callable[[DoubleTapFunctor], None] = DoubleTapFunctor._timeout

    def counted(self: DoubleTapFunctor) -> None:
        fired.append(1)
        original(self)

    monkeypatch.setattr(DoubleTapFunctor, "_timeout", counted)
    return fired


def test_exclusive_single(
    jgbot: JoystickGremlinBot, double_tap_profile: Path
) -> None:
    jgbot.load_profile(double_tap_profile)

    # A tap: the single action pulses once the double-tap time is out.
    jgbot.tap_button(inout.IN_BUTTON_1)
    assert (
        EventSpec(InputType.JoystickButton, inout.OUT_BUTTON_1, True)
        == next_event(jgbot)
    )
    assert (
        EventSpec(InputType.JoystickButton, inout.OUT_BUTTON_1, False)
        == next_event(jgbot)
    )

    # Held past the double-tap time: pressed then, released with the button.
    jgbot.press_button(inout.IN_BUTTON_1)
    assert (
        EventSpec(InputType.JoystickButton, inout.OUT_BUTTON_1, True)
        == next_event(jgbot)
    )
    jgbot.release_button(inout.IN_BUTTON_1)
    assert (
        EventSpec(InputType.JoystickButton, inout.OUT_BUTTON_1, False)
        == next_event(jgbot)
    )

    # Ensure no additional events are generated.
    assert_no_event_for(jgbot, 0.5)


def test_exclusive_double(
    jgbot: JoystickGremlinBot, double_tap_profile: Path
) -> None:
    jgbot.load_profile(double_tap_profile)

    jgbot.tap_button(inout.IN_BUTTON_1)
    jgbot.tap_button(inout.IN_BUTTON_1)
    assert (
        EventSpec(InputType.JoystickButton, inout.OUT_BUTTON_2, True)
        == next_event(jgbot)
    )
    assert (
        EventSpec(InputType.JoystickButton, inout.OUT_BUTTON_2, False)
        == next_event(jgbot)
    )

    # No single action once the double-tap time is out.
    assert_no_event_for(jgbot, THRESHOLD * 1.5)


def test_combined_single(
    jgbot: JoystickGremlinBot, double_tap_profile: Path, timeouts: list[int]
) -> None:
    jgbot.load_profile(double_tap_profile)

    # A tap: the single action follows the button.
    jgbot.tap_button(inout.IN_BUTTON_2)
    assert (
        EventSpec(InputType.JoystickButton, inout.OUT_BUTTON_1, True)
        == next_event(jgbot)
    )
    assert (
        EventSpec(InputType.JoystickButton, inout.OUT_BUTTON_1, False)
        == next_event(jgbot)
    )

    # Wait out the double tap time.
    wait_until(jgbot, lambda: len(timeouts) == 1)

    # Held past the double-tap time.
    jgbot.press_button(inout.IN_BUTTON_2)
    assert (
        EventSpec(InputType.JoystickButton, inout.OUT_BUTTON_1, True)
        == next_event(jgbot)
    )
    wait_until(jgbot, lambda: len(timeouts) == 2)
    jgbot.release_button(inout.IN_BUTTON_2)
    assert (
        EventSpec(InputType.JoystickButton, inout.OUT_BUTTON_1, False)
        == next_event(jgbot)
    )

    # Ensure no additional events are generated.
    assert_no_event_for(jgbot, 0.5)


def test_combined_double(
    jgbot: JoystickGremlinBot, double_tap_profile: Path
) -> None:
    jgbot.load_profile(double_tap_profile)

    jgbot.tap_button(inout.IN_BUTTON_2)
    jgbot.tap_button(inout.IN_BUTTON_2)
    assert (
        EventSpec(InputType.JoystickButton, inout.OUT_BUTTON_1, True)
        == next_event(jgbot)
    )
    assert (
        EventSpec(InputType.JoystickButton, inout.OUT_BUTTON_1, False)
        == next_event(jgbot)
    )
    assert (
        EventSpec(InputType.JoystickButton, inout.OUT_BUTTON_1, True)
        == next_event(jgbot)
    )
    assert (
        EventSpec(InputType.JoystickButton, inout.OUT_BUTTON_2, True)
        == next_event(jgbot)
    )
    assert (
        EventSpec(InputType.JoystickButton, inout.OUT_BUTTON_1, False)
        == next_event(jgbot)
    )
    assert (
        EventSpec(InputType.JoystickButton, inout.OUT_BUTTON_2, False)
        == next_event(jgbot)
    )

    # Ensure no additional events are generated.
    assert_no_event_for(jgbot, THRESHOLD * 1.5)
