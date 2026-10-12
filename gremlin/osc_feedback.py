# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""OSC feedback (D-09-OSC-FEEDBACK): while a profile runs, OSC's feedback
rows send the state of the current mode, vJoy buttons and axes, Logical
Device controls, OSC inputs, actions (action_state) and Running / Paused
to their target.

Sources are read on the main thread on a short timer and a row sends when
its value changes, at most feedback_rate messages a second per address (the
latest value wins). A full resend goes out at Run start, on a mode change,
on a profile switch (each behind its own switch) and when a message arrives
on the sync address. Every send happens on the main thread, through
osc_output.send.

The server settings are held in memory and read again only when OSC's file
changes (E2: no file read per incoming message). Every step, skip and
refusal is a Feedback line in Trace (D-09-OSC-TRACE).
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from PySide6 import QtCore

from gremlin import clock, trace

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
# None: read again (OSC's file changed).
_settings: dict[str, Any] | None = None
_hooked = False


def _tr(text: str, **kw: Any) -> None:  # noqa: ANN401
    """A Feedback line in Trace (callers check trace.osc_on first when the
    text costs anything to build)."""
    trace.osc("feedback", text, **kw)


def _invalidate() -> None:
    global _settings
    with _lock:
        _settings = None


def _hook() -> None:
    """Once: the signals OSC's file writers give drop the held settings,
    Run or not (handle_incoming reads them for every message)."""
    global _hooked
    if _hooked:
        return
    _hooked = True
    try:
        from gremlin.signal import signal

        for name in ("oscServerSettingsChanged", "oscDeviceReloaded"):
            sig = getattr(signal, name, None)
            if sig is not None:
                sig.connect(_invalidate)
    except Exception:  # noqa: BLE001 - no signals (bare tests)
        log.debug("OSC feedback: settings signals not connected", exc_info=True)


def _read_server() -> dict[str, Any]:
    settings = dict(_DEFAULTS)
    try:
        from gremlin import osc_device_file

        settings.update(osc_device_file.read_server() or {})
    except Exception as error:  # noqa: BLE001 - defaults then; say it
        trace.log_limited(
            "system",
            "osc-feedback-settings",
            logging.ERROR,
            f"OSC feedback: settings could not be read: {error!r}",
        )
    return settings


def _read_rows() -> list[dict]:
    try:
        from gremlin import osc_device_file

        reader = getattr(osc_device_file, "read_feedback", None)
        return list(reader() or []) if reader is not None else []
    except Exception as error:  # noqa: BLE001 - no rows then; say it
        trace.log_limited(
            "system",
            "osc-feedback-rows",
            logging.ERROR,
            f"OSC feedback: rows could not be read: {error!r}",
        )
        return []


def settings() -> dict[str, Any]:
    """The server settings, read once and held until OSC's file changes."""
    global _settings
    _hook()
    with _lock:
        held = _settings
    if held is None:
        held = _read_server()
        with _lock:
            _settings = held
    return dict(held)


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


def _color_address(address: object) -> bool:
    """Companion's key colours: /location/<p>/<r>/<c>/style/bgcolor or
    .../style/color."""
    return str(address or "").rstrip("/").endswith(("/style/bgcolor", "/style/color"))


def _color(value: object) -> list[int] | None:
    """"#rrggbb" or "r g b" text as three ints 0-255; None when value isn't
    a colour."""
    text = str(value).strip()
    if text.startswith("#") and len(text) == 7:
        try:
            return [int(text[i : i + 2], 16) for i in (1, 3, 5)]
        except ValueError:
            return None
    parts = text.replace(",", " ").split()
    if len(parts) == 3:
        try:
            numbers = [int(part) for part in parts]
        except ValueError:
            return None
        if all(0 <= n <= 255 for n in numbers):
            return numbers
    return None


def _shape(row: dict, value: object) -> list:
    """The values an off/on value sends: a colour to a colour address goes
    as three ints r g b (Companion v3+ takes that); a number is converted
    like Min/Max; other text goes as it is."""
    if isinstance(value, str) and _color_address(row.get("address")):
        rgb = _color(value)
        if rgb is not None:
            if trace.osc_on("feedback"):
                _tr(
                    f"{row.get('address')}: colour {value} → "
                    f"{rgb[0]} {rgb[1]} {rgb[2]} (Companion)",
                    rate=True,
                    key=f"colour {row.get('address')}",
                )
            return rgb
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return [_convert(float(value), row.get("type", "auto"))]
    return [value]


def _send_types(row: dict, values: list) -> list[str] | None:
    if (
        len(values) == 3
        and all(isinstance(v, int) and not isinstance(v, bool) for v in values)
        and _color_address(row.get("address"))
    ):
        return ["int", "int", "int"]
    value = values[0] if values else None
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


def _action_state(source: dict) -> bool | None:
    """An action's on/off from the action state registry (S157); None when
    the action isn't in the running profile (S158: nothing is sent)."""
    action = source.get("action")
    if not action:
        return None
    from gremlin import action_state

    try:
        value = action_state.read(str(action))
    except Exception as error:  # noqa: BLE001 - nothing sent; say it
        trace.log_limited(
            "system",
            f"osc-feedback-action {action}",
            logging.ERROR,
            f"OSC feedback: action state of {action} could not be read: {error!r}",
        )
        return None
    return None if value is None else bool(value)


def _paused() -> bool | None:
    """The Running / Paused source: on while the profile runs, off while
    it is paused (RP1); None when no profile runs."""
    from gremlin import action_state

    paused = action_state.paused_state()
    return None if paused is None else not paused


def _osc_row(key: object) -> Any:  # noqa: ANN401
    """The OSC input a feedback source names (by id, else by address), or
    None when it's gone."""
    from gremlin.osc import OscDevice

    if key is None:
        return None
    rows = OscDevice().rows
    row = rows.by_uid(str(key))
    if row is None:
        found = rows.matches(str(key))
        row = found[0] if found else None
    return row


def source_text(source: dict) -> str:
    """A row's source in Trace words."""
    kind = source.get("kind")
    if kind == "mode":
        return "mode"
    if kind in ("vjoy_button", "vjoy_axis"):
        what = "button" if kind == "vjoy_button" else "axis"
        return f"vJoy {source.get('device')} {what} {source.get('input')}"
    if kind == "logical":
        return f"Logical Device {source.get('input')}"
    if kind == "osc_input":
        # Named like the match and event lines; the id only once it's gone.
        row = _osc_row(source.get("input"))
        if row is None:
            return f"OSC input {source.get('input')}"
        from gremlin.osc import input_name

        return input_name(row)
    if kind == "action_state":
        return f"action {source.get('action')}"
    if kind == "paused":
        return "Running / Paused"
    return f"unknown source {kind}"


def _values_text(values: list) -> str:
    return " ".join(repr(v) if isinstance(v, str) else str(v) for v in values)


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
        # row id -> its number on the Feedback tab (1 first), for Trace.
        self._numbers: dict[str, int] = {}
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
        if trace.osc_on("feedback"):
            on = self._settings.get("feedback_enabled", True)
            off = "" if on else "; Feedback is Off"
            _tr(f"start ({len(self._active_rows())} of {len(self._rows)} rows on{off})")
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
                self._last[row["id"]] = (values, _send_types(row, values))

    def stop(self) -> None:
        was = self._running
        self._running = False
        self._timer.stop()
        self._connect(False)
        self._pending.clear()
        self._last.clear()
        if was:
            _tr("stop")

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
        self._numbers = {row["id"]: i + 1 for i, row in enumerate(self._rows)}
        if self._running and trace.osc_on("feedback"):
            _tr(f"rows read ({len(self._rows)})")
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
        from gremlin.types import InputType

        row = _osc_row(source.get("input"))
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
        elif kind == "action_state":
            raw = _action_state(source)
        elif kind == "paused":
            raw = _paused()
        else:
            return None
        if raw is None:
            return None
        if isinstance(raw, bool):
            # Off/on values, when set, go instead of Min/Max.
            chosen = row.get("on_value" if raw else "off_value")
            if chosen is not None:
                return _shape(row, chosen)
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

    def _number(self, row: dict) -> int:
        return self._numbers.get(str(row.get("id")), 0)

    def _send(self, row: dict, values: list, types: list | None) -> None:
        try:
            from gremlin import osc_output
        except ImportError:
            return
        address = row["address"]
        target = row.get("target") or "reply"
        n = self._number(row)
        self._sent_at[address] = clock.monotonic()
        self._pending.pop(address, None)
        if trace.osc_on("feedback"):
            source = source_text(row.get("source") or {})
            _tr(
                f"row {n} {source} → {address} {_values_text(values)}",
                rate=True,
                key=f"row {n}",
            )
        try:
            sent = osc_output.send(
                target, address, values, types, source=f"feedback row {n}"
            )
        except Exception as error:  # noqa: BLE001 - one row never stops the rest
            text = f"OSC feedback: sending {address} failed: {error!r}"
            trace.log_limited(
                "system", f"osc-feedback-send {address}", logging.ERROR, text
            )
            if trace.osc_on("feedback"):
                _tr(
                    f"row {n}: sending failed ({type(error).__name__})",
                    warning=True,
                    key=f"row {n}",
                )
            sent = False
        if sent is False:
            # Refused (output off, no reply address yet): forget it, so the
            # value goes out once sending works again (no stale controller).
            self._last.pop(row["id"], None)
            if trace.osc_on("feedback"):
                why = getattr(osc_output, "refusal", None)
                reason = (why(target, address) if why is not None else "") or "not sent"
                _tr(
                    f"row {n} refused: {reason} (sent again when sending works)",
                    blocked=True,
                    key=f"row {n}",
                )

    def poll(self) -> None:
        """Reads every source; changed values send, within the rate limit."""
        if not self._running:
            return
        traced = trace.osc_on("feedback")
        for row in self._active_rows():
            values = self.value_of(row)
            if values is None:
                if traced:
                    n = self._number(row)
                    source = source_text(row.get("source") or {})
                    _tr(
                        f"row {n} {source} has no value (not sent)",
                        rate=True,
                        key=f"row {n} none",
                    )
                continue
            types = _send_types(row, values)
            if self._last.get(row["id"]) == (values, types):
                if traced:
                    n = self._number(row)
                    _tr(f"row {n} unchanged (not sent)", rate=True, key=f"row {n} same")
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
            elif trace.osc_on("feedback"):
                n = self._number(row)
                rate = self._settings.get("feedback_rate")
                _tr(
                    f"row {n} held back (rate {rate}/s)",
                    rate=True,
                    key=f"row {n} held",
                )

    def resend_all(self, reason: str = "") -> int:
        """Sends every row's current value now. The number sent."""
        if not self._running:
            _tr(f"resend skipped ({reason}): not running")
            return 0
        count = 0
        for row in self._active_rows():
            values = self.value_of(row)
            if values is None:
                if trace.osc_on("feedback"):
                    n = self._number(row)
                    source = source_text(row.get("source") or {})
                    _tr(f"row {n} {source} has no value (not resent)")
                continue
            types = _send_types(row, values)
            self._last[row["id"]] = (values, types)
            self._send(row, values, types)
            count += 1
        if count:
            log.debug("OSC feedback: resent %s rows (%s)", count, reason)
        _tr(f"resent {count} rows ({reason})")
        return count

    def _on_mode_changed(self, _name: str) -> None:
        if not self._running:
            return
        if self._settings.get("resend_mode", True):
            self.resend_all("mode change")
        else:
            _tr("mode change: no resend (Resend on mode change is Off)")

    def _on_sync(self, host: str, port: int) -> None:
        if host and port >= 0:
            try:
                from gremlin import osc_output

                osc_output.note_sender(host, port)
            except Exception as error:  # noqa: BLE001 - resend anyway
                _tr(
                    f"sync: reply address not noted ({type(error).__name__})",
                    warning=True,
                    key="sync",
                )
        who = f"{host}:{port}" if host and port >= 0 else "an unknown sender"
        self.resend_all(f"sync from {who}")

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


def handle_incoming(address: str, args: Any, peer: tuple | None) -> bool:  # noqa: ANN401
    """Any thread (OscRuntime, first for every message). True when address
    is the sync address: the message is consumed (never reaches inputs) and
    every row is sent again while a profile runs."""
    running = _feedback is not None and _feedback.is_running()
    # Held in memory, read again when OSC's file changes (E2).
    s = settings()
    if not s.get("sync_enabled", True):
        return False
    sync = str(s.get("sync_address") or "").strip()
    # OSC addresses match without regard to case (incoming ones come
    # casefolded), so a mixed-case sync address matches too.
    if not sync or str(address).strip().casefold() != sync.casefold():
        return False
    if running and _feedback is not None:
        _tr(f"sync {address}: resend asked", key="sync")
        _feedback.request_sync(peer)
    else:
        _tr(f"sync {address}: not running (no resend)", blocked=True, key="sync")
    return True
