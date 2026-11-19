# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The not-responding watchdog also watches the input thread (S113 amendment).

The input thread's heartbeat is faked (is_running / silent_for / last_beat);
the watchdog thread's own checks are waited for by counting the reads.
"""

from __future__ import annotations

import sys

sys.path.append(".")

import threading
import time
import types
from collections.abc import Callable, Iterator

import pytest
from PySide6 import QtCore

from gremlin import input_thread, watchdog

_LIMIT_S = 10.0


@pytest.fixture(autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    yield QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])


@pytest.fixture(autouse=True)
def notes(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    """A stand-in window_trace (as test_watchdog_recent does), so the real one
    isn't imported here and left on the gremlin.ui package for other tests."""
    got: list[tuple[str, str]] = []
    stand_in = types.ModuleType("gremlin.ui.window_trace")
    stand_in.note = lambda a, t, ring=True: got.append((a, t))  # type: ignore[attr-defined]
    stand_in.last_known = lambda: {}  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "gremlin.ui.window_trace", stand_in)
    ui = sys.modules.get("gremlin.ui")
    if ui is not None:
        monkeypatch.setattr(ui, "window_trace", stand_in, raising=False)
    return got


class _FakeInput:
    def __init__(self) -> None:
        self.running = True
        self.silent = 0.0
        self.reads = 0

    def is_running(self) -> bool:
        return self.running

    def silent_for(self) -> float:
        self.reads += 1
        return self.silent

    def last_beat(self) -> float | None:
        return time.monotonic() if self.running else None


def _wait(done: Callable[[], bool]) -> None:
    end = time.monotonic() + _LIMIT_S
    while not done():
        assert time.monotonic() < end, "the watchdog thread did not get there"
        time.sleep(0.01)


def _checks(fake: _FakeInput, count: int = 3) -> None:
    seen = fake.reads
    _wait(lambda: fake.reads >= seen + count)


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch) -> _FakeInput:
    f = _FakeInput()
    monkeypatch.setattr(input_thread, "is_running", f.is_running)
    monkeypatch.setattr(input_thread, "silent_for", f.silent_for)
    monkeypatch.setattr(input_thread, "last_beat", f.last_beat)
    return f


def _run(fake: _FakeInput, body: Callable[[watchdog.Watchdog], None]) -> None:
    dog = watchdog.Watchdog(threshold_s=0.4)
    dog.start()
    try:
        body(dog)
    finally:
        dog.stop()


def test_a_silent_input_thread_gives_one_dump_and_one_recovery(
    fake: _FakeInput, caplog: pytest.LogCaptureFixture
) -> None:
    def body(dog: watchdog.Watchdog) -> None:
        _checks(fake)
        assert "Input thread not responding" not in caplog.text
        fake.silent = 7.0
        _wait(lambda: "Input thread not responding for" in caplog.text)
        _checks(fake)  # still stalled: no repeat
        fake.silent = 0.1
        _wait(lambda: "Input thread responding again after" in caplog.text)
        _checks(fake)

    _run(fake, body)
    assert caplog.text.count("Input thread not responding for 7 s.") == 1
    assert caplog.text.count("Input thread responding again after") == 1
    assert "Threads: MainThread" in caplog.text
    assert "Recent events:" in caplog.text


def test_the_stall_goes_to_the_window_events_and_timing(
    fake: _FakeInput, monkeypatch: pytest.MonkeyPatch, notes: list[tuple[str, str]]
) -> None:
    from gremlin import trace

    events: list[str] = []
    monkeypatch.setattr(trace, "timing_on", lambda: True)
    monkeypatch.setattr(trace, "event", events.append)

    def body(dog: watchdog.Watchdog) -> None:
        fake.silent = 6.0
        _wait(lambda: len(notes) >= 1)
        fake.silent = 0.0
        _wait(lambda: len(notes) >= 2)

    _run(fake, body)
    assert notes[0][0] == "Input thread" and notes[0][1].startswith("stall began")
    assert notes[1][0] == "Input thread" and notes[1][1].startswith("stall ended")
    assert any(e.startswith("Input thread not responding") for e in events)
    assert any(e.startswith("Input thread responding again") for e in events)


def test_nothing_when_the_input_thread_is_not_running(
    fake: _FakeInput, caplog: pytest.LogCaptureFixture
) -> None:
    fake.running = False
    fake.silent = 30.0

    def body(dog: watchdog.Watchdog) -> None:
        time.sleep(1.2)  # several checks (every threshold / 2 = 0.2 s)

    _run(fake, body)
    assert "Input thread not responding" not in caplog.text
    assert fake.reads == 0


def test_a_failing_check_never_kills_the_watchdog(
    fake: _FakeInput, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom() -> float:
        raise RuntimeError("nope")

    monkeypatch.setattr(input_thread, "silent_for", boom)

    def body(dog: watchdog.Watchdog) -> None:
        time.sleep(0.8)
        assert dog.running

    _run(fake, body)


def test_the_real_input_thread_is_not_reported_when_off() -> None:
    # Option off: no watchdog thread exists, so nothing reads the heartbeat.
    assert not any(t.name == "not-responding watchdog" for t in threading.enumerate())
