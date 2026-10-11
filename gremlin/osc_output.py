# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""OSC output: messages to a target or back to the last sender
(decision D-09-OSC-OUTPUT).

Send OSC actions and feedback send through send(). Targets and the output
switches come from OSC's own file (gremlin.osc_device_file), held in memory
and read again only when that file changes (E1, E2: its writers say
oscServerSettingsChanged; a replaced file also oscDeviceReloaded) and once
at each Run and Stop. Nothing
is sent while OSC output is off, or with no profile running, unless force
is given. One UDP client per (host, port), kept until the Run stops.

Every step and refusal is an Output line in Trace (D-09-OSC-TRACE); send
failures reach the logs at most 10 times per target per Run (E4).
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from gremlin import run_scope, trace

log = logging.getLogger("system")

REPLY = "reply"
VALUE_TYPES = ("auto", "int", "float", "bool", "text")

_lock = threading.Lock()
_last_sender: tuple[str, int] | None = None
# address -> the type of each value last received there.
_received: dict[str, list[str]] = {}
_clients: dict[tuple[str, int], Any] = {}
_close_at: int | None = None
# (server settings, targets) as last read from OSC's file; None: read again.
_cache: tuple[dict, list[dict]] | None = None
# The Run number _cache was read in: each Run and Stop reads the file once
# more (an edit made outside the program counts from the next Run).
_cache_run: int | None = None
_hooked = False


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
    """Forgets senders, received types, clients and the held settings
    (tests, quit)."""
    global _last_sender
    close_all()
    _last_sender = None
    _received.clear()
    invalidate()


def invalidate() -> None:
    """OSC's file changed: settings and targets are read again on the next
    send."""
    global _cache
    with _lock:
        _cache = None


def _hook() -> None:
    """Once: the signals OSC's file writers give drop the held settings."""
    global _hooked
    if _hooked:
        return
    _hooked = True
    try:
        from gremlin.signal import signal

        for name in ("oscServerSettingsChanged", "oscDeviceReloaded"):
            sig = getattr(signal, name, None)
            if sig is not None:
                sig.connect(invalidate)
    except Exception:  # noqa: BLE001 - no signals (bare tests): reset() only
        log.debug("OSC output: settings signals not connected", exc_info=True)


def _settings() -> tuple[dict, list[dict]]:
    """(server settings, targets): read from OSC's file once, held until
    the file changes."""
    global _cache, _cache_run
    _hook()
    run = run_scope.number()
    with _lock:
        held = _cache if _cache_run == run else None
    if held is not None:
        return held
    from gremlin import osc_device_file

    fresh = (osc_device_file.read_server(), osc_device_file.read_targets())
    with _lock:
        _cache, _cache_run = fresh, run
    if trace.osc_on("setup"):
        trace.osc(
            "setup", f"settings read from OSC/module.json ({len(fresh[1])} targets)"
        )
    return fresh


def _resolve(
    target_id: str, server: dict, targets: list[dict]
) -> tuple[tuple[str, int] | None, str, str]:
    """(peer or None, why not, the target's name)."""
    if target_id == REPLY:
        if not server.get("reply_to_sender", True):
            return None, "Reply to sender is Off", "reply"
        if _last_sender is None:
            return None, "no reply address yet", "reply"
        return _last_sender, "", "reply"
    for target in targets:
        if target.get("id") == target_id:
            name = str(target.get("name") or target_id)
            host = str(target.get("host") or "").strip()
            try:
                port = int(str(target.get("port")))
            except (TypeError, ValueError):
                port = 0
            if host and 0 < port < 65536:
                return (host, port), "", name
            return None, f"target {name} has no host or port", name
    return None, f"no target named {target_id}", str(target_id)


def resolve_target(target_id: str) -> tuple[str, int] | None:
    """(host, port) of a target id, or of the last sender for "reply"
    (None with Reply to sender off, nobody heard yet, or no such target)."""
    server, targets = _settings()
    return _resolve(target_id, server, targets)[0]


def convert(value: object, kind: str, address: str = "", index: int = 0) -> object:
    """value as the OSC type kind; "auto" is the type last received on the
    address, else float (text that isn't a number stays text)."""
    if kind not in VALUE_TYPES or kind == "auto":
        kind = received_type(address, index) or "float"
    if kind == "text":
        return _text(value)
    try:
        return _as(value, kind)
    except (TypeError, ValueError):
        if trace.osc_on("output"):
            trace.osc(
                "output",
                f"{address} value {value!r} is not {kind}: sent as text",
                rate=True,
                key=f"convert {address}",
            )
        return _text(value)


def _as(value: object, kind: str) -> object:
    """value as int, float or bool; raises TypeError/ValueError."""
    if kind == "int":
        if isinstance(value, str):
            return int(round(float(value.strip())))
        return int(round(float(value)))  # type: ignore[arg-type]
    if kind == "bool":
        if isinstance(value, str):
            text = value.strip().lower()
            if text in ("true", "yes", "on"):
                return True
            if text in ("false", "no", "off", ""):
                return False
            return float(text) != 0
        return bool(value)
    if isinstance(value, str):
        return float(value.strip())
    return float(value)  # type: ignore[arg-type]


def _text(value: object) -> str:
    """Text the short way, as Feedback sends it: 1 rather than 1.0."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _client(host: str, port: int) -> Any:  # noqa: ANN401
    global _close_at
    with _lock:
        client = _clients.get((host, port))
        opened = client is None
        if client is None:
            client = _make_client(host, port)
            _clients[(host, port)] = client
        if run_scope.running() and _close_at != run_scope.number():
            _close_at = run_scope.number()
            run_scope.on_stop(run_scope.Stage.DRIVERS, "OSC output", close_all)
    if opened and trace.osc_on("output"):
        trace.osc("output", f"client {host}:{port} open")
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
    if clients and trace.osc_on("output"):
        trace.osc("output", f"clients closed ({len(clients)})")


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
    except Exception as error:  # noqa: BLE001 - the send went; say it, go on
        trace.log_limited(
            "system",
            "osc-monitor-out",
            logging.ERROR,
            f"OSC Monitor: an outgoing message was not noted: {error!r}",
        )
        if trace.osc_on("output"):
            trace.osc(
                "output",
                f"Monitor: an outgoing message was not noted ({type(error).__name__})",
                warning=True,
                key="monitor",
            )


def _tags(args: list) -> str:
    """OSC type tags as sent, e.g. ",ifsT"."""
    out = ","
    for value in args:
        if isinstance(value, bool):
            out += "T" if value else "F"
        elif isinstance(value, int):
            out += "i"
        elif isinstance(value, float):
            out += "f"
        else:
            out += "s"
    return out


def _shown(args: list) -> str:
    return " ".join(repr(v) if isinstance(v, str) else str(v) for v in args)


def refusal(target_id: str, address: str, force: bool = False) -> str:
    """Why send() would refuse address to target_id now; "" when it would
    go (held settings only, no file read)."""
    address = str(address or "").strip()
    if not address.startswith("/"):
        return f"{address} is not an OSC address"
    server, targets = _settings()
    if not force and not server.get("output_enabled", True):
        return "OSC output is Off"
    if not force and not run_scope.running():
        return "the profile isn't running"
    return _resolve(target_id, server, targets)[1]


def _refused(target_id: str, address: str, reason: str) -> bool:
    """A send that didn't go: a BLOCKED Output line (never capped; rate
    limited per target and address, D-09-OSC-TRACE-ERRORS). False."""
    if trace.osc_on("output"):
        trace.osc(
            "output",
            f"send refused: {reason}",
            blocked=True,
            key=f"{target_id} {address}",
        )
    return False


def send(
    target_id: str,
    address: str,
    values: list | tuple,
    types: list[str] | tuple[str, ...] | None = None,
    force: bool = False,
    source: str = "",
) -> bool:
    """Sends address with values to target_id ("reply": the last sender).

    types gives each value's type (auto/int/float/bool/text; missing:
    auto). source names the sender in Trace (Send OSC, script, feedback
    row N). Returns True when the message went out.
    """
    address = str(address or "").strip()
    why = refusal(target_id, address, force)
    if why:
        return _refused(target_id, address, why)
    server, targets = _settings()
    peer, why, name = _resolve(target_id, server, targets)
    if peer is None:
        return _refused(target_id, address, why)
    kinds = list(types or [])
    args = [
        convert(value, kinds[i] if i < len(kinds) else "auto", address, i)
        for i, value in enumerate(values)
    ]
    try:
        _client(*peer).send_message(address, args)
    except (OSError, ValueError) as error:
        text = f"OSC: could not send {address} to {peer[0]}:{peer[1]}: {error}"
        # System and user log (OX3), at most 10 per target per Run (E4).
        key = f"osc-send {target_id}"
        trace.log_limited("system", key, logging.WARNING, text)
        trace.log_limited("user", key, logging.WARNING, text)
        if trace.osc_on("output"):
            trace.osc(
                "output",
                f"send error {name} {peer[0]}:{peer[1]}: {error}",
                warning=True,
                key=str(target_id),
            )
        return False
    if trace.osc_on("output"):
        where = f" ({source})" if source else ""
        trace.osc(
            "output",
            f"out {name} {peer[0]}:{peer[1]} {address} {_tags(args)} "
            f"{_shown(args)}{where}",
            rate=True,
            key=f"{target_id} {address}",
        )
    _note_out(address, args, peer)
    return True
