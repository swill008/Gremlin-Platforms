# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""threads.thread_timer, threads.main_call and threads.has_event_loop
(thread batch 3, claude/plans/fix-plans/contract-THR.md): a timer runs on
the thread that made it when that thread has a Qt event loop, else on a
named timer thread; cancel() works from any thread; main_call hops to the
main thread.
"""

from __future__ import annotations

import sys

sys.path.append(".")

import threading
import time
from collections.abc import Callable, Iterator

import pytest
from PySide6 import QtCore

from gremlin import input_thread, threads


def _wait_for(check: Callable[[], bool], seconds: float = 2.0) -> bool:
    """Runs the main thread's events until check() or the limit."""
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        QtCore.QCoreApplication.processEvents()
        if check():
            return True
        time.sleep(0.005)
    return check()


@pytest.fixture
def qt_warnings() -> Iterator[list[str]]:
    """Qt's own warnings meanwhile (a timer stopped from the wrong thread)."""
    seen: list[str] = []

    def handler(_mode: object, _context: object, message: str) -> None:
        seen.append(message)

    previous = QtCore.qInstallMessageHandler(handler)
    yield seen
    QtCore.qInstallMessageHandler(previous)


def test_has_event_loop_on_main_and_input_but_not_a_plain_thread(
    input_thread_running: None,
) -> None:
    assert threads.has_event_loop()
    assert input_thread.call_wait(threads.has_event_loop, timeout=2.0)
    seen: list[bool] = []
    t = threading.Thread(target=lambda: seen.append(threads.has_event_loop()))
    t.start()
    t.join(2.0)
    assert seen == [False]


def test_timer_made_on_the_input_thread_fires_there(
    input_thread_running: None,
) -> None:
    fired: list[bool] = []
    handles: list[object] = []

    def arm() -> None:
        handles.append(
            threads.thread_timer(
                "test input timer",
                0.05,
                lambda: fired.append(input_thread.is_input_thread()),
            )
        )

    input_thread.call_wait(arm, timeout=2.0)
    assert isinstance(handles[0], threads.QtTimer)
    assert "Gremlin-Platforms: test input timer" in threads.running()
    # The main thread runs no events meanwhile: the input thread does it.
    time.sleep(0.3)
    assert fired == [True]
    assert "Gremlin-Platforms: test input timer" not in threads.running()


def test_cancel_from_another_thread_stops_it_on_its_own(
    input_thread_running: None, qt_warnings: list[str]
) -> None:
    fired: list[bool] = []
    handles: list[threads.QtTimer | threading.Timer] = []
    input_thread.call_wait(
        lambda: handles.append(
            threads.thread_timer("test cancel", 0.15, lambda: fired.append(True))
        ),
        timeout=2.0,
    )
    handle = handles[0]
    assert isinstance(handle, threads.QtTimer)
    handle.cancel()  # from the main thread
    assert not handle.is_alive()
    # The queued stop has run on the input thread.
    input_thread.call_wait(lambda: None, timeout=2.0)
    assert handle._timer is None
    time.sleep(0.3)
    assert fired == []
    assert not [w for w in qt_warnings if "another thread" in w]


def test_thread_timer_falls_back_to_a_timer_thread_off_loop() -> None:
    fired: list[str] = []
    handles: list[threads.QtTimer | threading.Timer] = []

    def arm() -> None:
        handles.append(
            threads.thread_timer(
                "test fallback",
                0.02,
                lambda: fired.append(threading.current_thread().name),
            )
        )

    t = threading.Thread(target=arm)
    t.start()
    t.join(2.0)
    assert isinstance(handles[0], threading.Timer)
    handles[0].join(2.0)
    assert fired == ["Gremlin-Platforms: test fallback"]


def test_shutdown_cancels_an_input_thread_timer_on_its_thread(
    input_thread_running: None,
    qt_warnings: list[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Only this test's timer: the shared threads are left alone.
    monkeypatch.setattr(threads, "_live", {})
    fired: list[bool] = []
    handles: list[threads.QtTimer | threading.Timer] = []
    input_thread.call_wait(
        lambda: handles.append(
            threads.thread_timer("test shutdown", 0.15, lambda: fired.append(True))
        ),
        timeout=2.0,
    )
    threads.shutdown(timeout=1.0)
    assert not handles[0].is_alive()
    input_thread.call_wait(lambda: None, timeout=2.0)
    time.sleep(0.3)
    assert fired == []
    assert not [w for w in qt_warnings if "another thread" in w]


def test_main_call_runs_on_the_main_thread(input_thread_running: None) -> None:
    seen: list[bool] = []
    input_thread.call_wait(
        threads.main_call,
        lambda: seen.append(threading.current_thread() is threading.main_thread()),
        timeout=2.0,
    )
    assert seen == []  # queued: runs when the main thread handles its events
    assert _wait_for(lambda: seen == [True])


def test_main_call_is_inline_on_the_main_thread(qapp: object) -> None:
    seen: list[int] = []
    threads.main_call(seen.append, 1)
    assert seen == [1]


def _call_from_input_while_main_runs_events(
    fn: Callable[[], object], seconds: float = 2.0
) -> dict[str, object]:
    """fn() on the input thread while the main thread handles its events."""
    out: dict[str, object] = {}

    def job() -> None:
        try:
            out["result"] = fn()
        except BaseException as error:  # noqa: BLE001 - handed to the test
            out["error"] = error

    input_thread.call(job)
    assert _wait_for(lambda: bool(out), seconds)
    return out


def test_main_call_wait_returns_the_result_from_main(
    input_thread_running: None,
) -> None:
    out = _call_from_input_while_main_runs_events(
        lambda: threads.main_call_wait(
            lambda x: (x * 2, threading.current_thread() is threading.main_thread()),
            21,
            timeout=2.0,
        )
    )
    assert out == {"result": (42, True)}


def test_main_call_wait_raises_fn_error(input_thread_running: None) -> None:
    def boom() -> None:
        raise ValueError("boom")

    out = _call_from_input_while_main_runs_events(
        lambda: threads.main_call_wait(boom, timeout=2.0)
    )
    assert isinstance(out["error"], ValueError)


def test_main_call_wait_times_out_while_main_is_blocked(
    input_thread_running: None,
) -> None:
    out: dict[str, object] = {}
    ran: list[bool] = []

    def job() -> None:
        started = time.monotonic()
        try:
            threads.main_call_wait(lambda: ran.append(True), timeout=0.1)
        except TimeoutError as error:
            out["error"] = error
        out["took"] = time.monotonic() - started

    input_thread.call(job)
    time.sleep(0.4)  # the main thread runs no events: the call can't run
    assert isinstance(out.get("error"), TimeoutError)
    assert float(out["took"]) < 0.35  # type: ignore[arg-type]
    # The main thread frees up: a timed-out call never runs later.
    QtCore.QCoreApplication.processEvents()
    assert ran == []


def test_main_call_wait_is_inline_on_main(qapp: object) -> None:
    assert threads.main_call_wait(lambda: 7, timeout=0.01) == 7


def test_a_timer_is_deleted_on_its_own_thread(input_thread_running: None) -> None:
    """Fired or cancelled, the QTimer goes with deleteLater on its thread, so
    dropping the handle elsewhere (or after the thread ended) deletes
    nothing from the wrong thread."""
    from shiboken6 import Shiboken

    handles: list[threads.QtTimer | threading.Timer] = []
    kept: list[QtCore.QTimer] = []

    def arm() -> None:
        handle = threads.thread_timer("test delete", 0.02, lambda: None)
        assert isinstance(handle, threads.QtTimer)
        assert handle._timer is not None
        kept.append(handle._timer)
        handles.append(handle)

    input_thread.call_wait(arm, timeout=2.0)
    time.sleep(0.2)
    input_thread.call_wait(lambda: None, timeout=2.0)
    assert not handles[0].is_alive()
    assert not Shiboken.isValid(kept[0])  # deleted (on the input thread)
