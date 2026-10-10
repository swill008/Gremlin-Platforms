# -*- coding: utf-8; -*-

# Copyright (C) 2015 - 2026 Lionel Ott - Gremlin-Platforms contributors
#
# SPDX-License-Identifier: GPL-3.0-only

"""A macro's OSC step plays through OscRuntime.play (09 S159): the event is
marked synthetic (02 S44), the recorded, already-shaped value is not shaped
again (S161) and is not recorded again."""

from __future__ import annotations

import threading
import time
from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

import pytest
from PySide6 import QtCore

from gremlin import macro, osc, shared_state
from gremlin import osc_device_file as odf
from gremlin.event_handler import EventListener
from gremlin.osc import OscDevice, OscRuntime
from gremlin.types import InputType

AXIS = InputType.JoystickAxis
BUTTON = InputType.JoystickButton


class FakeListener:
    def __init__(self, host: str, port: int, callback: object) -> None:
        self.host, self.port, self.callback = host, port, callback

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass


def _settle(until: Any = None, limit_s: float = 2.0) -> None:  # noqa: ANN401
    """Processes queued events; with until, until it is true (bounded)."""
    end = time.monotonic() + limit_s
    while True:
        QtCore.QCoreApplication.processEvents()
        if until is None or until() or time.monotonic() > end:
            if until is None:
                for _ in range(2):
                    QtCore.QCoreApplication.processEvents()
            return
        time.sleep(0.005)


@pytest.fixture
def rt(qapp: object, monkeypatch: pytest.MonkeyPatch) -> Iterator[SimpleNamespace]:
    monkeypatch.setattr(odf, "read_server", lambda: {"host": "127.0.0.1"})
    monkeypatch.setattr(osc, "OscListener", FakeListener)
    monkeypatch.setattr(
        shared_state,
        "current_profile",
        SimpleNamespace(inputs={osc.OSC_DEVICE_UUID: [object()]}),
    )
    rows = OscDevice().rows
    saved = rows.to_dict()
    rows.reset()
    runtime = OscRuntime()
    runtime.stop()
    runtime.reset_live()
    events: list[Any] = []

    def record(event: Any) -> None:  # noqa: ANN401
        if event.device_guid == osc.OSC_DEVICE_UUID:
            events.append((event, threading.current_thread()))

    EventListener().joystick_event.connect(record)
    yield SimpleNamespace(runtime=runtime, rows=rows, events=events)
    EventListener().joystick_event.disconnect(record)
    runtime.stop()
    runtime.reset_live()
    rows.load_dict(saved)


def test_played_events_are_synthetic(rt: SimpleNamespace) -> None:
    button = rt.rows.create(BUTTON, "/btn")
    axis = rt.rows.create(AXIS, "/fader", range_min=0.0, range_max=1.0)
    rt.runtime.start()
    macro.OscAction(button.uid, BUTTON, True)()
    macro.OscAction(button.uid, BUTTON, False)()
    macro.OscAction(axis.uid, AXIS, 0.5)()
    _settle()
    got = [(e.event_type, e.identifier, e.is_pressed, e.value) for e, _ in rt.events]
    assert got == [
        (BUTTON, button.input_id, True, None),
        (BUTTON, button.input_id, False, None),
        (AXIS, axis.input_id, None, pytest.approx(0.5)),
    ]
    assert all(e.synthetic for e, _ in rt.events)
    # The live value updates, marked synthetic.
    live = rt.runtime.live(axis.uid)
    assert live is not None and live["synthetic"] is True
    assert live["axis"] == pytest.approx(0.5)


def test_shaped_axis_is_not_shaped_again(rt: SimpleNamespace) -> None:
    axis = rt.rows.create(
        AXIS,
        "/fader",
        range_min=0.0,
        range_max=1.0,
        invert=True,
        deadzone=[-0.2, 0.2],
    )
    rt.runtime.start()
    macro.OscAction(axis.uid, AXIS, 0.5)()
    _settle()
    assert [round(e.value, 4) for e, _ in rt.events] == [0.5]


def test_play_while_recording_records_nothing(rt: SimpleNamespace) -> None:
    button = rt.rows.create(BUTTON, "/btn")
    axis = rt.rows.create(AXIS, "/fader", range_min=0.0, range_max=1.0)
    seen: list[tuple] = []
    rt.runtime.start()
    assert rt.runtime.add_recorder(lambda *a: seen.append(a))
    try:
        macro.OscAction(button.uid, BUTTON, True)()
        macro.OscAction(axis.uid, AXIS, 0.25)()
        _settle()
    finally:
        rt.runtime.remove_recorder(rt.runtime._recorders[0])
    assert seen == []
    assert len(rt.events) == 2


def test_play_while_stopped_does_nothing(rt: SimpleNamespace) -> None:
    button = rt.rows.create(BUTTON, "/btn")
    rt.runtime.play(button.uid, "button", True)
    macro.OscAction(button.uid, BUTTON, True)()
    _settle()
    assert rt.events == []
    assert rt.runtime.live(button.uid) is None


def test_play_from_a_worker_thread_reaches_the_main_thread(
    rt: SimpleNamespace,
) -> None:
    button = rt.rows.create(BUTTON, "/btn")
    rt.runtime.start()
    worker = threading.Thread(
        target=lambda: rt.runtime.play(button.uid, "button", True)
    )
    worker.start()
    worker.join(2.0)
    assert not worker.is_alive()
    _settle(until=lambda: rt.events)
    assert len(rt.events) == 1
    event, thread = rt.events[0]
    assert event.is_pressed is True and event.synthetic
    assert thread is threading.main_thread()
