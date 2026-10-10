# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Background loops wait with a timeout and re-check their stop flag; timed
code uses gremlin.clock (AUD-THREADS-02..05, -10)."""

from __future__ import annotations

import inspect
import threading
import uuid
from collections.abc import Callable
from types import SimpleNamespace

import pytest

from gremlin import clock, code_runner, device_helpers, event_handler, macro
from gremlin.types import InputType


class _RecordingEvent:
    """Stands in for threading.Event: records each wait's timeout; after
    `stop_after` waits it runs `on_stop` so the loop under test ends."""

    def __init__(self, stop_after: int, on_stop: Callable[[], None]) -> None:
        self.timeouts: list[float | None] = []
        self._stop_after = stop_after
        self._on_stop = on_stop

    def wait(self, timeout: float | None = None) -> bool:
        self.timeouts.append(timeout)
        if len(self.timeouts) >= self._stop_after:
            self._on_stop()
        return False

    def clear(self) -> None:
        pass

    def set(self) -> None:
        pass


class _NoDill:
    def set_device_change_callback(self, _cb: object) -> None:
        pass

    def set_input_event_callback(self, _cb: object) -> None:
        pass


_LISTENER = event_handler.EventListener.klass


def _bare_listener(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """Stands in for an EventListener (a QObject singleton): the methods under
    test are called unbound on it."""
    monkeypatch.setattr(event_handler.dill, "DILL", _NoDill())
    listener = SimpleNamespace(_running=True)
    listener._joystick_device_handler = None
    listener._joystick_event_handler = None
    return listener


def test_event_listener_waits_with_a_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    listener = _bare_listener(monkeypatch)
    listener._stop_event = _RecordingEvent(
        3, lambda: setattr(listener, "_running", False)
    )
    listener._generation = 0
    _LISTENER._run(listener, 0)
    assert listener._stop_event.timeouts
    assert all(t is not None and t > 0 for t in listener._stop_event.timeouts)


def test_restart_retires_the_old_listener_thread(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A listener thread from before restart() ends instead of looping on
    beside the new one."""
    listener = _bare_listener(monkeypatch)
    listener._running = False
    listener._generation = 0
    listener._stop_event = threading.Event()
    started: list[int] = []
    listener._start_thread = lambda: started.append(listener._generation)

    class _Hook:
        def start(self) -> None:
            pass

    listener.keyboard_hook = _Hook()
    _LISTENER.restart(listener)
    assert started == [1]
    # The old thread (generation 0) wakes after the restart: it must end
    # without waiting again.
    listener._stop_event = _RecordingEvent(
        3, lambda: setattr(listener, "_running", False)
    )
    _LISTENER._run(listener, 0)
    assert listener._stop_event.timeouts == []


def test_macro_scheduler_waits_with_a_timeout() -> None:
    manager = object.__new__(macro.MacroManager)
    manager._is_running = True
    manager._queued_macros = []
    manager._queued_macros_lock = threading.Lock()
    manager._executing_macro = {}
    manager._executing_macro_lock = threading.Lock()
    manager._schedule_event = _RecordingEvent(
        3, lambda: setattr(manager, "_is_running", False)
    )
    manager._run_scheduler()
    assert manager._schedule_event.timeouts
    assert all(t is not None and t > 0 for t in manager._schedule_event.timeouts)


def test_callback_has_no_sleep_on_the_event_thread() -> None:
    source = inspect.getsource(code_runner.CallbackObject.__call__)
    assert "sleep" not in source


def _axis_event(value: float) -> event_handler.Event:
    return event_handler.Event(
        InputType.JoystickAxis,
        1,
        uuid.UUID(int=7),
        "Default",
        value=value,
    )


def test_axis_significance_uses_the_program_clock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The 5 s 'no recent data' reset follows gremlin.clock, so tests can
    step it."""
    now = [1000.0]
    monkeypatch.setattr(clock, "monotonic", lambda: now[0])
    significant = object.__new__(device_helpers.JoystickInputSignificant)
    significant.reset()
    assert significant.should_process(_axis_event(0.0)) is False
    now[0] += 10.0
    # A big move after 10 s without data resets instead of counting.
    assert significant.should_process(_axis_event(0.5)) is False
    now[0] += 1.0
    assert significant.should_process(_axis_event(-0.5)) is True


def test_axis_change_tracker_uses_the_program_clock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = [50.0]
    monkeypatch.setattr(clock, "monotonic", lambda: now[0])
    tracker = device_helpers.AxisChangeSignificanceTracker(0.2, 0.1, 1.0, False)
    assert tracker.is_significant_change(0.5) is False
    now[0] += 2.0
    assert tracker.is_significant_change(0.5) is True
