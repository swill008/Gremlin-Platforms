# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""OSC Receive and Inputs trace (D-09-OSC-TRACE): a message read on the
loopback is traced at each step (in, match, event); blocked senders,
malformed packets and bad wildcard addresses are refused with no error
traceback (E3); errors (malformed, bad wildcard) stop at 10 and a note,
blocked senders are never capped (D-09-OSC-TRACE-ERRORS); per-message and
blocked lines are rate limited;
with the areas unticked nothing is written. Loopback only (127.0.0.1, an
OS-picked port)."""

from __future__ import annotations

import logging
import socket
import sys
from collections.abc import Iterator
from types import ModuleType, SimpleNamespace

import pytest
from PySide6 import QtTest

from gremlin import osc, shared_state, trace
from gremlin import osc_device_file as odf
from gremlin.osc import OscDevice, OscRuntime
from gremlin.profile import InputItem, Library
from gremlin.types import InputType

BUTTON = InputType.JoystickButton
AXIS = InputType.JoystickAxis
PEER = ("192.168.1.20", 9000)


def _packet(address: str, *values: object) -> bytes:
    from pythonosc.osc_message_builder import OscMessageBuilder

    builder = OscMessageBuilder(address=address)
    for value in values:
        builder.add_arg(value)
    return builder.build().dgram


def _osc_lines(area: str | None = None) -> list[tuple[str, str]]:
    """(point, detail) of OSC lines, of one area (display name) or all."""
    return [
        (line[2], line[3])
        for line in trace.lines()
        if line[1].startswith("OSC ")
        and (area is None or line[1] == f"OSC {area}")
    ]


def _wait(check, ms: int = 3000) -> bool:  # noqa: ANN001
    for _ in range(ms // 10):
        if check():
            return True
        QtTest.QTest.qWait(10)
    return check()


@pytest.fixture
def run(qapp: object, monkeypatch: pytest.MonkeyPatch) -> Iterator[SimpleNamespace]:
    server: dict = {"host": "127.0.0.1"}
    monkeypatch.setattr(odf, "read_server", lambda: odf.clean_server(server))
    # The port the OS picks (the settings can't hold 0).
    monkeypatch.setattr(osc, "parse_port", lambda value, default=0: 0)
    monkeypatch.setattr(
        shared_state,
        "current_profile",
        SimpleNamespace(inputs={osc.OSC_DEVICE_UUID: [InputItem(Library())]}),
    )
    traffic = ModuleType("gremlin.osc_traffic")
    traffic.note = lambda *a: None  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "gremlin.osc_traffic", traffic)
    rows = OscDevice().rows
    saved = rows.to_dict()
    rows.reset()
    runtime = OscRuntime()
    runtime.stop()
    trace._reset_for_tests()
    trace.set_enabled(True)
    trace.set_osc("receive", True)
    trace.set_osc("inputs", True)
    yield SimpleNamespace(runtime=runtime, rows=rows, server=server)
    for token in list(runtime._holders):
        runtime.release_open(token)
    runtime.stop()
    rows.load_dict(saved)
    trace.set_osc_all(False)
    trace._reset_for_tests()


def _port(runtime: OscRuntime) -> int:
    listener = runtime._listener
    assert listener is not None
    return listener.bound_port()


def test_a_message_on_the_loopback_is_traced_at_each_step(
    run: SimpleNamespace,
) -> None:
    run.rows.create(BUTTON, "/btn")
    run.runtime.start()
    port = _port(run.runtime)
    assert ("OSC", f"port 127.0.0.1:{port} open (Run)") in _osc_lines("Receive")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
        sender.bind(("127.0.0.1", 0))
        sender_port = sender.getsockname()[1]
        sender.sendto(_packet("/btn", 1.0), ("127.0.0.1", port))
        assert _wait(lambda: len(_osc_lines("Inputs")) >= 2)
    assert (
        "OSC",
        f"in 127.0.0.1:{sender_port} /btn ,f 1",
    ) in _osc_lines("Receive")
    inputs = _osc_lines("Inputs")
    assert ("OSC", "/btn → OSC Button 1 (button)") in inputs
    assert ("OSC", "event OSC Button 1 pressed") in inputs
    run.runtime.stop()
    assert ("OSC", "port closed") in _osc_lines("Receive")


def _trace_clock(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """trace's clock only (the runtime keeps the real one); no flush timer."""
    now = [1000.0]
    fake = SimpleNamespace(**vars(trace.clock))
    fake.monotonic = lambda: now[0]
    monkeypatch.setattr(trace, "clock", fake)
    monkeypatch.setattr(trace, "_schedule_flush", lambda: None)
    return now


def test_a_blocked_sender_is_never_capped_only_rate_limited(
    run: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    # D-09-OSC-TRACE-ERRORS: an expected refusal is no error: no 10 cap.
    now = _trace_clock(monkeypatch)
    gap = 1.0 / trace.axis_rate()
    run.server["allow_senders"] = ["10.0.0.0/8"]
    run.rows.create(BUTTON, "/b")
    run.runtime.start()
    for _ in range(15):
        run.runtime._on_main("/b", (1.0,), PEER)
        now[0] += gap
    blocked = [d for p, d in _osc_lines("Receive") if p == "BLOCKED"]
    text = "sender 192.168.1.20 not on Allowed senders"
    assert blocked == [text] * 15
    assert not any(d.startswith("event") for _p, d in _osc_lines("Inputs"))
    # Faster than the Axis lines rate: counted on the next line.
    for _ in range(3):
        run.runtime._on_main("/b", (1.0,), PEER)
        now[0] += gap / 10
    now[0] += gap
    run.runtime._on_main("/b", (1.0,), PEER)
    blocked = [d for p, d in _osc_lines("Receive") if p == "BLOCKED"]
    assert blocked[-1] == f"{text}  (2 messages between)"


def test_a_bad_wildcard_address_is_refused_without_an_error(
    run: SimpleNamespace, caplog: pytest.LogCaptureFixture
) -> None:
    run.rows.create(BUTTON, "/a/b")
    run.runtime.start()
    with caplog.at_level(logging.DEBUG, logger="system"):
        for _ in range(12):
            run.runtime._on_main("/a/[b", (1.0,), PEER)
    errors = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert errors == [], [r.getMessage() for r in errors]
    assert not any(r.exc_info for r in caplog.records)
    warned = [
        r for r in caplog.records
        if r.name == "system" and "/a/[b" in r.getMessage()
    ]
    assert len(warned) == 11  # 10, then the "not logged until the next Run" line
    blocked = [d for p, d in _osc_lines("Receive") if p == "BLOCKED"]
    assert blocked[0] == (
        'wildcard address /a/[b from 192.168.1.20 ("[" at position 4 is never '
        "closed.)"
    )
    assert len(blocked) == 11


def test_a_good_incoming_pattern_still_reaches_exact_inputs(
    run: SimpleNamespace,
) -> None:
    """S148 is kept: only a bad pattern is refused."""
    run.rows.create(BUTTON, "/a/b")
    run.runtime.start()
    run.runtime._on_main("/a/*", (1.0,), PEER)
    inputs = _osc_lines("Inputs")
    assert ("OSC", "/a/* → OSC Button 1 (button) from an incoming pattern") in inputs
    assert ("OSC", "event OSC Button 1 pressed") in inputs
    # One that reaches no exact input is refused (pattern inputs can't take it).
    run.runtime._on_main("/z/*", (1.0,), PEER)
    assert (
        "BLOCKED",
        "wildcard address /z/* from 192.168.1.20 (inputs need exact addresses)",
    ) in _osc_lines("Receive")
    # The Receive refusal says why: no Inputs line repeats it.
    assert not any("/z/*" in text for _, text in _osc_lines("Inputs"))


def test_unmatched_data_and_hidden_patterns_are_traced(
    run: SimpleNamespace,
) -> None:
    run.rows.create(BUTTON, "/x/1")
    run.rows.create(BUTTON, "/x/*")
    run.rows.create(BUTTON, "/d", cmd_mode="data", data=[5])
    run.runtime.start()
    run.runtime._on_main("/nobody", (1.0,), PEER)
    run.runtime._on_main("/x/1", (1.0,), PEER)
    run.runtime._on_main("/d", (4,), PEER)
    inputs = _osc_lines("Inputs")
    assert ("BLOCKED", "/nobody: no input answers") in inputs
    assert (
        "OSC",
        "/x/1: the exact input wins; not sent to OSC Button 2 (/x/*)",
    ) in inputs
    assert ("BLOCKED", "/d: data doesn't match (OSC Button 3 wants 5)") in inputs


def test_axis_not_a_number_and_not_running_are_refusals(
    run: SimpleNamespace,
) -> None:
    run.rows.create(AXIS, "/f")
    run.rows.create(BUTTON, "/b")
    run.runtime.hold_open("monitor")
    run.runtime._on_main("/b", (1.0,), PEER)
    run.runtime.start()
    run.runtime._on_main("/f", ("high",), PEER)
    run.runtime._on_main("/f", (0.5,), PEER)
    inputs = _osc_lines("Inputs")
    assert ("BLOCKED", "OSC Button 1: not running (no event)") in inputs
    assert ("BLOCKED", "OSC Axis 1: value is not a number") in inputs
    assert ("OSC", "OSC Axis 1: 0.5 → 0 → 0") in inputs


def test_per_message_lines_are_rate_limited(run: SimpleNamespace) -> None:
    run.rows.create(AXIS, "/f")
    run.runtime.start()
    for i in range(50):
        run.runtime._on_main("/f", (i / 100,), PEER)
    received = [d for _p, d in _osc_lines("Receive") if d.startswith("in ")]
    assert 1 <= len(received) < 5
    # The values between are counted on the next line (or the flush).
    assert _wait(
        lambda: any(
            "messages between" in d for _p, d in _osc_lines("Receive")
        ),
        2000,
    )


def test_malformed_packets_are_bounded_per_sender(
    run: SimpleNamespace, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.DEBUG):
        for _ in range(12):
            osc.report_malformed(("10.0.0.9", 5), "cannot be read")
    user = [r for r in caplog.records if r.name == "user"]
    assert len(user) == 11
    blocked = [d for p, d in _osc_lines("Receive") if p == "BLOCKED"]
    assert blocked[0] == "malformed packet from 10.0.0.9 (cannot be read)"
    assert len(blocked) == 11


def test_listen_capture_is_in_the_trace_not_the_log(
    run: SimpleNamespace, caplog: pytest.LogCaptureFixture
) -> None:
    trace.set_osc("setup", True)
    assert run.runtime.listen_bulk()
    with caplog.at_level(logging.DEBUG, logger="system"):
        run.runtime._on_main("/new", (1.0,), PEER)
    assert not any(
        "/new" in r.getMessage() for r in caplog.records if r.name == "system"
    )
    assert (
        "OSC",
        "Listen captured /new ,f 1 (Bulk capture)",
    ) in _osc_lines("Setup and files")
    run.runtime.cancel_listen()


def test_nothing_is_written_with_the_areas_unticked(run: SimpleNamespace) -> None:
    trace.set_osc_all(False)
    run.rows.create(BUTTON, "/b")
    run.runtime.start()
    run.runtime._on_main("/b", (1.0,), PEER)
    run.runtime._on_main("/nobody", (1.0,), PEER)
    run.runtime._on_main("/a/[b", (1.0,), PEER)
    assert _osc_lines() == []
