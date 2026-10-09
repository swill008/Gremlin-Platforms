# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Finding OSC devices on the network and being found by them (zeroconf).

Two switches in OSC's server settings, both off by default
(D-09-OSC-DISCOVERY): "announce" advertises this PC as an _osc._udp service
on the listening port; "find_devices" browses for _osc._udp services and
keeps the list found() returns (signal.oscDevicesFound says it changed).

Nothing here touches the network while both switches are off. The calls
only record what is wanted; one worker thread (gremlin.threads) does the
network work, so the UI thread never waits on it. Without the zeroconf
library available() is False and the switches do nothing.
"""

from __future__ import annotations

import ipaddress
import logging
import socket
import threading
from collections.abc import Callable
from typing import Any

from gremlin import threads
from gremlin.log_once import log_once

SERVICE_TYPE = "_osc._udp.local."
LOG = "system"
INFO_TIMEOUT_MS = 3000
SHUTDOWN_WAIT = 2.0

try:
    import zeroconf as _zeroconf_lib
except Exception:  # missing or broken: the program runs without discovery
    _zeroconf_lib = None

# Tests swap these for stand-ins; the program uses the zeroconf library.
_lib: Any = _zeroconf_lib


def available() -> bool:
    """True when the zeroconf library can be used."""
    return _lib is not None


def service_name() -> str:
    """This PC's announced name: "Gremlin-Platforms on <PC name>"."""
    return f"Gremlin-Platforms on {_pc_name()}"


def _pc_name() -> str:
    try:
        return socket.gethostname() or "this PC"
    except OSError:
        return "this PC"


_lock = threading.Lock()
# What the switches ask for; the worker makes it so.
_want: dict = {"announce": False, "port": 0, "host": "", "find": False}
_worker: threading.Thread | None = None
_stopping = False
_connected = False
# Owned by the worker thread (read under _lock by found()).
_zc: Any = None
_info: Any = None
_info_key: tuple | None = None
_browser: Any = None
_found: dict[str, dict] = {}


def set_announce(on: bool, port: int, host: str = "") -> None:
    """Announce this PC (on its addresses, or on host when one is set) on
    port, or stop announcing. Returns at once."""
    with _lock:
        _want["announce"] = bool(on)
        _want["port"] = int(port)
        _want["host"] = str(host or "")
    _kick()


def set_find(on: bool) -> None:
    """Browse for OSC devices, or stop and forget them. Returns at once."""
    with _lock:
        _want["find"] = bool(on)
    _kick()


def found() -> list[dict]:
    """The OSC devices found: [{name, host, port}], sorted by name."""
    with _lock:
        rows = [dict(row) for row in _found.values()]
    return sorted(rows, key=lambda r: r["name"].lower())


def start() -> None:
    """Follows OSC's server settings from now on (and applies them now).
    Safe to call more than once."""
    global _connected
    _make_relay()
    if not _connected:
        from gremlin.signal import signal

        sig = getattr(signal, "oscServerSettingsChanged", None)
        if sig is not None:
            sig.connect(apply_settings)
        _connected = True
    apply_settings()


def apply_settings() -> None:
    """Reads the switches and port from OSC's file and applies them."""
    from gremlin import osc_device_file

    try:
        server = osc_device_file.read_server()
    except Exception:
        logging.getLogger(LOG).exception("OSC discovery: reading settings")
        return
    host = str(server.get("host") or "")
    set_announce(bool(server.get("announce")), int(server.get("port") or 0), host)
    set_find(bool(server.get("find_devices")))


def shutdown(timeout: float = SHUTDOWN_WAIT) -> None:
    """Stops announcing and browsing and closes zeroconf (at quit). Waits
    up to timeout seconds; does nothing when discovery never ran."""
    global _stopping
    with _lock:
        _stopping = True
        _want["announce"] = False
        _want["find"] = False
        idle = _zc is None and _worker is None
    if idle:
        return
    worker = _kick(at_quit=True)
    if worker is not None:
        worker.join(timeout)
        if worker.is_alive():
            log_once(
                LOG,
                "osc-discovery-quit",
                logging.WARNING,
                "OSC discovery: still stopping at quit",
            )


def _kick(at_quit: bool = False) -> threading.Thread | None:
    """Starts the worker unless it is running (it re-reads _want each pass)."""
    global _worker
    with _lock:
        if _stopping and not at_quit:
            return None
        if not available():
            return None
        nothing = not (_want["announce"] or _want["find"]) and _zc is None
        if nothing:
            return None
        if _worker is not None:
            return _worker
        _worker = threads.start("OSC discovery", _work)
        return _worker


def _wanted() -> tuple:
    with _lock:
        return (_want["announce"], _want["port"], _want["host"], _want["find"])


def _work() -> None:
    global _worker
    try:
        while True:
            want = _wanted()
            try:
                _apply(*want)
            except Exception:
                log_once(
                    LOG,
                    "osc-discovery-apply",
                    logging.ERROR,
                    "OSC discovery: could not apply the switches",
                )
                logging.getLogger(LOG).debug("OSC discovery", exc_info=True)
            with _lock:
                if (
                    _want["announce"],
                    _want["port"],
                    _want["host"],
                    _want["find"],
                ) == want:
                    _worker = None
                    return
    finally:
        with _lock:
            if _worker is threading.current_thread():
                _worker = None


def _apply(announce: bool, port: int, host: str, find: bool) -> None:
    global _zc, _info, _info_key, _browser
    if (announce or find) and _zc is None:
        _zc = _lib.Zeroconf()
    key = (port, host)
    if _info is not None and (not announce or key != _info_key):
        info, _info, _info_key = _info, None, None
        _quietly(lambda: _zc.unregister_service(info), "unannounce")
    if announce and _info is None and port > 0:
        info = _service_info(port, host)
        _zc.register_service(info, allow_name_change=True)
        _info, _info_key = info, key
    if find and _browser is None:
        _browser = _lib.ServiceBrowser(_zc, SERVICE_TYPE, handlers=[_on_change])
    if not find and _browser is not None:
        browser, _browser = _browser, None
        _quietly(browser.cancel, "stop finding")
        with _lock:
            had = bool(_found)
            _found.clear()
        if had:
            _emit()
    if not (announce or find) and _zc is not None:
        zc, _zc = _zc, None
        _quietly(zc.close, "close")


def _quietly(fn: Callable[[], object], what: str) -> None:
    try:
        fn()
    except Exception:
        logging.getLogger(LOG).debug("OSC discovery: %s", what, exc_info=True)


def _addresses(host: str) -> list[bytes]:
    hosts: list[str]
    if host and host != "0.0.0.0":
        hosts = [host]
    else:
        from gremlin.osc import local_ipv4_addresses

        hosts = [
            ip for ip in local_ipv4_addresses() if ip not in ("0.0.0.0", "127.0.0.1")
        ] or ["127.0.0.1"]
    out = []
    for ip in hosts:
        try:
            out.append(ipaddress.IPv4Address(ip).packed)
        except ValueError:
            pass
    return out


def _service_info(port: int, host: str) -> Any:  # noqa: ANN401
    pc = _pc_name()
    return _lib.ServiceInfo(
        SERVICE_TYPE,
        f"{service_name()}.{SERVICE_TYPE}",
        addresses=_addresses(host),
        port=port,
        properties={},
        server=f"{pc}.local.",
    )


def _on_change(**kwargs: Any) -> None:  # noqa: ANN401
    """ServiceBrowser handler (zeroconf's thread): keeps _found current."""
    name = str(kwargs.get("name") or "")
    state = kwargs.get("state_change")
    zc = kwargs.get("zeroconf")
    removed = getattr(state, "name", str(state)) == "Removed"
    own = _info is not None and name == getattr(_info, "name", None)
    if removed or own:
        with _lock:
            changed = _found.pop(name, None) is not None
    else:
        row = _lookup(zc, str(kwargs.get("service_type") or SERVICE_TYPE), name)
        if row is None:
            return
        with _lock:
            if _browser is None:
                return
            changed = _found.get(name) != row
            _found[name] = row
    if changed:
        _emit()


def _lookup(zc: Any, service_type: str, name: str) -> dict | None:  # noqa: ANN401
    try:
        info = zc.get_service_info(service_type, name, timeout=INFO_TIMEOUT_MS)
    except Exception:
        logging.getLogger(LOG).debug("OSC discovery: lookup", exc_info=True)
        return None
    if info is None or not info.port:
        return None
    hosts = [a for a in info.parsed_addresses() if ":" not in a]
    if not hosts:
        return None
    suffix = "." + service_type
    label = name[: -len(suffix)] if name.endswith(suffix) else name
    return {"name": label, "host": hosts[0], "port": int(info.port)}


def _say_found() -> None:
    from gremlin.signal import signal

    sig = getattr(signal, "oscDevicesFound", None)
    if sig is not None:
        sig.emit()


_relay: Any = None


def _make_relay() -> None:
    """Made on the main thread (start()): oscDevicesFound said from
    zeroconf's or the worker's thread is queued to the main thread."""
    global _relay
    if _relay is not None:
        return
    from PySide6 import QtCore

    class _Relay(QtCore.QObject):
        wake = QtCore.Signal()

    relay = _Relay()
    relay.wake.connect(_say_found, QtCore.Qt.ConnectionType.QueuedConnection)
    _relay = relay


def _emit() -> None:
    """Says oscDevicesFound on the main thread."""
    if threading.current_thread() is threading.main_thread() or _relay is None:
        _say_found()
    else:
        _relay.wake.emit()


def _reset_for_tests() -> None:
    """Forgets all state (tests only; nothing is closed)."""
    global _worker, _stopping, _zc, _info, _info_key, _browser
    with _lock:
        _want.update(announce=False, port=0, host="", find=False)
        _worker = None
        _stopping = False
        _zc = _info = _info_key = _browser = None
        _found.clear()
