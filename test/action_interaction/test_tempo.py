# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Tempo: a short press runs one action, a long one the other.

The threshold in the test profile is made comfortably large (1 s) so a
"short" press stays short on a busy PC, and the tests wait for the long
action instead of a fixed time (GL-001, AU-119).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from gremlin.types import InputType

from . import input_definitions as inout
from .conftest import (
    EventSpec,
    JoystickGremlinBot,
)
from .waits import assert_no_event_for, next_event, profile_with, wait_until

THRESHOLD = 1.0
_TEMPOS = (
    "43363fb8-46fa-4499-b169-90e1110bf941",  # button 2, on press
    "52979a05-7ba1-47c0-931b-5f4b706aee4c",  # button 1, on release
    "be3383ac-d0a9-458b-b94f-7e7b21d27fc2",  # button 3, Default mode
    "455ebcf1-22dc-4e82-b4ef-096126aaa691",  # button 3, Second mode
)


@pytest.fixture
def tempo_profile(profile_dir: Path, tmp_path: Path) -> Path:
    return profile_with(
        profile_dir / "tempo.xml",
        tmp_path,
        {tempo: {"threshold": str(THRESHOLD)} for tempo in _TEMPOS},
    )


def test_on_press_short(jgbot: JoystickGremlinBot, tempo_profile: Path) -> None:
    jgbot.load_profile(tempo_profile)

    jgbot.press_button(inout.IN_BUTTON_2)
    assert (
        EventSpec(InputType.JoystickButton, inout.OUT_BUTTON_1, True)
        == next_event(jgbot)
    )
    assert jgbot.button(inout.OUT_BUTTON_1)
    jgbot.wait(0.1)
    jgbot.release_button(inout.IN_BUTTON_2)
    assert (
        EventSpec(InputType.JoystickButton, inout.OUT_BUTTON_1, False)
        == next_event(jgbot)
    )
    assert not jgbot.button(inout.OUT_BUTTON_1)

    # No long action after the threshold.
    assert_no_event_for(jgbot, THRESHOLD * 1.5)


def test_on_press_long(jgbot: JoystickGremlinBot, tempo_profile: Path) -> None:
    jgbot.load_profile(tempo_profile)

    jgbot.press_button(inout.IN_BUTTON_2)
    assert (
        EventSpec(InputType.JoystickButton, inout.OUT_BUTTON_1, True)
        == next_event(jgbot)
    )
    jgbot.wait(0.15)  # well under the threshold
    assert jgbot.button(inout.OUT_BUTTON_1)
    assert not jgbot.button(inout.OUT_BUTTON_2)
    assert (
        EventSpec(InputType.JoystickButton, inout.OUT_BUTTON_2, True)
        == next_event(jgbot)
    )

    jgbot.release_button(inout.IN_BUTTON_2)
    assert (
        EventSpec(InputType.JoystickButton, inout.OUT_BUTTON_2, False)
        == next_event(jgbot)
    )
    assert (
        EventSpec(InputType.JoystickButton, inout.OUT_BUTTON_1, False)
        == next_event(jgbot)
    )

    # Ensure no additional events are generated.
    assert_no_event_for(jgbot, 0.5)


def test_on_release_short_tap(jgbot: JoystickGremlinBot, tempo_profile: Path) -> None:
    jgbot.load_profile(tempo_profile)

    assert not jgbot.button(inout.OUT_BUTTON_1)
    jgbot.tap_button(inout.IN_BUTTON_1)

    assert (
        EventSpec(InputType.JoystickButton, inout.OUT_BUTTON_1, True)
        == next_event(jgbot)
    )
    assert (
        EventSpec(InputType.JoystickButton, inout.OUT_BUTTON_1, False)
        == next_event(jgbot)
    )
    assert not jgbot.button(inout.OUT_BUTTON_1)

    # No long action after the threshold.
    assert_no_event_for(jgbot, THRESHOLD * 1.5)


def test_on_release_short_hold(
    jgbot: JoystickGremlinBot, tempo_profile: Path
) -> None:
    jgbot.load_profile(tempo_profile)

    assert not jgbot.button(inout.OUT_BUTTON_1)
    jgbot.press_button(inout.IN_BUTTON_1)
    jgbot.wait(0.15)  # well under the threshold
    jgbot.release_button(inout.IN_BUTTON_1)

    assert (
        EventSpec(InputType.JoystickButton, inout.OUT_BUTTON_1, True)
        == next_event(jgbot)
    )
    assert (
        EventSpec(InputType.JoystickButton, inout.OUT_BUTTON_1, False)
        == next_event(jgbot)
    )

    # No long action after the threshold.
    assert_no_event_for(jgbot, THRESHOLD * 1.5)


def test_on_release_long(jgbot: JoystickGremlinBot, tempo_profile: Path) -> None:
    jgbot.load_profile(tempo_profile)

    jgbot.press_button(inout.IN_BUTTON_1)
    # The long action starts at the threshold, while the button is held.
    assert (
        EventSpec(InputType.JoystickButton, inout.OUT_BUTTON_2, True)
        == next_event(jgbot)
    )
    assert jgbot.button(inout.OUT_BUTTON_2)

    jgbot.release_button(inout.IN_BUTTON_1)
    assert (
        EventSpec(InputType.JoystickButton, inout.OUT_BUTTON_2, False)
        == next_event(jgbot)
    )
    assert not jgbot.button(inout.OUT_BUTTON_2)


def test_release_out_of_rder(jgbot: JoystickGremlinBot, tempo_profile: Path) -> None:
    jgbot.load_profile(tempo_profile)

    # A long hold changes the mode at the threshold; the release then comes
    # in the other mode.
    assert jgbot.current_mode() == "Default"
    jgbot.press_button(inout.IN_BUTTON_3)
    wait_until(jgbot, lambda: jgbot.current_mode() == "Second")
    jgbot.release_button(inout.IN_BUTTON_3)
    assert jgbot.current_mode() == "Second"
    jgbot.press_button(inout.IN_BUTTON_3)
    wait_until(jgbot, lambda: jgbot.current_mode() == "Default")
    jgbot.release_button(inout.IN_BUTTON_3)
    assert jgbot.current_mode() == "Default"
