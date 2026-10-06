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
from typing import Any

PREFIX = "Gremlin-Platforms: "

_LOCK = threading.Lock()
# Live threads and the request that stops each (None: it ends by itself).
_live: dict[threading.Thread, Callable[[], None] | None] = {}


def _forget(thread: threading.Thread) -> None:
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
