# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The macro manager on upstream's model (B4, 05 S147-S150, S92; 06 S21).

Steps are plain callables that note what ran; the tests wait for a state
instead of sleeping a fixed time where they can.
"""

from __future__ import annotations

import sys
import threading
import time
from collections.abc import Callable, Iterator

sys.path.append(".")

import pytest

from gremlin import threads
from gremlin.macro import (
    CountRepeat,
    HoldRepeat,
    Macro,
    MacroManager,
    PauseAction,
    ToggleRepeat,
)


@pytest.fixture
def manager() -> Iterator[MacroManager]:
    mm = MacroManager()
    old_delay = mm.default_delay
    mm.default_delay = 0.0
    mm.start()
    yield mm
    mm.stop()
    mm.default_delay = old_delay
    assert _wait_for(lambda: not _macro_threads(), 3.0)


def _wait_for(check: Callable[[], bool], seconds: float = 5.0) -> bool:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if check():
            return True
        time.sleep(0.01)
    return check()


def _macro_threads() -> set[threading.Thread]:
    name = threads.PREFIX + "macro"
    return {t for t in threading.enumerate() if t.name == name}


def _macro(ran: list[str], *steps: str | float) -> Macro:
    """A macro noting each named step; a number is a Pause."""
    macro = Macro()
    for step in steps:
        if isinstance(step, str):
            macro.add_action(lambda s=step: ran.append(s))
        else:
            macro.add_action(PauseAction(step))
    return macro


def test_api_names() -> None:
    mm = MacroManager()
    for name in ("run_macro", "stop_macro", "toggle_macro", "start", "stop"):
        assert callable(getattr(mm, name))
    for old in ("queue_macro", "terminate_macro"):
        assert not hasattr(mm, old)


def test_exclusive_still_blocks_after_a_preemptive_one_ends(
    manager: MacroManager,
) -> None:
    """05 S149: the old single flag was cleared when the preemptive macro
    ended, so a plain macro ran while the exclusive one was still going."""
    ran: list[str] = []
    exclusive = _macro(ran, "e1", 0.8, "e2")
    exclusive.is_exclusive = True
    preemptive = _macro(ran, "p")
    preemptive.is_exclusive = True
    preemptive.is_preempting = True
    plain = _macro(ran, "n")

    manager.run_macro(exclusive)
    assert _wait_for(lambda: "e1" in ran)
    manager.run_macro(preemptive)
    assert _wait_for(lambda: "p" in ran)
    assert _wait_for(lambda: preemptive.id not in manager._running_macros)
    manager.run_macro(plain)
    assert _wait_for(lambda: "n" in ran)
    assert ran.index("n") > ran.index("e2")


def test_hold_repeat_delay_ends_on_its_own_stop(manager: MacroManager) -> None:
    """05 S147: the delay used to wait out its full length after release."""
    ran: list[str] = []
    macro = _macro(ran, "a")
    macro.repeat = HoldRepeat(delay=5.0)
    manager.run_macro(macro)
    assert _wait_for(lambda: ran == ["a"])
    start = time.monotonic()
    manager.stop_macro(macro)
    assert _wait_for(lambda: macro.id not in manager._running_macros, 2.0)
    assert time.monotonic() - start < 1.0
    assert ran == ["a"]


def test_toggle_repeat_delay_ends_when_toggled_off(manager: MacroManager) -> None:
    ran: list[str] = []
    macro = _macro(ran, "a")
    macro.repeat = ToggleRepeat(delay=5.0)
    manager.toggle_macro(macro)
    assert _wait_for(lambda: ran == ["a"])
    manager.toggle_macro(macro)
    assert _wait_for(lambda: macro.id not in manager._running_macros, 1.0)


def test_count_has_no_delay_after_the_last_repetition(
    manager: MacroManager,
) -> None:
    ran: list[str] = []
    macro = _macro(ran, "a")
    macro.repeat = CountRepeat(count=2, delay=1.0)
    start = time.monotonic()
    manager.run_macro(macro)
    assert _wait_for(lambda: macro.id not in manager._running_macros
                     and ran == ["a", "a"], 4.0)
    took = time.monotonic() - start
    assert 0.9 < took < 1.7  # one delay, not two


def test_second_tap_on_a_waiting_toggle_switches_it_off(
    manager: MacroManager,
) -> None:
    """05 S148."""
    ran: list[str] = []
    exclusive = _macro(ran, "e1", 0.5, "e2")
    exclusive.is_exclusive = True
    toggle = _macro(ran, "t")
    toggle.repeat = ToggleRepeat(delay=0.1)

    manager.run_macro(exclusive)
    assert _wait_for(lambda: "e1" in ran)
    manager.toggle_macro(toggle)  # waits behind the exclusive one
    manager.toggle_macro(toggle)  # switches it off
    assert _wait_for(lambda: not manager._running_macros, 3.0)
    time.sleep(0.2)
    assert "t" not in ran


def test_release_then_press_during_the_delay_restarts_a_hold_macro(
    manager: MacroManager,
) -> None:
    """05 S147."""
    ran: list[str] = []
    macro = _macro(ran, "a")
    macro.repeat = HoldRepeat(delay=5.0)
    manager.run_macro(macro)
    assert _wait_for(lambda: ran == ["a"])
    manager.stop_macro(macro)
    manager.run_macro(macro)
    assert _wait_for(lambda: ran == ["a", "a"], 1.0)
    manager.stop_macro(macro)


def test_a_held_hold_macro_ignores_another_press(manager: MacroManager) -> None:
    ran: list[str] = []
    macro = _macro(ran, "a", 0.3)
    macro.repeat = HoldRepeat(delay=5.0)
    manager.run_macro(macro)
    manager.run_macro(macro)
    assert not manager._waiting_macros
    manager.stop_macro(macro)


def test_stop_ends_every_macro_at_once(manager: MacroManager) -> None:
    """05 S92: Pause and repeat delay end at once on Stop."""
    ran: list[str] = []
    hold = _macro(ran, "h", 5.0, "h2")
    hold.repeat = HoldRepeat(delay=5.0)
    count = _macro(ran, "c")
    count.repeat = CountRepeat(count=5, delay=5.0)
    waiting = _macro(ran, "w")
    exclusive = _macro(ran, "x", 5.0)
    exclusive.is_exclusive = True

    manager.run_macro(hold)
    manager.run_macro(count)
    assert _wait_for(lambda: "h" in ran and "c" in ran)
    manager.run_macro(exclusive)  # waits for the running ones
    manager.run_macro(waiting)  # waits behind the exclusive one
    start = time.monotonic()
    manager.stop()
    assert _wait_for(lambda: not _macro_threads(), 1.0)
    assert time.monotonic() - start < 1.0
    time.sleep(0.1)
    assert sorted(ran) == ["c", "h"]


def test_no_step_after_stop(manager: MacroManager) -> None:
    """06 S21/S32: Stop waits for the step in flight; none comes after."""
    ran: list[str] = []
    in_step = threading.Event()

    def slow_step() -> None:
        in_step.set()
        time.sleep(0.3)
        ran.append("slow done")

    macro = Macro()
    macro.add_action(slow_step)
    macro.add_action(lambda: ran.append("late"))
    manager.run_macro(macro)
    assert in_step.wait(2.0)
    manager.stop()
    assert ran == ["slow done"]  # Stop returned after the step's output
    time.sleep(0.1)
    assert ran == ["slow done"]


def test_a_failing_step_ends_only_its_macro(manager: MacroManager) -> None:
    ran: list[str] = []

    def boom() -> None:
        raise RuntimeError("step failed")

    bad = Macro()
    bad.add_action(boom)
    good = _macro(ran, "g")
    manager.run_macro(bad)
    manager.run_macro(good)
    assert _wait_for(lambda: ran == ["g"])
    assert _wait_for(lambda: bad.id not in manager._running_macros)
    manager.run_macro(good)
    assert _wait_for(lambda: ran == ["g", "g"])


def test_macro_not_changed_by_the_default_delay(manager: MacroManager) -> None:
    ran: list[str] = []
    macro = _macro(ran, "a", "b")
    manager.default_delay = 0.01
    manager.run_macro(macro)
    assert _wait_for(lambda: ran == ["a", "b"])
    assert len(macro.sequence) == 2  # pauses go into a copy
