# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Timing probes (S179) on the real path: a fake dill input event goes into
EventListener._joystick_event_handler, through the input-module gate
(InputModuleRuntime._on_hid) into EventHandler.process_event and a vJoy write
(vJoy faked). An injected counter gives exact hop values; with Timing off the
counter is never called.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from PySide6 import QtCore

import dill
from gremlin import event_handler, trace, trace_timing
from gremlin.modules import output, runtime
from gremlin.types import Event
from test import fake_hardware

_APP = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
_STICK = dill.GUID(fake_hardware.raw_guid(is_virtual=False)).uuid
BUTTON = 2


def _input() -> dill._JoystickInputData:
    return dill._JoystickInputData(
        device_guid=fake_hardware.raw_guid(is_virtual=False),
        input_type=BUTTON, input_index=6, value=1,
    )


@pytest.fixture
def path(monkeypatch: pytest.MonkeyPatch) -> Iterator[event_handler.EventListener]:
    trace._reset_for_tests()
    trace_timing._reset()
    monkeypatch.setattr(trace_timing, "_arm", lambda: None)
    monkeypatch.setattr(runtime, "should_forward", lambda *a, **k: True)
    monkeypatch.setattr(output, "_write_vjoy", lambda *a, **k: "written")
    bus = runtime.InputModuleRuntime()
    listener = event_handler.EventListener()
    handler = event_handler.EventHandler()
    key = Event(event_handler.InputType.JoystickButton, 6, _STICK,
                              "Default", is_pressed=True)
    monkeypatch.setattr(handler, "callbacks", {
        _STICK: {"Default": {key: [lambda e: output.write_vjoy(1, "button", 1, True)]}}
    })
    monkeypatch.setattr(handler, "process_callbacks", True)
    monkeypatch.setattr(
        event_handler.mode_manager.ModeManager(), "_mode_stack",
        [event_handler.mode_manager.Mode("Default", None)],
    )
    bus.event.connect(handler.process_event, QtCore.Qt.ConnectionType.DirectConnection)
    yield listener
    bus.event.disconnect(handler.process_event)
    trace.set_timing(False)
    trace.set_enabled(False)
    trace._reset_for_tests()
    trace_timing._reset()


def _timing_lines() -> list[str]:
    return [line[3] for line in trace.lines() if line[2] == trace.TIMING]


def test_one_event_is_counted_with_the_hop_values(
    path: event_handler.EventListener, monkeypatch: pytest.MonkeyPatch
) -> None:
    # t0, t1, t2 (dispatch), t3 (wiring), t5 (output write), t4 (actions done).
    stamps = iter([0, 100_000, 1_100_000, 1_400_000, 2_000_000, 2_400_000])
    last = [2_400_000]

    def counter() -> int:
        last[0] = next(stamps, last[0])
        return last[0]

    monkeypatch.setattr(trace_timing, "counter", counter)
    trace.set_enabled(True)
    trace.set_timing(True)
    assert trace_timing.on
    path._joystick_event_handler(_input())
    trace_timing.flush()
    lines = _timing_lines()
    assert len(lines) == 1
    text = lines[0]
    assert "1 events (1 devices)" in text
    assert "driver to emit median 0.10 ms" in text
    assert "waited behind earlier events median 0.00 ms" in text
    assert "hand-over median 1.00 ms" in text
    assert "gate to wiring median 0.30 ms" in text
    assert "actions median 1.00 ms" in text
    assert "end to end median 2.00 ms" in text


def test_off_never_calls_the_counter(
    path: event_handler.EventListener, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[int] = []
    monkeypatch.setattr(trace_timing, "counter", lambda: calls.append(1) or 0)
    trace.set_enabled(True)  # Tracing on, Timing not ticked
    assert not trace_timing.on
    path._joystick_event_handler(_input())
    trace_timing.flush()
    assert calls == []
    assert _timing_lines() == []
