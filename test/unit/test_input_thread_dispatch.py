# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Dispatch on the input thread (contract-THR.md, thread-input.md batch 2):
an event the listener emits on a driver thread reaches the claim gate and
EventHandler on the input thread, and an event re-emitted from inside an
action (Map to Logical Device) is still handled at once, inside it.

Every wait has a limit.
"""

from __future__ import annotations

import threading
import time
import uuid
from collections.abc import Callable, Iterator

import pytest
from PySide6 import QtCore

from gremlin import clock, code_runner, event_handler, input_thread, mode_manager
from gremlin.event_handler import Event, EventHandler, EventListener
from gremlin.modules import runtime
from gremlin.types import InputType

_STICK = uuid.UUID("77777777-5555-2222-3333-444444444002")
_LIMIT = 3.0


def _pump(until: Callable[[], bool], limit: float = _LIMIT) -> bool:
    end = clock.monotonic() + limit
    while clock.monotonic() < end:
        QtCore.QCoreApplication.processEvents()
        if until():
            return True
        time.sleep(0.005)
    QtCore.QCoreApplication.processEvents()
    return until()


def _press(button: int, mode: str) -> Event:
    return Event(InputType.JoystickButton, button, _STICK, mode, is_pressed=True)


@pytest.fixture
def wired(
    input_thread_running: None, monkeypatch: pytest.MonkeyPatch
) -> Iterator[str]:
    """The runtime adopted by the input thread, the claim gate open, and
    the input modules' bus connected to EventHandler as a Run connects it
    (on the input thread)."""
    monkeypatch.setattr(runtime, "should_forward", lambda *a, **k: True)
    code_runner.adopt_runtime_objects()
    handler = EventHandler()
    bus = runtime.InputModuleRuntime()
    mode = mode_manager.ModeManager().current.name
    saved = (handler.callbacks, handler.process_callbacks)

    def connect() -> None:
        bus.event.connect(handler.process_event)
        handler.process_callbacks = True

    input_thread.call_wait(connect, timeout=_LIMIT)
    try:
        yield mode
    finally:

        def undo() -> None:
            bus.event.disconnect(handler.process_event)
            handler.callbacks, handler.process_callbacks = saved

        try:
            input_thread.call_wait(undo, timeout=_LIMIT)
        finally:
            code_runner.release_runtime_objects()


def _install(callbacks: dict[Event, list[Callable[[Event], None]]]) -> None:
    handler = EventHandler()

    def put() -> None:
        by_mode: dict[str, dict[Event, list[Callable[[Event], None]]]] = {}
        for event, cbs in callbacks.items():
            by_mode.setdefault(event.mode, {})[event] = cbs
        handler.callbacks = {_STICK: by_mode}

    input_thread.call_wait(put, timeout=_LIMIT)


def test_listener_event_reaches_event_handler_on_input_thread(wired: str) -> None:
    seen: list[bool] = []
    def record(_event: Event) -> None:
        seen.append(input_thread.is_input_thread())

    _install({_press(3, wired): [record]})

    # The driver's callback thread emits, as dill does.
    driver = threading.Thread(
        target=lambda: EventListener().joystick_event.emit(_press(3, wired)),
        name="test-driver",
    )
    driver.start()
    driver.join(_LIMIT)
    assert _pump(lambda: bool(seen)), "the event never reached EventHandler"
    assert seen == [True], "EventHandler ran off the input thread"


def test_logical_device_reentry_is_synchronous(wired: str) -> None:
    order: list[str] = []

    def map_to_logical(_event: Event) -> None:
        # Map to Logical Device re-emits on the listener from its action.
        EventListener().joystick_event.emit(_press(9, wired))
        order.append("after re-emit")

    def logical_input(_event: Event) -> None:
        order.append(f"logical on input thread={input_thread.is_input_thread()}")

    _install({_press(4, wired): [map_to_logical], _press(9, wired): [logical_input]})
    input_thread.call(EventListener().joystick_event.emit, _press(4, wired))
    assert _pump(lambda: len(order) == 2), f"only {order}"
    assert order == ["logical on input thread=True", "after re-emit"]


def test_inline_mode_keeps_dispatch_on_the_callers_thread(
    monkeypatch: pytest.MonkeyPatch, qapp: object
) -> None:
    """Inline (the other tests): nothing moves, dispatch is direct as before."""
    assert input_thread.is_inline()
    monkeypatch.setattr(runtime, "should_forward", lambda *a, **k: True)
    code_runner.adopt_runtime_objects()  # does nothing inline
    handler = EventHandler()
    bus = runtime.InputModuleRuntime()
    app = QtCore.QCoreApplication.instance()
    assert app is not None and handler.thread() == app.thread()
    mode = mode_manager.ModeManager().current.name
    seen: list[str] = []
    saved = handler.callbacks
    handler.callbacks = {_STICK: {mode: {_press(5, mode): [lambda _e: seen.append(
        threading.current_thread().name)]}}}
    bus.event.connect(handler.process_event)
    try:
        event_handler.EventListener().joystick_event.emit(_press(5, mode))
        assert seen == [threading.current_thread().name]
    finally:
        bus.event.disconnect(handler.process_event)
        handler.callbacks = saved
