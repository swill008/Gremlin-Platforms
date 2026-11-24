# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Macro scheduling: Hold, Toggle and Count repeats, exclusive and
preemptive macros, and Stop (05 S92, S147-S150, S85).

Ported from upstream's test_macro_scheduling.py (WhiteMagic/JoystickGremlin
2af6d18a, user answer 14a). Upstream's profile is rebuilt in our format
(macro_scheduling.xml): the same macros, Logical Device buttons 1-10 as
inputs (upstream's input 11, Long pause, is 5 here) and buttons 21-30 and
axis 21 as outputs. Two tests follow our Stop rule instead of upstream's
(05 S92: Stop ends a running macro at once, its last steps do not run):
upstream's running macro finishes its repetition within a grace period.

A restart that must come before a 5 s repeat delay ends is waited for with
SOON, well under that delay; the rest wait with the generous LIMIT_MS.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from pathlib import Path

import pytest
import win32api
import win32con

from gremlin.logical_device import LogicalDevice
from gremlin.types import (
    Event,
    InputType,
)

from . import conftest
from .conftest import (
    EventSpec,
    JoystickGremlinBot,
)
from .waits import assert_no_event_for, next_event, wait_until

HOLD = 1  # Hold pulse every 5 s -> OUT 21
TOGGLE = 2  # Toggle pulse every 5 s -> OUT 22
EXCLUSIVE = 3  # Exclusive pulse -> OUT 23
PREEMPTIVE = 4  # Preemptive (and exclusive) pulse -> OUT 24
LONG_PAUSE = 5  # 1.5 s pause between press and release -> OUT 30
HOLD_AND_RELEASE = 6  # Hold pulse -> OUT 26, release macro -> OUT 27
MAP_TO_K = 7  # Map to Keyboard, key K
BOTH_EDGES = 8  # Hold on press and release every 0.2 s -> axis 21 (+0.1)
EMPTY_THEN_MACRO = 9  # an empty macro, then a macro -> OUT 28
COUNT = 10  # Count 1 every 5 s -> OUT 29

OUT_AXIS = 21

# Comfortably under the 5 s repeat delay the restart tests must beat.
SOON = 2.0
# Nothing more comes: longer than any step that could follow.
QUIET = 0.8
K_SCAN_CODE = 37


def _button(input_id: int, pressed: bool) -> EventSpec:
    return EventSpec(InputType.JoystickButton, input_id, pressed)


def _set_up_logical_device(device: LogicalDevice) -> None:
    """The shared Logical Device plus the inputs this profile needs."""
    set_up_shared(device)
    for number in range(5, 11):
        device.create(InputType.JoystickButton, number, f"Input Button {number}")
    for number in range(21, 31):
        device.create(InputType.JoystickButton, number, f"Output Button {number}")
    device.create(InputType.JoystickAxis, OUT_AXIS, f"Output Axis {OUT_AXIS}")


set_up_shared = conftest.set_up_logical_device


@pytest.fixture
def jgbot_ms(
    jgbot: JoystickGremlinBot,
    profile_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[JoystickGremlinBot]:
    """The bot with macro_scheduling.xml loaded and running."""
    monkeypatch.setattr(conftest, "set_up_logical_device", _set_up_logical_device)
    jgbot.load_profile(profile_dir / "macro_scheduling.xml")
    yield jgbot


@pytest.fixture
def keys_down(monkeypatch: pytest.MonkeyPatch) -> set[int]:
    """Scan codes held down; no key reaches Windows."""
    down: set[int] = set()

    def fake_keybd_event(_vk: int, scan: int, flags: int, _extra: int = 0) -> None:
        if flags & win32con.KEYEVENTF_KEYUP:
            down.discard(scan)
        else:
            down.add(scan)

    monkeypatch.setattr(win32api, "keybd_event", fake_keybd_event)
    return down


def _soon(jgbot: JoystickGremlinBot) -> Event:
    jgbot.qtbot.waitUntil(lambda: jgbot.event_count() > 0, timeout=int(SOON * 1000))
    return jgbot.next_event()


# 1. upstream test_hold_macro_restarts_after_release
def test_hold_macro_restarts_after_release(jgbot_ms: JoystickGremlinBot) -> None:
    bot = jgbot_ms
    bot.press_button(HOLD)
    assert _button(21, True) == next_event(bot)
    assert _button(21, False) == next_event(bot)

    # Released and pressed again during the 5 s repeat delay (S147).
    bot.release_button(HOLD)
    bot.press_button(HOLD)
    assert _button(21, True) == _soon(bot)


# 2. upstream test_hold_macro_finishes_repetition_before_restarting
def test_hold_macro_finishes_repetition_before_restarting(
    jgbot_ms: JoystickGremlinBot,
) -> None:
    bot = jgbot_ms
    bot.press_button(HOLD)
    assert _button(21, True) == next_event(bot)

    # Released and pressed again during the repetition's pause.
    bot.release_button(HOLD)
    bot.press_button(HOLD)
    bot.wait(0)
    assert bot.event_count() == 0
    assert _button(21, False) == next_event(bot)
    assert _button(21, True) == _soon(bot)


# 3. upstream test_hold_macro_never_runs_during_exclusive_macro
def test_hold_macro_never_runs_during_exclusive_macro(
    jgbot_ms: JoystickGremlinBot,
) -> None:
    bot = jgbot_ms
    bot.press_button(EXCLUSIVE)
    assert _button(23, True) == next_event(bot)

    # Released before it ever started: it never runs.
    bot.press_button(HOLD)
    bot.release_button(HOLD)
    assert _button(23, False) == next_event(bot)
    assert_no_event_for(bot, QUIET)


# 4. upstream test_hold_macro_runs_after_exclusive_macro
def test_hold_macro_runs_after_exclusive_macro(jgbot_ms: JoystickGremlinBot) -> None:
    bot = jgbot_ms
    bot.press_button(EXCLUSIVE)
    assert _button(23, True) == next_event(bot)

    bot.press_button(HOLD)
    assert _button(23, False) == next_event(bot)
    assert _button(21, True) == next_event(bot)
    assert _button(21, False) == next_event(bot)


# 5. upstream test_toggle_macro_never_runs_during_exclusive_macro
def test_toggle_macro_never_runs_during_exclusive_macro(
    jgbot_ms: JoystickGremlinBot,
) -> None:
    bot = jgbot_ms
    bot.press_button(EXCLUSIVE)
    assert _button(23, True) == next_event(bot)

    # On and off again while it waits (S148).
    bot.tap_button(TOGGLE)
    bot.tap_button(TOGGLE)
    assert _button(23, False) == next_event(bot)
    assert_no_event_for(bot, QUIET)


# 6. upstream test_toggle_macro_runs_after_exclusive_macro
def test_toggle_macro_runs_after_exclusive_macro(jgbot_ms: JoystickGremlinBot) -> None:
    bot = jgbot_ms
    bot.press_button(EXCLUSIVE)
    assert _button(23, True) == next_event(bot)

    bot.tap_button(TOGGLE)
    assert _button(23, False) == next_event(bot)
    assert _button(22, True) == next_event(bot)
    assert _button(22, False) == next_event(bot)


# 7. upstream test_toggle_macro_restarts_after_toggling_off
def test_toggle_macro_restarts_after_toggling_off(
    jgbot_ms: JoystickGremlinBot,
) -> None:
    bot = jgbot_ms
    bot.tap_button(TOGGLE)
    assert _button(22, True) == next_event(bot)
    assert _button(22, False) == next_event(bot)

    # Off and on again during the 5 s repeat delay (S147).
    bot.tap_button(TOGGLE)
    bot.tap_button(TOGGLE)
    assert _button(22, True) == _soon(bot)


# 8. upstream test_toggle_macro_finishes_repetition_before_restarting
def test_toggle_macro_finishes_repetition_before_restarting(
    jgbot_ms: JoystickGremlinBot,
) -> None:
    bot = jgbot_ms
    bot.tap_button(TOGGLE)
    assert _button(22, True) == next_event(bot)

    # Off and on again during the repetition's pause.
    bot.tap_button(TOGGLE)
    bot.tap_button(TOGGLE)
    assert bot.event_count() == 0
    assert _button(22, False) == next_event(bot)
    assert _button(22, True) == _soon(bot)


# 9. upstream test_release_macro_runs_in_parallel_with_hold_macro
def test_release_macro_runs_in_parallel_with_hold_macro(
    jgbot_ms: JoystickGremlinBot,
) -> None:
    bot = jgbot_ms
    bot.press_button(HOLD_AND_RELEASE)
    assert _button(26, True) == next_event(bot)

    bot.release_button(HOLD_AND_RELEASE)
    assert _button(27, True) == next_event(bot)
    assert _button(26, False) == next_event(bot)


# 10. upstream test_map_to_keyboard_runs_during_exclusive_macro
def test_map_to_keyboard_runs_during_exclusive_macro(
    jgbot_ms: JoystickGremlinBot, keys_down: set[int]
) -> None:
    bot = jgbot_ms
    assert K_SCAN_CODE not in keys_down

    bot.press_button(EXCLUSIVE)
    assert _button(23, True) == next_event(bot)

    # Keys go down at once, not after the exclusive macro (S85).
    bot.press_button(MAP_TO_K)
    try:
        bot.wait_until(lambda: K_SCAN_CODE in keys_down, timeout=0.2)
        # The exclusive macro has not ended yet.
        assert bot.event_count() == 0
    finally:
        bot.release_button(MAP_TO_K)
    wait_until(bot, lambda: K_SCAN_CODE not in keys_down)


# 11. upstream test_hold_macro_activated_on_press_and_release_stops_on_release
def test_hold_macro_activated_on_press_and_release_stops_on_release(
    jgbot_ms: JoystickGremlinBot,
) -> None:
    bot = jgbot_ms
    bot.press_button(BOTH_EDGES)
    assert EventSpec(InputType.JoystickAxis, OUT_AXIS, 0.1) == next_event(bot)

    bot.release_button(BOTH_EDGES)
    assert_no_event_for(bot, QUIET)


# 12. upstream test_empty_macro_does_not_block_next_macro
def test_empty_macro_does_not_block_next_macro(jgbot_ms: JoystickGremlinBot) -> None:
    bot = jgbot_ms
    assert not bot.button(28)

    bot.press_button(EMPTY_THEN_MACRO)
    assert _button(28, True) == next_event(bot)


# 13. upstream test_macro_runs_twice_when_triggered_while_running
def test_macro_runs_twice_when_triggered_while_running(
    jgbot_ms: JoystickGremlinBot,
) -> None:
    bot = jgbot_ms
    bot.tap_button(EXCLUSIVE)
    bot.tap_button(EXCLUSIVE)
    assert _button(23, True) == next_event(bot)
    assert _button(23, False) == next_event(bot)
    assert _button(23, True) == next_event(bot)


# 14. upstream test_count_macro_restarts_after_finishing
def test_count_macro_restarts_after_finishing(jgbot_ms: JoystickGremlinBot) -> None:
    bot = jgbot_ms
    bot.tap_button(COUNT)
    assert _button(29, True) == next_event(bot)

    # No repeat delay after the last count (S147).
    bot.tap_button(COUNT)
    assert _button(29, True) == _soon(bot)


# 15. upstream test_macro_waits_for_exclusive_macro_after_preemptive_macro_ends
def test_macro_waits_for_exclusive_macro_after_preemptive_macro_ends(
    jgbot_ms: JoystickGremlinBot,
) -> None:
    bot = jgbot_ms
    bot.press_button(EXCLUSIVE)
    assert _button(23, True) == next_event(bot)
    bot.press_button(PREEMPTIVE)
    assert _button(24, True) == next_event(bot)

    # S149: the paused exclusive macro still blocks it.
    bot.press_button(EMPTY_THEN_MACRO)
    assert _button(24, False) == next_event(bot)
    assert _button(23, False) == next_event(bot)
    assert _button(28, True) == next_event(bot)


# 16. upstream test_waiting_macro_is_dropped_on_profile_stop, to our Stop
# rule (05 S92): the running exclusive macro ends at once too, so its
# release step never comes (upstream expects OUT 23 False first).
def test_waiting_macro_is_dropped_on_profile_stop(
    jgbot_ms: JoystickGremlinBot,
) -> None:
    bot = jgbot_ms
    bot.press_button(EXCLUSIVE)
    assert _button(23, True) == next_event(bot)
    bot.press_button(EMPTY_THEN_MACRO)

    bot.stop()
    assert_no_event_for(bot, QUIET)
    assert not bot.button(28)


# 17. upstream test_running_macro_finishes_on_profile_stop, to our Stop rule
# (05 S92): the running macro ends at once instead of finishing its
# repetition (upstream expects OUT 23 False within its grace period).
def test_running_macro_ends_at_once_on_profile_stop(
    jgbot_ms: JoystickGremlinBot,
) -> None:
    bot = jgbot_ms
    bot.press_button(EXCLUSIVE)
    assert _button(23, True) == next_event(bot)

    bot.stop()
    assert_no_event_for(bot, QUIET)


# 18. upstream test_running_macro_aborted_after_stop_grace_period: ours has
# no grace period, so Stop also returns before the 1.5 s pause is over.
def test_running_macro_aborted_on_profile_stop(jgbot_ms: JoystickGremlinBot) -> None:
    bot = jgbot_ms
    bot.press_button(LONG_PAUSE)
    assert _button(30, True) == next_event(bot)

    started = time.monotonic()
    bot.stop()
    assert time.monotonic() - started < 1.0
    assert_no_event_for(bot, QUIET)
