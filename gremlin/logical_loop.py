# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Stops a loop between Logical Device controls (06 S94, S94a, D-06-LD-LOOP,
D-06-LOOP-CHAIN).

A Logical Device control's actions can drive a Logical Device control:
itself, or one whose actions drive it back (A → B → A). Every send to a
control goes through guarded(); a chain holds at most MAX_HOPS sends, the
next one is dropped and the loop is reported once per Run.

The chain travels with the event (S94a): each event sent to a Logical
Device control carries the controls it came through (Event.ld_chain), and
an action that sends on continues the chain of the event that started it,
however slowly (a macro step, a Relative loop). A new input (a stick, a key,
a fresh press) starts an empty chain, so fast repeated presses never trip
the guard. On one thread a thread-local stack holds the chain too: a send
made while another is under way continues it even when an event on the way
was rebuilt without its chain. A macro thread starts its stack with the
chain of the event that started the macro (continuing()).
"""

from __future__ import annotations

import contextlib
import logging
import threading
from collections.abc import Callable, Hashable, Iterator

from gremlin.log_once import log_once

MAX_HOPS = 8

Hop = tuple[Hashable, str]  # (control key, label)
Chain = tuple[Hop, ...]

_LOCK = threading.Lock()
_local = threading.local()
_told = False


def _stack() -> list[Chain]:
    stack = getattr(_local, "stack", None)
    if stack is None:
        stack = []
        _local.stack = stack
    return stack


def chain_of(carried: Chain | None = ()) -> Chain:
    """The chain a send continues: the one its event carried, or this
    thread's send under way when that one is longer."""
    carried = tuple(carried or ())
    stack = _stack()
    if stack and len(stack[-1]) > len(carried):
        return stack[-1]
    return carried


@contextlib.contextmanager
def continuing(chain: Chain | None) -> Iterator[None]:
    """Sends made on this thread inside it continue chain (a macro's thread
    continues the chain of the event that started the macro)."""
    stack = _stack()
    stack.append(tuple(chain or ()))
    try:
        yield
    finally:
        stack.pop()


def _loop_text(path: Chain, key: Hashable, label: str) -> str:
    """The loop's controls, from the dropped control's earlier hop on."""
    start = 0
    for index in range(len(path) - 1, -1, -1):
        if path[index][0] == key:
            start = index
            break
    names = [hop_label for _, hop_label in path[start:]] + [label]
    return " → ".join(names)


def _report(path: Chain, key: Hashable, label: str) -> None:
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
    send: Callable[[Chain], None],
    chain: Chain | None = (),
) -> bool:
    """Runs send(path) unless the chain already holds MAX_HOPS hops.

    control_key: (InputType, input_id) of the Logical Device control sent
    to; label: its name; chain: the chain of the event whose action makes
    this send (Event.ld_chain; empty for a new input). send gets the chain
    with this hop added, for the event it sends. Returns False when the
    send was dropped. The guard itself never raises; send()'s own errors
    pass through.
    """
    try:
        base = chain_of(chain)
        if len(base) >= MAX_HOPS:
            try:
                _report(base, control_key, label)
            except Exception:
                logging.getLogger("system").exception("Logical Device loop report")
            return False
        path = base + ((control_key, str(label)),)
        stack = _stack()
    except Exception:  # a guard fault never stops an input
        logging.getLogger("system").exception("Logical Device loop guard")
        send(tuple(chain or ()))
        return True
    stack.append(path)
    try:
        send(path)
    finally:
        stack.pop()
    return True


def reset() -> None:
    """Lets the loop notice show again (Run start and Stop)."""
    global _told
    with _LOCK:
        _told = False
