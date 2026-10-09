# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""OSC feedback (D-09-OSC-FEEDBACK): rows send the mode, vJoy, Logical
Device and OSC input state on change within the rate limit, a full resend at
Run start / mode change / profile switch / sync message. No network:
osc_output is a stand-in that records the sends."""

from __future__ import annotations

import sys
import time
import types
from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any
from unittest import mock

import pytest
from PySide6 import QtTest

import gremlin
from gremlin import code_runner, osc, osc_feedback, run_scope, shared_state
from gremlin import osc_device_file as odf
from gremlin.mode_manager import ModeManager
from gremlin.modules import output
from gremlin.osc import OscDevice, OscRuntime
from gremlin.types import InputType


class FakeOutput(types.ModuleType):
    def __init__(self) -> None:
        super().__init__("gremlin.osc_output")
        self.sent: list[tuple] = []
        self.senders: list[tuple] = []

    def send(
        self, target_id: str, address: str, values: list, types: list | None = None
    ) -> bool:
        self.sent.append((target_id, address, list(values), types))
        return True

    def note_sender(self, host: str, port: int) -> None:
        self.senders.append((host, port))


def _row(
    rid: str,
    kind: str,
    address: str,
    device: int | None = None,
    input: int | str | None = None,
    **extra: object,
) -> dict:
    row = {
        "id": rid,
        "enabled": True,
        "source": {"kind": kind, "device": device, "input": input},
        "target": "t1",
        "address": address,
        "min": 0.0,
        "max": 1.0,
        "type": "auto",
    }
    row.update(extra)
    return row


@pytest.fixture
def fb(qapp: object, monkeypatch: pytest.MonkeyPatch) -> Iterator[SimpleNamespace]:
    server: dict[str, Any] = {}
    server.update(
        {
            "feedback_enabled": True,
            "resend_run": True,
            "resend_mode": True,
            "resend_profile": True,
            "sync_enabled": True,
            "sync_address": "/gremlin/sync",
            "feedback_rate": 1000,
        }
    )
    rows: list[dict] = []
    vjoy: dict[tuple, Any] = {}
    fake = FakeOutput()
    monkeypatch.setitem(sys.modules, "gremlin.osc_output", fake)
    monkeypatch.setattr(gremlin, "osc_output", fake, raising=False)
    monkeypatch.setattr(odf, "read_server", lambda: dict(server))
    monkeypatch.setattr(odf, "read_feedback", lambda: [dict(r) for r in rows])
    monkeypatch.setattr(
        output,
        "vjoy_value",
        lambda vid, kind, iid: vjoy.get(
            (vid, kind, iid), 0.0 if kind == "axis" else False
        ),
    )
    osc_feedback.stop()
    osc_feedback._settings = None
    # Each test starts with no earlier Run's profile (a "profile switch"
    # resend must not leak in from the test before).
    osc_feedback.instance()._profile_path = None
    ns = SimpleNamespace(server=server, rows=rows, vjoy=vjoy, out=fake)
    yield ns
    osc_feedback.stop()
    osc_feedback._settings = None


def _poll() -> None:
    osc_feedback.instance().poll()


# -- Run start / Stop through the real CodeRunner ----------------------------


@pytest.fixture
def runner(monkeypatch: pytest.MonkeyPatch) -> Iterator[code_runner.CodeRunner]:
    for name in ("output", "OscRuntime", "InputModuleRuntime", "audio_player", "tts"):
        monkeypatch.setattr(code_runner, name, mock.MagicMock())
    run = code_runner.CodeRunner()
    monkeypatch.setattr(run, "_refresh_axes", lambda: None)
    yield run
    run.stop()
    shared_state.set_runtime_active(False)
    run_scope._reset_for_tests()


def test_run_start_resends_every_row_and_stop_ends_feedback(
    fb: SimpleNamespace, runner: code_runner.CodeRunner
) -> None:
    from gremlin.profile import Profile

    fb.rows.append(_row("m", "mode", "/mode"))
    fb.rows.append(
        _row("b", "vjoy_button", "/b1", 1, 3, min=0.0, max=127.0, type="int")
    )
    fb.vjoy[(1, "button", 3)] = True
    runner.start(Profile(), "Default")
    assert osc_feedback.instance().is_running()
    assert ("t1", "/mode", ["Default"], ["text"]) in fb.out.sent
    assert ("t1", "/b1", [127], ["int"]) in fb.out.sent
    runner.stop()
    assert not osc_feedback.instance().is_running()
    fb.out.sent.clear()
    fb.vjoy[(1, "button", 3)] = False
    _poll()
    QtTest.QTest.qWait(30)
    assert fb.out.sent == []


def test_run_start_without_resend_sends_only_changes(fb: SimpleNamespace) -> None:
    fb.server["resend_run"] = False
    fb.rows.append(_row("b", "vjoy_button", "/b1", 1, 3))
    osc_feedback.start("a.xml")
    _poll()
    assert fb.out.sent == []
    fb.vjoy[(1, "button", 3)] = True
    _poll()
    assert fb.out.sent == [("t1", "/b1", [1.0], None)]


# -- sources and values ------------------------------------------------------


def test_vjoy_axis_scales_to_min_max_and_type(fb: SimpleNamespace) -> None:
    fb.server["resend_run"] = False
    fb.rows.append(_row("a", "vjoy_axis", "/ax", 2, 1, min=0.0, max=100.0, type="int"))
    fb.rows.append(_row("t", "vjoy_axis", "/axt", 2, 1, min=-1.0, max=1.0, type="text"))
    osc_feedback.start()
    fb.vjoy[(2, "axis", 1)] = 0.5
    _poll()
    assert ("t1", "/ax", [75], ["int"]) in fb.out.sent
    assert ("t1", "/axt", ["0.5"], ["text"]) in fb.out.sent


def test_logical_device_control_is_a_source(fb: SimpleNamespace) -> None:
    from gremlin.logical_device import LogicalDevice

    device = LogicalDevice()
    button = device.create(InputType.JoystickButton, label="FB test button")
    try:
        fb.server["resend_run"] = False
        fb.rows.append(_row("l", "logical", "/ld", None, button.uid, type="bool"))
        osc_feedback.start()
        button.update(True)
        _poll()
        assert fb.out.sent == [("t1", "/ld", [True], ["bool"])]
    finally:
        device.delete(button.identifier)


def test_osc_input_echo_follows_the_runtime(
    fb: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(odf, "read_server", lambda: dict(fb.server))
    monkeypatch.setattr(
        shared_state,
        "current_profile",
        SimpleNamespace(inputs={osc.OSC_DEVICE_UUID: [object()]}),
    )
    monkeypatch.setattr(osc, "OscListener", mock.MagicMock())
    rows = OscDevice().rows
    saved = rows.to_dict()
    rows.reset()
    runtime = OscRuntime()
    try:
        row = rows.create(InputType.JoystickButton, "/in")
        fb.server["resend_run"] = False
        fb.rows.append(_row("e", "osc_input", "/echo", None, row.uid))
        osc_feedback.start()
        runtime.start()
        runtime._on_main("/in", (1.0,))
        _poll()
        runtime._on_main("/in", (0.0,))
        _poll()
        QtTest.QTest.qWait(20)  # within the 1 ms rate gap: the timer sends it
        assert fb.out.sent == [
            ("t1", "/echo", [1.0], None),
            ("t1", "/echo", [0.0], None),
        ]
    finally:
        runtime.stop()
        rows.load_dict(saved)


# -- switches, rate limit ----------------------------------------------------


def test_master_off_and_row_off_send_nothing(fb: SimpleNamespace) -> None:
    fb.rows.append(_row("b", "vjoy_button", "/b1", 1, 3))
    fb.rows.append(_row("c", "vjoy_button", "/b2", 1, 4, enabled=False))
    fb.server["feedback_enabled"] = False
    osc_feedback.start()
    fb.vjoy[(1, "button", 3)] = True
    _poll()
    assert fb.out.sent == []
    fb.server["feedback_enabled"] = True
    osc_feedback.instance().reload()
    fb.vjoy[(1, "button", 4)] = True
    _poll()
    assert [s[1] for s in fb.out.sent] == ["/b1"]


def test_rate_limit_coalesces_to_the_latest_value(fb: SimpleNamespace) -> None:
    fb.server["resend_run"] = False
    fb.server["feedback_rate"] = 10  # one message per 100 ms per address
    fb.rows.append(_row("a", "vjoy_axis", "/ax", 1, 1, min=-1.0, max=1.0))
    osc_feedback.start()
    for value in (0.1, 0.2, 0.3):
        fb.vjoy[(1, "axis", 1)] = value
        _poll()
    assert [s[2] for s in fb.out.sent] == [[pytest.approx(0.1)]]
    QtTest.QTest.qWait(150)  # the poll timer sends the waiting value
    assert [s[2] for s in fb.out.sent] == [[pytest.approx(0.1)], [pytest.approx(0.3)]]


# -- resends -----------------------------------------------------------------


def test_mode_change_resends_everything(fb: SimpleNamespace) -> None:
    fb.server["resend_run"] = False
    fb.rows.append(_row("b", "vjoy_button", "/b1", 1, 3))
    osc_feedback.start()
    osc_feedback.instance()._on_mode_changed("Other")
    assert fb.out.sent == [("t1", "/b1", [0.0], None)]
    fb.server["resend_mode"] = False
    osc_feedback.instance().reload()
    fb.out.sent.clear()
    osc_feedback.instance()._on_mode_changed("Other")
    assert fb.out.sent == []


def test_mode_signal_from_mode_manager_reaches_feedback(fb: SimpleNamespace) -> None:
    fb.server["resend_run"] = False
    fb.rows.append(_row("b", "vjoy_button", "/b1", 1, 3))
    osc_feedback.start()
    ModeManager().mode_changed.emit("Default")
    QtTest.QTest.qWait(10)
    assert fb.out.sent == [("t1", "/b1", [0.0], None)]


def test_profile_switch_resends_when_run_resend_is_off(fb: SimpleNamespace) -> None:
    fb.server["resend_run"] = False
    fb.rows.append(_row("b", "vjoy_button", "/b1", 1, 3))
    osc_feedback.start("a.xml")
    osc_feedback.stop()
    osc_feedback.start("a.xml")
    assert fb.out.sent == []
    osc_feedback.stop()
    osc_feedback.start("b.xml")
    assert fb.out.sent == [("t1", "/b1", [0.0], None)]
    fb.server["resend_profile"] = False
    osc_feedback.stop()
    fb.out.sent.clear()
    osc_feedback.start("c.xml")
    assert fb.out.sent == []


def test_sync_address_is_consumed_and_resends_to_the_sender(
    fb: SimpleNamespace,
) -> None:
    fb.server["resend_run"] = False
    fb.rows.append(_row("b", "vjoy_button", "/b1", 1, 3, target="reply"))
    osc_feedback.start()
    assert osc_feedback.handle_incoming("/other", (), ("10.0.0.5", 9000)) is False
    assert osc_feedback.handle_incoming("/gremlin/sync", (), ("10.0.0.5", 9000)) is True
    QtTest.QTest.qWait(10)
    assert fb.out.senders == [("10.0.0.5", 9000)]
    assert fb.out.sent == [("reply", "/b1", [0.0], None)]
    fb.server["sync_enabled"] = False
    osc_feedback.instance().reload()
    assert osc_feedback.handle_incoming("/gremlin/sync", (), None) is False


def test_sync_from_another_thread_sends_on_the_main_thread(fb: SimpleNamespace) -> None:
    import threading

    from PySide6 import QtCore

    fb.server["resend_run"] = False
    fb.rows.append(_row("b", "vjoy_button", "/b1", 1, 3))
    threads: list[bool] = []
    fb.out.send = lambda *a, **k: (
        threads.append(  # type: ignore[method-assign]
            QtCore.QThread.currentThread()
            is QtCore.QCoreApplication.instance().thread()
        )
        or True
    )
    osc_feedback.start()
    worker = threading.Thread(
        target=lambda: osc_feedback.handle_incoming("/gremlin/sync", (), None)
    )
    worker.start()
    worker.join(2)
    QtTest.QTest.qWait(30)
    assert threads == [True]


def test_sync_without_a_run_is_still_consumed(fb: SimpleNamespace) -> None:
    fb.rows.append(_row("b", "vjoy_button", "/b1", 1, 3))
    assert osc_feedback.handle_incoming("/gremlin/sync", (), None) is True
    QtTest.QTest.qWait(10)
    assert fb.out.sent == []


def test_a_value_refused_while_output_is_off_goes_out_when_it_is_back_on(
    fb: SimpleNamespace,
) -> None:
    # Output off: osc_output refuses (False). The controller must not stay out
    # of date once output is back on (D-09-OSC-FEEDBACK).
    fb.rows.append(_row("b", "vjoy_button", "/b1", 1, 3))
    refused = {"on": True}
    real_send = fb.out.send

    def send(target_id, address, values, types=None):  # noqa: ANN001, ANN202
        if refused["on"]:
            return False
        return real_send(target_id, address, values, types)

    fb.out.send = send
    osc_feedback.start()
    fb.vjoy[(1, "button", 3)] = True
    time.sleep(0.05)  # past the gap since the Run-start resend
    _poll()  # the change is tried now, and refused
    assert fb.out.sent == []
    refused["on"] = False
    time.sleep(0.05)  # past the rate limit's gap since the refused try
    _poll()
    assert fb.out.sent, "nothing went out once output was back on"
    address, values = fb.out.sent[-1][1], fb.out.sent[-1][2]
    assert (address, float(values[0])) == ("/b1", 1.0)
