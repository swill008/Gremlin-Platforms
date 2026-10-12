# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The Home OSC card's second line (D-09-OSC-CARD-LINE): where the server
listens, the last message while messages arrive, or why it isn't open."""

from __future__ import annotations

from typing import Any

from PySide6 import QtCore

import gremlin.ui.type_aliases as ta
from gremlin import clock
from gremlin.ui.device import QML_IMPORT_MAJOR_VERSION, QML_IMPORT_NAME

assert QML_IMPORT_NAME == "Gremlin.Device"
assert QML_IMPORT_MAJOR_VERSION == 1

# Back to "Listening on ..." this long after the last message.
BACK_MS = 3000
# During a flood the line changes at most this often (the newest shows).
THROTTLE_MS = 250
# A first value longer than this is cut with "…" (the Label elides the rest).
VALUE_CHARS = 40

ALL_ADDRESSES = "0.0.0.0"
CLOSED_OFF = "Not listening (Listen for OSC messages is off)"
CLOSED = "Not listening yet"


def listen_text(info: dict[str, Any]) -> tuple[str, bool]:
    """(line, warn) for an OscRuntime.listenInfo() dict."""
    state = info.get("state")
    host = str(info.get("host") or "")
    port = info.get("port")
    if state == "listening":
        if host in ("", ALL_ADDRESSES):
            return f"Listening on all addresses, port {port}", False
        return f"Listening on {host}:{port}", False
    if state == "failed":
        return f"Server not started: {info.get('reason') or 'unknown error'}", True
    if info.get("reason") == "off":
        return CLOSED_OFF, False
    return CLOSED, False


def _first_value(payload: object) -> str:
    values = tuple(payload) if isinstance(payload, (tuple, list)) else ()
    if not values:
        return ""
    value = values[0]
    if isinstance(value, float):
        text = format(value, "g")
    elif isinstance(value, (bytes, bytearray)):
        text = f"<{len(value)} bytes>"
    else:
        text = str(value)
    return text if len(text) <= VALUE_CHARS else text[:VALUE_CHARS] + "…"


def message_text(address: str, payload: object, peer: object) -> str:
    """ "From <sender ip>: <address> <first value>"."""
    sender = "?"
    if isinstance(peer, (tuple, list)) and peer:
        sender = str(peer[0])
    value = _first_value(payload)
    return f"From {sender}: {address} {value}".rstrip()


@ta.QmlElement
class OscCardStatus(QtCore.QObject):
    """text/warn for the OSC card. Reads OscRuntime.listenInfo() on
    listenChanged; a message shows for BACK_MS after the last one, changing
    at most every THROTTLE_MS. Lives on the main thread (Qt timers)."""

    changed = QtCore.Signal()

    def __init__(
        self, parent: ta.OQO = None, runtime: QtCore.QObject | None = None
    ) -> None:
        super().__init__(parent)
        if runtime is None:
            from gremlin.osc import OscRuntime

            runtime = OscRuntime()
        self._runtime = runtime
        self._text = ""
        self._warn = False
        self._listen = ("", False)
        self._showing_message = False
        self._pending: str | None = None
        self._shown_at: float | None = None
        self._back = QtCore.QTimer(self)
        self._back.setSingleShot(True)
        self._back.setInterval(BACK_MS)
        self._back.timeout.connect(self._back_to_listening)
        self._throttle = QtCore.QTimer(self)
        self._throttle.setSingleShot(True)
        self._throttle.timeout.connect(self._flush)
        runtime.listenChanged.connect(self._on_listen)  # type: ignore[attr-defined]
        runtime.incoming.connect(self._on_message)  # type: ignore[attr-defined]
        self._on_listen()

    def _set(self, text: str, warn: bool) -> None:
        if (text, warn) != (self._text, self._warn):
            self._text, self._warn = text, warn
            self.changed.emit()

    @QtCore.Slot()
    def _on_listen(self) -> None:
        self._listen = listen_text(self._runtime.listenInfo())  # type: ignore[attr-defined]
        if self._listen[0].startswith("Listening") and self._showing_message:
            return
        # Not open: that shows at once, over any message.
        self._stop_message()
        self._set(*self._listen)

    @QtCore.Slot(str, object, object)
    def _on_message(self, address: str, payload: object, peer: object) -> None:
        self._pending = message_text(address, payload, peer)
        self._showing_message = True
        self._back.start()
        now = clock.monotonic()
        wait = 0.0
        if self._shown_at is not None:
            wait = self._shown_at + THROTTLE_MS / 1000 - now
        if wait <= 0:
            self._flush()
        elif not self._throttle.isActive():
            self._throttle.start(max(1, int(wait * 1000)))

    @QtCore.Slot()
    def _flush(self) -> None:
        if self._pending is None:
            return
        self._shown_at = clock.monotonic()
        text, self._pending = self._pending, None
        self._set(text, False)

    @QtCore.Slot()
    def _back_to_listening(self) -> None:
        self._stop_message()
        self._set(*self._listen)

    def _stop_message(self) -> None:
        self._showing_message = False
        self._pending = None
        self._back.stop()
        self._throttle.stop()

    text = QtCore.Property(str, fget=lambda self: self._text, notify=changed)
    warn = QtCore.Property(bool, fget=lambda self: self._warn, notify=changed)
