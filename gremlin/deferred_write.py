# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Write to disk a little later, once, instead of on every change.

schedule(key, write, delay_ms) runs write() once, delay_ms after the last
request for that key; more requests in between only move it later. Every
pending write also runs on flush_all(), which runs when the program quits
(app.aboutToQuit and atexit), so nothing waiting is lost.

Without a running Qt application (tests, tools, early start-up) a request
writes at once. Requests from other threads are handed to the main thread.
"""

from __future__ import annotations

import atexit
import threading
from collections.abc import Callable

from PySide6 import QtCore

_LOCK = threading.Lock()
# key -> the write waiting for it.
_pending: dict[str, Callable[[], None]] = {}


class _Scheduler(QtCore.QObject):
    """Lives on the main thread; owns one single-shot timer per key."""

    request = QtCore.Signal(str, int)

    def __init__(self) -> None:
        super().__init__()
        self._timers: dict[str, QtCore.QTimer] = {}
        # Queued when emitted from another thread, direct on the main one.
        self.request.connect(self._start)

    @QtCore.Slot(str, int)
    def _start(self, key: str, delay_ms: int) -> None:
        timer = self._timers.get(key)
        if timer is None:
            timer = QtCore.QTimer(self)
            timer.setSingleShot(True)
            timer.timeout.connect(lambda k=key: flush(k))
            self._timers[key] = timer
        timer.start(delay_ms)


_SCHEDULER: _Scheduler | None = None


def _scheduler() -> _Scheduler | None:
    """The scheduler, made on the main thread once the application runs."""
    global _SCHEDULER
    app = QtCore.QCoreApplication.instance()
    if app is None:
        return None
    if _SCHEDULER is None:
        if QtCore.QThread.currentThread() is not app.thread():
            return None
        _SCHEDULER = _Scheduler()
        app.aboutToQuit.connect(flush_all)
    return _SCHEDULER


def schedule(
    key: str, write: Callable[[], None], delay_ms: int = 1000, *, hold: bool = False
) -> None:
    """Run write() once, delay_ms after the last request for this key.

    Without a scheduler (before the application runs, or off the main
    thread) the write runs at once, unless hold is True: then it waits for
    the next request that has a scheduler, a flush, or quitting.
    """
    scheduler = _scheduler()
    if scheduler is None:
        if hold:
            with _LOCK:
                _pending[key] = write
            return
        write()
        return
    with _LOCK:
        _pending[key] = write
    scheduler.request.emit(key, delay_ms)


def pending(key: str) -> bool:
    with _LOCK:
        return key in _pending


def flush(key: str) -> None:
    """Run the write waiting for this key now (if any)."""
    with _LOCK:
        write = _pending.pop(key, None)
    if write is not None:
        try:
            write()
        except Exception:
            import logging

            logging.getLogger("system").exception(f"Deferred write '{key}' failed")


def flush_all() -> None:
    """Run every waiting write now (on quit, and before a restart). A write
    may ask for another (the last mode saves the settings), so repeat until
    nothing waits."""
    for _round in range(5):
        with _LOCK:
            keys = list(_pending)
        if not keys:
            return
        for key in keys:
            flush(key)


atexit.register(flush_all)
