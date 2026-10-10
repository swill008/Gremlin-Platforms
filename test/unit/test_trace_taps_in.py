# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Trace tab input taps (D-01-TRACE): RAW in the hardware listener, WIRING
at the claim gate and in EventHandler.process_event, EVENT lines for device
changes, Run start/stop and mode changes.

Driven through the real path: a fake dill.dll input event goes into
EventListener._joystick_event_handler, through the input-module gate
(InputModuleRuntime) and into EventHandler.process_event.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from PySide6 import QtCore

import dill
from gremlin import code_runner, event_handler, trace
from gremlin.modules import runtime
from test import fake_hardware

_APP = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
_STICK = dill.GUID(fake_hardware.raw_guid(is_virtual=False)).uuid

AXIS, BUTTON, HAT = 1, 2, 3


def _input(kind: int, index: int, value: int) -> dill._JoystickInputData:
    return dill._JoystickInputData(
        device_guid=fake_hardware.raw_guid(is_virtual=False),
        input_type=kind, input_index=index, value=value,
    )


def _points() -> list[tuple[str, str]]:
    """(point, detail) of every line but the Tracing on/off ones."""
    return [
        (line[2], line[3]) for line in trace.lines()
        if line[3] not in ("Tracing on", "Tracing off")
    ]


@pytest.fixture
def tracing() -> Iterator[None]:
    trace._reset_for_tests()
    trace.set_enabled(True)
    yield
    trace.set_enabled(False)
    trace.set_device(_STICK, False)
    trace._reset_for_tests()


@pytest.fixture
def listener() -> event_handler.EventListener:
    # The gate listens to the listener's signal, as in the program.
    runtime.InputModuleRuntime()
    return event_handler.EventListener()


def test_a_ticked_stick_gives_raw_lines(
    tracing: None, listener: event_handler.EventListener
) -> None:
    trace.set_device(_STICK, True)
    listener._joystick_event_handler(_input(BUTTON, 3, 1))
    listener._joystick_event_handler(_input(BUTTON, 3, 0))
    listener._joystick_event_handler(_input(AXIS, 1, 1000))
    raw = [detail for point, detail in _points() if point == trace.RAW]
    assert raw[:2] == ["pressed", "released"]
    assert any(detail.startswith("raw 1000") for detail in raw)


def test_an_unclaimed_ticked_input_is_traced_as_dropped(
    tracing: None, listener: event_handler.EventListener,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runtime, "should_forward", lambda *a, **k: False)
    trace.set_device(_STICK, True)
    listener._joystick_event_handler(_input(BUTTON, 5, 1))
    assert (trace.WIRING, "not claimed, dropped") in _points()


def test_a_claimed_input_traces_its_wiring_around_the_actions(
    tracing: None, listener: event_handler.EventListener,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runtime, "should_forward", lambda *a, **k: True)
    trace.set_device(_STICK, True)
    handler = event_handler.EventHandler()
    seen: list[object] = []
    key = event_handler.Event(event_handler.InputType.JoystickButton, 6, _STICK,
                              "Default", is_pressed=True)
    monkeypatch.setattr(handler, "callbacks", {
        _STICK: {"Default": {key: [lambda e: seen.append(trace.current_input())]}}
    })
    monkeypatch.setattr(handler, "process_callbacks", True)
    bus = runtime.InputModuleRuntime()
    bus.event.connect(handler.process_event, QtCore.Qt.ConnectionType.DirectConnection)
    try:
        monkeypatch.setattr(
            event_handler.mode_manager.ModeManager(), "_mode_stack",
            [event_handler.mode_manager.Mode("Default", None)],
        )
        listener._joystick_event_handler(_input(BUTTON, 6, 1))
        listener._joystick_event_handler(_input(BUTTON, 7, 1))
    finally:
        bus.event.disconnect(handler.process_event)
    wiring = [detail for point, detail in _points() if point == trace.WIRING]
    assert "claimed · mode Default · ran script" in wiring
    assert "claimed · mode Default · no actions" in wiring
    # Outputs written by the action belong to this input; none after it.
    assert seen == [(_STICK, "button", 6)]
    assert trace.current_input() is None


def test_an_unticked_stick_gives_no_lines(
    tracing: None, listener: event_handler.EventListener
) -> None:
    listener._joystick_event_handler(_input(BUTTON, 3, 1))
    listener._joystick_event_handler(_input(AXIS, 1, 1000))
    assert _points() == []


def test_tracing_off_asks_nothing_per_input(
    listener: event_handler.EventListener, monkeypatch: pytest.MonkeyPatch
) -> None:
    trace._reset_for_tests()
    asked: list[tuple] = []
    monkeypatch.setattr(trace, "ticked", lambda *a: asked.append(a) or True)
    listener._joystick_event_handler(_input(BUTTON, 3, 1))
    listener._joystick_event_handler(_input(AXIS, 1, 1000))
    handler = event_handler.EventHandler()
    handler.process_event(event_handler.Event(
        event_handler.InputType.JoystickButton, 3, _STICK, "Default", is_pressed=True))
    assert asked == [] and trace.lines() == []


def test_device_change_and_run_events(
    tracing: None, listener: event_handler.EventListener,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(listener, "_device_update_timer", None)
    monkeypatch.setattr(event_handler.threads, "timer", lambda *a: None)
    listener._joystick_device_handler(fake_hardware.raw_device(is_virtual=False), 2)
    runner = object.__new__(code_runner.CodeRunner)
    runner._running = True
    runner._restarting = False
    monkeypatch.setattr(code_runner.Configuration, "value", lambda *a: False)
    runner._refresh_on_mode_change("Combat")
    monkeypatch.setattr(code_runner.run_scope, "stop", lambda: None)
    runner.stop()
    runner.stop()  # not running: nothing more
    events = [detail for point, detail in _points() if point == trace.EVENT]
    assert events == ["pJoy Pro unplugged", "Mode changed to Combat", "Profile stopped"]
