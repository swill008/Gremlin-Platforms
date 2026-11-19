# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Not responding dump ends with the recent events and the last known
window state (01 S113, S177); stall begin/end go to the window events."""

from __future__ import annotations

import sys

sys.path.append(".")

import time
import types
from collections.abc import Iterator

import pytest
from PySide6 import QtCore

from gremlin import clock, trace, watchdog


@pytest.fixture(autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    yield QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])


def _freeze(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """A freeze of 10 s of clock time with no beats; stops once logged."""
    value = [1000.0]
    monkeypatch.setattr(clock, "monotonic", lambda: value[0])
    dog = watchdog.Watchdog(threshold_s=0.4)
    dog.start()
    try:
        value[0] += 10.0
        end = time.monotonic() + 10.0
        while "Not responding for" not in caplog.text:
            assert time.monotonic() < end, "no dump"
            time.sleep(0.01)
    finally:
        dog.stop()


def test_a_freeze_dump_includes_the_recent_events(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    trace.recent("Main window", "tray: entered (minimize)")
    notes: list[tuple[str, str]] = []
    fake = types.ModuleType("gremlin.ui.window_trace")
    fake.last_known = lambda: {"visible": True, "state": "Minimized"}  # type: ignore[attr-defined]
    fake.note = lambda c, t, ring=True: notes.append((c, t))  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "gremlin.ui.window_trace", fake)
    _freeze(monkeypatch, caplog)
    text = caplog.text
    assert "Recent events:" in text
    assert "tray: entered (minimize)" in text
    assert "Last known window state:" in text
    assert "state: Minimized" in text
    assert any("stall began" in t for _c, t in notes)


def test_the_stall_texts_are_trace_events_while_timing_is_on(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    events: list[str] = []
    monkeypatch.setattr(trace, "timing_on", lambda: True)
    monkeypatch.setattr(trace, "event", events.append)
    _freeze(monkeypatch, caplog)
    assert any(e.startswith("Not responding for") for e in events)
