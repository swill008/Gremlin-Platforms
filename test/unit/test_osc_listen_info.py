# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""OscRuntime.listenInfo() for the Home OSC card (D-09-OSC-CARD-LINE):
listening on the bound host and port, a port held by another socket gives
"port <p> is in use", closed when nothing needs the port or OSC is Off, and
listenChanged follows each change. Bind errors map to short reasons.
Loopback only (127.0.0.1, an OS-picked port).

Spec: 09 S172a, D-09-OSC-CARD-LINE.
"""

from __future__ import annotations

import errno
import socket
import sys
from collections.abc import Iterator
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

from gremlin import osc
from gremlin import osc_device_file as odf
from gremlin.osc import OscRuntime


@pytest.fixture
def rt(qapp: object, monkeypatch: pytest.MonkeyPatch) -> Iterator[SimpleNamespace]:
    server: dict[str, Any] = {"host": "127.0.0.1"}
    ports = {"port": 0}  # 0: the port the OS picks
    monkeypatch.setattr(odf, "read_server", lambda: odf.clean_server(server))
    monkeypatch.setattr(osc, "parse_port", lambda value, default=0: ports["port"])
    monkeypatch.setattr(osc, "profile_uses_osc", lambda: False)
    traffic = ModuleType("gremlin.osc_traffic")
    traffic.note = lambda *a: None  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "gremlin.osc_traffic", traffic)
    from gremlin.signal import signal as ui_signal

    errors: list[tuple[str, str]] = []

    def on_error(title: str, detail: str) -> None:
        errors.append((title, detail))

    ui_signal.showError.connect(on_error)
    runtime = OscRuntime()
    runtime.stop()
    runtime.close_always()
    changes: list[dict[str, Any]] = []

    def on_change() -> None:
        changes.append(runtime.listenInfo())

    runtime.listenChanged.connect(on_change)
    yield SimpleNamespace(
        runtime=runtime, server=server, ports=ports, errors=errors, changes=changes
    )
    runtime.listenChanged.disconnect(on_change)
    ui_signal.showError.disconnect(on_error)
    runtime.close_always()
    runtime.stop()
    runtime._unbind()
    runtime._bind_failure = None


def test_listening_gives_the_bound_host_and_port(rt: SimpleNamespace) -> None:
    rt.runtime.open_always()
    port = rt.runtime._listener.bound_port()
    assert port > 0
    info = rt.runtime.listenInfo()
    assert info == {"state": "listening", "host": "127.0.0.1", "port": port,
                    "reason": ""}
    assert rt.changes[-1] == info


def test_a_port_held_by_another_socket_is_in_use(rt: SimpleNamespace) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as holder:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            holder.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        holder.bind(("127.0.0.1", 0))
        port = holder.getsockname()[1]
        rt.ports["port"] = port
        rt.runtime.open_always()
        assert not rt.runtime.is_open()
        info = rt.runtime.listenInfo()
        assert info == {"state": "failed", "host": "127.0.0.1", "port": port,
                        "reason": f"port {port} is in use"}
        assert rt.changes[-1] == info
        assert len(rt.errors) == 1  # the existing error message still shows
    # Freed: a settings change binds and the failure goes.
    rt.runtime.sync_bind()
    assert rt.runtime.listenInfo()["state"] == "listening"


def test_closed_when_nothing_needs_the_port_and_off(rt: SimpleNamespace) -> None:
    info = rt.runtime.listenInfo()
    assert info["state"] == "closed" and info["reason"] == ""
    rt.runtime.open_always()
    assert rt.runtime.listenInfo()["state"] == "listening"
    rt.server["enabled"] = False
    rt.runtime.sync_bind()
    info = rt.runtime.listenInfo()
    assert info["state"] == "closed" and info["reason"] == "off"
    assert rt.changes[-1] == info
    rt.server["enabled"] = True
    rt.runtime.sync_bind()
    assert rt.runtime.listenInfo()["state"] == "listening"
    rt.runtime.close_always()
    info = rt.runtime.listenInfo()
    assert info["state"] == "closed" and info["reason"] == ""
    assert rt.changes[-1] == info


def test_closed_before_any_bind_gives_the_saved_host_and_port(
    rt: SimpleNamespace,
) -> None:
    # Fresh: nothing has read the settings yet (only the defaults are held).
    rt.runtime._settings = dict(osc.SERVER_DEFAULTS)
    rt.ports["port"] = 9123
    assert rt.runtime.listenInfo() == {
        "state": "closed", "host": "127.0.0.1", "port": 9123, "reason": ""
    }


def test_a_failure_clears_when_nothing_needs_the_port(
    rt: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    class Refused:
        def __init__(self, host: str, port: int, callback: object) -> None:
            self.host, self.port = host, port

        def start(self) -> None:
            raise OSError(errno.EACCES, "access denied")

        def stop(self) -> None:
            pass

    monkeypatch.setattr(osc, "OscListener", Refused)
    rt.ports["port"] = 9000
    rt.runtime.open_always()
    assert rt.runtime.listenInfo()["reason"] == "Windows refused port 9000"
    rt.runtime.close_always()
    assert rt.runtime.listenInfo()["state"] == "closed"


def _err(code: int, text: str = "boom") -> OSError:
    exc = OSError(code, text)
    exc.winerror = code  # type: ignore[attr-defined]
    return exc


@pytest.mark.parametrize(
    ("exc", "reason"),
    [
        (_err(10048), "port 8001 is in use"),
        (OSError(errno.EADDRINUSE, "in use"), "port 8001 is in use"),
        (_err(10049), "10.1.2.3 is not an address of this PC"),
        (_err(10013), "Windows refused port 8001"),
        (OSError(errno.ENOBUFS, "No buffer space."), "No buffer space"),
    ],
)
def test_bind_errors_map_to_short_reasons(exc: OSError, reason: str) -> None:
    assert osc.bind_error_reason("10.1.2.3", 8001, exc) == reason
