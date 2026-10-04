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


def running() -> list[str]:
    """The names of the program's threads that are still running."""
    with _LOCK:
        return sorted(t.name for t in _live if t.is_alive())


def shutdown(timeout: float = 2.0) -> list[str]:
    """Asks every thread to stop and waits up to timeout seconds in all.

    Returns the names of those still running (they are logged too).
    """
    with _LOCK:
        threads = list(_live.items())
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
