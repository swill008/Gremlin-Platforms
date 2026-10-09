# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""OSC traffic for the OSC Monitor (D-09-OSC-MONITOR): the last 200 messages
in and out.

note() is called from the OSC thread (and the sender); it never raises.
Listeners get each entry on the main thread, through a queued signal."""

from __future__ import annotations

import threading
import time
from collections import deque
from collections.abc import Callable
from typing import Any

from PySide6 import QtCore

LIMIT = 200

Entry = dict[str, Any]
Listener = Callable[[Entry], None]

_lock = threading.Lock()
_buffer: deque[Entry] = deque(maxlen=LIMIT)
_listeners: list[Listener] = []
_seq = 0


class _Relay(QtCore.QObject):
    """Lives on the main thread; noted from any thread runs _deliver there."""

    noted = QtCore.Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self.noted.connect(self._deliver, QtCore.Qt.ConnectionType.QueuedConnection)

    @QtCore.Slot(object)
    def _deliver(self, entry: Entry) -> None:
        _call_listeners(entry)


_relay: _Relay | None = None


def _get_relay() -> _Relay | None:
    """The relay, made on first use and moved to the main thread; None
    without a Qt application (listeners are then called directly)."""
    global _relay
    app = QtCore.QCoreApplication.instance()
    if app is None:
        return None
    with _lock:
        if _relay is None:
            relay = _Relay()
            if relay.thread() is not app.thread():
                relay.moveToThread(app.thread())
            _relay = relay
        return _relay


def _call_listeners(entry: Entry) -> None:
    with _lock:
        listeners = list(_listeners)
    for listener in listeners:
        try:
            listener(entry)
        except Exception:  # noqa: BLE001  a bad listener mustn't stop the rest
            pass


def _peer_text(peer: object) -> str:
    if not peer:
        return ""
    try:
        host, port = peer  # type: ignore[misc]
        return f"{host}:{port}"
    except (TypeError, ValueError):
        return str(peer)


def note(
    direction: str,
    address: str,
    args: object = (),
    peer: object = None,
    matched: list[str] | None = None,
) -> None:
    """Record one message: direction "in" or "out", its address and values,
    the peer (host, port) or None, and the inputs it matched."""
    global _seq
    try:
        values = list(args) if isinstance(args, (list, tuple)) else (
            [] if args is None else [args]
        )
        with _lock:
            _seq += 1
            entry: Entry = {
                "seq": _seq,
                "time": time.time(),
                "direction": "out" if direction == "out" else "in",
                "address": str(address),
                "args": values,
                "peer": _peer_text(peer),
                "matched": [str(m) for m in (matched or [])],
            }
            _buffer.append(entry)
            wanted = bool(_listeners)
        if not wanted:
            return
        relay = _get_relay()
        if relay is None:
            _call_listeners(entry)
        else:
            relay.noted.emit(entry)
    except Exception:  # noqa: BLE001  never break the OSC thread
        pass


def add_listener(callback: Listener) -> None:
    _get_relay()
    with _lock:
        if callback not in _listeners:
            _listeners.append(callback)


def remove_listener(callback: Listener) -> None:
    with _lock:
        if callback in _listeners:
            _listeners.remove(callback)


def recent() -> list[Entry]:
    """The kept messages, oldest first."""
    with _lock:
        return list(_buffer)


def clear() -> None:
    with _lock:
        _buffer.clear()
