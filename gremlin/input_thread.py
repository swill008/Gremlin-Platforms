# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The input thread: a Qt thread with its own event loop for the input path.

Input -> wiring -> output is meant to run here, so a busy or frozen window
never delays a binding (claude/plans/fix-plans/thread-input.md). This module
only owns the thread; nothing is moved onto it yet.

Work goes in through a command queue: call(fn, *args) runs fn on the input
thread and returns at once; call_wait(fn, *args, timeout=...) also waits for
the result, never longer than timeout.

Timers: a QTimer belongs to the thread that creates it, and only that thread
may start or stop it. A timer for the input thread is made inside a call():

    def arm() -> None:
        timer = QtCore.QTimer()          # made here: owned by the input thread
        timer.setSingleShot(True)
        timer.timeout.connect(fire)      # fire runs on the input thread
        timer.start(250)
    input_thread.call(arm)

Keep a reference to the timer (it is gone when Python drops it) and stop it
from a call() too.

Inline mode (set_inline): call() and call_wait() run fn at once on the
caller's thread instead. The unit tests that drive the wiring on their own
thread use it; tests of the thread itself turn it off and start the thread.

heartbeat: the thread bumps a time stamp every BEAT_S, so a watchdog can
tell when the input thread has stopped responding (silent_for()).
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import Any, TypeVar

from PySide6 import QtCore

from gremlin import clock, threads

NAME = "input thread"
BEAT_S = 0.5
START_LIMIT_S = 2.0
STOP_LIMIT_S = 2.0

_log = logging.getLogger("system")

_T = TypeVar("_T")


class _Door(QtCore.QObject):
    """Lives on the input thread; runs what is posted to it there."""

    posted = QtCore.Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self.posted.connect(self._run, QtCore.Qt.ConnectionType.QueuedConnection)

    @QtCore.Slot(object)
    def _run(self, job: Callable[[], None]) -> None:
        try:
            job()
        except Exception:
            _log.exception("A call on the input thread failed")


class _InputThread(QtCore.QThread):
    def __init__(self) -> None:
        super().__init__()
        self.ready = threading.Event()
        self.ident: int | None = None
        self.last_beat: float | None = None

    def _beat(self) -> None:
        self.last_beat = clock.monotonic()

    def run(self) -> None:
        threading.current_thread().name = threads.PREFIX + NAME
        self.ident = threading.get_ident()
        # Made here, so it belongs to this thread.
        beat = QtCore.QTimer()
        beat.setInterval(round(BEAT_S * 1000))
        # Direct: self lives on the main thread, so an auto connection
        # would beat there.
        beat.timeout.connect(self._beat, QtCore.Qt.ConnectionType.DirectConnection)
        beat.start()
        self._beat()
        self.ready.set()
        try:
            self.exec()
        finally:
            beat.stop()
            self.ident = None


_lock = threading.Lock()
_thread: _InputThread | None = None
_door: _Door | None = None
_inline = False


def set_inline(on: bool) -> None:
    """Inline mode on: call() and call_wait() run fn on the caller's thread."""
    global _inline
    _inline = on


def is_inline() -> bool:
    return _inline


def is_running() -> bool:
    thread = _thread
    return thread is not None and thread.isRunning()


def is_input_thread() -> bool:
    """True on the input thread itself (not in inline mode on the caller)."""
    thread = _thread
    return thread is not None and thread.ident == threading.get_ident()


def start() -> None:
    """Starts the input thread (does nothing when it runs already).

    Needs the Qt application. Waits at most START_LIMIT_S for its loop.
    """
    global _thread, _door
    if QtCore.QCoreApplication.instance() is None:
        raise RuntimeError("The input thread needs the Qt application")
    with _lock:
        if _thread is not None and _thread.isRunning():
            return
        thread = _InputThread()
        door = _Door()
        door.moveToThread(thread)
        _thread, _door = thread, door
        threads.start_qt(NAME, thread)
    if not thread.ready.wait(START_LIMIT_S):
        stop()
        raise RuntimeError(f"The input thread did not start within {START_LIMIT_S} s")


def stop(timeout: float = STOP_LIMIT_S) -> bool:
    """Quits the input thread's loop after the calls already made, and
    waits at most timeout seconds.

    True when it stopped. A thread stuck in a call is left running (and
    logged); the program's exit ends it.
    """
    global _thread, _door
    with _lock:
        thread = _thread
    if thread is None:
        return True
    if threading.get_ident() == thread.ident:
        raise RuntimeError("The input thread cannot stop itself")
    # Queued behind the calls already made, so they still run first.
    door = _door
    if door is not None and thread.isRunning():
        door.posted.emit(thread.quit)
    else:
        thread.quit()
    stopped = thread.wait(max(0, round(timeout * 1000)))
    if not stopped:
        _log.warning(f"The input thread did not stop within {timeout:.1f} s")
        return False
    with _lock:
        if _thread is thread:
            _thread, _door = None, None
    return True


def call(fn: Callable[..., Any], *args: object) -> None:
    """Runs fn(*args) on the input thread; returns at once.

    Calls run in the order they were made. An exception is logged.
    """
    if _inline:
        fn(*args)
        return
    door = _door
    if door is None or not is_running():
        raise RuntimeError("The input thread is not running")
    door.posted.emit(lambda: fn(*args))


def call_wait(fn: Callable[..., _T], *args: object, timeout: float) -> _T:
    """Runs fn(*args) on the input thread and returns its result.

    Waits at most timeout seconds, then raises TimeoutError (fn may still
    run later; its result is dropped). fn's own exception is raised here.
    """
    if _inline or is_input_thread():
        return fn(*args)
    done = threading.Event()
    outcome: dict[str, Any] = {}

    def job() -> None:
        try:
            outcome["result"] = fn(*args)
        except BaseException as error:
            outcome["error"] = error
        finally:
            done.set()

    call(job)
    if not done.wait(timeout):
        name = getattr(fn, "__qualname__", repr(fn))
        _log.warning(f"Input thread call {name} took over {timeout:.1f} s")
        raise TimeoutError(f"Input thread call {name} took over {timeout:.1f} s")
    if "error" in outcome:
        raise outcome["error"]
    return outcome["result"]


def last_beat() -> float | None:
    """clock.monotonic() of the input thread's latest heartbeat (None when
    it isn't running)."""
    thread = _thread
    return thread.last_beat if thread is not None and thread.isRunning() else None


def silent_for() -> float:
    """Seconds since the input thread's latest heartbeat (0 when it isn't
    running)."""
    beat = last_beat()
    return 0.0 if beat is None else max(0.0, clock.monotonic() - beat)
