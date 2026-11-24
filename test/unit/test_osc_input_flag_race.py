# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Thread audit N1: a packet is routed once (one read of the input-thread
flag under _state_lock in _from_thread), and main gets that decision, so a
packet arriving while start()/stop() flip the flag is applied exactly once,
on one thread, never twice and never dropped.

Spec: 09 (OSC runtime), 06 S100.
"""

from __future__ import annotations

import threading

import pytest
from PySide6 import QtCore

from gremlin import input_thread, osc
from gremlin.osc import OscRuntime


@pytest.fixture
def rt(monkeypatch: pytest.MonkeyPatch) -> OscRuntime:
    if QtCore.QCoreApplication.instance() is None:
        QtCore.QCoreApplication([])
    runtime = OscRuntime()
    # Put back after the test: the runtime is shared, and a later test
    # would see a Run (seed 809820, unit-2).
    monkeypatch.setattr(runtime, "_running", True)
    return runtime


def _collect(rt: OscRuntime, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Where each packet is applied: the input thread, or main (_handle
    applies only when the packet was not routed to the input thread)."""
    applied: list[str] = []
    monkeypatch.setattr(osc, "_call_hook", lambda *a, **k: False)
    monkeypatch.setattr(
        input_thread, "call", lambda fn, *a, **k: applied.append("input")
    )
    real_handle = rt._handle

    def handle(address, payload, peer=None, to_input=None):  # noqa: ANN001, ANN202
        if not (rt._route() if to_input is None else to_input):
            applied.append("main")
        return []

    monkeypatch.setattr(rt, "_handle", handle)
    del real_handle
    return applied


@pytest.mark.parametrize("flag_at_emit", [True, False])
def test_flip_between_emit_and_main_applies_once(
    rt: OscRuntime, monkeypatch: pytest.MonkeyPatch, flag_at_emit: bool
) -> None:
    """The flag changes after _from_thread chose and before main runs: the
    packet still goes to the one place chosen at emit time (old code:
    applied twice or dropped)."""
    applied = _collect(rt, monkeypatch)
    rt._input_here = flag_at_emit
    rt._from_thread("/a", (1.0,), None)
    rt._input_here = not flag_at_emit  # start()/stop() flipped it meanwhile
    QtCore.QCoreApplication.processEvents()
    assert applied == ["input" if flag_at_emit else "main"]


def test_route_read_under_lock(rt: OscRuntime) -> None:
    """start()/stop() hold the lock while they flip; _route waits for it."""
    rt._input_here = True
    seen: list[bool] = []
    with rt._state_lock:
        t = threading.Thread(target=lambda: seen.append(rt._route()))
        t.start()
        t.join(0.2)
        assert t.is_alive()  # blocked on the lock, no torn read
        rt._input_here = False
    t.join(2)
    assert seen == [False]


def test_each_packet_once_across_flips(
    rt: OscRuntime, monkeypatch: pytest.MonkeyPatch
) -> None:
    applied = _collect(rt, monkeypatch)
    n = 0
    for flag in (True, False, True, False, True):
        rt._input_here = flag
        rt._from_thread("/a", (1.0,), None)
        n += 1
        rt._input_here = not flag  # flips before main drains
        QtCore.QCoreApplication.processEvents()
    assert len(applied) == n
