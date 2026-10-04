# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-only
"""OSC virtual device, UDP listener, and event inject for Path B."""

from __future__ import annotations

import logging
import socket
import threading
from collections.abc import Callable
from typing import Any

from PySide6 import QtCore

from gremlin import threads
from gremlin.common import SingletonDecorator, SingletonMetaclass
from gremlin.error import GremlinError
from gremlin.modules import ids
from gremlin.types import InputType

log = logging.getLogger("system")

OSC_DEVICE_UUID = ids.OSC

OSC_SECTION = "osc"
OSC_GROUP = "connection"

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
DEFAULT_OUTPUT_PORT = 8000
DEFAULT_AUTORELEASE_MS = 250

BIND_OPTION_NAMES = ("enabled", "host", "port")

MessageCallback = Callable[[str, tuple[Any, ...]], None]

_config_hooked = False


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


def axis_value(args: tuple[Any, ...]) -> float:
    if not args:
        return 0.0
    try:
        value = float(args[0])
    except (TypeError, ValueError):
        return 0.0
    return max(-1.0, min(1.0, value))


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
    device_guid = OSC_DEVICE_UUID

    class Input:
        def __init__(self, label: str, input_id: int, input_type: InputType) -> None:
            self.label = label
            self.id = input_id
            self.type = input_type
            self.value: float | bool = (
                0.0 if input_type == InputType.JoystickAxis else False
            )

    def __init__(self) -> None:
        self._inputs: dict[str, OscDevice.Input] = {}
        self._by_id: dict[tuple[InputType, int], str] = {}

    def reset(self) -> None:
        self._inputs = {}
        self._by_id = {}

    def create(
        self,
        input_type: InputType,
        label: str | None = None,
        input_id: int | None = None,
    ) -> OscDevice.Input:
        if input_type not in (InputType.JoystickAxis, InputType.JoystickButton):
            raise GremlinError(f"OSC inputs must be axis or button, got {input_type}")
        if input_id is None:
            used = {item.id for item in self._inputs.values() if item.type == input_type}
            input_id = 1
            while input_id in used:
                input_id += 1
        if label is None:
            prefix = "/osc/axis" if input_type == InputType.JoystickAxis else "/osc/button"
            label = f"{prefix}/{input_id}"
        label = str(label).casefold()
        if label in self._inputs:
            raise GremlinError(f"OSC address '{label}' already exists")
        item = OscDevice.Input(label, int(input_id), input_type)
        self._inputs[label] = item
        self._by_id[(input_type, int(input_id))] = label
        return item

    def set_label(self, old_label: str, new_label: str) -> None:
        old_label = old_label.casefold()
        new_label = new_label.casefold()
        if old_label == new_label:
            return
        if old_label not in self._inputs:
            raise GremlinError(f"No OSC input '{old_label}'")
        if new_label in self._inputs:
            raise GremlinError(f"OSC address '{new_label}' already exists")
        item = self._inputs.pop(old_label)
        item.label = new_label
        self._inputs[new_label] = item
        self._by_id[(item.type, item.id)] = new_label

    def delete(self, label: str) -> None:
        label = label.casefold()
        item = self._inputs.pop(label)
        del self._by_id[(item.type, item.id)]

    def labels_of_type(self, type_list: list[InputType] | None = None) -> list[str]:
        if not type_list:
            type_list = [InputType.JoystickAxis, InputType.JoystickButton]
        return [
            item.label
            for item in sorted(self._inputs.values(), key=lambda x: (x.type.name, x.id))
            if item.type in type_list
        ]

    def find_address(self, address: str) -> OscDevice.Input | None:
        return self._inputs.get((address or "").casefold())

    def find_by_id(
        self, input_type: InputType, input_id: int
    ) -> OscDevice.Input | None:
        label = self._by_id.get((input_type, int(input_id)))
        if label is None:
            return None
        return self._inputs.get(label)

    def __getitem__(self, label: str) -> OscDevice.Input:
        label = label.casefold()
        if label not in self._inputs:
            raise GremlinError(f"No OSC input '{label}'")
        return self._inputs[label]


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


def _install_config_hook() -> None:
    """Rebind the listener when host/port/enabled are saved from Options."""
    global _config_hooked
    if _config_hooked:
        return
    from gremlin.config import Configuration

    original = Configuration.set

    def hooked(
        self: Any, section: str, group: str, name: str, value: Any
    ) -> None:
        original(self, section, group, name, value)
        if (
            section == OSC_SECTION
            and group == OSC_GROUP
            and name in BIND_OPTION_NAMES
        ):
            OscRuntime().sync_bind()

    Configuration.set = hooked
    _config_hooked = True


@SingletonDecorator
class OscRuntime(QtCore.QObject):
    incoming = QtCore.Signal(str, object)
    learned = QtCore.Signal(str, object)
    listenChanged = QtCore.Signal()

    def __init__(self) -> None:
        super().__init__()
        self._listener: OscListener | None = None
        self._learn = False
        self._hold_learn = False
        self._pad_args = False
        self._autorelease = True
        self._autorelease_ms = DEFAULT_AUTORELEASE_MS
        self._output_host = DEFAULT_HOST
        self._output_port = DEFAULT_OUTPUT_PORT
        self.incoming.connect(self._on_main)
        _install_config_hook()

    def is_listening(self) -> bool:
        return self._learn

    def listen_once(self, hold: bool = False) -> bool:
        from gremlin.signal import signal as ui_signal

        self._hold_learn = hold
        self.start()
        if self._listener is None:
            self._learn = False
            self._hold_learn = False
            self.listenChanged.emit()
            ui_signal.showError.emit(
                "Could not start OSC listener.",
                "Enable OSC in Options and check host/port.",
            )
            return False
        self._learn = True
        self.listenChanged.emit()
        log.info(
            "OSC listen-once waiting for next packet hold=%s",
            hold,
        )
        return True

    def listen_bulk(self) -> bool:
        return self.listen_once(hold=True)

    def cancel_listen(self) -> None:
        self._hold_learn = False
        if not self._learn:
            return
        self._learn = False
        self.listenChanged.emit()
        log.info("OSC listen-once cancelled")

    def _refresh_behavior(self) -> None:
        from gremlin.config import Configuration

        cfg = Configuration()
        raw = osc_option(cfg, "pad-args")
        if raw is not None:
            self._pad_args = bool(raw)
        raw = osc_option(cfg, "autorelease-no-arg")
        if raw is not None:
            self._autorelease = bool(raw)
        raw = osc_option(cfg, "autorelease-delay")
        if raw is not None:
            self._autorelease_ms = parse_delay_ms(raw)

    def _read_options(self) -> tuple[bool, str, int]:
        from gremlin.config import Configuration

        cfg = Configuration()
        enabled = True
        host = default_bind_host()
        port = DEFAULT_PORT
        raw = osc_option(cfg, "enabled")
        if raw is not None:
            enabled = bool(raw)
        raw = osc_option(cfg, "host")
        if raw is not None:
            host = str(raw or host).strip()
        raw = osc_option(cfg, "port")
        if raw is not None:
            port = parse_port(raw)
        raw = osc_option(cfg, "output-host")
        if raw is not None:
            self._output_host = str(raw or DEFAULT_HOST).strip()
        raw = osc_option(cfg, "output-port")
        if raw is not None:
            self._output_port = parse_port(raw, DEFAULT_OUTPUT_PORT)
        self._refresh_behavior()
        return enabled, host, port

    def start(self) -> None:
        keep_learn = self._learn
        keep_hold = self._hold_learn
        self.stop()
        self._hold_learn = keep_hold
        from gremlin.signal import signal as ui_signal

        enabled, host, port = self._read_options()
        if not enabled:
            log.info("OSC listener disabled in options")
            return
        try:
            self._listener = OscListener(host, port, self._from_thread)
            self._listener.start()
            if keep_learn:
                self._learn = True
                self.listenChanged.emit()
            log.info(
                "OSC output target %s:%s pad=%s autorelease=%s delay=%sms",
                self._output_host,
                self._output_port,
                self._pad_args,
                self._autorelease,
                self._autorelease_ms,
            )
        except ImportError:
            ui_signal.showError.emit(
                "OSC requires python-osc.",
                "In the repo folder run: poetry add python-osc",
            )
            self._listener = None
        except OSError as exc:
            ui_signal.showError.emit(
                f"Could not bind OSC on {host}:{port}.",
                str(exc),
            )
            self._listener = None

    def stop(self) -> None:
        self._hold_learn = False
        self._learn = False
        self.listenChanged.emit()
        if self._listener is None:
            return
        self._listener.stop()
        self._listener = None

    def sync_bind(self) -> None:
        """Restart the UDP bind if host/port/enabled changed while running."""
        if self._listener is None and not self._learn:
            return
        enabled, host, port = self._read_options()
        if not enabled:
            log.info("OSC disabled; stopping listener")
            self.stop()
            return
        if (
            self._listener is not None
            and self._listener.host == host
            and self._listener.port == port
        ):
            return
        log.info("OSC bind changed to %s:%s; rebinding", host, port)
        self.start()

    def _from_thread(self, address: str, args: tuple[Any, ...]) -> None:
        self.incoming.emit(address, args)

    def _emit_button(self, item: OscDevice.Input, pressed: bool, mode: str) -> None:
        from gremlin.event_handler import Event, EventListener

        item.value = pressed
        EventListener().joystick_event.emit(
            Event(
                event_type=InputType.JoystickButton,
                identifier=item.id,
                device_guid=OSC_DEVICE_UUID,
                mode=mode,
                is_pressed=pressed,
            )
        )

    def _release_button(self, input_id: int, mode: str) -> None:
        item = OscDevice().find_by_id(InputType.JoystickButton, input_id)
        if item is None:
            return
        self._emit_button(item, False, mode)

    def _on_main(self, address: str, args: object) -> None:
        from gremlin.mode_manager import ModeManager

        self._refresh_behavior()
        payload = args if isinstance(args, tuple) else ()
        had_args = len(payload) > 0
        if self._learn:
            if not self._hold_learn:
                self._learn = False
                self.listenChanged.emit()
            log.info("OSC listen captured %s %s", address, payload)
            self.learned.emit(address, payload)

        item = OscDevice().find_address(address)
        if item is None:
            log.debug("OSC ignored unmatched address %s %s", address, args)
            return
        if not had_args and self._pad_args:
            payload = (1.0,)
        log.debug("OSC %s %s -> %s %s", address, args, item.type.name, item.id)
        mode = ModeManager().current.name
        if item.type == InputType.JoystickButton:
            pressed = is_pressed(payload)
            self._emit_button(item, pressed, mode)
            if pressed and not had_args and self._autorelease:
                QtCore.QTimer.singleShot(
                    self._autorelease_ms,
                    lambda iid=item.id, current=mode: self._release_button(
                        iid, current
                    ),
                )
        elif item.type == InputType.JoystickAxis:
            from gremlin.event_handler import Event, EventListener

            value = axis_value(payload)
            item.value = value
            EventListener().joystick_event.emit(
                Event(
                    event_type=InputType.JoystickAxis,
                    identifier=item.id,
                    device_guid=OSC_DEVICE_UUID,
                    mode=mode,
                    value=value,
                    raw_value=value,
                )
            )
