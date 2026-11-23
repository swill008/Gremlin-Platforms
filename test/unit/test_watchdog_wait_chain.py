# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The freeze report's wait chain (gremlin/watchdog.py; 01 S113): what Windows
says the main thread is waiting on, via Wait Chain Traversal."""

from __future__ import annotations

import sys

sys.path.append(".")

import logging
import os
import threading
from collections.abc import Iterator

import pytest
from PySide6 import QtCore

from gremlin import watchdog

_TYPE = {n: i + 1 for i, n in enumerate(watchdog._OBJECT_TYPES)}
_STATUS = {n: i + 1 for i, n in enumerate(watchdog._OBJECT_STATUSES)}


@pytest.fixture(autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    yield QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])


def _lock(kind: str, status: str, name: str = "") -> watchdog.WaitChainNodeInfo:
    n = watchdog.WaitChainNodeInfo()
    n.ObjectType, n.ObjectStatus = _TYPE[kind], _STATUS[status]
    n.u.LockObject.ObjectName = name
    return n


def _thread(status: str, pid: int, tid: int) -> watchdog.WaitChainNodeInfo:
    n = watchdog.WaitChainNodeInfo()
    n.ObjectType, n.ObjectStatus = _TYPE["Thread"], _STATUS[status]
    n.u.ThreadObject.ProcessId, n.u.ThreadObject.ThreadId = pid, tid
    return n


def test_the_formatter_names_each_node() -> None:
    nodes = [
        _thread("Blocked", os.getpid(), 4321),
        _lock("SendMessage", "Blocked"),
        _lock("Mutex", "Owned", "Global\\thing"),
        _thread("Running", 999, 77),
    ]
    text = watchdog.format_wait_chain(nodes, True, {4321: "input thread"})
    lines = text.splitlines()
    assert lines[0] == "Main thread wait chain (Windows):"
    assert lines[1] == "  Thread, Blocked, this process, thread 4321 (input thread)"
    assert lines[2] == "  SendMessage, Blocked"
    assert lines[3] == "  Mutex, Owned, Global\\thing"
    assert lines[4] == "  Thread, Running, process 999, thread 77"
    assert lines[5] == "  deadlock cycle"


def test_no_cycle_no_cycle_line() -> None:
    text = watchdog.format_wait_chain([_lock("Com", "Blocked")], False)
    assert "deadlock" not in text


@pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
@pytest.mark.parametrize("how", ["false", "raise"])
def test_an_api_failure_gives_the_not_available_line(
    monkeypatch: pytest.MonkeyPatch, how: str
) -> None:
    def broken(tid: int) -> tuple[list, bool]:
        if how == "raise":
            raise RuntimeError("boom")
        raise OSError("GetThreadWaitChain failed (5)")

    monkeypatch.setattr(watchdog, "_query_wait_chain", broken)
    text = watchdog.wait_chain_block()
    assert text.startswith("Main thread wait chain: not available (")


@pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
def test_the_freeze_report_includes_the_wait_chain(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    chain = ([_lock("SendMessage", "Blocked")], False)
    monkeypatch.setattr(watchdog, "_query_wait_chain", lambda tid: chain)
    caplog.set_level(logging.WARNING, logger="system")
    dog = watchdog.Watchdog(threshold_s=0.2)
    dog.start()
    try:
        # No main loop runs here: the beats stop. Wait for the warning
        # itself: it is logged only after every block of the report, and
        # stop() waits just 2 s for the watchdog's thread (CI seed 418907).
        pause = threading.Event()
        for _ in range(500):  # at most about 10 s
            if "Not responding for" in caplog.text:
                break
            pause.wait(0.02)
    finally:
        dog.stop()
    assert "Not responding for" in caplog.text
    assert "Main thread wait chain (Windows):\n  SendMessage, Blocked" in caplog.text
    assert caplog.text.index("Threads:") < caplog.text.index("Main thread wait chain")


@pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
def test_a_real_call_on_a_blocked_thread_gives_nodes() -> None:
    gate = threading.Event()
    t = threading.Thread(target=gate.wait, args=(10.0,), name="wc-helper")
    t.start()
    try:
        while not t.native_id:
            pass
        nodes, _cycle = watchdog._query_wait_chain(t.native_id)
        assert len(nodes) >= 1
    finally:
        gate.set()
        t.join()
