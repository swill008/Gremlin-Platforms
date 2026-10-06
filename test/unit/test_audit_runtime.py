# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Runtime fixes from the code audit (AU-16, 17, 34, 35, 36, 37, 59)."""

from __future__ import annotations

import os
import sys
import threading
import time
import uuid
from pathlib import Path

sys.path.append(".")

import pytest

from gremlin.types import InputType

_GUID = uuid.UUID("55555555-6666-7777-8888-999999999999")


def test_one_failing_action_does_not_stop_the_others() -> None:
    from gremlin.event_handler import Event, EventHandler

    handler = EventHandler()
    event = Event(InputType.JoystickButton, 77, _GUID, "Default", is_pressed=True)
    ran: list[int] = []

    def fails(_event: Event) -> None:
        raise RuntimeError("an action failed")

    handler.add_callback(_GUID, "Default", event, fails)
    handler.add_callback(_GUID, "Default", event, lambda _e: ran.append(1))
    handler.process_callbacks = True
    try:
        handler.process_event(event)
    finally:
        handler.clear()
    assert ran == [1]


def _wait_for(check: object, seconds: float = 2.0) -> bool:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if check():  # type: ignore[operator]
            return True
        time.sleep(0.02)
    return False


def test_a_failing_macro_step_blocks_nothing() -> None:
    from gremlin.macro import Macro, MacroManager

    manager = MacroManager()
    manager.start()
    try:
        bad = Macro()
        bad.is_exclusive = True

        def fails() -> None:
            raise RuntimeError("a step failed")

        bad.add_action(fails)
        manager.queue_macro(bad)
        assert _wait_for(lambda: not manager._is_executing_exclusive)
        ran: list[int] = []
        good = Macro()
        good.add_action(lambda: ran.append(1))
        manager.queue_macro(good)
        assert _wait_for(lambda: ran == [1])
    finally:
        manager.stop()


def test_a_periodic_callback_with_no_interval_still_stops() -> None:
    from gremlin.user_script import PeriodicRegistry

    registry = PeriodicRegistry()
    calls: list[int] = []
    registry.add(lambda: calls.append(1), 0)
    registry.start()
    time.sleep(0.2)
    registry.stop()
    assert not registry._thread.is_alive()
    count = len(calls)
    time.sleep(0.1)
    assert len(calls) == count


def test_a_run_after_a_slow_stop_starts_its_own_loop() -> None:
    from gremlin.user_script import PeriodicRegistry

    registry = PeriodicRegistry()
    busy, release = threading.Event(), threading.Event()
    ran_on: list[threading.Thread] = []

    def slow() -> None:
        if not busy.is_set():  # the first call holds the old loop
            busy.set()
            release.wait(10)
        ran_on.append(threading.current_thread())

    registry.add(slow, 0.05)
    registry.start()
    first = registry._thread
    try:
        assert busy.wait(2)
        registry.stop()  # gives up waiting: the old loop is still in slow()
        assert first.is_alive()
        registry.start()
        second = registry._thread
        assert second is not first and second.is_alive()
        release.set()
        first.join(2)
        assert not first.is_alive()  # the old loop ended by itself
        assert _wait_for(lambda: second in ran_on)
        assert ran_on.count(first) == 1  # it ran nothing after the new Run
    finally:
        release.set()
        registry.stop()


def test_hat_conditions_have_their_own_directions() -> None:
    from action_plugins.condition.comparator import DirectionComparator

    one, two = DirectionComparator(), DirectionComparator()
    one.directions.append("north")
    assert two.directions == []


def test_a_broken_user_plugin_is_skipped(tmp_path: Path) -> None:
    from gremlin.plugin_manager import PluginManager

    plugin = tmp_path / "broken_plugin_audit"
    plugin.mkdir()
    (plugin / "__init__.py").write_text("raise ValueError('broken')\n")
    PluginManager()._discover_plugins(tmp_path, False)  # no error


def test_swap_devices_moves_references_both_ways() -> None:
    from gremlin import swap_devices
    from gremlin.profile import Profile

    a, b = uuid.uuid4(), uuid.uuid4()
    profile = Profile()
    seen: list[tuple] = []

    class Ref:
        def __init__(self, device: uuid.UUID) -> None:
            self.device = device

        def swap_uuid(self, old: uuid.UUID, new: uuid.UUID) -> bool:
            if self.device == old:
                self.device = new
                seen.append((old, new))
                return True
            return False

    on_a, on_b = Ref(a), Ref(b)
    profile.library.actions_by_predicate = lambda _p: [on_a, on_b]  # type: ignore[method-assign]
    empty = profile.get_input_item(a, InputType.JoystickButton, 1, "Default", True)
    swap_devices.swap_devices(profile, a, b)
    assert on_a.device == b and on_b.device == a
    assert empty.device_id == b


def test_the_program_path_is_read_in_full() -> None:
    from gremlin.process_monitor import ProcessMonitor

    monitor = ProcessMonitor()
    path = monitor._image_path(os.getpid())
    # This process's program (a virtual environment starts the real one).
    assert Path(path).is_file() and Path(path).name.lower().startswith("python")
    assert monitor._image_path(0) == ""


def test_a_pulse_on_the_main_thread_releases_later(
    qapp: object,
) -> None:
    from PySide6 import QtTest

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
    press = Event(InputType.JoystickButton, 1, _GUID, "Default", is_pressed=True)
    started = time.monotonic()
    functor._pulse_event([Record()], press, Value(True))
    assert time.monotonic() - started < 0.04  # the window isn't held
    assert states == [True]
    QtTest.QTest.qWait(150)
    assert states == [True, False]


@pytest.fixture
def qapp() -> object:
    from PySide6 import QtCore

    return QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
