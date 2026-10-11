# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""OSC Output and Feedback tracing and the quiet, bounded output path
(D-09-OSC-TRACE; 09 E1 E2 E4 E9): settings and targets are read from OSC's
file once and again only when the file changes (its writers' signal); a
refused send is a BLOCKED Output line with the exact reason; a failing
target reaches the logs at most 10 times plus one "not logged until the
next Run" line; Feedback steps and skips are traced; with tracing off
nothing is written. No network: the UDP client is a stand-in."""

from __future__ import annotations

import importlib
import json
import logging
import pathlib
import sys
import types
import uuid
from collections.abc import Iterator
from typing import Any

import pytest

from gremlin import osc_device_file, osc_output, run_scope, trace, util
from gremlin.base_classes import Value
from gremlin.event_handler import Event
from gremlin.types import ActionActivationMode, InputType

_EVENT = Event(
    InputType.JoystickButton, 1, uuid.UUID(int=5), "Default", is_pressed=True
)


class FakeClient:
    sent: list[tuple] = []
    fail = False

    def __init__(self, host: str, port: int) -> None:
        self.peer = (host, port)

    def send_message(self, address: str, args: list) -> None:
        if FakeClient.fail:
            raise OSError(10051, "network unreachable")
        FakeClient.sent.append((self.peer, address, list(args)))


@pytest.fixture
def osc(
    qapp: object, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[dict]:
    global osc_output
    if osc_output.send.__module__ != "gremlin.osc_output":
        # Another test file replaced send without putting it back.
        osc_output = importlib.reload(osc_output)
    monkeypatch.setattr(util, "logs_dir", lambda: tmp_path / "logs")
    trace._reset_for_tests()
    file = tmp_path / "module.json"
    file.write_text(
        json.dumps(
            {
                "server": {"output_enabled": True, "reply_to_sender": True},
                "targets": [
                    {"id": "t1", "name": "Desk", "host": "10.0.0.5", "port": 9000}
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(osc_device_file, "path", lambda: file)
    reads: list[str] = []
    real_server, real_targets = (
        osc_device_file.read_server,
        osc_device_file.read_targets,
    )
    monkeypatch.setattr(
        osc_device_file,
        "read_server",
        lambda: reads.append("server") or real_server(),
    )
    monkeypatch.setattr(
        osc_device_file,
        "read_targets",
        lambda: reads.append("targets") or real_targets(),
    )
    FakeClient.sent = []
    FakeClient.fail = False
    monkeypatch.setattr(osc_output, "_make_client", FakeClient)
    monkeypatch.setattr(run_scope, "running", lambda: True)
    monkeypatch.setattr(run_scope, "on_stop", lambda *a: None)
    osc_output.reset()
    yield {"reads": reads, "file": file}
    osc_output.reset()
    trace.set_osc_all(False)
    trace._reset_for_tests()


def _on() -> None:
    trace.set_osc_all(True)
    trace.set_enabled(True)


def _lines(area: str) -> list[tuple[str, str]]:
    name = f"OSC {trace.OSC_AREA_NAMES[area]}"
    return [(line[2], line[3]) for line in trace.lines() if line[1] == name]


def test_settings_are_read_once_not_per_send(osc: dict) -> None:
    for _ in range(100):
        assert osc_output.send("t1", "/a", [1])
    # Old code: 4 file reads per send (400).
    assert len(osc["reads"]) == 2
    assert len(FakeClient.sent) == 100


def test_a_change_through_the_file_writer_is_read_again(osc: dict) -> None:
    assert osc_output.send("t1", "/a", [1])
    server = osc_device_file.read_server()
    server["output_enabled"] = False
    assert osc_device_file.write_server(server, "test")
    # The write's signal dropped the held settings: the change applies.
    assert not osc_output.send("t1", "/a", [1])
    after = len(osc["reads"])
    for _ in range(10):
        assert not osc_output.send("t1", "/a", [1])
    # Held again: no read per send.
    assert len(osc["reads"]) == after


def test_refused_sends_are_traced_with_the_exact_reason(
    osc: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    _on()
    assert not osc_output.send("t1", "light", [1])
    assert not osc_output.send("nope", "/a", [1])
    assert not osc_output.send("reply", "/a", [1])
    monkeypatch.setattr(run_scope, "running", lambda: False)
    assert not osc_output.send("t1", "/a", [1])
    monkeypatch.setattr(run_scope, "running", lambda: True)
    server = osc_device_file.read_server()
    server["output_enabled"] = False
    osc_device_file.write_server(server, "test")
    assert not osc_output.send("t1", "/a", [1])
    blocked = [text for point, text in _lines("output") if point == trace.BLOCKED]
    assert blocked == [
        "send refused: light is not an OSC address",
        "send refused: no target named nope",
        "send refused: no reply address yet",
        "send refused: the profile isn't running",
        "send refused: OSC output is Off",
    ]


def test_a_sent_message_is_an_out_line(osc: dict) -> None:
    _on()
    assert osc_output.send("t1", "/a", [1, "2"], ["int", "float"], source="Send OSC")
    texts = [text for _, text in _lines("output")]
    assert "client 10.0.0.5:9000 open" in texts
    assert "out Desk 10.0.0.5:9000 /a ,if 1 2.0 (Send OSC)" in texts
    # Reading OSC/module.json is a Setup and files line, not an Output one.
    assert not any(t.startswith("settings read") for t in texts)
    setup = [text for _, text in _lines("setup")]
    assert "settings read from OSC/module.json (1 targets)" in setup


def test_a_failing_target_logs_at_most_ten_then_one_note(
    osc: dict, caplog: pytest.LogCaptureFixture
) -> None:
    FakeClient.fail = True
    caplog.set_level(logging.WARNING)
    for _ in range(30):
        assert not osc_output.send("t1", "/a", [1])
    for name in ("system", "user"):
        records = [
            r.getMessage()
            for r in caplog.records
            if r.name == name and "could not send" in r.getMessage()
        ]
        # Old code: a system warning every time (30).
        assert len(records) == 11
        assert "not logged until the next Run" in records[-1]
        assert all("not logged" not in text for text in records[:10])


def test_tracing_off_writes_nothing(osc: dict) -> None:
    trace.set_osc_all(True)  # ticked, but tracing is off
    osc_output.send("t1", "/a", [1])
    osc_output.send("nope", "/a", [1])
    assert trace.lines() == []


def test_send_osc_refusal_is_traced(osc: dict) -> None:
    from action_plugins.send_osc import SendOscData, SendOscFunctor

    _on()
    action = SendOscData(InputType.JoystickButton)
    action.address = "/a b"
    SendOscFunctor(action)(_EVENT, Value(True))
    action.address = "/ok"
    action.activation_mode = ActionActivationMode.Press
    SendOscFunctor(action)(_EVENT, Value(True))
    lines = _lines("output")
    assert any(
        point == trace.BLOCKED and text.startswith("Send OSC refused: '/a b'")
        for point, text in lines
    )
    assert any(text.endswith("(Send OSC)") and " /ok " in text for _, text in lines)


# --- feedback -----------------------------------------------------------------


@pytest.fixture
def fb(osc: dict, monkeypatch: pytest.MonkeyPatch) -> Iterator[dict]:
    from gremlin import osc_feedback
    from gremlin.modules import output

    rows = [
        {
            "id": "r1",
            "enabled": True,
            "address": "/b1",
            "target": "t1",
            "type": "float",
            "min": 0.0,
            "max": 1.0,
            "source": {"kind": "vjoy_button", "device": 1, "input": 3},
        }
    ]
    vjoy: dict[tuple, Any] = {}
    monkeypatch.setattr(
        osc_device_file, "read_feedback", lambda: [dict(r) for r in rows]
    )
    monkeypatch.setattr(
        output, "vjoy_value", lambda vid, kind, iid: vjoy.get((vid, kind, iid), False)
    )
    osc_feedback.stop()
    osc_feedback._settings = None
    osc_feedback.instance()._profile_path = None
    yield {"vjoy": vjoy, "fb": osc_feedback}
    osc_feedback.stop()
    osc_feedback._settings = None


def test_feedback_steps_are_traced(fb: dict) -> None:
    osc_feedback = fb["fb"]
    _on()
    osc_feedback.start("a.xml")
    osc_feedback.instance().poll()
    lines = [text for _, text in _lines("feedback")]
    assert "rows read (1)" in lines
    assert "start (1 of 1 rows on)" in lines
    assert "row 1 vJoy 1 button 3 → /b1 0.0" in lines
    assert "resent 1 rows (run start)" in lines
    assert "row 1 unchanged (not sent)" in lines
    out = [text for _, text in _lines("output")]
    assert "out Desk 10.0.0.5:9000 /b1 ,f 0.0 (feedback row 1)" in out
    osc_feedback.stop()
    assert _lines("feedback")[-1][1] == "stop"


def test_an_osc_input_source_is_named_like_the_match_lines(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A feedback source that is an OSC input shows its name ("OSC Button
    1"), not its id; the id only once the input is gone."""
    from gremlin import osc, osc_feedback

    row = types.SimpleNamespace(input_type=InputType.JoystickButton, input_id=1)
    rows = types.SimpleNamespace(
        by_uid=lambda uid: row if uid == "2b1bc636" else None,
        matches=lambda *a: [],
    )
    monkeypatch.setattr(osc, "OscDevice", lambda: types.SimpleNamespace(rows=rows))
    assert osc_feedback.source_text({"kind": "osc_input", "input": "2b1bc636"}) == (
        "OSC Button 1"
    )
    assert osc_feedback.source_text({"kind": "osc_input", "input": "gone"}) == (
        "OSC input gone"
    )


def test_feedback_refusal_is_traced_with_the_reason(fb: dict) -> None:
    osc_feedback = fb["fb"]
    server = osc_device_file.read_server()
    server["output_enabled"] = False
    osc_device_file.write_server(server, "test")
    _on()
    osc_feedback.start("a.xml")
    blocked = [text for point, text in _lines("feedback") if point == trace.BLOCKED]
    assert blocked == [
        "row 1 refused: OSC output is Off (sent again when sending works)"
    ]


def test_incoming_messages_read_no_file(fb: dict, osc: dict) -> None:
    osc_feedback = fb["fb"]
    osc_feedback.handle_incoming("/x", (), None)  # the first reads once
    before = len(osc["reads"])
    for _ in range(100):
        assert osc_feedback.handle_incoming("/x", (), None) is False
    # Old code: one file read per incoming message while not running (100).
    assert len(osc["reads"]) == before


def test_companion_check_lines_are_traced(osc: dict) -> None:
    from gremlin.osc_companion_check import OscCompanionCheck

    _on()
    check = OscCompanionCheck()
    check._lines = []
    import gremlin.osc_companion_check as cc

    real = cc.check
    cc.check = lambda: [  # type: ignore[assignment]
        cc._line("OSC is on.", True),
        cc._line("OSC output is off.", False, 'Tick "OSC output" above.'),
    ]
    try:
        check.run()
    finally:
        cc.check = real  # type: ignore[assignment]
    texts = [text for _, text in _lines("setup")]
    assert texts == [
        "Companion check: 1 to fix of 2",
        "Companion check OK: OSC is on.",
        'Companion check to fix: OSC output is off. Tick "OSC output" above.',
    ]


def test_monitor_note_failure_is_logged_bounded(
    osc: dict, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    fake = types.ModuleType("gremlin.osc_traffic")

    def broken(*_a: object) -> None:
        raise RuntimeError("model gone")

    fake.note = broken  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "gremlin.osc_traffic", fake)
    import gremlin

    monkeypatch.setattr(gremlin, "osc_traffic", fake, raising=False)
    caplog.set_level(logging.ERROR)
    for _ in range(20):
        assert osc_output.send("t1", "/a", [1])
    records = [r for r in caplog.records if "was not noted" in r.getMessage()]
    # Old code: a traceback every send (20).
    assert len(records) == 11
