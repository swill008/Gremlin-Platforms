# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-only
"""OSC virtual device, UDP listener, and event inject for Path B."""

from __future__ import annotations

import logging
import math
import socket
import threading
from collections.abc import Callable
from typing import Any

from PySide6 import QtCore

from gremlin import threads
from gremlin.common import SingletonDecorator, SingletonMetaclass
from gremlin.error import GremlinError
from gremlin.modules import ids
from gremlin.osc_rows import OscRow, OscRows
from gremlin.types import InputType

log = logging.getLogger("system")

OSC_DEVICE_UUID = ids.OSC

OSC_SECTION = "osc"
OSC_GROUP = "connection"

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8001
DEFAULT_OUTPUT_PORT = 8000
DEFAULT_AUTORELEASE_MS = 250

MessageCallback = Callable[[str, tuple[Any, ...]], None]


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
        from pythonosc.dispatcher import Dispatcher
        from pythonosc.osc_server import ThreadingOSCUDPServer

        dispatcher = Dispatcher()
        dispatcher.set_default_handler(self._on_message)
        self._server = ThreadingOSCUDPServer((self.host, self.port), dispatcher)
        # Stopping waits for the server's next poll (0.5 s at most).
        self._thread = threads.start(
            "OSC listener", self._server.serve_forever, stop=self._server.shutdown
        )
        log.info("OSC listening on %s:%s", self.host, self.port)

    def stop(self) -> None:
        if self._server is None:
            return
        self._server.shutdown()
        self._server.server_close()
        self._server = None
        self._thread = None
        log.info("OSC listener stopped")

    def _on_message(self, address: str, *args: Any) -> None:
        address = (address or "").casefold()
        if address == "/noop":
            return
        if self.callback is not None:
            self.callback(address, args)


SERVER_DEFAULTS: dict[str, Any] = {
    "enabled": True,
    "host": "",
    "port": DEFAULT_PORT,
    "output_host": DEFAULT_HOST,
    "output_port": DEFAULT_OUTPUT_PORT,
    "autorelease_no_arg": True,
    "autorelease_delay_ms": DEFAULT_AUTORELEASE_MS,
    "pad_args": False,
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
    incoming = QtCore.Signal(str, object)
    learned = QtCore.Signal(str, object)
    listenChanged = QtCore.Signal()

    def __init__(self) -> None:
        super().__init__()
        self._listener: OscListener | None = None
        # A profile runs (start() until stop()); the port opens for it only
        # when it uses OSC inputs (09 Q5). A Listen keeps the port open only
        # while it lasts.
        self._running = False
        self._uses_osc = False
        self._learn = False
        self._hold_learn = False
        self._settings: dict[str, Any] = dict(SERVER_DEFAULTS)
        self._timers: dict[str, QtCore.QTimer] = {}
        self._last: dict[str, Any] = {}
        self.incoming.connect(self._on_main)
        from gremlin.signal import signal as ui_signal

        changed = getattr(ui_signal, "oscServerSettingsChanged", None)
        if changed is not None:
            changed.connect(self.sync_bind)

    def is_listening(self) -> bool:
        return self._learn

    def listen_once(self, hold: bool = False) -> bool:
        from gremlin.signal import signal as ui_signal

        self._hold_learn = hold
        self._bind()
        if self._listener is None:
            self._learn = False
            self._hold_learn = False
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

    def listen_bulk(self) -> bool:
        return self.listen_once(hold=True)

    def cancel_listen(self) -> None:
        self._hold_learn = False
        was = self._learn
        self._learn = False
        self._close_if_idle()
        if was:
            self.listenChanged.emit()
            log.info("OSC listen-once cancelled")

    def _needs_port(self) -> bool:
        return self._learn or (self._running and self._uses_osc)

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
            ui_signal.showError.emit(
                "OSC requires python-osc.",
                "In the repo folder run: poetry add python-osc",
            )
        except OSError as exc:
            ui_signal.showError.emit(f"Could not bind OSC on {host}:{port}.", str(exc))

    def _unbind(self) -> None:
        if self._listener is None:
            return
        self._listener.stop()
        self._listener = None

    def start(self) -> None:
        """A profile starts running: listen until stop() when it uses OSC
        inputs (09 Q5)."""
        self._running = True
        self._uses_osc = profile_uses_osc()
        if self._needs_port():
            self._bind()
        else:
            self._settings = server_settings()
            log.info("OSC port not opened: the profile has no OSC inputs")

    def stop(self) -> None:
        """The profile stopped: pending auto-releases cancelled, port closed."""
        self._running = False
        self._uses_osc = False
        for uid in list(self._timers):
            self._cancel_release(uid)
        self._last.clear()
        self._hold_learn = False
        self._learn = False
        self.listenChanged.emit()
        self._unbind()

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

    def _from_thread(self, address: str, args: tuple[Any, ...]) -> None:
        self.incoming.emit(address, args)

    # -- inputs (D-09-OSC-INPUT) ----------------------------------------------

    def _emit_button(self, row: OscRow, pressed: bool, mode: str) -> None:
        from gremlin.event_handler import Event, EventListener

        EventListener().joystick_event.emit(
            Event(
                event_type=InputType.JoystickButton,
                identifier=row.input_id,
                device_guid=OSC_DEVICE_UUID,
                mode=mode,
                is_pressed=pressed,
            )
        )

    def _emit_axis(self, row: OscRow, value: float, mode: str) -> None:
        from gremlin.event_handler import Event, EventListener

        EventListener().joystick_event.emit(
            Event(
                event_type=InputType.JoystickAxis,
                identifier=row.input_id,
                device_guid=OSC_DEVICE_UUID,
                mode=mode,
                value=value,
                raw_value=value,
            )
        )

    def _delay_of(self, row: OscRow) -> int:
        if row.delay_ms is not None:
            return parse_delay_ms(row.delay_ms)
        return parse_delay_ms(self._settings.get("autorelease_delay_ms"))

    def _cancel_release(self, uid: str) -> None:
        timer = self._timers.pop(uid, None)
        if timer is not None:
            timer.stop()
            timer.deleteLater()

    def _pulse(self, row: OscRow, mode: str) -> None:
        """Press, then release after the input's delay; a new press restarts
        the wait."""
        self._emit_button(row, True, mode)
        self._cancel_release(row.uid)
        timer = QtCore.QTimer(self)
        timer.setSingleShot(True)
        timer.setInterval(self._delay_of(row))
        uid = row.uid
        timer.timeout.connect(lambda: self._release(uid, mode))
        self._timers[uid] = timer
        timer.start()

    def _release(self, uid: str, mode: str) -> None:
        self._cancel_release(uid)
        row = OscDevice().rows.by_uid(uid)
        if row is not None:
            self._emit_button(row, False, mode)

    def _apply(self, row: OscRow, args: tuple[Any, ...], mode: str) -> None:
        value = _value_at(args, row.source)
        if row.input_type == InputType.JoystickAxis:
            number = _number(value)
            if number is not None:
                scaled = scale_axis(number, row.range_min, row.range_max)
                self._emit_axis(row, scaled, mode)
            return
        if row.cmd_mode == "data" or row.trigger is True:
            self._pulse(row, mode)
            return
        if row.mode == "change":
            number = _number(value)
            current = number if number is not None else value
            last = self._last.get(row.uid, _UNSET)
            self._last[row.uid] = current
            if last is _UNSET or last != current:
                self._pulse(row, mode)
            return
        if value is None:
            trigger = row.trigger
            if trigger is None:
                trigger = bool(self._settings.get("autorelease_no_arg", True))
            if trigger:
                self._pulse(row, mode)
            else:
                self._cancel_release(row.uid)
                self._emit_button(row, True, mode)
            return
        self._cancel_release(row.uid)
        self._emit_button(row, is_pressed((value,)), mode)

    def _on_main(self, address: str, args: object) -> None:
        from gremlin.mode_manager import ModeManager

        payload = tuple(args) if isinstance(args, (tuple, list)) else ()
        if self._learn:
            if not self._hold_learn:
                self._learn = False
                self.listenChanged.emit()
            log.info("OSC listen captured %s %s", address, payload)
            self.learned.emit(address, payload)
            # A single Listen ends on its message; with no profile running
            # the port closes.
            self._close_if_idle()
        if not self._running:
            return
        rows = OscDevice().rows.matches(address, payload)
        if not rows:
            log.debug("OSC ignored unmatched address %s %s", address, payload)
            return
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
            self._apply(row, payload, mode)
