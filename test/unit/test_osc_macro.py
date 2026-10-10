# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Macros and OSC (09 S159): Record captures OSC inputs with no Run (the
recorder holds the port), an OSC step stores the input's permanent id, and
playing it fires the OSC input's binding through the OSC runtime.
No network: the UDP listener is a stand-in; messages go in at _on_main."""

from __future__ import annotations

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
from gremlin.ui.util import MacroRecorder

AXIS = InputType.JoystickAxis
BUTTON = InputType.JoystickButton


class FakeListener:
    def __init__(self, host: str, port: int, callback: object) -> None:
        self.host, self.port, self.callback = host, port, callback

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass


def _settle() -> None:
    for _ in range(3):
        QtCore.QCoreApplication.processEvents()


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
    events: list[tuple] = []

    def record(event: Any) -> None:  # noqa: ANN401
        if event.device_guid == osc.OSC_DEVICE_UUID:
            if event.event_type == AXIS:
                events.append(("axis", event.identifier, round(event.value, 4)))
            else:
                events.append(("button", event.identifier, event.is_pressed))

    EventListener().joystick_event.connect(record)
    yield SimpleNamespace(runtime=runtime, rows=rows, events=events)
    EventListener().joystick_event.disconnect(record)
    runtime.stop()
    runtime.reset_live()
    rows.load_dict(saved)


def test_record_captures_osc_without_a_run(rt: SimpleNamespace) -> None:
    button = rt.rows.create(BUTTON, "/btn")
    axis = rt.rows.create(AXIS, "/fader", range_min=0.0, range_max=1.0)
    steps: list[Any] = []
    recorder = MacroRecorder(steps.append)
    assert not rt.runtime.is_open()
    recorder.start([BUTTON, AXIS], False)
    try:
        # Record holds the port open with no profile running.
        assert rt.runtime.is_open()
        rt.runtime._on_main("/btn", (1.0,), None)
        rt.runtime._on_main("/btn", (0.0,), None)
        rt.runtime._on_main("/fader", (0.75,), None)
        _settle()
    finally:
        recorder.stop()
    assert not rt.runtime.is_open()
    got = [(type(s).__name__, s.uid, s.value) for s in steps]
    assert got == [
        ("OscAction", button.uid, True),
        ("OscAction", button.uid, False),
        ("OscAction", axis.uid, pytest.approx(0.5)),
    ]
    # Nothing fired: no Run.
    assert rt.events == []


def test_playback_fires_the_osc_binding(rt: SimpleNamespace) -> None:
    button = rt.rows.create(BUTTON, "/btn")
    axis = rt.rows.create(AXIS, "/fader", range_min=0.0, range_max=1.0)
    rt.runtime.start()
    macro.OscAction(button.uid, BUTTON, True)()
    macro.OscAction(button.uid, BUTTON, False)()
    macro.OscAction(axis.uid, AXIS, 0.5)()
    _settle()
    assert rt.events == [
        ("button", button.input_id, True),
        ("button", button.input_id, False),
        ("axis", axis.input_id, 0.5),
    ]
    # A step whose input is gone does nothing.
    macro.OscAction("no-such-input", BUTTON, True)()
    _settle()
    assert len(rt.events) == 3


def test_step_stores_the_permanent_id(rt: SimpleNamespace) -> None:
    assert macro.STEP_TYPES["osc"] is macro.OscAction
    # No inputs: a step with none chosen, not valid.
    empty = macro.OscAction.create()
    assert empty.uid is None and not empty.is_valid()
    axis = rt.rows.create(AXIS, "/fader")
    rt.rows.create(BUTTON, "/btn")
    first = macro.OscAction.create()
    assert (first.uid, first.input_type, first.value) == (axis.uid, AXIS, 0.0)
    button = rt.rows.by_uid(
        next(r.uid for r in rt.rows.rows() if r.input_type == BUTTON)
    )
    step = macro.OscAction(button.uid, BUTTON, True)
    node = step.to_xml()
    assert node.get("type") == "osc"
    assert node.get("uid") == button.uid
    back = macro.OscAction.create()
    back.from_xml(node)
    assert (back.uid, back.input_type, back.value) == (button.uid, BUTTON, True)
    # Renumbering the input keeps the step on it: the uid names it.
    button.input_id = 40
    assert back.row() is button
    # A step whose input is gone is kept (05 S117 style), marked missing.
    gone = macro.OscAction("gone-uid", BUTTON, True)
    assert gone.is_valid() and gone.is_missing()


def test_new_step_on_a_button_starts_pressed(rt: SimpleNamespace) -> None:
    from action_plugins.macro import OscActionModel

    rt.rows.create(BUTTON, "/btn")
    axis = rt.rows.create(AXIS, "/fader")
    step = macro.OscAction.create()
    assert step.input_type == BUTTON and step.value is True
    model = OscActionModel(step)
    assert model.property("inputType") == "button"
    assert model.property("isPressed") is True
    assert [c["text"] for c in model.property("inputChoices")] == ["/btn", "/fader"]
    model.setProperty("inputUid", axis.uid)
    assert step.uid == axis.uid and step.input_type == AXIS
    assert model.property("inputType") == "axis"


def test_editor_offers_an_osc_step() -> None:
    import pathlib

    import action_plugins.macro as macro_plugin

    qml = (pathlib.Path(macro_plugin.__file__).parent / "MacroAction.qml").read_text(
        encoding="utf-8"
    )
    assert '{value: "osc", text: "OSC"}' in qml
    assert 'roleValue: "osc"' in qml
    assert "modelData.inputChoices" in qml
    assert macro_plugin.MacroModel.model_lookup["osc"] is macro_plugin.OscActionModel
