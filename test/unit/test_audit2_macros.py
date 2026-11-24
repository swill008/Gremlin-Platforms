# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Macros stop with Stop; a pulse release waiting at Stop goes out first
(audit 2, group D).

The tests wait for the macro threads to end, or for a later timer, instead
of fixed sleeps (GL-001, AU-119).
"""

from __future__ import annotations

import sys
import threading
import time
import uuid
from collections.abc import Callable, Iterator

sys.path.append(".")

import pytest
from PySide6 import QtCore

from gremlin import threads
from gremlin.macro import Macro, MacroManager, PauseAction
from gremlin.types import InputType

_APPS: list[QtCore.QCoreApplication] = []


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


@pytest.fixture
def manager() -> Iterator[MacroManager]:
    mm = MacroManager()
    mm.start()
    yield mm
    mm.stop()


def _wait_for(check: Callable[[], bool], seconds: float = 10.0) -> bool:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if check():
            return True
        time.sleep(0.02)
    return False


def _macro_threads() -> set[threading.Thread]:
    """Macro threads running now (not the scheduler)."""
    name = threads.PREFIX + "macro"
    return {t for t in threading.enumerate() if t.name == name}


def test_a_one_shot_macro_stops_with_stop(manager: MacroManager) -> None:
    ran: list[str] = []
    macro = Macro()
    macro.add_action(lambda: ran.append("a"))
    macro.add_action(PauseAction(1.0))
    macro.add_action(lambda: ran.append("b"))
    before = _macro_threads()
    manager.run_macro(macro)
    assert _wait_for(lambda: ran == ["a"])
    manager.stop()
    assert _wait_for(lambda: not _macro_threads() - before)  # its Pause ended
    assert ran == ["a"]  # b used to run after Stop


def test_a_macro_paused_behind_a_preempting_one_stops(
    manager: MacroManager,
) -> None:
    ran: list[str] = []
    long = Macro()
    long.is_exclusive = True
    long.is_preempting = True
    long.add_action(PauseAction(1.0))
    preempted = threading.Event()
    normal = Macro()
    # Its first step lasts until `long` runs; the next one waits behind it.
    normal.add_action(lambda: (ran.append("n1"), preempted.wait(5.0)))
    normal.add_action(lambda: ran.append("n2"))
    before = _macro_threads()
    manager.run_macro(normal)
    assert _wait_for(lambda: ran == ["n1"])
    manager.run_macro(long)
    assert long.id in manager._running_macros
    preempted.set()
    assert _wait_for(lambda: len(_macro_threads() - before) == 2)
    manager.stop()
    assert _wait_for(lambda: not _macro_threads() - before)
    assert ran == ["n1"]  # n2 never ran


def test_a_macro_of_the_last_run_leaves_the_new_run_alone(
    manager: MacroManager,
) -> None:
    old = Macro()
    old.is_exclusive = True
    old.add_action(PauseAction(1.0))
    before = _macro_threads()
    manager.run_macro(old)
    assert _wait_for(lambda: len(_macro_threads() - before) == 1)
    first = _macro_threads() - before
    manager.stop()
    manager.start()
    manager.run_macro(old)  # the new Run plays the same exclusive macro
    new_execution = manager._running_macros[old.id]
    # The old run's thread ends late; it leaves the new Run's run alone.
    assert _wait_for(lambda: not first & _macro_threads())
    assert manager._running_macros.get(old.id) is new_execution
    ran: list[str] = []
    other = Macro()
    other.add_action(lambda: ran.append("x"))
    manager.run_macro(other)  # still waits behind the exclusive macro
    assert ran == []
    assert [e.macro for e in manager._waiting_macros] == [other]


def test_a_pulse_release_waiting_at_stop_is_sent_first() -> None:
    from gremlin import base_classes
    from gremlin.base_classes import AbstractFunctor, Value
    from gremlin.types import Event

    states: list[bool] = []

    class Record:
        def __call__(self, event: Event, value: Value, properties: list) -> None:
            states.append(bool(event.is_pressed))

    class Pulse(AbstractFunctor):
        def __call__(self, *args: object) -> None:
            pass

    functor = Pulse.__new__(Pulse)
    press = Event(InputType.JoystickButton, 1, uuid.uuid4(), "Default", is_pressed=True)
    functor._pulse_event([Record()], press, Value(True))
    assert states == [True]
    base_classes.flush_pulses()  # Stop
    assert states == [True, False]
    # The pulse's own 50 ms timer runs before a later one.
    later: list[bool] = []
    QtCore.QTimer.singleShot(100, lambda: later.append(True))
    assert _wait_for(lambda: QtCore.QCoreApplication.processEvents() or bool(later))
    assert states == [True, False]  # not sent twice
