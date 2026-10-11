# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""OSC always listens while the program is open and "Listen for OSC
messages" is on (D-09-OSC-ALWAYS-LISTEN): with the Monitor closed and the
profile stopped a loopback message updates the input's live value and last
seen and is traced; turning the switch off closes the port at once and on
opens it; Run and Stop leave it open; quit closes it; a port that can't open
shows its error once. Loopback only (127.0.0.1, an OS-picked port).

Spec: 09 S172a, G-OSC7, Q5 (D-09-OSC-ALWAYS-LISTEN).
"""

from __future__ import annotations

import socket
import sys
from collections.abc import Iterator
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest
from PySide6 import QtTest

from gremlin import osc, shared_state, trace
from gremlin import osc_device_file as odf
from gremlin.osc import OscDevice, OscRuntime
from gremlin.profile import InputItem, Library
from gremlin.types import InputType

BUTTON = InputType.JoystickButton


def _packet(address: str, *values: object) -> bytes:
    from pythonosc.osc_message_builder import OscMessageBuilder

    builder = OscMessageBuilder(address=address)
    for value in values:
        builder.add_arg(value)
    return builder.build().dgram


def _wait(check, ms: int = 3000) -> bool:  # noqa: ANN001
    for _ in range(ms // 10):
        if check():
            return True
        QtTest.QTest.qWait(10)
    return check()


def _receive_lines() -> list[str]:
    return [ln[3] for ln in trace.lines() if ln[1] == "OSC Receive"]


@pytest.fixture
def rt(qapp: object, monkeypatch: pytest.MonkeyPatch) -> Iterator[SimpleNamespace]:
    server: dict[str, Any] = {"host": "127.0.0.1"}
    monkeypatch.setattr(odf, "read_server", lambda: odf.clean_server(server))
    # The port the OS picks (the settings can't hold 0).
    monkeypatch.setattr(osc, "parse_port", lambda value, default=0: 0)
    monkeypatch.setattr(osc, "profile_uses_osc", lambda: False)
    monkeypatch.setattr(
        shared_state,
        "current_profile",
        SimpleNamespace(inputs={osc.OSC_DEVICE_UUID: [InputItem(Library())]}),
    )
    traffic = ModuleType("gremlin.osc_traffic")
    traffic.note = lambda *a: None  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "gremlin.osc_traffic", traffic)
    from gremlin.signal import signal as ui_signal

    errors: list[tuple[str, str]] = []

    def on_error(title: str, detail: str) -> None:
        errors.append((title, detail))

    ui_signal.showError.connect(on_error)
    rows = OscDevice().rows
    saved = rows.to_dict()
    rows.reset()
    runtime = OscRuntime()
    runtime.stop()
    runtime.reset_live()
    trace._reset_for_tests()
    trace.set_enabled(True)
    trace.set_osc("receive", True)
    yield SimpleNamespace(runtime=runtime, rows=rows, server=server, errors=errors)
    ui_signal.showError.disconnect(on_error)
    if hasattr(runtime, "close_always"):
        runtime.close_always()
    runtime.stop()
    runtime._unbind()
    runtime.reset_live()
    rows.load_dict(saved)
    trace.set_osc_all(False)
    trace._reset_for_tests()


def _send(runtime: OscRuntime, data: bytes) -> None:
    listener = runtime._listener
    assert listener is not None
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.sendto(data, ("127.0.0.1", listener.bound_port()))


def test_stopped_without_the_monitor_a_message_updates_live_and_is_traced(
    rt: SimpleNamespace,
) -> None:
    row = rt.rows.create(BUTTON, "/btn")
    rt.runtime.open_always()
    assert rt.runtime.is_open()
    port = rt.runtime._listener.bound_port()
    assert f"port 127.0.0.1:{port} open (always listening)" in _receive_lines()
    _send(rt.runtime, _packet("/btn", 1.0))
    assert _wait(lambda: rt.runtime.live(row.uid) is not None)
    live = rt.runtime.live(row.uid)
    assert live["pressed"] is True and live["last_seen"] is not None
    assert _wait(lambda: any(t.startswith("in ") and "/btn" in t
                             for t in _receive_lines()))


def test_listen_switch_off_closes_the_port_and_on_opens_it(
    rt: SimpleNamespace,
) -> None:
    rt.runtime.open_always()
    assert rt.runtime.is_open()
    rt.server["enabled"] = False
    rt.runtime.sync_bind()  # what oscServerSettingsChanged calls
    assert not rt.runtime.is_open()
    rt.server["enabled"] = True
    rt.runtime.sync_bind()
    assert rt.runtime.is_open()


def test_run_and_stop_leave_the_port_open_and_quit_closes_it(
    rt: SimpleNamespace,
) -> None:
    rt.runtime.open_always()
    listener = rt.runtime._listener
    rt.runtime.start()  # a profile with no OSC inputs
    assert rt.runtime._listener is listener
    rt.runtime.stop()
    assert rt.runtime._listener is listener and rt.runtime.is_open()
    # The Monitor folding doesn't close it either.
    assert rt.runtime.hold_open("mon")
    rt.runtime.release_open("mon")
    assert rt.runtime.is_open()
    rt.runtime.close_always()
    assert not rt.runtime.is_open()


def test_a_taken_port_shows_its_error_once(
    rt: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    class Refused:
        def __init__(self, host: str, port: int, callback: object) -> None:
            self.host, self.port = host, port

        def start(self) -> None:
            raise OSError(10048, "address in use")

        def stop(self) -> None:
            pass

    monkeypatch.setattr(osc, "OscListener", Refused)
    rt.runtime.open_always()
    assert not rt.runtime.is_open()
    assert len(rt.errors) == 1 and "Could not bind" in rt.errors[0][0]
    # A Run of a profile with no OSC inputs doesn't show it again.
    rt.runtime.start()
    rt.runtime.stop()
    assert len(rt.errors) == 1
    assert any("(always listening)" in t for t in _receive_lines())


# -- the real Run path (bug seen live 2026-10-10: Stop closed the port) ------


@pytest.fixture
def runner(rt: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> Iterator[Any]:
    """A CodeRunner whose drivers, devices, sound and speech are stand-ins;
    OSC's runtime and the Run's Stop stages (run_scope) are the real ones."""
    from unittest import mock

    from gremlin import code_runner, run_scope

    for name in ("output", "InputModuleRuntime", "audio_player", "tts"):
        monkeypatch.setattr(code_runner, name, mock.MagicMock())
    listener = mock.MagicMock()
    fake_listener = mock.MagicMock(return_value=listener)
    fake_listener.instance = None
    monkeypatch.setattr(code_runner.event_handler, "EventListener", fake_listener)
    run_scope.stop()
    run_scope._reset_for_tests()
    run = code_runner.CodeRunner()
    monkeypatch.setattr(run, "_refresh_axes", lambda: None)
    yield run
    run.stop()
    run_scope._reset_for_tests()
    shared_state.set_runtime_active(False)


@pytest.mark.parametrize("uses_osc", [True, False])
def test_run_and_stop_through_the_code_runner_keep_the_port_open(
    rt: SimpleNamespace,
    runner: Any,  # noqa: ANN401
    monkeypatch: pytest.MonkeyPatch,
    uses_osc: bool,
) -> None:
    from gremlin.profile import Profile

    monkeypatch.setattr(osc, "profile_uses_osc", lambda: uses_osc)
    rt.runtime.open_always()
    listener = rt.runtime._listener
    assert listener is not None
    for _ in range(2):  # two Run/Stop cycles
        runner.start(Profile(), "Default")
        assert rt.runtime._listener is listener
        runner.stop()
        assert rt.runtime._listener is listener and rt.runtime.is_open()
    assert "port closed" not in _receive_lines()
