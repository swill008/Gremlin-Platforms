# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Actions that misbehaved (3 Oct review, ACT3, ACT4, ACT6, ACT10, ACT17,
ACT19, ACT20, ACT21).

- Cycle went from its own counter: the first press did nothing and copies in
  different modes cycled separately; it now goes to the mode after the
  current one (ACT3).
- Split Axis left the half it crossed out of at its last value (ACT4).
- Chain held past its timeout reset to step 0 before the release, so the
  pressed step stayed down (ACT6).
- While paused, a user-script callback (a plain function) raised before
  anything ran, Resume included (ACT10).
- A Hold release that came before the macro thread started was lost, the
  stop request stayed queued, and stale macros ran on the next Run (ACT17).
- Loading a profile shuffled sys.path (ACT19).
- Tempo, Double Tap and Smart Toggle ran their timeouts on a timer thread
  (ACT20).
- A Run that failed after connecting left the signals connected, so the next
  Run handled every event twice (ACT21).

The macro and timer tests wait for the macro threads or for a later timer,
not a fixed time (GL-001, AU-119).
"""

from __future__ import annotations

import sys

sys.path.append(".")

import threading
import time
from collections.abc import Callable, Iterator
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest import mock

import pytest
from PySide6 import QtCore

from gremlin import threads

if TYPE_CHECKING:
    from gremlin.macro import MacroManager


@pytest.fixture(autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    yield QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])


# ACT3 ---------------------------------------------------------------------


def test_cycle_goes_to_the_mode_after_the_current_one() -> None:
    from gremlin.mode_manager import ModeSequence

    sequence = ModeSequence(["A", "B", "C"])
    assert sequence.next("A") == "B"  # the first press moves on
    assert sequence.next("C") == "A"  # wraps around
    assert sequence.next("Elsewhere") == "A"  # not in the list: the first
    # A second copy of the action (in another mode) agrees with the first.
    assert ModeSequence(["A", "B", "C"]).next("B") == "C"


def test_cycle_without_a_current_mode_keeps_its_own_counter() -> None:
    from gremlin.mode_manager import ModeSequence

    sequence = ModeSequence(["A", "B"])  # as user scripts call it
    assert [sequence.next(), sequence.next(), sequence.next()] == ["A", "B", "A"]


# ACT4 ---------------------------------------------------------------------


def test_split_axis_puts_the_half_it_leaves_at_rest() -> None:
    from action_plugins.split_axis import SplitAxisFunctor

    functor = object.__new__(SplitAxisFunctor)
    functor.data = SimpleNamespace(split_value=0.0)
    functor._side = None
    sent = []
    functor.functors = {
        side: [lambda e, v, p, side=side: sent.append((side, round(v.current, 3)))]
        for side in ("lower", "upper")
    }
    functor(None, SimpleNamespace(current=-0.98), [])  # brake almost full on
    sent.clear()
    functor(None, SimpleNamespace(current=1.0), [])  # straight to full throttle
    assert sent == [("lower", -1.0), ("upper", 1.0)]  # the brake goes to rest


# ACT6 ---------------------------------------------------------------------


def test_chain_held_past_the_timeout_releases_the_pressed_step() -> None:
    from action_plugins import chain

    functor = object.__new__(chain.ChainFunctor)
    functor.data = SimpleNamespace(chain_sequences=[[], []], timeout=1.0)
    calls = []
    functor.functors = {
        str(i): [lambda e, v, p, i=i: calls.append((i, v.current))] for i in range(2)
    }
    functor.current_index = 0
    functor.last_execution = 0.0
    functor._pressed_index = None
    now = [100.0]
    with mock.patch.object(chain.clock, "monotonic", lambda: now[0]):
        functor(None, SimpleNamespace(current=True), [])
        functor(None, SimpleNamespace(current=False), [])  # step 0 done
        now[0] += 0.5
        functor(None, SimpleNamespace(current=True), [])  # step 1 pressed
        now[0] += 5.0  # held past the timeout
        functor(None, SimpleNamespace(current=False), [])
    assert calls == [(0, True), (0, False), (1, True), (1, False)]  # 1 released


# ACT10 --------------------------------------------------------------------


class _Event:
    """Just enough of an event to look callbacks up by."""

    device_guid = "dev"
    mode = "Default"


def test_while_paused_a_script_callback_does_not_stop_the_rest() -> None:
    from gremlin.event_handler import EventHandler

    def script_callback(event: object) -> None:  # a plain function
        pass

    resume = SimpleNamespace(always_execute=True)
    event = _Event()
    handler = SimpleNamespace(
        process_callbacks=False,  # paused
        callbacks={"dev": {"Default": {event: [script_callback, resume]}}},
    )
    assert EventHandler.klass._matching_callbacks(handler, event) == [resume]


# ACT17 --------------------------------------------------------------------


@pytest.fixture
def macros(monkeypatch: pytest.MonkeyPatch) -> Iterator[object]:
    from gremlin.macro import MacroManager

    monkeypatch.setattr(threads, "_live", {})
    manager = MacroManager()
    monkeypatch.setattr(manager, "default_delay", 0.0)
    manager.start()
    yield manager
    manager.stop()
    assert threads.shutdown(timeout=2.0) == []


def _hold_macro(runs: list) -> object:
    from gremlin.macro import HoldRepeat, Macro

    macro = Macro()
    macro.repeat = HoldRepeat()
    macro.repeat.delay = 0.01
    macro.add_action(lambda: (runs.append(1), time.sleep(0.01)))
    return macro


_LIMIT_S = 10.0  # generous: a busy PC is slow, never wrong


def _wait_for(check: Callable[[], bool]) -> bool:
    end = time.monotonic() + _LIMIT_S
    while not check():
        if time.monotonic() > end:
            return False
        time.sleep(0.01)
    return True


def _no_macro_running() -> bool:
    return threads.PREFIX + "macro" not in threads.running()


def _run_one_macro(macros: "MacroManager") -> None:
    """Queues a one-step macro and waits until it ran (wakes the scheduler)."""
    from gremlin.macro import Macro

    woken: list = []
    other = Macro()
    other.add_action(lambda: woken.append(1))
    macros.queue_macro(other)
    assert _wait_for(lambda: bool(woken) and _no_macro_running())


def test_a_hold_macro_released_at_once_stops(macros: "MacroManager") -> None:
    runs: list = []
    macro = _hold_macro(runs)
    macros.queue_macro(macro)
    macros.terminate_macro(macro)  # released before its thread started
    # Handled, and it stopped (it used to keep running).
    assert _wait_for(lambda: macros._queued_macros == [] and _no_macro_running())
    count = len(runs)
    _run_one_macro(macros)  # the scheduler runs again: it doesn't come back
    assert len(runs) == count
    assert macros._queued_macros == []  # the stop request went too


def test_run_starts_with_no_stale_macros(macros: "MacroManager") -> None:
    from gremlin.macro import MacroEntry

    stale_runs: list = []
    stale = _hold_macro(stale_runs)
    with macros._queued_macros_lock:  # left queued when the profile stopped
        macros._queued_macros.append(MacroEntry(stale, True))
    macros.stop()
    macros.start()
    _run_one_macro(macros)  # wakes the scheduler; a stale one would run too
    assert stale_runs == []  # the stale one didn't run
    macros.terminate_macro(stale)


# ACT19 --------------------------------------------------------------------


def test_loading_a_profile_keeps_the_search_path_in_order(
    monkeypatch: pytest.MonkeyPatch, tmp_path: object
) -> None:
    from gremlin.ui import backend

    order = ["z_first", "a_second", "m_third"]
    monkeypatch.setattr(sys, "path", list(order))
    model = SimpleNamespace(profile=None)
    fake_profile = mock.MagicMock()
    fake_profile.from_xml.return_value = False
    with (
        mock.patch.object(backend.profile, "Profile", return_value=fake_profile),
        mock.patch.object(backend, "LogicalDevice"),
    ):
        backend.Backend.klass._read_profile(model, str(tmp_path) + "/folder/p.xml")
    assert sys.path == [str(tmp_path) + "/folder", *order]


# ACT20 --------------------------------------------------------------------


def _run_events_until(check: Callable[[], bool]) -> bool:
    return _wait_for(lambda: QtCore.QCoreApplication.processEvents() or check())


def test_action_timeouts_run_on_the_main_thread() -> None:
    ran_on = []
    t = threads.main_timer(
        "test", 0.01, lambda: ran_on.append(threading.current_thread())
    )
    assert t.is_alive()
    assert _run_events_until(lambda: bool(ran_on))
    assert ran_on == [threading.main_thread()]
    cancelled = []
    t = threads.main_timer("test", 0.01, lambda: cancelled.append(1))
    t.cancel()
    later: list = []  # a later timer: the cancelled one would have run first
    QtCore.QTimer.singleShot(50, lambda: later.append(1))
    assert _run_events_until(lambda: bool(later))
    assert cancelled == [] and not t.is_alive()


# ACT21 --------------------------------------------------------------------


def test_stop_disconnects_after_a_failed_run() -> None:
    from gremlin import code_runner

    disconnected = []

    def signal() -> SimpleNamespace:
        return SimpleNamespace(disconnect=lambda f: disconnected.append(f))

    listener = SimpleNamespace(virtual_event=signal(), gremlin_active=True)
    bus = SimpleNamespace(event=signal(), key_event=signal())
    runner = SimpleNamespace(
        _connected=True,  # start() connected, then failed before running
        _running=False,
        _listen_to_mode_changes=lambda on: None,
        _listen_to_pause=lambda on: None,
        _listen_to_config=lambda on: None,
        event_handler=SimpleNamespace(process_event="handler", clear=lambda: None),
    )
    # Stop's first stage (run_scope CUT_INPUT) is the runner's _cut_input;
    # the other stages stop the program's subsystems.
    others = ["shared_state"]
    with (
        mock.patch.object(
            code_runner.event_handler, "EventListener", return_value=listener
        ),
        mock.patch.object(code_runner, "InputModuleRuntime", return_value=bus),
        mock.patch.multiple(code_runner, **{name: mock.DEFAULT for name in others}),
    ):
        code_runner.CodeRunner._cut_input(runner)
    assert disconnected == ["handler"] * 3
    assert runner._connected is False and listener.gremlin_active is False
