# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Every thread the program starts: named, tracked, and stopped on exit.

Threads used to be started anonymously ("Thread-12") and nothing could stop
them all: the program ended through os._exit, and a script or test that
ended any other way waited for them forever. Start every thread through
start() or timer() instead. Each one gets a readable name and is listed
while it runs, with the request that stops it, so shutdown() can stop them
all and say which didn't stop.

A stop request only asks: it sets a flag, wakes a wait or cancels a timer,
and returns at once. shutdown() does the waiting, within one time limit.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from PySide6 import QtCore

PREFIX = "Gremlin-Platforms: "


class _Thread(Protocol):
    """What shutdown() needs of a listed thread (a threading.Thread or a
    _QtThread)."""

    name: str

    def is_alive(self) -> bool: ...

    def join(self, timeout: float | None = None) -> None: ...


_LOCK = threading.Lock()
# Live threads and the request that stops each (None: it ends by itself).
_live: dict[_Thread, Callable[[], None] | None] = {}


def _forget(thread: _Thread) -> None:
    with _LOCK:
        _live.pop(thread, None)


def start(
    name: str,
    target: Callable[..., Any],
    *args: object,
    stop: Callable[[], None] | None = None,
) -> threading.Thread:
    """Starts target(*args) on a new thread called name.

    stop asks the thread to end (see the module notes); leave it out for a
    thread that ends by itself soon.
    """

    def run() -> None:
        try:
            target(*args)
        finally:
            _forget(thread)

    thread = threading.Thread(target=run, name=PREFIX + name)
    with _LOCK:
        _live[thread] = stop
    try:
        thread.start()
    except BaseException:
        _forget(thread)
        raise
    return thread


class _Timer(threading.Timer):
    """A threading.Timer that leaves the list when it is done or cancelled."""

    def run(self) -> None:
        try:
            super().run()
        finally:
            _forget(self)


def timer(
    name: str, seconds: float, function: Callable[..., Any], *args: object
) -> threading.Timer:
    """Calls function(*args) on a new thread after seconds (cancel() stops it)."""
    t = _Timer(seconds, function, args)
    t.name = PREFIX + name
    with _LOCK:
        _live[t] = t.cancel
    try:
        t.start()
    except BaseException:
        _forget(t)
        raise
    return t


# Main-thread timers still waiting (listed by running(), cancelled by
# shutdown()); they are Qt timers, not threads.
_main_timers: set[MainTimer] = set()


class MainTimer:
    """A one-shot timer whose function runs on the main thread (the Qt event
    loop), with the same cancel() / is_alive() as threading.Timer.

    Listed while it waits, like a thread, so shutdown() cancels it and a
    check can name it.
    """

    def __init__(
        self, name: str, seconds: float, function: Callable[..., Any], args: tuple
    ) -> None:
        from PySide6 import QtCore

        self.name = PREFIX + name
        self._function = function
        self._args = args
        self._timer = QtCore.QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._fire)
        with _LOCK:
            _main_timers.add(self)
        self._timer.start(max(0, round(seconds * 1000)))

    def _fire(self) -> None:
        with _LOCK:
            _main_timers.discard(self)
        self._function(*self._args)

    def cancel(self) -> None:
        with _LOCK:
            _main_timers.discard(self)
        self._timer.stop()

    def is_alive(self) -> bool:
        return self._timer.isActive()


def main_timer(
    name: str, seconds: float, function: Callable[..., Any], *args: object
) -> MainTimer | threading.Timer:
    """Calls function(*args) on the main thread after seconds.

    For actions: what they run (other actions, a mode change) then runs on the
    main thread like every other action, not on a timer thread. Made from
    another thread (no event loop there to run it), it falls back to timer().
    """
    if threading.current_thread() is not threading.main_thread():
        return timer(name, seconds, function, *args)
    return MainTimer(name, seconds, function, args)


class _QtThread:
    """A QThread as shutdown() sees it: listed by name, stopped by quitting
    its event loop, waited for within the limit."""

    def __init__(self, name: str, qthread: QtCore.QThread) -> None:
        self.name = name
        self.qthread = qthread

    def is_alive(self) -> bool:
        return self.qthread.isRunning()

    def join(self, timeout: float | None = None) -> None:
        from PySide6 import QtCore

        # Waiting for itself would never end.
        if QtCore.QThread.currentThread() is self.qthread:
            return
        if timeout is None:
            self.qthread.wait()
        else:
            self.qthread.wait(max(0, round(timeout * 1000)))


def start_qt(name: str, qthread: QtCore.QThread) -> None:
    """Starts qthread (a Qt thread with its own event loop) called name.

    Listed by running() like a thread; shutdown() asks it to stop with
    quit() and waits for it within its limit.
    """
    from PySide6 import QtCore

    qthread.setObjectName(PREFIX + name)
    entry = _QtThread(PREFIX + name, qthread)
    # finished is emitted on qthread itself; the list has its own lock.
    qthread.finished.connect(
        lambda: _forget(entry), QtCore.Qt.ConnectionType.DirectConnection
    )
    with _LOCK:
        _live[entry] = qthread.quit
    try:
        qthread.start()
    except BaseException:
        _forget(entry)
        raise


# | Wrong-thread guards (debug helpers). Qt objects belong to one thread:
# | the window's to the main thread, the input path's to the input thread
# | (gremlin/input_thread.py). A function that must run on one of them
# | calls assert_main(what) / assert_input(what) first. With
# | guards_raise on (tests) a wrong thread raises WrongThread; otherwise
# | it is logged once per what to the system log.

guards_raise = False
_guard_logged: set[str] = set()


class WrongThread(AssertionError):
    """A function that belongs to one thread was called on another."""


def _wrong_thread(what: str, wanted: str) -> None:
    text = f"{what} must run on the {wanted}, not on {threading.current_thread().name}"
    if guards_raise:
        raise WrongThread(text)
    with _LOCK:
        if what in _guard_logged:
            return
        _guard_logged.add(what)
    logging.getLogger("system").warning(text)


def assert_main(what: str) -> None:
    """Checks that the caller is on the main (window) thread."""
    if threading.current_thread() is not threading.main_thread():
        _wrong_thread(what, "main thread")


def assert_input(what: str) -> None:
    """Checks that the caller is on the input thread (or that the input
    thread runs inline on the caller, see input_thread.set_inline)."""
    from gremlin import input_thread

    if not (input_thread.is_inline() or input_thread.is_input_thread()):
        _wrong_thread(what, "input thread")


def running() -> list[str]:
    """The names of the program's threads (and main-thread timers) that are
    still running."""
    with _LOCK:
        names = [t.name for t in _live if t.is_alive()]
        names += [t.name for t in _main_timers if t.is_alive()]
    return sorted(names)


def shutdown(timeout: float = 2.0) -> list[str]:
    """Asks every thread to stop and waits up to timeout seconds in all.

    Returns the names of those still running (they are logged too).
    """
    with _LOCK:
        threads = list(_live.items())
        main_timers = list(_main_timers)
    # A Qt timer is stopped only from the thread it lives on.
    if threading.current_thread() is threading.main_thread():
        for main_timer_ in main_timers:
            try:
                main_timer_.cancel()
            except Exception:
                logging.getLogger("system").exception(
                    f"Could not cancel {main_timer_.name}"
                )
    for thread, stop in threads:
        if stop is None:
            continue
        try:
            stop()
        except Exception:
            logging.getLogger("system").exception(
                f"Could not ask {thread.name} to stop"
            )
    deadline = time.monotonic() + timeout
    for thread, _ in threads:
        if thread is not threading.current_thread():
            thread.join(max(0.0, deadline - time.monotonic()))
    left = sorted(t.name for t, _ in threads if t.is_alive())
    if left:
        logging.getLogger("system").warning(
            f"Still running after {timeout:.0f} s: {', '.join(left)}"
        )
    return left
