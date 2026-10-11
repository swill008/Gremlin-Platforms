# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""09 S18: Listen that can't open the port says "Could not start OSC
listener." and, when the port is in use, names the program holding it like
the bind error does (S142); it is logged (S143); OSC off keeps its own text.
Listen on the OSC page and Bulk capture both go through listen_once.
Network: loopback only, on a port the OS picks (port 0)."""

from __future__ import annotations

import logging
import os
import socket
import sys
from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

import pytest

from gremlin import osc, shared_state
from gremlin import osc_device_file as odf
from gremlin.osc import OscRuntime
from gremlin.profile import InputItem, Library


@pytest.fixture
def rt(qapp: object, monkeypatch: pytest.MonkeyPatch) -> Iterator[SimpleNamespace]:
    server: dict[str, Any] = {"host": "127.0.0.1"}
    monkeypatch.setattr(odf, "read_server", lambda: dict(server))
    monkeypatch.setattr(
        shared_state,
        "current_profile",
        SimpleNamespace(inputs={osc.OSC_DEVICE_UUID: [InputItem(Library())]}),
    )
    runtime = OscRuntime()
    runtime.stop()
    errors: list[tuple[str, str]] = []

    from gremlin.signal import signal as ui_signal

    def on_error(title: str, detail: str) -> None:
        errors.append((title, detail))

    ui_signal.showError.connect(on_error)
    yield SimpleNamespace(runtime=runtime, errors=errors, server=server)
    ui_signal.showError.disconnect(on_error)
    runtime.cancel_listen()
    runtime.stop()


@pytest.mark.skipif(sys.platform != "win32", reason="port owner lookup is Windows")
@pytest.mark.parametrize("bulk", [False, True], ids=["listen", "bulk"])
def test_listen_names_the_port_holder(
    rt: SimpleNamespace, caplog: pytest.LogCaptureFixture, bulk: bool
) -> None:
    caplog.set_level(logging.WARNING)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        rt.server["port"] = port
        start = rt.runtime.listen_bulk if bulk else rt.runtime.listen_once
        assert start() is False
    assert not rt.runtime.is_listening()
    # One message, the Listen one, carrying the bind error's holder text.
    assert len(rt.errors) == 1, rt.errors
    title, detail = rt.errors[0]
    assert title == "Could not start OSC listener."
    assert f"127.0.0.1:{port}" in detail
    assert f"PID {os.getpid()}" in detail
    assert "python" in detail.lower()
    names = {r.name for r in caplog.records if str(port) in r.getMessage()}
    assert {"user", "system"} <= names


def test_listen_when_osc_is_off(rt: SimpleNamespace) -> None:
    rt.server["enabled"] = False
    assert rt.runtime.listen_once() is False
    assert rt.errors == [
        (
            "Could not start OSC listener.",
            "Turn OSC on and check its host and port in OSC › Module Setup.",
        )
    ]
