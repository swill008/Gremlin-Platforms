# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""OSC runtime additions of the OSC page rewrite (batch 1):
OX1 live value and last seen per input (throttled change signal),
OX2 a port-in-use error names the program holding the port,
OX3 OSC errors (bind, send, malformed packet) reach the user and program logs,
OX5 send_test injects a synthetic press/release/value through _apply.
Network: loopback only, on ports the OS picks (port 0)."""

from __future__ import annotations

import logging
import os
import socket
import sys
from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

import pytest
from PySide6 import QtTest

from gremlin import clock, log_once, osc, osc_output, run_scope, shared_state
from gremlin import osc_device_file as odf
from gremlin.event_handler import EventListener
from gremlin.osc import OscDevice, OscRuntime
from gremlin.types import InputType

AXIS = InputType.JoystickAxis
BUTTON = InputType.JoystickButton
OscListenerReal = osc.OscListener


class FakeListener:
    """Stands in for the UDP listener; fail_ports refuse to bind."""

    fail_ports: set[int] = set()

    def __init__(self, host: str, port: int, callback: object) -> None:
        self.host, self.port, self.callback = host, port, callback

    def start(self) -> None:
        if self.port in FakeListener.fail_ports:
            raise OSError(10048, "address in use")

    def stop(self) -> None:
        pass


class Clock:
    def __init__(self) -> None:
        self.t = 1000.0

    def now(self) -> float:
        return self.t

    def monotonic(self) -> float:
        return self.t


@pytest.fixture
def rt(qapp: object, monkeypatch: pytest.MonkeyPatch) -> Iterator[SimpleNamespace]:
    server: dict[str, Any] = {"host": "127.0.0.1"}
    monkeypatch.setattr(odf, "read_server", lambda: dict(server))
    monkeypatch.setattr(osc, "OscListener", FakeListener)
    monkeypatch.setattr(
        shared_state,
        "current_profile",
        SimpleNamespace(inputs={osc.OSC_DEVICE_UUID: [object()]}),
    )
    fake = Clock()
    monkeypatch.setattr(clock, "now", fake.now)
    monkeypatch.setattr(clock, "monotonic", fake.monotonic)
    FakeListener.fail_ports = set()
    log_once.reset()
    rows = OscDevice().rows
    saved = rows.to_dict()
    rows.reset()
    runtime = OscRuntime()
    runtime.stop()
    runtime.reset_live()
    events: list[tuple] = []
    errors: list[tuple[str, str]] = []

    def record(event: Any) -> None:  # noqa: ANN401
        if event.device_guid == osc.OSC_DEVICE_UUID:
            if event.event_type == AXIS:
                events.append(("axis", event.identifier, round(event.value, 4)))
            else:
                events.append(("button", event.identifier, event.is_pressed))

    from gremlin.signal import signal as ui_signal

    def on_error(title: str, detail: str) -> None:
        errors.append((title, detail))

    EventListener().joystick_event.connect(record)
    ui_signal.showError.connect(on_error)
    yield SimpleNamespace(
        runtime=runtime,
        rows=rows,
        events=events,
        errors=errors,
        server=server,
        clock=fake,
    )
    ui_signal.showError.disconnect(on_error)
    EventListener().joystick_event.disconnect(record)
    for token in ("t", "mon"):
        runtime.release_open(token)
    runtime.stop()
    runtime.reset_live()
    rows.load_dict(saved)


# -- OX1 live value and last seen -------------------------------------------


def test_live_value_recorded_without_a_run(rt: SimpleNamespace) -> None:
    axis = rt.rows.create(AXIS, "/fader", range_min=0.0, range_max=1.0)
    button = rt.rows.create(BUTTON, "/btn")
    assert rt.runtime.live(axis.uid) is None
    assert rt.runtime.hold_open("mon")
    rt.runtime._on_main("/fader", (0.75,), None)
    rt.runtime._on_main("/btn", (1.0,), None)
    live = rt.runtime.live(axis.uid)
    assert live["value"] == 0.75
    assert live["axis"] == pytest.approx(0.5)
    assert live["last_seen"] == 1000.0
    assert live["synthetic"] is False
    assert rt.runtime.live(button.uid)["pressed"] is True
    # Only the Monitor holds the port: no actions fire.
    assert rt.events == []


def test_live_changed_is_throttled_per_input(rt: SimpleNamespace) -> None:
    axis = rt.rows.create(AXIS, "/fader")
    other = rt.rows.create(AXIS, "/other")
    seen: list[str] = []
    rt.runtime.liveChanged.connect(seen.append)
    try:
        for i in range(5):
            rt.runtime._on_main("/fader", (i / 10,), None)
        rt.runtime._on_main("/other", (0.1,), None)
        # One at once per input; the rest wait for the throttle.
        assert seen == [axis.uid, other.uid]
        rt.clock.t += 0.2
        QtTest.QTest.qWait(250)
        assert seen == [axis.uid, other.uid, axis.uid]
        assert rt.runtime.live(axis.uid)["value"] == 0.4
    finally:
        rt.runtime.liveChanged.disconnect(seen.append)


# -- OX5 send_test ------------------------------------------------------------


def test_send_test_fires_only_while_running(rt: SimpleNamespace) -> None:
    button = rt.rows.create(BUTTON, "/btn")
    axis = rt.rows.create(AXIS, "/fader", range_min=0.0, range_max=1.0)
    assert rt.runtime.send_test(button.uid, "press") is False
    assert rt.events == []
    assert rt.runtime.live(button.uid)["synthetic"] is True
    rt.runtime.start()
    assert rt.runtime.send_test(button.uid, "press") is True
    assert rt.runtime.send_test(button.uid, "release") is True
    assert rt.runtime.send_test(axis.uid, "value", 1.0) is True
    assert rt.events == [
        ("button", button.input_id, True),
        ("button", button.input_id, False),
        ("axis", axis.input_id, 1.0),
    ]
    assert rt.runtime.live(axis.uid)["synthetic"] is True
    assert rt.runtime.send_test("no-such-input", "press") is False


# -- OX3 errors are logged ----------------------------------------------------


def test_bind_failure_goes_to_user_and_program_log(
    rt: SimpleNamespace, caplog: pytest.LogCaptureFixture
) -> None:
    rt.server["port"] = 8123
    FakeListener.fail_ports = {8123}
    caplog.set_level(logging.WARNING)
    assert rt.runtime.hold_open("t") is False
    assert rt.errors and "Could not bind OSC on 127.0.0.1:8123" in rt.errors[0][0]
    by_logger = {r.name for r in caplog.records if "8123" in r.getMessage()}
    assert {"user", "system"} <= by_logger


def test_send_failure_goes_to_user_log(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    log_once.reset()

    class Broken:
        def send_message(self, address: str, args: list) -> None:
            raise OSError(10051, "network unreachable")

    monkeypatch.setattr(
        osc_output,
        "_settings",
        lambda: ({}, [{"id": "t", "host": "127.0.0.1", "port": 9}]),
    )
    monkeypatch.setattr(osc_output, "_client", lambda host, port: Broken())
    caplog.set_level(logging.WARNING)
    assert osc_output.send("t", "/x", [1], force=True) is False
    names = {r.name for r in caplog.records if "/x" in r.getMessage()}
    assert {"user", "system"} <= names


def test_malformed_packet_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    log_once.reset()
    caplog.set_level(logging.WARNING)
    listener = osc.OscListener("127.0.0.1", 0, lambda *a: None)
    listener.start()
    try:
        port = listener.bound_port()
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.sendto(b"not osc at all", ("127.0.0.1", port))
            # Looks like a message, but the type tag string is cut short.
            sock.sendto(b"/a\x00\x00,i", ("127.0.0.1", port))
        deadline = clock.monotonic() + 3.0
        while clock.monotonic() < deadline:
            names = {
                r.name for r in caplog.records if "malformed" in r.getMessage()
            }
            if {"user", "system"} <= names:
                break
            QtTest.QTest.qWait(20)
        assert {"user", "system"} <= names
    finally:
        listener.stop()


# -- OX2 the program holding the port -----------------------------------------


@pytest.mark.skipif(sys.platform != "win32", reason="port owner lookup is Windows")
def test_port_holder_names_the_process() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        holder = osc.port_holder(port)
    assert holder is not None
    name, pid = holder
    assert pid == os.getpid()
    assert name.lower().startswith("python")


@pytest.mark.skipif(sys.platform != "win32", reason="port owner lookup is Windows")
def test_bind_error_names_the_holder(
    rt: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The real listener this time: a socket of ours holds the port.
    monkeypatch.setattr(osc, "OscListener", OscListenerReal)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        rt.server["port"] = port
        assert rt.runtime.hold_open("t") is False
    assert rt.errors
    title, detail = rt.errors[0]
    assert f"127.0.0.1:{port}" in title
    assert f"PID {os.getpid()}" in detail



def test_bind_error_says_another_program_when_unknown(
    rt: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(osc, "port_holder", lambda port, host="": None)
    rt.server["port"] = 8124
    FakeListener.fail_ports = {8124}
    assert rt.runtime.hold_open("t") is False
    assert "another program" in rt.errors[0][1]


def test_run_scope_untouched() -> None:
    # The tests above never leave a Run going.
    assert not run_scope.running()
