# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""OSC encoder inputs (D-09-OSC-ENCODER), the Monitor's hold on the port
(D-09-OSC-MONITOR) and the hooks every incoming packet passes through
(feedback sync, output's last sender/types, traffic). No network: messages
go straight into the runtime's handler; the UDP listener is a stand-in."""

from __future__ import annotations

import sys
from collections.abc import Iterator
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest
from PySide6 import QtTest

from gremlin import osc, osc_rows, shared_state
from gremlin import osc_device_file as odf
from gremlin.error import GremlinError
from gremlin.event_handler import EventListener
from gremlin.osc import OscDevice, OscRuntime
from gremlin.osc_rows import OscRows
from gremlin.types import InputType

AXIS = InputType.JoystickAxis
BUTTON = InputType.JoystickButton


class FakeListener:
    made: list[FakeListener] = []

    def __init__(self, host: str, port: int, callback: object) -> None:
        self.host, self.port, self.callback = host, port, callback
        self.open = False

    def start(self) -> None:
        self.open = True
        FakeListener.made.append(self)

    def stop(self) -> None:
        self.open = False


@pytest.fixture
def run(qapp: object, monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple]:
    monkeypatch.setattr(odf, "read_server", lambda: {})
    monkeypatch.setattr(osc, "OscListener", FakeListener)
    monkeypatch.setattr(
        shared_state,
        "current_profile",
        SimpleNamespace(inputs={osc.OSC_DEVICE_UUID: [object()]}),
    )
    FakeListener.made = []
    rows = OscDevice().rows
    saved = rows.to_dict()
    rows.reset()
    runtime = OscRuntime()
    runtime.stop()
    events: list[tuple] = []

    def record(event: Any) -> None:  # noqa: ANN401
        if event.device_guid == osc.OSC_DEVICE_UUID:
            if event.event_type == AXIS:
                events.append(("axis", event.identifier, round(event.value, 4)))
            else:
                events.append(("button", event.identifier, event.is_pressed))

    EventListener().joystick_event.connect(record)
    yield runtime, rows, events
    EventListener().joystick_event.disconnect(record)
    for token in list(runtime._holders):
        runtime.release_open(token)
    runtime.stop()
    rows.load_dict(saved)


def _wait(ms: int) -> None:
    QtTest.QTest.qWait(ms)


# -- rows ----------------------------------------------------------------------


def test_encoder_mode_is_valid_with_defaults_and_type_follows_output() -> None:
    rows = OscRows()
    axis = rows.create(AXIS, "/enc", mode="encoder")
    assert (axis.enc_format, axis.enc_step, axis.enc_output) == ("auto", 0.05, "axis")
    cw = rows.create(BUTTON, "/enc", mode="encoder", enc_output="pulse_cw", source=1)
    assert cw.input_type == BUTTON
    with pytest.raises(GremlinError):
        rows.create(BUTTON, "/x", mode="encoder")  # output axis needs an axis
    # Changing the output moves the input to the other type.
    rows.update(axis.uid, enc_output="pulse_ccw")
    assert axis.input_type == BUTTON and axis.input_id == 2
    rows.update(axis.uid, enc_output="axis")
    assert axis.input_type == AXIS


@pytest.mark.parametrize(
    "settings",
    [
        {"enc_format": "spin"},
        {"enc_output": "pulse"},
        {"enc_step": 0},
        {"enc_step": -0.1},
        {"enc_step": float("nan")},
        {"enc_step": True},
        {"enc_step": "fast"},
        {"enc_step": 5.0},
    ],
)
def test_encoder_settings_are_validated(settings: dict) -> None:
    with pytest.raises(GremlinError):
        osc_rows.check_settings(settings)


def test_encoder_fields_round_trip_through_the_file_layout() -> None:
    rows = OscRows()
    rows.create(AXIS, "/a", mode="encoder", enc_format="signed", enc_step=0.1)
    rows.create(BUTTON, "/b", mode="encoder", enc_format="direction",
                enc_output="pulse_ccw")
    data = rows.to_dict()
    entry = data["inputs"][1]
    assert (entry["enc_format"], entry["enc_step"], entry["enc_output"]) == (
        "direction", 0.05, "pulse_ccw")
    # A file whose type disagrees with enc_output is read by enc_output.
    data["inputs"][1]["type"] = "axis"
    again = OscRows()
    again.load_dict(data)
    assert again.load_warnings == []
    assert again.to_dict()["inputs"][0] == rows.to_dict()["inputs"][0]
    assert again.rows()[1].input_type == BUTTON
    assert again.rows()[0].enc_step == 0.1


# -- encoder runtime -----------------------------------------------------------


def test_encoder_axis_auto_direction_accumulates_and_clamps(run: tuple) -> None:
    runtime, rows, events = run
    rows.create(AXIS, "/enc", mode="encoder", enc_step=0.4)
    runtime.start()
    for value in (1, 1, 0, 1, 1, 1):
        runtime._on_main("/enc", (value,))
    assert [e[2] for e in events] == [0.4, 0.8, 0.4, 0.8, 1.0, 1.0]
    assert runtime._enc_format[rows.rows()[0].uid] == "direction"


def test_encoder_axis_auto_switches_to_signed_on_a_negative(run: tuple) -> None:
    runtime, rows, events = run
    rows.create(AXIS, "/enc", mode="encoder")
    runtime.start()
    runtime._on_main("/enc", (1,))  # direction: +1 step
    runtime._on_main("/enc", (-3,))  # signed from now on: -3 steps
    runtime._on_main("/enc", (0,))  # signed 0: no movement
    runtime._on_main("/enc", (1,))  # signed +1
    assert [e[2] for e in events] == [0.05, -0.1, -0.05]


def test_encoder_fixed_format_is_not_auto_detected(run: tuple) -> None:
    runtime, rows, events = run
    rows.create(AXIS, "/s", mode="encoder", enc_format="signed")
    rows.create(AXIS, "/d", mode="encoder", enc_format="direction")
    runtime.start()
    runtime._on_main("/s", (0,))
    runtime._on_main("/d", (0,))
    runtime._on_main("/d", (5,))
    assert events == [("axis", 2, -0.05), ("axis", 2, 0.0)]


def test_encoder_pulses_one_press_release_per_tick_its_way(run: tuple) -> None:
    runtime, rows, events = run
    cw = rows.create(BUTTON, "/enc", mode="encoder", enc_output="pulse_cw",
                     delay_ms=20)
    ccw = rows.create(BUTTON, "/enc", mode="encoder", enc_output="pulse_ccw",
                      enc_format="signed", delay_ms=20, source=1)
    runtime.start()
    runtime._on_main("/enc", (2, 0))  # signed: 2 ticks cw; ccw input sees 0
    assert events == [("button", cw.input_id, True)]
    _wait(200)
    assert events == [
        ("button", cw.input_id, True), ("button", cw.input_id, False),
        ("button", cw.input_id, True), ("button", cw.input_id, False),
    ]
    events.clear()
    runtime._on_main("/enc", (0, -1))  # cw input: 0 in signed = nothing
    _wait(100)
    assert events == [("button", ccw.input_id, True), ("button", ccw.input_id, False)]


def test_encoder_ticks_during_a_pulse_queue_after_it(run: tuple) -> None:
    runtime, rows, events = run
    rows.create(BUTTON, "/e", mode="encoder", enc_output="pulse_cw",
                enc_format="direction", delay_ms=30)
    runtime.start()
    runtime._on_main("/e", (1,))
    runtime._on_main("/e", (1,))
    runtime._on_main("/e", (0,))  # ccw: not this input's way
    _wait(250)
    assert events == [("button", 1, True), ("button", 1, False)] * 2


def test_stop_drops_queued_encoder_ticks(run: tuple) -> None:
    runtime, rows, events = run
    rows.create(BUTTON, "/e", mode="encoder", enc_output="pulse_cw", delay_ms=30)
    runtime.start()
    runtime._on_main("/e", (5,))
    runtime.stop()
    _wait(150)
    assert events == [("button", 1, True), ("button", 1, False)]


# -- Monitor hold --------------------------------------------------------------


def test_hold_open_opens_the_port_without_a_run_until_released(run: tuple) -> None:
    runtime, _rows, _events = run
    assert runtime.hold_open("monitor") is True
    assert runtime.is_open() and FakeListener.made[-1].open
    # A Run starting and stopping leaves the held port open.
    runtime.start()
    runtime.stop()
    assert runtime.is_open()
    # Listen ending leaves it open too.
    runtime.listen_once()
    runtime.cancel_listen()
    assert runtime.is_open()
    runtime.release_open("monitor")
    assert not runtime.is_open() and not FakeListener.made[-1].open


def test_release_open_keeps_the_port_for_a_run(run: tuple) -> None:
    runtime, _rows, _events = run
    runtime.hold_open("monitor")
    runtime.start()
    runtime.release_open("monitor")
    assert runtime.is_open()
    runtime.stop()
    assert not runtime.is_open()


# -- incoming hooks --------------------------------------------------------------


@pytest.fixture
def hooks(monkeypatch: pytest.MonkeyPatch) -> dict:
    calls: dict[str, Any] = {"order": [], "consume": False}

    def module(name: str, **funcs: Any) -> None:  # noqa: ANN401
        mod = ModuleType(f"gremlin.{name}")
        for fname, func in funcs.items():
            setattr(mod, fname, func)
        monkeypatch.setitem(sys.modules, f"gremlin.{name}", mod)

    def handle_incoming(address: str, args: tuple, peer: object) -> bool:
        calls["order"].append(("feedback", address, args, peer))
        return calls["consume"]

    module("osc_feedback", handle_incoming=handle_incoming)
    module(
        "osc_output",
        note_sender=lambda h, p: calls["order"].append(("sender", h, p)),
        note_received_type=lambda a, v: calls["order"].append(("type", a, v)),
    )
    module(
        "osc_traffic",
        note=lambda d, a, v, peer, m: calls["order"].append(
            ("traffic", d, a, v, peer, m)
        ),
    )
    return calls


def test_incoming_packet_passes_hooks_in_order(run: tuple, hooks: dict) -> None:
    runtime, rows, events = run
    rows.create(BUTTON, "/b")
    runtime.start()
    peer = ("10.0.0.5", 9000)
    runtime._on_main("/b", (1.0,), peer)
    runtime._on_main("/none", (2,), peer)
    assert events == [("button", 1, True)]
    assert hooks["order"] == [
        ("feedback", "/b", (1.0,), peer),
        ("sender", "10.0.0.5", 9000),
        ("type", "/b", (1.0,)),
        ("traffic", "in", "/b", (1.0,), peer, ["OSC Button 1"]),
        ("feedback", "/none", (2,), peer),
        ("sender", "10.0.0.5", 9000),
        ("type", "/none", (2,)),
        ("traffic", "in", "/none", (2,), peer, []),
    ]


def test_traffic_names_matches_with_no_run(run: tuple, hooks: dict) -> None:
    """The Monitor shows the inputs a message would reach even with no Run."""
    runtime, rows, events = run
    rows.create(AXIS, "/x")
    runtime.hold_open("monitor")
    runtime._on_main("/x", (0.5,), None)
    assert events == []
    assert hooks["order"][-1] == ("traffic", "in", "/x", (0.5,), None, ["OSC Axis 1"])
    assert not any(c[0] == "sender" for c in hooks["order"])


def test_sync_message_consumed_by_feedback_reaches_no_input(
    run: tuple, hooks: dict
) -> None:
    runtime, rows, events = run
    rows.create(BUTTON, "/gremlin/sync")
    runtime.start()
    hooks["consume"] = True
    runtime._on_main("/gremlin/sync", (), ("1.2.3.4", 5))
    assert events == []
    # Consumed by feedback, but the Monitor still shows it (D-09-OSC-MONITOR).
    assert hooks["order"] == [
        ("feedback", "/gremlin/sync", (), ("1.2.3.4", 5)),
        ("traffic", "in", "/gremlin/sync", (), ("1.2.3.4", 5), ["Sync"]),
    ]


def test_missing_or_failing_hook_modules_do_not_break_inputs(
    run: tuple, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime, rows, events = run

    def boom(*_args: object) -> None:
        raise RuntimeError("broken")

    mod = ModuleType("gremlin.osc_traffic")
    mod.note = boom  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "gremlin.osc_traffic", mod)
    empty = ModuleType("gremlin.osc_feedback")  # no handle_incoming
    monkeypatch.setitem(sys.modules, "gremlin.osc_feedback", empty)
    rows.create(BUTTON, "/b")
    runtime.start()
    runtime._on_main("/b", (1.0,), ("h", 1))
    assert events == [("button", 1, True)]


def test_listener_passes_the_senders_address(qapp: object) -> None:
    got: list[tuple] = []
    listener = osc.OscListener(callback=lambda a, v, p: got.append((a, v, p)))
    listener._on_message(("192.168.1.9", 53000), "/Fader", 0.5)
    listener._on_message(("192.168.1.9", 53000), "/noop")
    assert got == [("/fader", (0.5,), ("192.168.1.9", 53000))]


def test_incoming_signal_carries_the_peer(run: tuple, hooks: dict) -> None:
    runtime, rows, _events = run
    rows.create(BUTTON, "/b")
    runtime.start()
    runtime._from_thread("/b", (1.0,), ("127.0.0.1", 7000))
    assert ("sender", "127.0.0.1", 7000) in hooks["order"]
