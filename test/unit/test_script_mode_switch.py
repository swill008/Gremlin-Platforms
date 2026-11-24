# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Scripts change the mode: user_script.switch_mode, previous_mode and
cycle_modes do what the Change Mode action's Switch, Previous and Cycle do,
on the input thread, without waiting.

Spec: 04 S99, D-04-SCRIPT-MODE.
"""

from __future__ import annotations

import logging
import sys
import threading
from collections.abc import Iterator

sys.path.append(".")

import pytest

from gremlin import input_thread, log_once, mode_manager, shared_state, threads
from gremlin import user_script as us
from gremlin.profile import Profile


@pytest.fixture
def modes() -> Iterator[None]:
    """An open profile with modes Default, Second and Third; the stack starts
    at Default and is put back afterwards."""
    previous = shared_state.current_profile
    shared_state.current_profile = profile = Profile()
    profile.modes.add_mode("Second")
    profile.modes.add_mode("Third")
    mm = mode_manager.ModeManager()
    stack = list(mm._mode_stack)  # noqa: SLF001 - one per process
    mm._mode_stack = [mode_manager.Mode("Default", None)]  # noqa: SLF001
    yield
    mm._mode_stack = stack  # noqa: SLF001
    shared_state.current_profile = previous


def test_switch_mode_changes_the_mode(modes: None) -> None:
    manager = mode_manager.ModeManager()
    us.switch_mode("Second")
    assert manager.current.name == "Second"
    assert manager.current.previous == "Default"


def test_previous_mode_swaps_back_like_the_action(
    modes: None,
) -> None:
    manager = mode_manager.ModeManager()
    us.switch_mode("Second")
    us.previous_mode()
    assert manager.current.name == "Default"
    us.previous_mode()
    assert manager.current.name == "Second"


def test_cycle_modes_goes_to_the_next_one_like_the_action(
    modes: None,
) -> None:
    manager = mode_manager.ModeManager()
    us.cycle_modes(["Default", "Second", "Third"])
    assert manager.current.name == "Second"
    us.cycle_modes(["Default", "Second", "Third"])
    assert manager.current.name == "Third"
    us.cycle_modes(["Default", "Second", "Third"])
    assert manager.current.name == "Default"
    # The current mode not in the list: the first one.
    us.cycle_modes(["Third", "Second"])
    assert manager.current.name == "Third"


def test_an_unknown_mode_leaves_the_mode_and_logs(
    modes: None, caplog: pytest.LogCaptureFixture
) -> None:
    manager = mode_manager.ModeManager()
    log_once.reset()  # the warning is logged once per mode name
    with caplog.at_level(logging.WARNING, logger="system"):
        us.switch_mode("No such mode")
    assert manager.current.name == "Default"
    assert "No such mode" in caplog.text


def test_from_a_timer_thread_the_change_runs_on_the_input_thread_without_waiting(
    modes: None,
    input_thread_running: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A periodic callback runs off the input thread: the switch is queued
    there and the call returns while the input thread is still busy."""
    manager = mode_manager.ModeManager()
    seen: list[bool] = []
    real_switch = manager.switch_to

    def switch_to(mode: mode_manager.Mode) -> None:
        seen.append(input_thread.is_input_thread())
        real_switch(mode)

    monkeypatch.setattr(manager, "switch_to", switch_to)
    # Keep the input thread busy, so a call that waited would not return.
    busy, release = threading.Event(), threading.Event()
    input_thread.call(lambda: (busy.set(), release.wait(5.0)))
    assert busy.wait(2.0)
    returned = threading.Event()

    def timer_callback() -> None:
        us.switch_mode("Second")
        returned.set()

    worker = threads.start("test-script-timer", timer_callback)
    try:
        assert returned.wait(2.0), "switch_mode waited for the input thread"
        assert seen == []  # not run yet: queued behind the busy call
    finally:
        release.set()
    worker.join(2.0)
    done = threading.Event()
    input_thread.call(done.set)  # after the queued switch
    assert done.wait(2.0)
    assert seen == [True]
    assert manager.current.name == "Second"


def test_from_the_input_thread_the_change_is_made_at_once(
    modes: None, input_thread_running: None
) -> None:
    """A button callback runs on the input thread: the mode has changed when
    switch_mode returns, as with the Change Mode action."""
    manager = mode_manager.ModeManager()
    after: list[str] = []
    done = threading.Event()

    def callback() -> None:
        us.switch_mode("Second")
        after.append(manager.current.name)
        done.set()

    input_thread.call(callback)
    assert done.wait(2.0)
    assert after == ["Second"]
