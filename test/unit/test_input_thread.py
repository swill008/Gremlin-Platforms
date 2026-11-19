# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The input thread (gremlin/input_thread.py): a Qt thread with its own
event loop, started and stopped through gremlin.threads, fed by a command
queue whose waits are bounded. Thread batch 1 (claude/plans/fix-plans/
thread-input.md); nothing runs on it yet. These tests start the real thread.
"""

from __future__ import annotations

import sys

sys.path.append(".")

import threading
import time
from collections.abc import Iterator

import pytest
from PySide6 import QtCore

from gremlin import input_thread, threads


@pytest.fixture
def running(qapp: object) -> Iterator[None]:
    """The real input thread, stopped afterwards."""
    was_inline = input_thread.is_inline()
    input_thread.set_inline(False)
    input_thread.start()
    yield
    try:
        assert input_thread.stop(2.0)
    finally:
        input_thread.set_inline(was_inline)


def test_the_thread_is_listed_and_shutdown_stops_it(
    qapp: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Only this test's threads: shutdown() must not stop shared ones.
    monkeypatch.setattr(threads, "_live", {})
    input_thread.set_inline(False)
    try:
        input_thread.start()
        name = "Gremlin-Platforms: input thread"
        assert name in threads.running()
        assert input_thread.is_running()
        started = time.monotonic()
        assert name not in threads.shutdown(timeout=2.0)
        assert time.monotonic() - started < 2.0
        assert not input_thread.is_running()
        assert name not in threads.running()
    finally:
        input_thread.stop(2.0)


def test_call_runs_on_the_input_thread_in_order(running: None) -> None:
    seen: list[tuple[int, bool]] = []
    for n in range(20):
        input_thread.call(lambda n=n: seen.append((n, input_thread.is_input_thread())))
    input_thread.call_wait(lambda: None, timeout=2.0)
    assert [n for n, _ in seen] == list(range(20))
    assert all(on_input for _, on_input in seen)
    assert not input_thread.is_input_thread()


def test_stop_runs_the_calls_made_before_it(qapp: object) -> None:
    input_thread.set_inline(False)
    seen: list[int] = []
    try:
        input_thread.start()
        for n in range(5):
            input_thread.call(seen.append, n)
        assert input_thread.stop(2.0)
        assert seen == [0, 1, 2, 3, 4]
    finally:
        input_thread.stop(2.0)


def test_call_wait_returns_the_result_and_raises_the_error(running: None) -> None:
    assert input_thread.call_wait(lambda a, b: a + b, 2, 3, timeout=2.0) == 5

    def fail() -> None:
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        input_thread.call_wait(fail, timeout=2.0)


def test_call_wait_times_out_instead_of_hanging(running: None) -> None:
    release = threading.Event()
    started = time.monotonic()
    with pytest.raises(TimeoutError):
        input_thread.call_wait(release.wait, 5.0, timeout=0.2)
    assert time.monotonic() - started < 1.0
    release.set()


def test_stop_is_bounded_with_a_stuck_call(qapp: object) -> None:
    input_thread.set_inline(False)
    release = threading.Event()
    try:
        input_thread.start()
        stuck = threading.Event()

        def hang() -> None:
            stuck.set()
            release.wait(10.0)

        input_thread.call(hang)
        assert stuck.wait(2.0)
        started = time.monotonic()
        assert input_thread.stop(0.3) is False
        assert time.monotonic() - started < 1.0
    finally:
        release.set()
        assert input_thread.stop(2.0)


def test_a_failing_call_is_logged_and_the_thread_goes_on(
    running: None, caplog: pytest.LogCaptureFixture
) -> None:
    def fail() -> None:
        raise ValueError("boom")

    input_thread.call(fail)
    assert input_thread.call_wait(lambda: 7, timeout=2.0) == 7
    assert "A call on the input thread failed" in caplog.text


def test_inline_mode_runs_on_the_callers_thread() -> None:
    was = input_thread.is_inline()
    input_thread.set_inline(True)
    try:
        seen: list[int] = []
        input_thread.call(lambda: seen.append(threading.get_ident()))
        assert seen == [threading.get_ident()]
        assert input_thread.call_wait(lambda: 4, timeout=0.1) == 4
    finally:
        input_thread.set_inline(was)


def test_call_without_the_thread_or_inline_mode_raises() -> None:
    was = input_thread.is_inline()
    input_thread.set_inline(False)
    try:
        assert not input_thread.is_running()
        with pytest.raises(RuntimeError):
            input_thread.call(lambda: None)
    finally:
        input_thread.set_inline(was)


def test_a_timer_made_inside_call_fires_on_the_input_thread(running: None) -> None:
    fired = threading.Event()
    on_input: list[bool] = []
    keep: list[QtCore.QTimer] = []

    def fire() -> None:
        on_input.append(input_thread.is_input_thread())
        fired.set()

    def arm() -> None:
        timer = QtCore.QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(fire)
        timer.start(50)
        keep.append(timer)

    input_thread.call(arm)
    # The main thread runs no event loop meanwhile: the timer needs none here.
    assert fired.wait(2.0)
    assert on_input == [True]
    input_thread.call_wait(lambda: keep.clear(), timeout=2.0)


def test_heartbeat_goes_on_while_the_main_thread_is_blocked(running: None) -> None:
    first = input_thread.last_beat()
    assert first is not None
    time.sleep(input_thread.BEAT_S * 3)  # main thread busy, no Qt events
    later = input_thread.last_beat()
    assert later is not None and later > first
    assert input_thread.silent_for() < input_thread.BEAT_S * 2


@pytest.fixture
def raising_guards(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(threads, "guards_raise", True)


def test_guards_raise_on_the_wrong_thread(running: None, raising_guards: None) -> None:
    threads.assert_main("a window slot")
    with pytest.raises(threads.WrongThread):
        threads.assert_input("the claim gate")
    input_thread.call_wait(threads.assert_input, "the claim gate", timeout=2.0)
    with pytest.raises(threads.WrongThread):
        input_thread.call_wait(threads.assert_main, "a window slot", timeout=2.0)


def test_assert_input_passes_in_inline_mode(raising_guards: None) -> None:
    was = input_thread.is_inline()
    input_thread.set_inline(True)
    try:
        threads.assert_input("the claim gate")
    finally:
        input_thread.set_inline(was)


def test_guards_log_once_when_not_raising(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(threads, "_guard_logged", set())
    result: list[BaseException] = []

    def off_main() -> None:
        try:
            threads.assert_main("sample slot")
            threads.assert_main("sample slot")
        except BaseException as error:  # pragma: no cover - reported below
            result.append(error)

    thread = threads.start("guard sample", off_main)
    thread.join(2.0)
    assert result == []
    assert caplog.text.count("sample slot must run on the main thread") == 1
