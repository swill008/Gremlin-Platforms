# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""OSC feedback (D-09-OSC-FEEDBACK): while a profile runs, OSC's feedback
rows send the state of the current mode, vJoy buttons and axes, Logical
Device controls and OSC inputs to their target.

Sources are read on the main thread on a short timer and a row sends when
its value changes, at most feedback_rate messages a second per address (the
latest value wins). A full resend goes out at Run start, on a mode change,
on a profile switch (each behind its own switch) and when a message arrives
on the sync address. Every send happens on the main thread, through
osc_output.send.
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from PySide6 import QtCore

from gremlin import clock

log = logging.getLogger("system")

# How often the sources are read while feedback runs.
POLL_MS = 10

_DEFAULTS: dict[str, Any] = {
    "feedback_enabled": True,
    "resend_run": True,
    "resend_mode": True,
    "resend_profile": True,
    "sync_enabled": True,
    "sync_address": "/gremlin/sync",
    "feedback_rate": 50,
}

_lock = threading.Lock()
# Server settings as last read; handle_incoming may run on the OSC thread.
_settings: dict[str, Any] | None = None


def _read_server() -> dict[str, Any]:
    settings = dict(_DEFAULTS)
    try:
        from gremlin import osc_device_file

        settings.update(osc_device_file.read_server() or {})
    except Exception:
        log.exception("OSC feedback: settings could not be read")
    return settings


def _read_rows() -> list[dict]:
    try:
        from gremlin import osc_device_file

        reader = getattr(osc_device_file, "read_feedback", None)
        return list(reader() or []) if reader is not None else []
    except Exception:
        log.exception("OSC feedback: rows could not be read")
        return []


def settings() -> dict[str, Any]:
    global _settings
    with _lock:
        if _settings is None:
            _settings = _read_server()
        return dict(_settings)


def _reload_settings() -> None:
    global _settings
    fresh = _read_server()
    with _lock:
        _settings = fresh


# -- values ------------------------------------------------------------------


def _scale(fraction: float, low: float, high: float) -> float:
    return low + fraction * (high - low)


def _convert(number: float, kind: str) -> Any:  # noqa: ANN401
    if kind == "int":
        return int(round(number))
    if kind == "bool":
        return bool(number)
    if kind == "text":
        return f"{number:g}"
    return float(number)


def _send_types(row: dict, value: Any) -> list[str] | None:  # noqa: ANN401
    kind = row.get("type", "auto")
    if kind == "auto":
        # Auto: osc_output picks the type last received on the address;
        # a mode name is always text.
        return ["text"] if isinstance(value, str) else None
    return [kind]


def _mode_name() -> str:
    from gremlin.mode_manager import ModeManager

    return str(ModeManager().current.name)


def _vjoy(kind: str, source: dict) -> Any:  # noqa: ANN401
    from gremlin.modules import output

    try:
        return output.vjoy_value(int(source["device"]), kind, int(source["input"]))
    except (TypeError, ValueError, KeyError):
        return None


def _logical(source: dict) -> Any:  # noqa: ANN401
    from gremlin.logical_device import LogicalDevice

    key = source.get("input")
    if key is None:
        return None
    device = LogicalDevice()
    item = device.by_uid(str(key))
    if item is None:
        try:
            item = device[str(key)]
        except Exception:
            return None
    for name in ("value", "is_pressed", "direction"):
        if hasattr(item, name):
            return getattr(item, name)
    return None


class OscFeedback(QtCore.QObject):
    """The running feedback; lives on the main thread."""

    # (peer host, peer port | -1): a sync message asked for a resend.
    _sync = QtCore.Signal(str, int)

    def __init__(self) -> None:
        super().__init__()
        self._running = False
        self._rows: list[dict] = []
        self._settings: dict[str, Any] = dict(_DEFAULTS)
        # row id -> (values, types) last sent.
        self._last: dict[str, tuple] = {}
        # address -> clock time of its last send.
        self._sent_at: dict[str, float] = {}
        # address -> (row, values, types) waiting for the rate limit.
        self._pending: dict[str, tuple[dict, list, list | None]] = {}
        # OSC inputs' state from their events: (type value, input id) -> value.
        self._osc_state: dict[tuple[int, int], Any] = {}
        self._profile_path: str | None = None
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(POLL_MS)
        self._timer.timeout.connect(self.poll)
        self._sync.connect(self._on_sync)
        self._connected = False

    # -- Run -----------------------------------------------------------------

    def start(self, profile_path: str | None = None) -> None:
        switched = (
            self._profile_path is not None
            and profile_path is not None
            and profile_path != self._profile_path
        )
        self._profile_path = profile_path
        self._running = True
        self._osc_state.clear()
        self._last.clear()
        self._sent_at.clear()
        self._pending.clear()
        self._connect(True)
        self.reload()
        s = self._settings
        if s.get("resend_run") or (switched and s.get("resend_profile")):
            self.resend_all("profile switch" if switched else "run start")
        else:
            # No resend: only later changes send.
            self._seed()

    def _seed(self) -> None:
        for row in self._active_rows():
            values = self.value_of(row)
            if values is not None:
                self._last[row["id"]] = (values, _send_types(row, values[0]))

    def stop(self) -> None:
        self._running = False
        self._timer.stop()
        self._connect(False)
        self._pending.clear()
        self._last.clear()

    def is_running(self) -> bool:
        return self._running

    def _connect(self, on: bool) -> None:
        if on == self._connected:
            return
        from gremlin.event_handler import EventListener
        from gremlin.mode_manager import ModeManager
        from gremlin.signal import signal as ui_signal

        pairs = [
            (ModeManager().mode_changed, self._on_mode_changed),
            (EventListener().joystick_event, self._on_input_event),
        ]
        for name, slot in (
            ("oscFeedbackChanged", self.reload),
            ("oscServerSettingsChanged", self.reload),
            ("oscDeviceReloaded", self.reload),
        ):
            sig = getattr(ui_signal, name, None)
            if sig is not None:
                pairs.append((sig, slot))
        for sig, slot in pairs:
            if on:
                sig.connect(slot)
            else:
                try:
                    sig.disconnect(slot)
                except (TypeError, RuntimeError):
                    pass
        self._connected = on

    def reload(self) -> None:
        """Rows or settings changed: read them again."""
        _reload_settings()
        self._settings = settings()
        self._rows = _read_rows()
        live = {row["id"] for row in self._rows}
        self._last = {k: v for k, v in self._last.items() if k in live}
        self._pending.clear()
        if self._running and self._active_rows():
            self._timer.start()
        else:
            self._timer.stop()

    def _active_rows(self) -> list[dict]:
        if not self._settings.get("feedback_enabled", True):
            return []
        return [r for r in self._rows if r.get("enabled", True) and r.get("address")]

    # -- sources -------------------------------------------------------------

    def _on_input_event(self, event: Any) -> None:  # noqa: ANN401
        from gremlin.osc import OSC_DEVICE_UUID
        from gremlin.types import InputType

        if getattr(event, "device_guid", None) != OSC_DEVICE_UUID:
            return
        if event.event_type == InputType.JoystickAxis:
            value: Any = float(event.value)
        else:
            value = bool(event.is_pressed)
        self._osc_state[(int(event.event_type.value), int(event.identifier))] = value

    def _osc_input(self, source: dict) -> Any:  # noqa: ANN401
        from gremlin.osc import OscDevice
        from gremlin.types import InputType

        key = source.get("input")
        if key is None:
            return None
        rows = OscDevice().rows
        row = rows.by_uid(str(key))
        if row is None:
            found = rows.matches(str(key))
            row = found[0] if found else None
        if row is None:
            return None
        value = self._osc_state.get((int(row.input_type.value), int(row.input_id)))
        if value is None:
            return 0.0 if row.input_type == InputType.JoystickAxis else False
        return value

    def value_of(self, row: dict) -> list | None:
        """The values row sends now; None when its source has none."""
        source = row.get("source") or {}
        kind = source.get("kind")
        low = float(row.get("min", 0.0))
        high = float(row.get("max", 1.0))
        vtype = row.get("type", "auto")
        if kind == "mode":
            name = _mode_name()
            return [name]
        if kind == "vjoy_button":
            raw = _vjoy("button", source)
        elif kind == "vjoy_axis":
            raw = _vjoy("axis", source)
        elif kind == "logical":
            raw = _logical(source)
        elif kind == "osc_input":
            raw = self._osc_input(source)
        else:
            return None
        if raw is None:
            return None
        if isinstance(raw, bool):
            number = high if raw else low
        elif isinstance(raw, (int, float)):
            # Axes are -1..1.
            number = _scale((max(-1.0, min(1.0, float(raw))) + 1.0) / 2.0, low, high)
        else:
            # A hat direction: its name.
            return [str(getattr(raw, "name", raw))]
        return [_convert(number, vtype)]

    # -- sending -------------------------------------------------------------

    def _min_gap(self) -> float:
        try:
            rate = float(self._settings.get("feedback_rate") or 0)
        except (TypeError, ValueError):
            rate = 0.0
        return 1.0 / rate if rate > 0 else 0.0

    def _send(self, row: dict, values: list, types: list | None) -> None:
        try:
            from gremlin import osc_output
        except ImportError:
            return
        address = row["address"]
        self._sent_at[address] = clock.monotonic()
        self._pending.pop(address, None)
        try:
            sent = osc_output.send(row.get("target") or "reply", address, values, types)
        except Exception:
            log.exception("OSC feedback: sending %s failed", address)
            sent = False
        if sent is False:
            # Refused (output off, no reply address yet): forget it, so the
            # value goes out once sending works again (no stale controller).
            self._last.pop(row["id"], None)

    def poll(self) -> None:
        """Reads every source; changed values send, within the rate limit."""
        if not self._running:
            return
        for row in self._active_rows():
            values = self.value_of(row)
            if values is None:
                continue
            types = _send_types(row, values[0])
            if self._last.get(row["id"]) == (values, types):
                continue
            self._last[row["id"]] = (values, types)
            self._pending[row["address"]] = (row, values, types)
        self._flush()

    def _flush(self) -> None:
        if not self._pending:
            return
        now = clock.monotonic()
        gap = self._min_gap()
        for address, (row, values, types) in list(self._pending.items()):
            last = self._sent_at.get(address)
            if last is None or now - last >= gap:
                self._send(row, values, types)

    def resend_all(self, reason: str = "") -> int:
        """Sends every row's current value now. The number sent."""
        if not self._running:
            return 0
        count = 0
        for row in self._active_rows():
            values = self.value_of(row)
            if values is None:
                continue
            types = _send_types(row, values[0])
            self._last[row["id"]] = (values, types)
            self._send(row, values, types)
            count += 1
        if count:
            log.debug("OSC feedback: resent %s rows (%s)", count, reason)
        return count

    def _on_mode_changed(self, _name: str) -> None:
        if self._running and self._settings.get("resend_mode", True):
            self.resend_all("mode change")

    def _on_sync(self, host: str, port: int) -> None:
        if host and port >= 0:
            try:
                from gremlin import osc_output

                osc_output.note_sender(host, port)
            except Exception:
                pass
        self.resend_all("sync")

    def request_sync(self, peer: tuple | None) -> None:
        """Any thread: a resend on the main thread (to peer for reply rows)."""
        host, port = "", -1
        if peer:
            try:
                host, port = str(peer[0]), int(peer[1])
            except (TypeError, ValueError, IndexError):
                host, port = "", -1
        self._sync.emit(host, port)


_feedback: OscFeedback | None = None


def instance() -> OscFeedback:
    """The feedback runtime; made on the main thread (by start())."""
    global _feedback
    if _feedback is None:
        _feedback = OscFeedback()
    return _feedback


def start(profile_path: str | None = None) -> None:
    """A Run starts (CodeRunner): feedback runs until stop()."""
    instance().start(profile_path)


def stop() -> None:
    if _feedback is not None:
        _feedback.stop()


def resend_all(reason: str = "") -> int:
    return instance().resend_all(reason) if _feedback is not None else 0


def handle_incoming(address: str, args: Any, peer: tuple | None) -> bool:  # noqa: ANN401
    """Any thread (OscRuntime, first for every message). True when address
    is the sync address: the message is consumed (never reaches inputs) and
    every row is sent again while a profile runs."""
    running = _feedback is not None and _feedback.is_running()
    # Cached while a Run keeps it current; read fresh otherwise.
    s = settings() if running else _read_server()
    if not s.get("sync_enabled", True):
        return False
    sync = str(s.get("sync_address") or "").strip()
    if not sync or str(address) != sync:
        return False
    if running and _feedback is not None:
        _feedback.request_sync(peer)
    return True
