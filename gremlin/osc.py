# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-only
"""OSC virtual device, UDP listener, and event inject for Path B."""

from __future__ import annotations

import collections
import ctypes
import errno
import functools
import importlib
import ipaddress
import logging
import math
import os
import socket
import sys
import threading
import weakref
from collections.abc import Callable
from typing import Any

from PySide6 import QtCore

from gremlin import axis_shaping, clock, threads
from gremlin.common import SingletonDecorator, SingletonMetaclass
from gremlin.error import GremlinError
from gremlin.log_once import log_once
from gremlin.modules import ids
from gremlin.osc_rows import OscRow, OscRows
from gremlin.types import InputType

log = logging.getLogger("system")
user_log = logging.getLogger("user")

OSC_DEVICE_UUID = ids.OSC

OSC_SECTION = "osc"
OSC_GROUP = "connection"

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8001
DEFAULT_OUTPUT_PORT = 8000
DEFAULT_AUTORELEASE_MS = 250

# address, args, peer (host, port) or None.
MessageCallback = Callable[[str, tuple[Any, ...], "tuple[str, int] | None"], None]
# Most pulses one encoder message can queue (a wild value can't flood).
MAX_ENC_TICKS = 32
# Fastest liveChanged per input (OX1): 10 a second.
LIVE_INTERVAL_S = 0.1
# Encoder acceleration (S164): ticks inside this window speed the turn up,
# multiplier = 1 + factor * (ticks in the window - 1), at most ENC_ACCEL_MAX.
ENC_ACCEL_WINDOW_S = 0.1
ENC_ACCEL_MAX = 8.0
ENC_ACCEL_FACTORS = {"off": 0.0, "low": 0.5, "medium": 1.0, "high": 2.0}
# The hold_open token recorders keep the port open with.
RECORDER_TOKEN = "osc-recorder"
# Monitor's Input column for a message from a sender not on the allow-list.
BLOCKED = "blocked"

# Run-time state of one input at one address: (uid, address key). A
# pattern input keeps its state per address it receives (OX7, S147); an
# exact input has one state (address key "").
StateKey = tuple[str, str]


def local_ipv4_addresses() -> list[str]:
    found: list[str] = []

    def add(ip: str) -> None:
        if ip and ip not in found:
            found.append(ip)

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            add(sock.getsockname()[0])
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            add(info[4][0])
    except OSError:
        pass
    add("127.0.0.1")
    add("0.0.0.0")
    return found


def default_bind_host() -> str:
    for ip in local_ipv4_addresses():
        if ip not in ("127.0.0.1", "0.0.0.0"):
            return ip
    return DEFAULT_HOST


def osc_option(cfg: Any, name: str) -> Any:
    if cfg.exists(OSC_SECTION, OSC_GROUP, name):
        return cfg.value(OSC_SECTION, OSC_GROUP, name)
    if cfg.exists("global", "osc", name):
        return cfg.value("global", "osc", name)
    return None


@functools.lru_cache(maxsize=64)
def _networks(entries: tuple[str, ...]) -> tuple[Any, ...]:
    out = []
    for entry in entries:
        try:
            out.append(ipaddress.ip_network(str(entry).strip(), strict=False))
        except ValueError:
            log.warning("OSC: allow-list entry %r is not an IP or range", entry)
    return tuple(out)


def sender_allowed(
    host: object, allow: list[str] | tuple[str, ...] | None = None
) -> bool:
    """True when OSC accepts a message from host (S160): the allow-list is
    empty (everyone), or host is one of its addresses or inside one of its
    CIDR ranges. allow defaults to OSC's saved server settings."""
    if allow is None:
        allow = server_settings().get("allow_senders") or []
    if not allow:
        return True
    try:
        address = ipaddress.ip_address(str(host).split("%", 1)[0].strip())
    except ValueError:
        return False
    candidates = [address]
    mapped = getattr(address, "ipv4_mapped", None)
    if mapped is not None:
        candidates.append(mapped)
    return any(
        ip in net
        for net in _networks(tuple(allow))
        for ip in candidates
        if ip.version == net.version
    )


def is_pressed(args: tuple[Any, ...]) -> bool:
    if not args:
        return True
    value = args[0]
    try:
        return float(value) != 0.0
    except (TypeError, ValueError):
        return bool(value)


def parse_port(value: Any, default: int = DEFAULT_PORT) -> int:
    text = str(value or "").replace(",", "").strip()
    try:
        port = int(text)
    except ValueError:
        return default
    if 1 <= port <= 65535:
        return port
    return default


def parse_delay_ms(value: Any) -> int:
    text = str(value or "").replace(",", "").strip()
    try:
        delay = int(float(text))
    except ValueError:
        return DEFAULT_AUTORELEASE_MS
    return max(0, min(delay, 10000))


def guess_input_type(args: tuple[Any, ...]) -> InputType:
    if not args:
        return InputType.JoystickButton
    try:
        value = float(args[0])
    except (TypeError, ValueError):
        return InputType.JoystickButton
    if value in (0.0, 1.0) or abs(value) > 1.0:
        return InputType.JoystickButton
    return InputType.JoystickAxis


class OscDevice(metaclass=SingletonMetaclass):
    """OSC's inputs: one shared OscRows (OSC's module file, D-09-OSC-FILE),
    the same for every profile."""

    device_guid = OSC_DEVICE_UUID

    class Input:
        # Old profile reader's row type; kept until profile.py reads the file.
        def __init__(self, label: str, input_id: int, input_type: InputType) -> None:
            self.label = label
            self.id = input_id
            self.type = input_type

    def __init__(self) -> None:
        self.rows = OscRows()

    # Thin forms of the rows' API for older callers.

    def reset(self) -> None:
        self.rows.reset()

    def create(
        self,
        input_type: InputType,
        label: str | None = None,
        input_id: int | None = None,
        **settings: Any,  # noqa: ANN401
    ) -> OscRow:
        if input_type not in (InputType.JoystickAxis, InputType.JoystickButton):
            raise GremlinError(f"OSC inputs must be axis or button, got {input_type}")
        if label is None:
            prefix = (
                "/osc/axis" if input_type == InputType.JoystickAxis else "/osc/button"
            )
            number = input_id or 1
            while self.rows.by_number(input_type, number) is not None:
                number += 1
            label = f"{prefix}/{number}"
        return self.rows.create(input_type, label, input_id=input_id, **settings)

    def labels_of_type(self, type_list: list[InputType] | None = None) -> list[str]:
        if not type_list:
            type_list = [InputType.JoystickAxis, InputType.JoystickButton]
        return [
            row.label
            for row in sorted(
                self.rows.rows(), key=lambda r: (r.input_type.name, r.input_id)
            )
            if row.input_type in type_list
        ]

    def find_address(self, address: str) -> OscRow | None:
        key = (address or "").strip().casefold()
        for row in self.rows.rows():
            if row.label.casefold() == key:
                return row
        return None

    def find_by_id(self, input_type: InputType, input_id: int) -> OscRow | None:
        return self.rows.by_number(input_type, input_id)


class OscListener:
    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        callback: MessageCallback | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.callback = callback
        self._server = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._server is not None:
            return
        dispatcher = _dispatcher_class()()
        dispatcher.set_default_handler(self._on_message, needs_reply_address=True)
        self._server = _server_class()((self.host, self.port), dispatcher)
        # Stopping waits for the server's next poll (0.5 s at most).
        self._thread = threads.start(
            "OSC listener", self._server.serve_forever, stop=self._server.shutdown
        )
        log.info("OSC listening on %s:%s", self.host, self.port)

    def bound_port(self) -> int:
        """The port actually open (the one the OS picked for port 0)."""
        if self._server is None:
            return 0
        return int(self._server.server_address[1])

    def stop(self) -> None:
        if self._server is None:
            return
        self._server.shutdown()
        self._server.server_close()
        self._server = None
        self._thread = None
        log.info("OSC listener stopped")

    def _on_message(
        self, client: Any, address: str, *args: Any  # noqa: ANN401
    ) -> None:
        address = (address or "").casefold()
        if address == "/noop":
            return
        peer = None
        if isinstance(client, (tuple, list)) and len(client) >= 2:
            peer = (str(client[0]), int(client[1]))
        if self.callback is not None:
            self.callback(address, args, peer)


def report_malformed(client: object, reason: str) -> None:
    """A packet that isn't OSC (OX3): once per sender into the user log and
    the program log (called on the listener's thread)."""
    host = client[0] if isinstance(client, (tuple, list)) and client else "?"
    text = f"OSC: a malformed packet from {host} was ignored ({reason})"
    log_once("user", ("osc-malformed", host), logging.WARNING, text)
    log_once("system", ("osc-malformed", host), logging.WARNING, text)


_CLASSES: dict[str, type] = {}


def _dispatcher_class() -> type:
    """python-osc's Dispatcher, reporting packets it can't parse (it drops
    them silently)."""
    if "dispatcher" not in _CLASSES:
        from pythonosc import osc_packet
        from pythonosc.dispatcher import Dispatcher

        class _Dispatcher(Dispatcher):
            def call_handlers_for_packet(
                self, data: bytes, client_address: tuple[str, int]
            ) -> list:
                try:
                    osc_packet.OscPacket(data)
                except osc_packet.ParseError as exc:
                    report_malformed(client_address, str(exc) or "cannot be read")
                    return []
                return super().call_handlers_for_packet(data, client_address)

        _CLASSES["dispatcher"] = _Dispatcher
    return _CLASSES["dispatcher"]


def _server_class() -> type:
    """python-osc's threading UDP server, reporting datagrams it refuses
    (not a message or bundle)."""
    if "server" not in _CLASSES:
        from pythonosc.osc_server import ThreadingOSCUDPServer

        class _Server(ThreadingOSCUDPServer):
            def verify_request(
                self, request: Any, client_address: Any  # noqa: ANN401
            ) -> bool:
                ok = super().verify_request(request, client_address)
                if not ok:
                    report_malformed(client_address, "not an OSC message")
                return ok

        _CLASSES["server"] = _Server
    return _CLASSES["server"]


# -- who holds a port (OX2) ---------------------------------------------------

_AF_INET6 = 23
_UDP_TABLE_OWNER_PID = 1
_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
_ADDR_IN_USE = {errno.EADDRINUSE, 10048}


def _udp_owner_pids(port: int) -> list[int]:
    """PIDs with a UDP socket on port (IPv4, then IPv6), from Windows'
    GetExtendedUdpTable."""
    iphlpapi = ctypes.WinDLL("iphlpapi")  # type: ignore[attr-defined]
    found: list[int] = []
    # Row words: IPv4 addr, port, pid; IPv6 addr[4], scope, port, pid.
    for family, words in ((socket.AF_INET, 3), (_AF_INET6, 7)):
        size = ctypes.c_ulong(0)
        iphlpapi.GetExtendedUdpTable(
            None, ctypes.byref(size), False, family, _UDP_TABLE_OWNER_PID, 0
        )
        if size.value == 0:
            continue
        buf = ctypes.create_string_buffer(size.value)
        if iphlpapi.GetExtendedUdpTable(
            buf, ctypes.byref(size), False, family, _UDP_TABLE_OWNER_PID, 0
        ):
            continue
        count = ctypes.c_ulong.from_buffer(buf).value
        table = (ctypes.c_ulong * (1 + count * words)).from_buffer(buf)
        for i in range(count):
            row = 1 + i * words
            if socket.ntohs(table[row + words - 2] & 0xFFFF) == port:
                found.append(int(table[row + words - 1]))
    return found


def _process_name(pid: int) -> str:
    kernel32 = ctypes.WinDLL("kernel32")  # type: ignore[attr-defined]
    handle = kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return ""
    try:
        size = ctypes.c_ulong(1024)
        buf = ctypes.create_unicode_buffer(size.value)
        if not kernel32.QueryFullProcessImageNameW(
            handle, 0, buf, ctypes.byref(size)
        ):
            return ""
        return os.path.basename(buf.value)
    finally:
        kernel32.CloseHandle(handle)


def port_holder(port: int, host: str = "") -> tuple[str, int] | None:
    """(process name, PID) of a program with a UDP socket on port, or None
    when it can't be told (not Windows, nobody found, the lookup failed)."""
    if sys.platform != "win32":
        return None
    try:
        for pid in _udp_owner_pids(int(port)):
            return (_process_name(pid) or "a program", pid)
    except (OSError, ValueError, AttributeError):
        log.debug("OSC: could not look up who holds port %s", port, exc_info=True)
    return None


def bind_error_detail(host: str, port: int, exc: OSError) -> str:
    """The text under "Could not bind OSC on host:port.": the OS error and,
    for a port in use, the program holding it (OX2)."""
    detail = str(exc)
    in_use = exc.errno in _ADDR_IN_USE or getattr(exc, "winerror", None) == 10048
    if in_use:
        holder = port_holder(port, host)
        if holder is None:
            detail += f" Port {port} is in use by another program."
        else:
            detail += f" Port {port} is in use by {holder[0]} (PID {holder[1]})."
    return detail


SERVER_DEFAULTS: dict[str, Any] = {
    "enabled": True,
    "host": "",
    "port": DEFAULT_PORT,
    "output_host": DEFAULT_HOST,
    "output_port": DEFAULT_OUTPUT_PORT,
    "autorelease_no_arg": True,
    "autorelease_delay_ms": DEFAULT_AUTORELEASE_MS,
    "pad_args": False,
    "allow_senders": [],
}


def server_settings() -> dict[str, Any]:
    """OSC's server settings (its module file's "server" part,
    D-09-OSC-FILE) over the defaults."""
    settings = dict(SERVER_DEFAULTS)
    try:
        from gremlin import osc_device_file
    except ImportError:
        return settings
    try:
        settings.update(osc_device_file.read_server() or {})
    except Exception:
        log.exception("OSC settings could not be read; using the defaults")
    return settings


def bind_address(host: object) -> str:
    """A blank host means every address on this PC."""
    return str(host or "").strip() or "0.0.0.0"


def _value_at(args: tuple[object, ...], index: int) -> object:
    return args[index] if 0 <= index < len(args) else None


def _number(value: object) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def scale_axis(value: float, low: float, high: float) -> float:
    """value from [low, high] to -1..1, clamped."""
    if high == low:
        return 0.0
    scaled = (value - low) / (high - low) * 2.0 - 1.0
    return max(-1.0, min(1.0, scaled))


_MISSING_HOOKS: set[str] = set()


def _hook(module: str, name: str) -> Callable[..., Any] | None:
    """A function of another OSC module (traffic, output, feedback), or None
    while that module is missing."""
    full = f"gremlin.{module}"
    mod = sys.modules.get(full)
    if mod is None:
        if module in _MISSING_HOOKS:
            return None
        try:
            mod = importlib.import_module(full)
        except ImportError:
            _MISSING_HOOKS.add(module)
            return None
    func = getattr(mod, name, None)
    return func if callable(func) else None


def _call_hook(module: str, name: str, *args: Any) -> Any:  # noqa: ANN401
    func = _hook(module, name)
    if func is None:
        return None
    try:
        return func(*args)
    except Exception:
        log.exception("OSC %s.%s failed", module, name)
        return None


def input_name(row: OscRow) -> str:
    kind = "Axis" if row.input_type == InputType.JoystickAxis else "Button"
    return f"OSC {kind} {row.input_id}"


def match_name(row: OscRow) -> str:
    """The Monitor's name for a match: a pattern input names its pattern,
    e.g. "OSC Axis 3 (/fader/*)"."""
    if row.is_pattern:
        return f"{input_name(row)} ({row.label})"
    return input_name(row)


def state_key(row: OscRow, address: str) -> StateKey:
    """Where a message's state is kept: per address for a pattern input
    (any case), once for an exact input."""
    if row.is_pattern:
        return (row.uid, str(address or "").strip().casefold())
    return (row.uid, "")


def shape_axis(row: OscRow, value: float) -> float:
    """An axis input's value after its deadzone and Invert (S161)."""
    low, high = row.deadzone
    return axis_shaping.shape(value, row.invert, low, high)


def _osc_state(method: str, *args: Any) -> None:  # noqa: ANN401
    """Writes OSC's last values for conditions, scripts and macros (S159)
    through input_cache.osc_state(); nothing while input_cache has none."""
    state = _call_hook("input_cache", "osc_state")
    func = getattr(state, method, None) if state is not None else None
    if not callable(func):
        return
    try:
        func(*args)
    except Exception:
        log.exception("OSC state %s failed", method)


def encoder_turn(fmt: str, value: float) -> float:
    """Steps turned (+ clockwise, - counter-clockwise) for a format:
    "direction" is 1 = cw, 0 = ccw; "signed" is +n / -n."""
    if fmt == "direction":
        return 1.0 if value != 0.0 else -1.0
    return value


def profile_uses_osc() -> bool:
    """The open profile has a binding or Assign Hardware link on an OSC
    input (any mode); both are input items under OSC's guid."""
    from gremlin import shared_state

    profile = getattr(shared_state, "current_profile", None)
    inputs = getattr(profile, "inputs", None) or {}
    try:
        return bool(inputs.get(OSC_DEVICE_UUID))
    except AttributeError:
        return False


_UNSET = object()


@SingletonDecorator
class OscRuntime(QtCore.QObject):
    incoming = QtCore.Signal(str, object, object)
    learned = QtCore.Signal(str, object)
    listenChanged = QtCore.Signal()
    # An input's live value changed (OX1): its uid; at most every
    # LIVE_INTERVAL_S per input, and the latest value always follows.
    liveChanged = QtCore.Signal(str)
    # play() from another thread: carried to the runtime's thread.
    _playRequested = QtCore.Signal(str, str, object)

    def __init__(self) -> None:
        super().__init__()
        # uid -> {value, axis, pressed, last_seen, synthetic} (OX1).
        self._live: dict[str, dict[str, Any]] = {}
        self._live_sent: dict[str, float] = {}
        self._live_pending: set[str] = set()
        self._live_timer = QtCore.QTimer(self)
        self._live_timer.setSingleShot(True)
        self._live_timer.timeout.connect(self._flush_live)
        self._listener: OscListener | None = None
        # A profile runs (start() until stop()); the port opens for it only
        # when it uses OSC inputs (09 Q5). A Listen keeps the port open only
        # while it lasts.
        self._running = False
        self._uses_osc = False
        self._learn = False
        self._hold_learn = False
        # Who started the Listen (a page model); only it handles the capture.
        self._learn_owner: weakref.ref | None = None
        self._settings: dict[str, Any] = dict(SERVER_DEFAULTS)
        self._timers: dict[StateKey, QtCore.QTimer] = {}
        self._last: dict[StateKey, Any] = {}
        # Buttons pressed and not yet released: state key -> the mode pressed
        # in. A pattern input is pressed while any of its addresses is (OR).
        self._held: dict[StateKey, str] = {}
        # The address each input last received (OX7 Q5).
        self._last_address: dict[str, str] = {}
        # Who holds the port open without a Run (the OSC Monitor).
        self._holders: set[str] = set()
        # Encoder state per state key (D-09-OSC-ENCODER; per address, OX7).
        self._enc_format: dict[StateKey, str] = {}
        self._enc_value: dict[StateKey, float] = {}
        self._enc_pending: dict[StateKey, int] = {}
        # Encoder acceleration (S164): uid -> (clock.monotonic(), ticks) of
        # the turns inside the window.
        self._enc_ticks: dict[str, collections.deque] = {}
        # Macro Record and others (S159): called with (uid, kind, value) for
        # every input event, with or without a Run, while registered.
        self._recorders: list[Callable[[str, str, Any], None]] = []
        self.incoming.connect(self._on_main)
        self._playRequested.connect(self._play_main)
        from gremlin.signal import signal as ui_signal

        changed = getattr(ui_signal, "oscServerSettingsChanged", None)
        if changed is not None:
            changed.connect(self.sync_bind)

    def is_listening(self) -> bool:
        return self._learn

    def listens_for(self, owner: object) -> bool:
        """True when owner started the current Listen (or nobody did, or
        the one who did is gone)."""
        held = None if self._learn_owner is None else self._learn_owner()
        return held is None or held is owner

    def listen_once(self, hold: bool = False, owner: object = None) -> bool:
        """Listen for the next message (every message with hold). owner, the
        page model asking, is the only one that handles the capture."""
        from gremlin.signal import signal as ui_signal

        self._hold_learn = hold
        self._learn_owner = None if owner is None else weakref.ref(owner)
        self._bind()
        if self._listener is None:
            self._learn = False
            self._hold_learn = False
            self._learn_owner = None
            self.listenChanged.emit()
            ui_signal.showError.emit(
                "Could not start OSC listener.",
                "Turn OSC on and check its host and port in OSC › Module Setup.",
            )
            return False
        self._learn = True
        self.listenChanged.emit()
        log.info("OSC listen-once waiting for next packet hold=%s", hold)
        return True

    def listen_bulk(self, owner: object = None) -> bool:
        return self.listen_once(hold=True, owner=owner)

    def cancel_listen(self, owner: object = None) -> None:
        """Stop listening. With owner, only a Listen it started (or one
        nobody owns) stops: another window's Cancel leaves it running."""
        if owner is not None and not self.listens_for(owner):
            return
        self._learn_owner = None
        self._hold_learn = False
        was = self._learn
        self._learn = False
        self._close_if_idle()
        if was:
            self.listenChanged.emit()
            log.info("OSC listen-once cancelled")

    def hold_open(self, token: str) -> bool:
        """Keeps the port open for token (the OSC Monitor) until
        release_open(token), with or without a Run; False when it can't bind."""
        self._holders.add(str(token))
        self._bind()
        return self._listener is not None

    def release_open(self, token: str) -> None:
        """token no longer needs the port; it closes when nothing else does."""
        self._holders.discard(str(token))
        self._close_if_idle()

    def is_open(self) -> bool:
        return self._listener is not None

    # -- recorders (S159) ------------------------------------------------------

    def add_recorder(self, callback: Callable[[str, str, Any], None]) -> bool:
        """callback gets (uid, kind, value) for every OSC input event, kind
        "button" (value pressed) or "axis" (value -1..1, after shaping), with
        or without a Run; the port is held open while any recorder is
        registered. False when the port can't open."""
        if callback not in self._recorders:
            self._recorders.append(callback)
        return self.hold_open(RECORDER_TOKEN)

    def remove_recorder(self, callback: Callable[[str, str, Any], None]) -> None:
        if callback in self._recorders:
            self._recorders.remove(callback)
        if self._recorders:
            return
        if not self._running:
            # What recording alone started (pulses, held buttons) ends quietly.
            self._reset_state()
        self.release_open(RECORDER_TOKEN)

    def recording(self) -> bool:
        return bool(self._recorders)

    def _record(self, uid: str, kind: str, value: Any) -> None:  # noqa: ANN401
        for callback in list(self._recorders):
            try:
                callback(uid, kind, value)
            except Exception:
                log.exception("OSC recorder failed")

    def _reset_state(self) -> None:
        """Run-time input state dropped without any event."""
        self._enc_pending.clear()
        for key in list(self._timers):
            self._cancel_release(key)
        self._held.clear()
        self._last.clear()
        self._enc_format.clear()
        self._enc_value.clear()
        self._enc_ticks.clear()

    def _needs_port(self) -> bool:
        return (
            self._learn
            or bool(self._holders)
            or (self._running and self._uses_osc)
        )

    def _close_if_idle(self) -> None:
        if not self._needs_port():
            self._unbind()

    def _read_options(self) -> tuple[bool, str, int]:
        self._settings = server_settings()
        return (
            bool(self._settings.get("enabled", True)),
            bind_address(self._settings.get("host")),
            parse_port(self._settings.get("port")),
        )

    def _bind(self) -> None:
        """Opens the port with the current settings (rebinds when they differ)."""
        from gremlin.signal import signal as ui_signal

        enabled, host, port = self._read_options()
        if not enabled:
            self._unbind()
            log.info("OSC listener off in OSC's settings")
            return
        if (
            self._listener is not None
            and self._listener.host == host
            and self._listener.port == port
        ):
            return
        self._unbind()
        try:
            listener = OscListener(host, port, self._from_thread)
            listener.start()
            self._listener = listener
            log.info(
                "OSC output target %s:%s",
                self._settings.get("output_host"),
                self._settings.get("output_port"),
            )
        except ImportError:
            log.error("OSC: python-osc is not installed")
            ui_signal.showError.emit(
                "OSC requires python-osc.",
                "In the repo folder run: poetry add python-osc",
            )
        except OSError as exc:
            title = f"Could not bind OSC on {host}:{port}."
            detail = bind_error_detail(host, port, exc)
            # Logged as well as shown (OX3): the user log and the program log.
            user_log.error("OSC: %s %s", title, detail)
            log.error("OSC: %s %s", title, detail)
            ui_signal.showError.emit(title, detail)

    def _unbind(self) -> None:
        if self._listener is None:
            return
        self._listener.stop()
        self._listener = None

    def start(self) -> None:
        """A profile starts running: listen until stop() when it uses OSC
        inputs (09 Q5)."""
        if not self._running:
            # State a recording made without a Run doesn't carry into it.
            self._reset_state()
        self._running = True
        self._uses_osc = profile_uses_osc()
        if self._needs_port():
            self._bind()
        else:
            self._settings = server_settings()
            log.info("OSC port not opened: the profile has no OSC inputs")

    def release_held(self) -> None:
        """Stop, while the profile's callbacks still run: every held button
        (a press not yet released, or waiting on its auto-release) gets one
        release; pending auto-releases are cancelled."""
        self._enc_pending.clear()
        for key in list(self._timers):
            self._cancel_release(key)
        held, self._held = self._held, {}
        released: set[str] = set()
        for (uid, _address), mode in held.items():
            if uid in released:
                continue  # one release per input, however many addresses
            released.add(uid)
            row = OscDevice().rows.by_uid(uid)
            if row is not None:
                self._emit_button(row, False, mode, self._last_address.get(uid))

    def stop(self) -> None:
        """The profile stopped: held buttons released, port closed."""
        # Released while still running: _emit_* only reach the profile then.
        self.release_held()
        self._running = False
        self._uses_osc = False
        self._last.clear()
        self._enc_format.clear()
        self._enc_value.clear()
        self._enc_ticks.clear()
        _osc_state("clear")
        self._hold_learn = False
        self._learn = False
        self.listenChanged.emit()
        self._close_if_idle()

    def sync_bind(self) -> None:
        """Settings changed: apply them at once while a profile runs or a
        Listen is open (turning OSC on binds; a failed bind tries again)."""
        if not self._needs_port():
            self._settings = server_settings()
            return
        self._bind()
        if self._listener is None and self._learn:
            self._learn = False
            self._hold_learn = False
            self.listenChanged.emit()

    def _from_thread(
        self,
        address: str,
        args: tuple[Any, ...],
        peer: tuple[str, int] | None = None,
    ) -> None:
        self.incoming.emit(address, args, peer)

    # -- inputs (D-09-OSC-INPUT) ----------------------------------------------

    def _emit_button(
        self, row: OscRow, pressed: bool, mode: str, address: str | None
    ) -> None:
        self._record(row.uid, "button", pressed)
        if not self._running:
            return
        self._send_button(row, pressed, mode, address, synthetic=False)

    def _send_button(
        self,
        row: OscRow,
        pressed: bool,
        mode: str,
        address: str | None,
        synthetic: bool,
    ) -> None:
        from gremlin.event_handler import Event, EventListener

        _osc_state("set_button", row.uid, pressed)
        EventListener().joystick_event.emit(
            Event(
                event_type=InputType.JoystickButton,
                identifier=row.input_id,
                device_guid=OSC_DEVICE_UUID,
                mode=mode,
                is_pressed=pressed,
                synthetic=synthetic,
                osc_address=address,
            )
        )

    def _button(
        self, row: OscRow, key: StateKey, address: str, pressed: bool, mode: str
    ) -> None:
        """One address presses or releases the input. A pattern input is
        pressed while any of its addresses is (OR, S147): another address's
        press or release changes nothing while one still holds it."""
        others = any(k[0] == row.uid and k != key for k in self._held)
        if pressed:
            self._held[key] = mode
        else:
            self._held.pop(key, None)
        if others:
            return
        self._emit_button(row, pressed, mode, address)

    def _emit_axis(self, row: OscRow, value: float, mode: str, address: str) -> None:
        self._record(row.uid, "axis", value)
        if not self._running:
            return
        self._send_axis(row, value, mode, address, synthetic=False)

    def _send_axis(
        self,
        row: OscRow,
        value: float,
        mode: str,
        address: str | None,
        synthetic: bool,
    ) -> None:
        from gremlin.event_handler import Event, EventListener

        _osc_state("set_axis", row.uid, value)
        EventListener().joystick_event.emit(
            Event(
                event_type=InputType.JoystickAxis,
                identifier=row.input_id,
                device_guid=OSC_DEVICE_UUID,
                mode=mode,
                value=value,
                raw_value=value,
                synthetic=synthetic,
                osc_address=address,
            )
        )

    def _delay_of(self, row: OscRow) -> int:
        if row.delay_ms is not None:
            return parse_delay_ms(row.delay_ms)
        return parse_delay_ms(self._settings.get("autorelease_delay_ms"))

    def _cancel_release(self, key: StateKey) -> None:
        timer = self._timers.pop(key, None)
        if timer is not None:
            timer.stop()
            timer.deleteLater()

    def _pulse(self, row: OscRow, key: StateKey, address: str, mode: str) -> None:
        """Press, then release after the input's delay; a new press restarts
        the wait."""
        self._button(row, key, address, True, mode)
        self._cancel_release(key)
        timer = QtCore.QTimer(self)
        timer.setSingleShot(True)
        timer.setInterval(self._delay_of(row))
        uid = row.uid
        timer.timeout.connect(lambda: self._release(uid, key, address, mode))
        self._timers[key] = timer
        timer.start()

    def _release(self, uid: str, key: StateKey, address: str, mode: str) -> None:
        self._cancel_release(key)
        row = OscDevice().rows.by_uid(uid)
        if row is not None:
            self._button(row, key, address, False, mode)
            # An encoder's queued ticks: one more press + release each.
            pending = self._enc_pending.get(key, 0)
            if pending > 0:
                self._enc_pending[key] = pending - 1
                self._pulse(row, key, address, mode)
            else:
                self._enc_pending.pop(key, None)

    def _encoder(
        self, row: OscRow, key: StateKey, address: str, value: object, mode: str
    ) -> None:
        """One encoder message (D-09-OSC-ENCODER). Auto picks the format from
        what the input has sent: a negative or a value other than 0/1 means
        signed (from then on), else direction. The axis moves by step per
        tick, clamped; a pulse output presses and releases once per tick its
        way, after the input's delay."""
        number = _number(value)
        if number is None:
            return
        fmt = row.enc_format
        if fmt == "auto":
            fmt = self._enc_format.get(key, "direction")
            if number not in (0.0, 1.0):
                fmt = "signed"
            self._enc_format[key] = fmt
        turn = encoder_turn(fmt, number)
        if turn == 0.0:
            return
        turn *= self._accel(row, abs(turn))
        if row.enc_output == "axis":
            current = self._enc_value.get(key, 0.0) + row.enc_step * turn
            current = max(-1.0, min(1.0, current))
            self._enc_value[key] = current
            self._emit_axis(row, shape_axis(row, current), mode, address)
            return
        if (turn > 0) != (row.enc_output == "pulse_cw"):
            return
        ticks = min(MAX_ENC_TICKS, max(1, round(abs(turn))))
        if key in self._timers:
            # A pulse is under way: these follow it.
            pending = self._enc_pending.get(key, 0) + ticks
            self._enc_pending[key] = min(MAX_ENC_TICKS, pending)
            return
        self._enc_pending[key] = ticks - 1
        self._pulse(row, key, address, mode)

    def _accel(self, row: OscRow, ticks: float) -> float:
        """The encoder's acceleration multiplier for a turn of ticks (S164):
        1 + factor * max(0, ticks in the last ENC_ACCEL_WINDOW_S - 1), at most
        ENC_ACCEL_MAX; 1 with acceleration off. Timed per input."""
        factor = ENC_ACCEL_FACTORS.get(row.enc_accel, 0.0)
        if factor <= 0.0:
            return 1.0
        now = clock.monotonic()
        recent = self._enc_ticks.setdefault(row.uid, collections.deque())
        while recent and now - recent[0][0] > ENC_ACCEL_WINDOW_S:
            recent.popleft()
        recent.append((now, ticks))
        in_window = sum(t for _, t in recent)
        return min(ENC_ACCEL_MAX, 1.0 + factor * max(0.0, in_window - 1.0))

    def _apply(
        self, row: OscRow, args: tuple[Any, ...], mode: str, address: str
    ) -> None:
        """One message (received at address) on one input. A pattern input
        keeps button, Change and encoder state per address; an axis takes
        the last value whichever address sent it (S147)."""
        key = state_key(row, address)
        value = _value_at(args, row.source)
        if row.mode == "encoder":
            self._encoder(row, key, address, value, mode)
            return
        if row.input_type == InputType.JoystickAxis:
            number = _number(value)
            if number is not None:
                scaled = scale_axis(number, row.range_min, row.range_max)
                self._emit_axis(row, shape_axis(row, scaled), mode, address)
            return
        if row.cmd_mode == "data" or row.trigger is True:
            self._pulse(row, key, address, mode)
            return
        if row.mode == "change":
            number = _number(value)
            current = number if number is not None else value
            last = self._last.get(key, _UNSET)
            self._last[key] = current
            if last is _UNSET or last != current:
                self._pulse(row, key, address, mode)
            return
        if value is None:
            trigger = row.trigger
            if trigger is None:
                trigger = bool(self._settings.get("autorelease_no_arg", True))
            if trigger:
                self._pulse(row, key, address, mode)
            else:
                self._cancel_release(key)
                self._button(row, key, address, True, mode)
            return
        self._cancel_release(key)
        self._button(row, key, address, is_pressed((value,)), mode)

    def _on_main(
        self,
        address: str,
        args: object,
        peer: tuple[str, int] | None = None,
    ) -> None:
        payload = tuple(args) if isinstance(args, (tuple, list)) else ()
        # The sender allow-list comes first (S160): a blocked message reaches
        # nothing (sync, Listen, inputs) and shows in the Monitor as blocked.
        if peer is not None and not sender_allowed(
            peer[0], self._settings.get("allow_senders") or ()
        ):
            _call_hook("osc_traffic", "note", "in", address, payload, peer, [BLOCKED])
            return
        # Feedback's sync address is answered there and reaches no input.
        if _call_hook("osc_feedback", "handle_incoming", address, payload, peer):
            # The Monitor still shows it (all incoming messages, D-09-OSC-MONITOR).
            _call_hook("osc_traffic", "note", "in", address, payload, peer, ["Sync"])
            return
        if peer is not None:
            _call_hook("osc_output", "note_sender", peer[0], peer[1])
        _call_hook("osc_output", "note_received_type", address, payload)
        matched = self._handle(address, payload)
        _call_hook(
            "osc_traffic",
            "note",
            "in",
            address,
            payload,
            peer,
            [match_name(row) for row in matched],
        )

    def _handle(self, address: str, payload: tuple[Any, ...]) -> list[OscRow]:
        """Listen, then the inputs while a profile runs; returns the inputs
        matched (also with no Run, for the Monitor)."""
        from gremlin.mode_manager import ModeManager

        if self._learn:
            owner = self._learn_owner
            if not self._hold_learn:
                self._learn = False
                self.listenChanged.emit()
            log.info("OSC listen captured %s %s", address, payload)
            self.learned.emit(address, payload)
            # A single Listen is over (unless a handler started a new one).
            if not self._learn and self._learn_owner is owner:
                self._learn_owner = None
            # A single Listen ends on its message; with no profile running
            # the port closes.
            self._close_if_idle()
        rows = OscDevice().rows.matches(address, payload)
        for row in rows:
            self._last_address[row.uid] = address
            self._note_live(row, payload, synthetic=False)
        if not self._running and not self._recorders:
            return rows
        if not rows:
            log.debug("OSC ignored unmatched address %s %s", address, payload)
            return rows
        if not payload and self._settings.get("pad_args"):
            payload = (1.0,)
        mode = ModeManager().current.name
        for row in rows:
            log.debug(
                "OSC %s %s -> %s %s",
                address,
                payload,
                row.input_type.name,
                row.input_id,
            )
            self._apply(row, payload, mode, address)
        return rows

    # -- live value and last seen (OX1) ---------------------------------------

    def live(self, uid: str) -> dict[str, Any] | None:
        """The input's last value, or None before any: "value" (at its
        source; None for no value), "axis" (-1..1 for an axis input, else
        None), "pressed" (for a button input, else None), "last_seen"
        (clock.now() when it came) and "synthetic" (True from send_test).
        Recorded for every matching message, with or without a Run."""
        entry = self._live.get(str(uid))
        return None if entry is None else dict(entry)

    def live_all(self) -> dict[str, dict[str, Any]]:
        return {uid: dict(entry) for uid, entry in self._live.items()}

    def last_address(self, uid: str) -> str | None:
        """The address the input last received (a pattern input: which of
        its addresses), with or without a Run; None before any (OX7 Q5)."""
        return self._last_address.get(str(uid))

    def reset_live(self) -> None:
        self._last_address.clear()
        self._live.clear()
        self._live_sent.clear()
        self._live_pending.clear()
        self._live_timer.stop()

    def _note_live(
        self, row: OscRow, payload: tuple[Any, ...], synthetic: bool
    ) -> None:
        value = _value_at(payload, row.source)
        axis = None
        pressed = None
        if row.input_type == InputType.JoystickAxis:
            number = _number(value)
            if number is not None and row.mode != "encoder":
                axis = scale_axis(number, row.range_min, row.range_max)
        else:
            pressed = True if value is None else is_pressed((value,))
        self._live[row.uid] = {
            "value": value,
            "axis": axis,
            "pressed": pressed,
            "last_seen": clock.now(),
            "synthetic": synthetic,
        }
        self._live_changed(row.uid)

    def _live_changed(self, uid: str) -> None:
        now = clock.monotonic()
        last = self._live_sent.get(uid)
        if last is None or now - last >= LIVE_INTERVAL_S:
            self._live_sent[uid] = now
            self._live_pending.discard(uid)
            self.liveChanged.emit(uid)
            return
        self._live_pending.add(uid)
        if not self._live_timer.isActive():
            wait = LIVE_INTERVAL_S - (now - last)
            self._live_timer.start(max(1, math.ceil(wait * 1000)))

    def _flush_live(self) -> None:
        """The throttle's wait is over: each waiting input whose interval
        has passed gets its signal; the rest wait again."""
        now = clock.monotonic()
        wait = LIVE_INTERVAL_S
        for uid in list(self._live_pending):
            gone = now - self._live_sent.get(uid, 0.0)
            if gone >= LIVE_INTERVAL_S:
                self._live_pending.discard(uid)
                self._live_sent[uid] = now
                self.liveChanged.emit(uid)
            else:
                wait = min(wait, LIVE_INTERVAL_S - gone)
        if self._live_pending:
            self._live_timer.start(max(1, math.ceil(wait * 1000)))

    # -- macro playback (S159) -------------------------------------------------

    def play(self, uid: str, kind: str, value: object) -> None:
        """A macro step plays the input (S159): kind "button" (value pressed)
        or "axis" (value -1..1, already shaped, as recorded). The event goes
        out marked synthetic (02 S44) the same way as a message's, without
        shaping it again and without recording it; only while a profile
        runs. Safe from any thread: it is carried to the runtime's thread."""
        self._playRequested.emit(str(uid), str(kind), value)

    def _play_main(self, uid: str, kind: str, value: object) -> None:
        from gremlin.mode_manager import ModeManager

        if not self._running:
            return
        row = OscDevice().rows.by_uid(uid)
        if row is None:
            return
        mode = ModeManager().current.name
        address = self._last_address.get(row.uid) or row.label
        if kind == "axis" and row.input_type == InputType.JoystickAxis:
            number = _number(value)
            if number is None:
                return
            axis = max(-1.0, min(1.0, number))
            self._note_played(row.uid, axis=axis, pressed=None)
            self._send_axis(row, axis, mode, address, synthetic=True)
        elif kind == "button" and row.input_type == InputType.JoystickButton:
            pressed = bool(value)
            self._note_played(row.uid, axis=None, pressed=pressed)
            self._send_button(row, pressed, mode, address, synthetic=True)

    def _note_played(self, uid: str, axis: float | None, pressed: bool | None) -> None:
        """The live value of a played step (no message: no source value)."""
        self._live[uid] = {
            "value": None,
            "axis": axis,
            "pressed": pressed,
            "last_seen": clock.now(),
            "synthetic": True,
        }
        self._live_changed(uid)

    # -- test inject (OX5) ----------------------------------------------------

    def send_test(self, uid: str, kind: str, value: object = None) -> bool:
        """As if the input received a message (Send Test Press / Send Test
        Value): kind "press", "release" or "value" (with value). The live
        value updates, marked synthetic, with or without a Run; the input
        fires its actions, through the same _apply as a message, only while
        a profile runs. True when it reached the running input."""
        from gremlin.mode_manager import ModeManager

        row = OscDevice().rows.by_uid(str(uid))
        if row is None or kind not in ("press", "release", "value"):
            return False
        if kind == "press":
            value = 1.0
        elif kind == "release":
            value = 0.0
        payload = tuple(value for _ in range(max(0, row.source) + 1))
        self._note_live(row, payload, synthetic=True)
        if not self._running:
            return False
        mode = ModeManager().current.name
        # A pattern input is tested at the address it last received.
        address = self._last_address.get(row.uid) or row.label
        key = state_key(row, address)
        if (
            kind == "release"
            and row.input_type == InputType.JoystickButton
            and (row.cmd_mode == "data" or row.trigger is True or row.mode != "button")
        ):
            # A pulsing input: a release only ends a held or pending press.
            self._cancel_release(key)
            if key in self._held:
                self._button(row, key, address, False, mode)
            return True
        self._apply(row, payload, mode, address)
        return True
