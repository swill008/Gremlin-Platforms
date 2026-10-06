# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Macros stop with Stop; a pulse release waiting at Stop goes out first
(audit 2, group D)."""

from __future__ import annotations

import sys
import time
import uuid
from collections.abc import Callable, Iterator

sys.path.append(".")

import pytest
from PySide6 import QtCore

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


def _wait_for(check: Callable[[], bool], seconds: float = 2.0) -> bool:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if check():
            return True
        time.sleep(0.02)
    return False


def test_a_one_shot_macro_stops_with_stop(manager: MacroManager) -> None:
    ran: list[str] = []
    macro = Macro()
    macro.add_action(lambda: ran.append("a"))
    macro.add_action(PauseAction(1.0))
    macro.add_action(lambda: ran.append("b"))
    manager.queue_macro(macro)
    assert _wait_for(lambda: ran == ["a"])
    manager.stop()
    time.sleep(1.3)  # past the Pause
    assert ran == ["a"]  # b used to run after Stop


def test_a_macro_paused_behind_a_preempting_one_stops(manager: MacroManager) -> None:
    ran: list[str] = []
    long = Macro()
    long.is_exclusive = True
    long.is_preempting = True
    long.add_action(PauseAction(1.0))
    normal = Macro()
    normal.add_action(lambda: ran.append("n1"))
    normal.add_action(lambda: ran.append("n2"))
    manager._is_executing_preemptive = True  # as while `long` runs
    manager.queue_macro(normal)
    time.sleep(0.2)
    manager.stop()
    time.sleep(0.6)
    assert ran == []
    del long


def test_a_macro_of_the_last_run_leaves_the_new_run_alone(
    manager: MacroManager,
) -> None:
    old = Macro()
    old.is_exclusive = True
    old.add_action(PauseAction(0.3))
    manager.queue_macro(old)
    assert _wait_for(lambda: manager._is_executing_exclusive)
    manager.stop()
    manager.start()
    manager._is_executing_exclusive = True  # the new Run's exclusive macro
    manager._finish_macro(old, manager._run - 1)  # the old one ends late
    assert manager._is_executing_exclusive


def test_a_pulse_release_waiting_at_stop_is_sent_first() -> None:
    from gremlin import base_classes
    from gremlin.base_classes import AbstractFunctor, Value
    from gremlin.event_handler import Event

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
    QtCore.QCoreApplication.processEvents()
    time.sleep(0.1)
    QtCore.QCoreApplication.processEvents()
    assert states == [True, False]  # not sent twice
