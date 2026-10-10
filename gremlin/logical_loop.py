# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Stops a loop between Logical Device controls (06 S94, D-06-LD-LOOP).

A Logical Device control's actions can drive a Logical Device control:
itself, or one whose actions drive it back (A -> B -> A). Every send to a
control goes through guarded(); a chain holds at most MAX_HOPS sends, the
next one is dropped and the loop is reported once per Run.

How a chain is followed:
- On one thread (an emit runs the control's actions straight away), a
  thread-local stack holds the chain.
- Across a queue (a Relative loop or a macro step sends from its own
  thread; the actions run later on the main thread), the chain is carried
  on the control: each send records the chain that reached its control.
  A send that names its source (the Logical Device control whose actions
  made it) continues the chain recorded for that source; this is exact.
  A send with no source (a macro step) continues the chain recorded for
  its own control when that send came from another thread within
  QUEUED_WINDOW: a macro run is a new thread each time, so a macro that
  re-triggers its own control is followed, while one thread sending to the
  same control again and again (a repeating macro, a Relative loop driven
  by a stick) starts a new chain each time.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable, Hashable
from typing import NamedTuple

from gremlin import clock
from gremlin.log_once import log_once

MAX_HOPS = 8
# A send with no source continues its control's chain when the last send to
# that control came from another thread at most this long ago (seconds).
QUEUED_WINDOW = 0.1

_Hop = tuple[Hashable, str]  # (control key, label)
_Path = tuple[_Hop, ...]


class _Carried(NamedTuple):
    path: _Path
    at: float
    thread: threading.Thread


_LOCK = threading.Lock()
_local = threading.local()
_carried: dict[Hashable, _Carried] = {}
_told = False


def _stack() -> list[_Path]:
    stack = getattr(_local, "stack", None)
    if stack is None:
        stack = []
        _local.stack = stack
    return stack


def _base(
    stack: list[_Path], key: Hashable, source: Hashable | None
) -> _Path:
    """The chain this send continues."""
    if stack:
        return stack[-1]
    with _LOCK:
        if source is not None:
            carried = _carried.get(source)
            return carried.path if carried is not None else ()
        carried = _carried.get(key)
    if (
        carried is not None
        and carried.thread is not threading.current_thread()
        and clock.monotonic() - carried.at <= QUEUED_WINDOW
    ):
        return carried.path
    return ()


def _loop_text(path: _Path, key: Hashable, label: str) -> str:
    """The loop's controls, from the dropped control's earlier hop on."""
    start = 0
    for index in range(len(path) - 1, -1, -1):
        if path[index][0] == key:
            start = index
            break
    names = [hop_label for _, hop_label in path[start:]] + [label]
    return " -> ".join(names)


def _report(path: _Path, key: Hashable, label: str) -> None:
    global _told
    text = (
        "Logical Device: a loop between controls was stopped "
        f"({_loop_text(path, key, label)})"
    )
    try:
        hash(key)
        once_key: Hashable = ("logical-loop", key)
    except TypeError:
        once_key = ("logical-loop", repr(key))
    log_once("user", once_key, logging.WARNING, text)
    with _LOCK:
        if _told:
            return
        _told = True
    from gremlin.signal import signal

    signal.showNotification.emit("Logical Device Loop", text)


def guarded(
    control_key: Hashable,
    label: str,
    send: Callable[[], None],
    source: Hashable | None = None,
) -> bool:
    """Runs send() unless its chain already holds MAX_HOPS hops.

    control_key: (InputType, input_id) of the Logical Device control sent
    to; label: its name; source: the Logical Device control whose actions
    made this send, when known. Returns False when the send was dropped.
    The guard itself never raises; send()'s own errors pass through.
    """
    try:
        stack = _stack()
        base = _base(stack, control_key, source)
        if len(base) >= MAX_HOPS:
            try:
                _report(base, control_key, label)
            except Exception:
                logging.getLogger("system").exception("Logical Device loop report")
            return False
        path = base + ((control_key, str(label)),)
        with _LOCK:
            _carried[control_key] = _Carried(
                path, clock.monotonic(), threading.current_thread()
            )
    except Exception:  # a guard fault never stops an input
        logging.getLogger("system").exception("Logical Device loop guard")
        send()
        return True
    stack.append(path)
    try:
        send()
    finally:
        stack.pop()
    return True


def reset() -> None:
    """Clears the Run's chains and lets the loop notice show again (Run
    start and Stop)."""
    global _told
    with _LOCK:
        _carried.clear()
        _told = False
