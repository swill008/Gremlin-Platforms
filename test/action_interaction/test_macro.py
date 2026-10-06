# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Macros: their steps, repeats, and exclusive / preemptive macros.

The tests wait for each event with a generous limit. Where a test checks
what happens between two repeats or during a Pause, those times in the test
profile are made comfortably large (repeats 0.5 s, the preemptive Pause
3 s) instead of relying on short waits staying short (GL-001, AU-119).
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from gremlin.macro import MacroManager
from gremlin.types import (
    HatDirection,
    InputType,
)

from . import input_definitions as inout
from .conftest import (
    EventSpec,
    JoystickGremlinBot,
)
from .waits import assert_no_event_for, next_event, profile_with, wait_until

REPEAT = 0.5
_TOGGLE = "8be44b05-e2da-4dba-8855-76361f041bc1"  # hat 1 south
_HOLD = "dd8b88db-7303-462f-b9cc-7c4c13d003a4"  # hat 1 west
_INTERRUPTIBLE = "4c1bcae6-8d09-4370-9ce7-a07e24bd37d4"  # button 4
_PREEMPTIVE = "408d2dca-dda6-4d05-a7a5-ef7fc718bd3d"  # hat 2 north


@pytest.fixture(autouse=True)
def _default_delay() -> Iterator[None]:
    """Puts back the shared MacroManager's delay the tests change."""
    manager = MacroManager()
    kept = manager.default_delay
    yield
    manager.default_delay = kept


@pytest.fixture
def macro_profile(profile_dir: Path, tmp_path: Path) -> Path:
    return profile_with(
        profile_dir / "macro.xml",
        tmp_path,
        {
            _TOGGLE: {"repeat-delay": str(REPEAT)},
            _HOLD: {"repeat-delay": str(REPEAT)},
            _INTERRUPTIBLE: {"repeat-delay": str(REPEAT)},
            _PREEMPTIVE: {"duration": "3.0"},
        },
    )


def _set_output_axis(jgbot: JoystickGremlinBot, value: float) -> None:
    jgbot.set_axis_absolute(inout.OUT_AXIS_1, value)
    wait_until(jgbot, lambda: jgbot.axis(inout.OUT_AXIS_1) == pytest.approx(value))


def test_simple(jgbot: JoystickGremlinBot, macro_profile: Path) -> None:
    jgbot.load_profile(macro_profile)
    MacroManager().default_delay = 0.0

    expected_event_sequence = [
        EventSpec(InputType.JoystickHat, inout.OUT_HAT_1, HatDirection.NorthEast),
        EventSpec(InputType.JoystickHat, inout.OUT_HAT_2, HatDirection.East),
        EventSpec(InputType.JoystickButton, inout.OUT_BUTTON_3, True),
        EventSpec(InputType.JoystickAxis, inout.OUT_AXIS_2, 0.7),
        EventSpec(InputType.JoystickAxis, inout.OUT_AXIS_3, -0.5),
        EventSpec(InputType.JoystickAxis, inout.OUT_AXIS_1, 0.2),
        EventSpec(InputType.JoystickAxis, inout.OUT_AXIS_4, -0.1),
    ]

    # Trigger action execution and ensure the sequence is sent as expected.
    jgbot.press_button(inout.IN_BUTTON_1)
    for entry in expected_event_sequence:
        assert entry == next_event(jgbot)


def test_repeat(
    jgbot: JoystickGremlinBot, macro_profile: Path, subtests: pytest.Subtests
) -> None:
    jgbot.load_profile(macro_profile)
    MacroManager().default_delay = 0.05

    expected_event_sequence = [
        EventSpec(InputType.JoystickButton, inout.OUT_BUTTON_1, True),
        EventSpec(InputType.JoystickHat, inout.OUT_HAT_1, HatDirection.North),
        EventSpec(InputType.JoystickButton, inout.OUT_BUTTON_1, False),
        EventSpec(InputType.JoystickHat, inout.OUT_HAT_1, HatDirection.Center),
    ]

    # Trigger action execution and ensure the sequence is repeated correctly.
    jgbot.press_button(inout.IN_BUTTON_2)
    for loop in range(3):
        with subtests.test("Repeat iteration", i=loop):
            for entry in expected_event_sequence:
                assert entry == next_event(jgbot)


def test_trigger_on_release(jgbot: JoystickGremlinBot, macro_profile: Path) -> None:
    jgbot.load_profile(macro_profile)
    MacroManager().default_delay = 0.0

    jgbot.press_button(inout.IN_BUTTON_3)
    # Ensure no events are generated before releasing the button.
    assert_no_event_for(jgbot, 0.05)

    # Ensure macro is executed upon button release.
    jgbot.release_button(inout.IN_BUTTON_3)
    assert (
        EventSpec(InputType.JoystickButton, inout.OUT_BUTTON_1, True)
        == next_event(jgbot)
    )
    assert (
        EventSpec(InputType.JoystickButton, inout.OUT_BUTTON_1, False)
        == next_event(jgbot)
    )

    with pytest.raises(jgbot.qtbot.TimeoutError):
        jgbot.next_event()


def test_hat_single(jgbot: JoystickGremlinBot, macro_profile: Path) -> None:
    jgbot.load_profile(macro_profile)
    MacroManager().default_delay = 0.0

    _set_output_axis(jgbot, 0.12)
    jgbot.set_hat_direction(inout.IN_HAT_1, HatDirection.North)
    assert (
        EventSpec(InputType.JoystickAxis, inout.OUT_AXIS_1, 0.17)
        == next_event(jgbot)
    )
    assert jgbot.axis(inout.OUT_AXIS_1) == pytest.approx(0.17, abs=0.01)


def test_hat_count(jgbot: JoystickGremlinBot, macro_profile: Path) -> None:
    jgbot.load_profile(macro_profile)
    MacroManager().default_delay = 0.0

    _set_output_axis(jgbot, -0.15)
    jgbot.set_hat_direction(inout.IN_HAT_1, HatDirection.East)

    assert (
        EventSpec(InputType.JoystickAxis, inout.OUT_AXIS_1, -0.05)
        == next_event(jgbot)
    )
    assert jgbot.axis(inout.OUT_AXIS_1) == pytest.approx(-0.05, abs=0.01)
    assert (
        EventSpec(InputType.JoystickAxis, inout.OUT_AXIS_1, 0.05)
        == next_event(jgbot)
    )
    assert jgbot.axis(inout.OUT_AXIS_1) == pytest.approx(0.05, abs=0.01)


def test_hat_toggle(jgbot: JoystickGremlinBot, macro_profile: Path) -> None:
    jgbot.load_profile(macro_profile)
    MacroManager().default_delay = 0.0

    _set_output_axis(jgbot, -0.15)
    jgbot.set_hat_direction(inout.IN_HAT_1, HatDirection.South)
    jgbot.set_hat_direction(inout.IN_HAT_1, HatDirection.Center)

    expected_value = -0.15
    for _ in range(4):
        expected_value += 0.1
        assert (
            EventSpec(InputType.JoystickAxis, inout.OUT_AXIS_1, expected_value)
            == next_event(jgbot)
        )

    # The next repeat is REPEAT away: toggled off before it.
    assert jgbot.axis(inout.OUT_AXIS_1) == pytest.approx(expected_value, abs=0.01)
    assert jgbot.event_count() == 0
    jgbot.set_hat_direction(inout.IN_HAT_1, HatDirection.South)
    jgbot.set_hat_direction(inout.IN_HAT_1, HatDirection.Center)
    assert_no_event_for(jgbot, REPEAT * 2)


def test_preemptive_exclusive_pauses_and_resumes_macro(
    jgbot: JoystickGremlinBot, macro_profile: Path
) -> None:
    jgbot.load_profile(macro_profile)
    MacroManager().default_delay = 0.0

    # Start a continuously repeating, non-exclusive macro.
    jgbot.press_button(inout.IN_BUTTON_4)
    assert (
        EventSpec(InputType.JoystickAxis, inout.OUT_AXIS_2, 0.1) == next_event(jgbot)
    )

    # Trigger a preemptive, exclusive macro while the previous one is still
    # running. It must dispatch immediately rather than being queued behind it.
    jgbot.set_hat_direction(inout.IN_HAT_2, HatDirection.North)
    assert (
        EventSpec(InputType.JoystickButton, inout.OUT_BUTTON_3, True)
        == next_event(jgbot)
    )

    # While the preemptive macro is still executing (it pauses for 3 s
    # between its two actions), the interrupted macro must produce no further
    # events even though its own repeat delay (REPEAT) has already elapsed.
    assert_no_event_for(jgbot, REPEAT * 1.5)

    # Once the preemptive macro finishes, the interrupted macro must resume.
    assert (
        EventSpec(InputType.JoystickButton, inout.OUT_BUTTON_3, False)
        == next_event(jgbot)
    )
    assert (
        EventSpec(InputType.JoystickAxis, inout.OUT_AXIS_2, 0.2) == next_event(jgbot)
    )

    jgbot.release_button(inout.IN_BUTTON_4)


def test_non_preemptive_exclusive_waits_for_running_macro(
    jgbot: JoystickGremlinBot, macro_profile: Path
) -> None:
    jgbot.load_profile(macro_profile)
    MacroManager().default_delay = 0.0

    # Start a continuously repeating, non-exclusive macro.
    jgbot.press_button(inout.IN_BUTTON_4)
    assert (
        EventSpec(InputType.JoystickAxis, inout.OUT_AXIS_2, 0.1) == next_event(jgbot)
    )

    # Trigger a non-preemptive exclusive macro. Unlike the preemptive case, it
    # must wait for the running macro to finish rather than interrupting it.
    jgbot.set_hat_direction(inout.IN_HAT_2, HatDirection.East)
    assert (
        EventSpec(InputType.JoystickAxis, inout.OUT_AXIS_2, 0.2)
        == next_event(jgbot)
    )
    assert (
        EventSpec(InputType.JoystickAxis, inout.OUT_AXIS_2, 0.3)
        == next_event(jgbot)
    )

    # Terminate the running macro (before its next repeat, REPEAT away),
    # allowing the exclusive one to dispatch.
    jgbot.release_button(inout.IN_BUTTON_4)
    assert (
        EventSpec(InputType.JoystickButton, inout.OUT_BUTTON_4, True)
        == next_event(jgbot)
    )
    assert (
        EventSpec(InputType.JoystickButton, inout.OUT_BUTTON_4, False)
        == next_event(jgbot)
    )


def test_hat_hold(jgbot: JoystickGremlinBot, macro_profile: Path) -> None:
    jgbot.load_profile(macro_profile)
    MacroManager().default_delay = 0.05

    # Set axis state and wait to ensure synchronization.
    _set_output_axis(jgbot, -0.15)
    jgbot.set_hat_direction(inout.IN_HAT_1, HatDirection.West)

    expected_value = -0.15
    for _ in range(4):
        expected_value += 0.1
        assert (
            EventSpec(InputType.JoystickAxis, inout.OUT_AXIS_1, expected_value)
            == next_event(jgbot)
        )
        assert jgbot.axis(inout.OUT_AXIS_1) == pytest.approx(expected_value, abs=0.01)

    # The next repeat is REPEAT away: released before it.
    assert jgbot.event_count() == 0
    jgbot.set_hat_direction(inout.IN_HAT_1, HatDirection.Center)
    assert_no_event_for(jgbot, REPEAT * 2)
