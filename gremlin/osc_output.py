# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""OSC output: messages to a target or back to the last sender
(decision D-09-OSC-OUTPUT).

Send OSC actions and feedback send through send(). Targets and the output
switches are read from OSC's own file (gremlin.osc_device_file). Nothing is
sent while OSC output is off, or with no profile running, unless force is
given. One UDP client per (host, port), kept until the Run stops.
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from gremlin import run_scope

log = logging.getLogger("system")

REPLY = "reply"
VALUE_TYPES = ("auto", "int", "float", "bool", "text")

_lock = threading.Lock()
_last_sender: tuple[str, int] | None = None
# address -> the type of each value last received there.
_received: dict[str, list[str]] = {}
_clients: dict[tuple[str, int], Any] = {}
_close_at: int | None = None


def _make_client(host: str, port: int) -> Any:  # noqa: ANN401
    from pythonosc.udp_client import SimpleUDPClient

    return SimpleUDPClient(host, port)


def _type_of(value: object) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, str):
        return "text"
    return "float"


def note_sender(host: str, port: int) -> None:
    """The last message came from (host, port): where "reply" sends."""
    global _last_sender
    try:
        _last_sender = (str(host), int(port))
    except (TypeError, ValueError):
        pass


def last_sender() -> tuple[str, int] | None:
    return _last_sender


def note_received_type(address: str, args: Any) -> None:  # noqa: ANN401
    """Remembers the value types last received on address (for Auto)."""
    if not address:
        return
    _received[_type_key(address)] = [_type_of(v) for v in tuple(args or ())]


def _type_key(address: object) -> str:
    """Received types are kept by the address casefolded: incoming addresses
    are matched without regard to case, so a Send OSC address typed in
    another case finds them."""
    return str(address).strip().casefold()


def received_type(address: str, index: int) -> str | None:
    """The type last received on address at value index (the last value's
    type past the end); None when nothing came there."""
    types = _received.get(_type_key(address))
    if not types:
        return None
    return types[min(index, len(types) - 1)]


def reset() -> None:
    """Forgets senders, received types and clients (tests, quit)."""
    global _last_sender
    close_all()
    _last_sender = None
    _received.clear()


def _settings() -> tuple[dict, list[dict]]:
    from gremlin import osc_device_file

    server = osc_device_file.read_server()
    reader = getattr(osc_device_file, "read_targets", None)
    if reader is not None:
        targets = reader()
    else:
        targets = [
            {
                "id": "default",
                "name": "Default",
                "host": server.get("output_host", "127.0.0.1"),
                "port": server.get("output_port", 8000),
            }
        ]
    return server, targets


def resolve_target(target_id: str) -> tuple[str, int] | None:
    """(host, port) of a target id, or of the last sender for "reply"
    (None with Reply to sender off, nobody heard yet, or no such target)."""
    server, targets = _settings()
    if target_id == REPLY:
        if not server.get("reply_to_sender", True):
            return None
        return _last_sender
    for target in targets:
        if target.get("id") == target_id:
            host = str(target.get("host") or "").strip()
            try:
                port = int(str(target.get("port")))
            except (TypeError, ValueError):
                return None
            return (host, port) if host and 0 < port < 65536 else None
    return None


def convert(value: object, kind: str, address: str = "", index: int = 0) -> object:
    """value as the OSC type kind; "auto" is the type last received on the
    address, else float (text that isn't a number stays text)."""
    if kind not in VALUE_TYPES or kind == "auto":
        kind = received_type(address, index) or "float"
    try:
        if kind == "int":
            if isinstance(value, str):
                return int(round(float(value.strip())))
            return int(round(float(value)))  # type: ignore[arg-type]
        if kind == "float":
            if isinstance(value, str):
                return float(value.strip())
            return float(value)  # type: ignore[arg-type]
        if kind == "bool":
            if isinstance(value, str):
                text = value.strip().lower()
                if text in ("true", "yes", "on"):
                    return True
                if text in ("false", "no", "off", ""):
                    return False
                return float(text) != 0
            return bool(value)
    except (TypeError, ValueError):
        return _text(value)
    return _text(value)


def _text(value: object) -> str:
    """Text the short way, as Feedback sends it: 1 rather than 1.0."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _client(host: str, port: int) -> Any:  # noqa: ANN401
    global _close_at
    with _lock:
        client = _clients.get((host, port))
        if client is None:
            client = _make_client(host, port)
            _clients[(host, port)] = client
        if run_scope.running() and _close_at != run_scope.number():
            _close_at = run_scope.number()
            run_scope.on_stop(run_scope.Stage.DRIVERS, "OSC output", close_all)
    return client


def close_all() -> None:
    """Closes every UDP client (Stop)."""
    global _close_at
    with _lock:
        clients = list(_clients.values())
        _clients.clear()
        _close_at = None
    for client in clients:
        sock = getattr(client, "_sock", None)
        try:
            if sock is not None:
                sock.close()
        except OSError:
            pass


def _note_out(address: str, args: list, peer: tuple[str, int]) -> None:
    try:
        from gremlin import osc_traffic  # type: ignore[attr-defined]
    except ImportError:
        return
    note = getattr(osc_traffic, "note", None)
    if note is None:
        return
    try:
        note("out", address, list(args), peer, [])
    except Exception:
        log.exception("OSC monitor: an outgoing message was not noted")


def send(
    target_id: str,
    address: str,
    values: list | tuple,
    types: list[str] | tuple[str, ...] | None = None,
    force: bool = False,
) -> bool:
    """Sends address with values to target_id ("reply": the last sender).

    types gives each value's type (auto/int/float/bool/text; missing:
    auto). Returns True when the message went out.
    """
    address = str(address or "").strip()
    if not address.startswith("/"):
        return False
    server, _ = _settings()
    enabled = server.get("output_enabled", True)
    if not force and (not enabled or not run_scope.running()):
        return False
    peer = resolve_target(target_id)
    if peer is None:
        return False
    kinds = list(types or [])
    args = [
        convert(value, kinds[i] if i < len(kinds) else "auto", address, i)
        for i, value in enumerate(values)
    ]
    try:
        _client(*peer).send_message(address, args)
    except (OSError, ValueError) as error:
        log.warning(f"OSC: could not send {address} to {peer[0]}:{peer[1]}: {error}")
        return False
    _note_out(address, args, peer)
    return True
