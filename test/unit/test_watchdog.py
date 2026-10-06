# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Log When Not Responding (gremlin/watchdog.py).

When the main loop stops for the threshold, system.log gets "Not
responding" with every thread's stack, once per freeze, and "Responding
again" when it comes back. The option (Options › Diagnostics) is off by
default and takes effect at once.

The freeze test steps gremlin.clock.monotonic and waits for results, no
fixed waits (GL-001, GL-002; 01 S94).
"""

from __future__ import annotations

import sys

sys.path.append(".")

import threading
import time
from collections.abc import Callable, Iterator

import pytest
from PySide6 import QtCore, QtTest

from gremlin import clock, watchdog
from gremlin.config import Configuration


@pytest.fixture(autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    yield app


_LIMIT_S = 10.0  # generous: a busy PC is slow, never wrong


class _Clock:
    """clock.monotonic for the watchdog: the test moves the time by hand and
    counts the watchdog thread's reads, so it can wait for its next checks
    (the beats read it on the main thread)."""

    def __init__(self) -> None:
        self.value = 1000.0
        self.watch_reads = 0

    def __call__(self) -> float:
        if threading.current_thread() is not threading.main_thread():
            self.watch_reads += 1
        return self.value


def _wait_while_stuck(done: Callable[[], bool]) -> None:
    """Waits without running the main loop (no beats), up to the limit."""
    end = time.monotonic() + _LIMIT_S
    while not done():
        assert time.monotonic() < end, "the watchdog thread did not get there"
        time.sleep(0.01)


def _wait_running(done: Callable[[], bool]) -> None:
    """Waits while the main loop runs (beats go on), up to the limit."""
    end = time.monotonic() + _LIMIT_S
    while not done():
        assert time.monotonic() < end, "the watchdog thread did not get there"
        QtTest.QTest.qWait(10)


def test_a_freeze_is_logged_once_with_the_stacks_then_the_recovery(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _Clock()
    monkeypatch.setattr(clock, "monotonic", fake)
    threshold = 0.4
    dog = watchdog.Watchdog(threshold_s=threshold)
    dog.start()
    try:
        # Responding: clock time runs on, many times the threshold, and the
        # beats keep up, so the watchdog's checks say nothing. A step is made
        # once a beat has read the last one, and is under half the threshold:
        # the thread reads the last beat before the clock, so a check can
        # straddle one step more (a step past the threshold would race it).
        start, checked_from = fake.value, None
        while checked_from is None or fake.watch_reads < checked_from + 3:
            fake.value += threshold * 0.45
            now = fake.value
            _wait_running(lambda: dog._last_beat == now)
            if checked_from is None and now - start >= 4 * threshold:
                checked_from = fake.watch_reads
        assert fake.value - start >= 4 * threshold
        assert "Not responding" not in caplog.text
        # The main loop is stuck for 10 s of clock time.
        fake.value += 10.0
        _wait_while_stuck(lambda: "Not responding for" in caplog.text)
        # Still stuck for two more checks: no repeat.
        seen = fake.watch_reads
        _wait_while_stuck(lambda: fake.watch_reads >= seen + 2)
        # And back: the next beat reads the clock and the watchdog sees it.
        _wait_running(lambda: "Responding again after" in caplog.text)
    finally:
        dog.stop()
    assert caplog.text.count("Not responding for 10 s") == 1
    assert "Threads: MainThread" in caplog.text
    assert "test_a_freeze_is_logged_once" in caplog.text  # where it was stuck
    assert caplog.text.count("Responding again after 10 s") == 1


def test_it_stops_cleanly() -> None:
    dog = watchdog.Watchdog()
    dog.start()
    assert dog.running
    dog.stop()
    assert not dog.running


def test_the_option_is_off_by_default_and_takes_effect_at_once() -> None:
    config = Configuration()
    stored = config.value(*watchdog.OPTION)
    assert stored is False  # the tests start from new settings
    try:
        watchdog.apply()
        assert watchdog._watchdog is None or not watchdog._watchdog.running
        config.set(*watchdog.OPTION, True)
        watchdog.apply()
        assert watchdog._watchdog is not None and watchdog._watchdog.running
        config.set(*watchdog.OPTION, False)
        watchdog.apply()
        assert not watchdog._watchdog.running
    finally:
        config.set(*watchdog.OPTION, stored)
        watchdog.apply()


def test_the_option_is_in_options_diagnostics() -> None:
    from gremlin.ui import option

    groups = dict(dict(option._LAYOUT)["General"])
    assert ("global", "general", "log-when-not-responding") in groups["Diagnostics"]
    assert option._ENTRY_TITLES["log-when-not-responding"] == "Log When Not Responding"
