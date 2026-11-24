# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The Screen Saver Mode window's model (12 S1-S20): its settings, the
two timers each with its switch and wait (S4, S5; stored in the program's
settings, so History records them, S10), the
status line read from screen_saver_mode.manager() once a second while the
window is open (with what last reset the idle time, S18, and the full-screen
program, S19), and the three checks (Refresh Devices, Refresh Programs,
Refresh System; S12, S13, S17) and the Ignore switches (programs, drivers
and services, S14), run on program threads. Programs and System each run
their own elevated check and keep their own half (power_requests.split).
Button presses and every message shown go to the Screen Saver Mode trace
(S16); failures also go to the normal log. The countdown per timer and
the count of times Windows turned the displays back on (S6, S20) come from
the status.

S21-S27: every device Refresh Devices ever found stays in the saved Devices
list until Remove (S27), each Automatic or Manual (S35) and recognised by
device_key (S43); the helper is started when the mode and Power off displays
are on and a row is Automatic (S25), not again after a refusal until
Try again (S26); the core's device hooks disable the Automatic devices
connected at the power-off and re-enable them at the first input (S21, S23),
and a device plugged in again retries (device_disable.DeviceDisabler).

S28-S32 (Wake PC): the saved Wake PC list (WAKE_PC) holds the touched
keyboards and mice; only the ticked ones' input counts (handed to the core
by apply_saved). The window's Wake PC tab merges it with the keyboards and
mice Windows reports (read on a program thread), ticks a device when one
of its keys or buttons is pressed while the tab is open (S30) and says
when nothing is ticked (S31)."""

from __future__ import annotations

import logging
import re
import time
import types
from collections.abc import Iterable
from datetime import datetime
from typing import Any, Callable

from PySide6 import QtCore

import gremlin.ui.type_aliases as ta
from gremlin import clock, config
from gremlin.device_key import device_key, device_numbers, has_numbers
from gremlin.signal import signal
from gremlin.types import PropertyType
from gremlin.ui.device import QML_IMPORT_MAJOR_VERSION, QML_IMPORT_NAME

assert QML_IMPORT_NAME == "Gremlin.Device"
assert QML_IMPORT_MAJOR_VERSION == 1

SECTION = "global"
GROUP = "screen-saver-mode"
ENABLED = "enabled"
SAVER_ON = "screen-saver-on"
SAVER_WAIT = "screen-saver-wait-s"
OFF_ON = "power-off-on"
OFF_WAIT = "power-off-wait-s"
HOLD_FULLSCREEN = "hold-fullscreen"
# S21: at most how long the displays wait for the devices to switch off.
DEVICES_WAIT = "devices-wait-s"
DEVICES_WAIT_DEFAULT = 10
DEVICES_WAIT_MIN = 1
DEVICES_WAIT_MAX = 60
# S27: the remembered Devices list, kept across restarts.
DEVICES = "devices"
# S35: a row's choice.
AUTOMATIC = "automatic"
MANUAL = "manual"
# S28: the Wake PC list: {"id", "name", "kinds", "ticked", "how"} per device.
WAKE_PC = "wake-pc"
NAMES = (
    ENABLED,
    SAVER_ON,
    SAVER_WAIT,
    OFF_ON,
    OFF_WAIT,
    HOLD_FULLSCREEN,
    DEVICES_WAIT,
    DEVICES,
    WAKE_PC,
)

# S31: the core's hold while nothing is ticked (screen_saver_mode
# HOLD_NO_WAKE_DEVICE) and the status line's words (glossary "Wake PC").
HOLD_NO_WAKE_DEVICE = "no_wake_device"
WAITING_TEXT = "Waiting: tick at least one keyboard or mouse on Wake PC."
# S30: how a row was ticked, as its note says it.
HOW_KEY = "key"
HOW_CLICK = "click"
HOW_YOU = "you"
HOW_UNTICK = "untick"
_HOW_NOTES = {
    HOW_KEY: "ticked when you pressed a key",
    HOW_CLICK: "ticked when you clicked",
    HOW_YOU: "ticked by you",
    HOW_UNTICK: "you unticked it",
}
NOT_CONNECTED = "not connected"
_KINDS = ("keyboard", "mouse")

# S26: shown when the helper should run and doesn't.
HELPER_MESSAGE = "Devices can't be disabled: the helper isn't running"
_WAITS = (SAVER_WAIT, OFF_WAIT)

# The longest wait that can be typed (minutes) and stored (seconds).
MAX_WAIT_MIN = 999
_MAX_WAIT_S = 86400

SCAN_SECONDS = 4.0

_log = logging.getLogger("system")

# powercfg's kinds of request (ProgramRequest.kind) and the word shown after
# a driver's or service's name.
KIND_PROCESS = "PROCESS"
_KIND_WORDS = {"DRIVER": "driver", "SERVICE": "service"}


def _trace(text: str) -> None:
    """One Screen Saver Mode trace line (S16); a no-op while tracing is off
    or before gremlin.trace has the Screen Saver Mode tick."""
    try:
        from gremlin import trace

        write = getattr(trace, "screen_saver", None)
        if write is not None:
            write(text)
    except Exception:
        _log.exception("Screen Saver Mode: the trace line could not be written")


def register_options() -> None:
    """The nine settings (01 S6: registered before the purge): the seven
    the window sets, the saved Devices list (S27) and the Wake PC list
    (S28). Exposed for History; Options leaves them out (the window has the
    controls)."""
    cfg = config.Configuration()
    rows: tuple[tuple[str, PropertyType, object, str, dict], ...] = (
        (
            ENABLED,
            PropertyType.Bool,
            False,
            "Screen Saver Mode: keep the program's own idle time from the "
            "keyboard and mouse only, and start the screen saver and power off "
            "the displays when their waits run out.",
            {},
        ),
        (
            SAVER_ON,
            PropertyType.Bool,
            True,
            "Screen Saver Mode: start the screen saver chosen in Windows.",
            {},
        ),
        (
            SAVER_WAIT,
            PropertyType.Int,
            0,
            "Screen Saver Mode's screen saver wait in seconds; 0 uses Windows' "
            "screen saver wait.",
            {"min": 0, "max": _MAX_WAIT_S},
        ),
        (
            OFF_ON,
            PropertyType.Bool,
            True,
            "Screen Saver Mode: power off the displays.",
            {},
        ),
        (
            OFF_WAIT,
            PropertyType.Int,
            0,
            "Screen Saver Mode's power off wait in seconds; 0 uses Windows' "
            "display-off time.",
            {"min": 0, "max": _MAX_WAIT_S},
        ),
        (
            HOLD_FULLSCREEN,
            PropertyType.Bool,
            True,
            "Screen Saver Mode: hold off during full-screen programs.",
            {},
        ),
        (
            DEVICES_WAIT,
            PropertyType.Int,
            DEVICES_WAIT_DEFAULT,
            "Screen Saver Mode: at most how many seconds the displays wait "
            "for the devices to switch off before they power off.",
            {"min": DEVICES_WAIT_MIN, "max": DEVICES_WAIT_MAX},
        ),
        (
            DEVICES,
            PropertyType.List,
            [],
            "Screen Saver Mode: the devices Refresh Devices found; the Automatic "
            "ones are disabled while the displays are off.",
            {},
        ),
        (
            WAKE_PC,
            PropertyType.List,
            [],
            "Screen Saver Mode: the keyboards and mice on the Wake PC tab; "
            "only the ticked ones' input counts.",
            {},
        ),
    )
    for name, kind, default, description, extra in rows:
        cfg.register(SECTION, GROUP, name, kind, default, description, extra, True)


def _ensure_options() -> None:
    cfg = config.Configuration()
    if not all(cfg.exists(SECTION, GROUP, n) for n in NAMES):
        register_options()


def _value(name: str) -> Any:  # noqa: ANN401 - a setting of any type
    _ensure_options()
    return config.Configuration().value(SECTION, GROUP, name)


def _set(name: str, value: object) -> None:
    _ensure_options()
    config.Configuration().set(SECTION, GROUP, name, value)


def saved_wait_s(name: str) -> int:
    """A timer's typed wait in seconds (SAVER_WAIT or OFF_WAIT); 0 = none."""
    try:
        return min(_MAX_WAIT_S, max(0, int(_value(name) or 0)))
    except (TypeError, ValueError):
        return 0


def _core() -> types.ModuleType:
    from gremlin import screen_saver_mode

    return screen_saver_mode


def saved_devices_wait_s() -> int:
    """S21: the devices wait in seconds, 1-60 (default 10)."""
    try:
        value = int(_value(DEVICES_WAIT) or DEVICES_WAIT_DEFAULT)
    except (TypeError, ValueError):
        return DEVICES_WAIT_DEFAULT
    return min(DEVICES_WAIT_MAX, max(DEVICES_WAIT_MIN, value))


def saved_settings() -> object:
    """The saved settings as screen_saver_mode.Settings."""
    core = _core()
    fields: dict[str, object] = dict(
        enabled=bool(_value(ENABLED)),
        screen_saver_on=bool(_value(SAVER_ON)),
        screen_saver_wait_s=saved_wait_s(SAVER_WAIT),
        power_off_on=bool(_value(OFF_ON)),
        power_off_wait_s=saved_wait_s(OFF_WAIT),
        hold_fullscreen=bool(_value(HOLD_FULLSCREEN)),
    )
    # A core (or a stand-in) without the devices wait ignores it.
    if "devices_wait_s" in getattr(core.Settings, "__dataclass_fields__", {}):
        fields["devices_wait_s"] = saved_devices_wait_s()
    return core.Settings(**fields)


# Whether the mode and Power off displays were both on when last applied
# (None before the first apply).
_off_timer_on: bool | None = None


def apply_saved() -> None:
    """Hands the saved settings to the one Screen Saver Mode (at start,
    after a change in the window, after History puts settings back)."""
    global _off_timer_on
    try:
        core = _core()
        wanted = saved_settings()
        manager = core.manager()
        # S3, S28, S31: only the ticked devices' input counts.
        ticked = ticked_wake_ids()
        manager.set_wake_devices(ticked)
        if manager.settings() != wanted:
            manager.apply(wanted)
        on = bool(wanted.enabled) and bool(wanted.power_off_on)  # type: ignore[attr-defined]
        was, _off_timer_on = _off_timer_on, on
        if was and not on:
            # The core calls after_input only while on: switching the mode
            # or Power off displays off re-enables what is pending (S23).
            _trace("mode or power off switched off: re-enabling devices")
            _disabler().enable_pending()
    except Exception:
        _log.exception("Screen Saver Mode: could not apply the settings")


# The tray's calls (12 S1; the tray menu's two items) ----------------------


def ssm_enabled() -> bool:
    """Whether Screen Saver Mode is on (the tray's checkable item)."""
    try:
        return bool(_value(ENABLED))
    except Exception:
        _log.exception("Screen Saver Mode: the setting could not be read")
        return False


def set_ssm_enabled(on: bool) -> None:
    """Switches Screen Saver Mode on or off as the window's switch does:
    saved, handed to the manager, an open window follows."""
    on = bool(on)
    if on == ssm_enabled():
        return
    _trace(f"Screen Saver Mode {'on' if on else 'off'} (tray)")
    _set(ENABLED, on)
    _settings_changed()
    signal.configChanged.emit()
    snapshot_changed()


def turn_displays_off_now() -> None:
    """The tray's "Turn displays off now": the sequence at once (devices
    first, then the displays, then keep-off until a counted input)."""
    _trace("Turn displays off now (tray)")
    try:
        _core().manager().turn_off_now()
    except Exception:
        _log.exception("Screen Saver Mode: turn off now failed")


# The state snapshot (trace.register_snapshot, 01 trace) -----------------------

SNAPSHOT_SECTION = "Screen Saver Mode"
# Names Windows has on Ignore, per list, as last read or changed.
_ignored: dict[str, list[str]] = {"programs": [], "system": []}


def _on_off(on: bool) -> str:
    return "on" if on else "off"


def _hold_now_line() -> str:
    """01 S185: the hold in effect now, with its full-screen program."""
    try:
        hold, program = _core().hold_now()
    except Exception:
        _log.exception("Screen Saver Mode: the hold in effect could not be read")
        hold, program = "", ""
    if not hold:
        return "Hold now: none"
    return f"Hold now: {hold}" + (f" ({program})" if program else "")


def snapshot_lines() -> list[str]:
    """Every setting, the hold in effect now, the Devices list by name with
    each one's choice, the ticked Wake PC devices and the Ignore lists, one
    line each, for the trace's state snapshot and Save Diagnostics."""
    lines: list[str] = []
    try:
        lines.append(f"Screen Saver Mode: {_on_off(bool(_value(ENABLED)))}")
        saver, off = saved_wait_s(SAVER_WAIT), saved_wait_s(OFF_WAIT)
        lines.append(
            f"Screen saver: {_on_off(bool(_value(SAVER_ON)))}, wait "
            + (duration_text(saver) if saver else "Windows' wait")
        )
        lines.append(
            f"Power off displays: {_on_off(bool(_value(OFF_ON)))}, wait "
            + (duration_text(off) if off else "Windows' wait")
        )
        hold = _on_off(bool(_value(HOLD_FULLSCREEN)))
        lines.append(f"Hold during full-screen programs: {hold}")
        lines.append(_hold_now_line())
        lines.append(f"Wait for devices to switch off: {saved_devices_wait_s()} s")
        for row in saved_devices():
            virtual = " (virtual)" if row["virtual"] else ""
            lines.append(f"Devices: {row['name']}{virtual}, {row['choice']}")
        ticked = [r["name"] or r["id"] for r in saved_wake_rows() if r["ticked"]]
        lines.append("Wake PC ticked: " + (", ".join(ticked) if ticked else "none"))
        for key, label in (("programs", "Programs"), ("system", "System")):
            names = _ignored[key]
            lines.append(f"Ignore {label}: " + (", ".join(names) if names else "none"))
    except Exception:
        _log.exception("Screen Saver Mode: the state snapshot could not be built")
    return lines


def register_snapshot() -> None:
    """Hands snapshot_lines to the trace (once); a trace without the
    snapshot is left alone."""
    try:
        from gremlin import trace

        register = getattr(trace, "register_snapshot", None)
        if register is not None:
            register(SNAPSHOT_SECTION, snapshot_lines)
    except Exception:
        _log.exception("Screen Saver Mode: the state snapshot could not be registered")


def snapshot_changed() -> None:
    """Asks the trace to rewrite this section's lines (after a setting,
    a device's choice, a Wake PC tick or an Ignore changed)."""
    try:
        from gremlin import trace

        changed = getattr(trace, "snapshot_changed", None)
        if changed is not None:
            changed(SNAPSHOT_SECTION)
    except Exception:
        _log.exception("Screen Saver Mode: the state snapshot could not be updated")


# The saved Devices list (S27) ---------------------------------------------


_VIRTUAL_NAMES = ("VJOY", "VIRTUAL JOYSTICK", "VIGEM", "VIRTUAL GAMEPAD")
_VIRTUAL_IDS = (
    "VID_1234&PID_BEAD",  # vJoy (gremlin.device_reset._VJOY)
    "VIGEM",
    "ROOT\\",
    "HID_DEVICE_SYSTEM_VHF",
)


def is_virtual_device(name: str, instance_id: str) -> bool:
    """True for a software device (vJoy, ViGEm, a virtual HID): Screen Saver
    Mode never switches these off (S12)."""
    upper_name, upper_id = str(name).upper(), str(instance_id).upper()
    return any(m in upper_name for m in _VIRTUAL_NAMES) or any(
        m in upper_id for m in _VIRTUAL_IDS
    )


def _float(value: object) -> float:
    try:
        return float(value or 0.0)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0


def _device_row(row: object) -> dict | None:
    """A saved row, cleaned; None when it isn't one (no key)."""
    if not isinstance(row, dict) or not row.get("key"):
        return None
    name = str(row.get("name", "") or "")
    raw = row.get("instance_ids")
    ids = [str(i) for i in raw if i] if isinstance(raw, list) else []
    virtual = bool(row.get("virtual", False)) or any(
        is_virtual_device(name, i) for i in ids or [""]
    )
    manual = virtual or row.get("choice") == MANUAL
    return {
        "key": str(row["key"]),
        "name": name,
        "instance_ids": ids,
        "rate": _float(row.get("rate")),
        "choice": MANUAL if manual else AUTOMATIC,
        "virtual": virtual,
        "last_seen": str(row.get("last_seen", "") or ""),
    }


def saved_devices() -> list[dict]:
    """The remembered devices (S27) as stored: {"key", "name",
    "instance_ids", "rate" (0 = the last Refresh Devices didn't find it),
    "choice", "virtual", "last_seen"}; [] before the first press."""
    raw = _value(DEVICES)
    out: dict[str, dict] = {}
    for r in (_device_row(r) for r in (raw if isinstance(raw, list) else [])):
        if r is not None:
            out.setdefault(r["key"], r)
    return list(out.values())


def save_devices(rows: list[dict]) -> None:
    """Saves the remembered devices (S27)."""
    stored = [r for r in (_device_row(r) for r in rows) if r is not None]
    if stored != _value(DEVICES):
        _set(DEVICES, stored)


def merge_devices(
    saved: list[dict],
    found: Iterable[tuple[str, str, float]],
    now: datetime | None = None,
) -> list[dict]:
    """S27, S43: the remembered rows after a Refresh Devices that found
    (name, instance id, rate). New devices are Automatic; a row not found
    stays with its choice and last seen, without a rate. Found rows first,
    highest rate first."""
    seen = (now or datetime.now()).isoformat(timespec="seconds")
    rows = {r["key"]: {**r, "rate": 0.0} for r in saved}
    fresh: set[str] = set()
    for name, instance_id, rate in found:
        if not instance_id:
            continue
        key = device_key(name, instance_id)
        row = rows.setdefault(
            key,
            {"key": key, "choice": AUTOMATIC, "virtual": False, "rate": 0.0},
        )
        if key not in fresh:
            fresh.add(key)
            row.update(name=name, instance_ids=[], last_seen=seen)
        if instance_id not in row["instance_ids"]:
            row["instance_ids"].append(instance_id)
        row["rate"] = max(row["rate"], rate)
    cleaned = [r for r in map(_device_row, rows.values()) if r is not None]
    return sorted(cleaned, key=lambda r: -r["rate"])


def found_text(row: dict, now: datetime | None = None) -> str:
    """S27: "" for a found device, else "Not found · last seen …"."""
    if row["rate"] > 0:
        return ""
    try:
        seen = datetime.fromisoformat(row["last_seen"])
    except ValueError:
        return "Not found"
    if seen.date() == (now or datetime.now()).date():
        return f"Not found · last seen today {seen:%H:%M}"
    return f"Not found · last seen {seen:%Y-%m-%d}"


def _device_view(row: dict) -> dict:
    """A remembered device as the Devices tab shows it."""
    return {
        "key": row["key"],
        "name": row["name"],
        "rate": row["rate"],
        "choice": row["choice"],
        "virtual": row["virtual"],
        "found": row["rate"] > 0,
        "foundText": found_text(row),
    }


def _counts(parts: list[tuple[int, str]], join: str) -> str:
    return join.join(f"{n} {word}" for n, word in parts if n)


def devices_summary(rows: list[dict]) -> str:
    """S12: "4 automatic · 1 manual · 1 not found"; virtual ones don't count."""
    rows = [r for r in rows if not r.get("virtual")]
    if not rows:
        return "No devices yet"
    automatic = sum(r["choice"] == AUTOMATIC for r in rows)
    missing = sum(r["rate"] <= 0 for r in rows)
    return _counts(
        [
            (automatic, AUTOMATIC),
            (len(rows) - automatic, MANUAL),
            (missing, "not found"),
        ],
        " · ",
    )


def checked_text(rows: list[dict]) -> str:
    """S27: "Checked 16:27 · 4 found, 1 not found"."""
    found = sum(r["rate"] > 0 for r in rows)
    counts = _counts([(found, "found"), (len(rows) - found, "not found")], ", ")
    counts = counts or "No device is sending reports all the time."
    return f"Checked {_clock_text()} · {counts}"


def _automatic_rows() -> list[dict]:
    return [r for r in saved_devices() if r["choice"] == AUTOMATIC and not r["virtual"]]


def _row_of(device: Any, rows: list[dict], name_of: Callable) -> dict | None:  # noqa: ANN401
    """The remembered row a connected device belongs to (S43). Its name is
    read only when rows with different names share its numbers; a name that
    can't be read leaves the row the device was last found as."""
    instance_id = str(device.instance_id)
    numbers = device_numbers(instance_id)
    if not has_numbers(numbers):
        key = device_key("", instance_id)
        return next((r for r in rows if r["key"] == key), None)
    same = [
        r for r in rows if any(device_numbers(i) == numbers for i in r["instance_ids"])
    ]
    if len(same) <= 1:
        return same[0] if same else None
    name = name_of(device)
    if name:
        key = device_key(name, instance_id)
        return next((r for r in same if r["key"] == key), None)
    known = [
        r for r in same if instance_id.upper() in (i.upper() for i in r["instance_ids"])
    ]
    return known[0] if len(known) == 1 else None


def _saved_pairs() -> list[tuple[str, str]]:
    """The connected devices of the Automatic rows, as
    DeviceDisabler.disable takes them: (name, id), never a virtual one
    (S21, S35, S43). Looked up now, so a device in another USB port
    counts."""
    if not _automatic_rows():
        return []
    from gremlin import hid_report_scan

    rows = saved_devices()
    pairs: list[tuple[str, str]] = []
    taken: set[str] = set()
    for device in hid_report_scan.present():
        instance_id = str(device.instance_id)
        if not instance_id or instance_id.upper() in taken:
            continue
        row = _row_of(device, rows, hid_report_scan.device_name)
        if row is None or row["choice"] != AUTOMATIC or row["virtual"]:
            continue
        if is_virtual_device(row["name"], instance_id):
            continue
        taken.add(instance_id.upper())
        pairs.append((row["name"], instance_id))
    return pairs


# The saved Wake PC list (S28-S30) -------------------------------------------


def _kinds_of(raw: object) -> list[str]:
    kinds = raw if isinstance(raw, (list, tuple)) else []
    return [k for k in _KINDS if k in kinds]


def _wake_row(row: object) -> dict | None:
    """A saved Wake PC row, cleaned; None when it isn't one."""
    if not isinstance(row, dict):
        return None
    physical_id = str(row.get("id", "") or "").strip()
    if not physical_id:
        return None
    how = str(row.get("how", "") or "")
    return {
        "id": physical_id,
        "name": str(row.get("name", "") or ""),
        "kinds": _kinds_of(row.get("kinds")),
        "ticked": bool(row.get("ticked", False)),
        "how": how if how in _HOW_NOTES else "",
    }


def saved_wake_rows() -> list[dict]:
    """The saved Wake PC list (S28); [] before the first tick."""
    raw = _value(WAKE_PC)
    rows = [_wake_row(r) for r in (raw if isinstance(raw, list) else [])]
    seen: set[str] = set()
    out = []
    for r in rows:
        if r is not None and r["id"] not in seen:
            seen.add(r["id"])
            out.append(r)
    return out


def ticked_wake_ids() -> list[str]:
    """The ticked devices' physical ids (S28)."""
    return [r["id"] for r in saved_wake_rows() if r["ticked"]]


def save_wake_rows(rows: list[dict]) -> bool:
    """Saves the touched rows (ticked, or with how they were set); devices
    never touched are left out, so an unplugged one doesn't stay listed.
    True when the setting changed."""
    stored = [
        {
            "id": r["id"],
            "name": r["name"],
            "kinds": list(r["kinds"]),
            "ticked": bool(r["ticked"]),
            "how": r["how"],
        }
        for r in (_wake_row(r) for r in rows)
        if r is not None and (r["ticked"] or r["how"])
    ]
    if stored == _value(WAKE_PC):
        return False
    _set(WAKE_PC, stored)
    return True


def merge_wake_rows(saved: list[dict], found: list[object] | None) -> list[dict]:
    """S28, S29: the saved rows with the devices Windows reports (found,
    screen_saver_mode.InputDevice; None before the first read). A device
    not seen before is unticked; a saved one not reported stays, not
    connected. Connected rows first, then by name."""
    rows = {r["id"]: dict(r) for r in saved}
    connected: set[str] = set()
    for dev in found or []:
        physical_id = str(getattr(dev, "physical_id", "") or "").strip()
        if not physical_id:
            continue
        connected.add(physical_id)
        name = str(getattr(dev, "name", "") or "")
        kinds = _kinds_of(getattr(dev, "kinds", ()))
        row = rows.setdefault(
            physical_id,
            {"id": physical_id, "name": "", "kinds": [], "ticked": False, "how": ""},
        )
        if name:
            row["name"] = name
        if kinds:
            row["kinds"] = kinds
    out = []
    for r in rows.values():
        r["connected"] = found is None or r["id"] in connected
        out.append(r)
    return sorted(
        out, key=lambda r: (not r["connected"], (r["name"] or r["id"]).casefold())
    )


# S33: a row stays "in use now" this long after its device's last input.
IN_USE_S = 2.0


def _wake_view(row: dict, in_use: bool = False) -> dict:
    """A Wake PC row as the tab shows it."""
    return {
        "id": row["id"],
        "name": row["name"] or row["id"],
        "kinds": ", ".join(row["kinds"]),
        "ticked": bool(row["ticked"]),
        "note": _HOW_NOTES.get(row["how"], ""),
        "connected": bool(row.get("connected", True)),
        "inUse": bool(in_use),
    }


# The helper (S25, S26) and the device hooks (S21, S23) ---------------------


def _disabler() -> Any:  # noqa: ANN401 - device_disable.DeviceDisabler
    from gremlin import device_disable

    return device_disable.manager()


# S25: not started again after a refusal until Try again.
_helper_refused = False
_helper_starting = False


def helper_wanted() -> bool:
    """S25: Screen Saver Mode on, Power off displays on, at least one
    Automatic device."""
    try:
        return (
            bool(_value(ENABLED)) and bool(_value(OFF_ON)) and bool(_automatic_rows())
        )
    except Exception:
        _log.exception("Screen Saver Mode: the helper's settings could not be read")
        return False


def _helper_done(ok: bool, error: str) -> None:
    """start_helper's answer (a program thread): a refusal stops further
    starts until Try again (S25, S26)."""
    global _helper_refused, _helper_starting
    _helper_starting = False
    if ok:
        _log.info("Screen Saver Mode: the device helper is running")
        _trace("device helper started")
    else:
        _helper_refused = True
        why = str(error or "it could not start")
        _log.warning(f"Screen Saver Mode: the device helper isn't running: {why}")
        _trace(f"device helper not started: {why}")


def ensure_helper() -> None:
    """Starts the helper when it is wanted, isn't running, isn't being
    started and wasn't refused (S25): at start, on a settings change,
    after a Refresh Devices that fills the list."""
    global _helper_starting
    if _helper_refused or _helper_starting or not helper_wanted():
        return
    try:
        disabler = _disabler()
        if disabler.helper_running():
            return
        _helper_starting = True
        _trace("device helper: starting")
        disabler.start_helper(_helper_done)
    except Exception:
        _helper_starting = False
        _log.exception("Screen Saver Mode: the device helper could not start")


def try_again() -> None:
    """S26's Try again: one more start, even after a refusal."""
    global _helper_refused
    _trace("Try again pressed")
    _helper_refused = False
    ensure_helper()


def helper_message() -> str:
    """S26: the window's text when the helper should run and doesn't; ""
    otherwise (also while it is being started)."""
    if _helper_starting or not helper_wanted():
        return ""
    try:
        disabler = _disabler()
        text = str(disabler.status_text() or "")
        if not text and not disabler.helper_running():
            text = HELPER_MESSAGE
        return text
    except Exception:
        _log.exception("Screen Saver Mode: the helper's state could not be read")
        return HELPER_MESSAGE


def _before_power_off() -> tuple[int, Callable[[], bool]] | None:
    """S21: the Automatic devices are disabled just before the power-off, when
    the helper runs (async). Returns (number of devices, probe) so the core
    waits for them (at most 10 s) before the power-off, or None when there
    is nothing to wait for."""
    if not _automatic_rows():
        return None
    disabler = _disabler()
    if not disabler.helper_running():
        _trace("devices not disabled: the helper isn't running")
        return None
    try:
        devices = _saved_pairs()
    except Exception:
        _log.exception("Screen Saver Mode: the connected devices could not be read")
        _trace("devices not disabled: the connected devices could not be read")
        return None
    if not devices:
        _trace("devices not disabled: no Automatic device is connected")
        return None
    disabler.disable(devices)
    return len(devices), lambda: not disabler.wait_idle(0)


def _after_input() -> None:
    """S23: the first counted input re-enables what the journal lists."""
    _disabler().enable_pending()


def _device_arrival() -> None:
    """S23: a device plugged in again: retry what is still to be enabled."""
    try:
        _disabler().on_device_arrival()
    except Exception:
        _log.exception("Screen Saver Mode: device arrival retry failed")


def _settings_changed() -> None:
    """A setting changed (the window, History's Restore): the manager gets
    it and the helper starts when it is now wanted (S25)."""
    apply_saved()
    ensure_helper()


_following = False
_arrival_signal: Any = None


def start() -> None:
    """At program start: apply the saved settings, follow changes made
    outside the window (History's Restore sends configChanged), wire the
    device hooks (S21, S23) and start the helper when wanted (S25)."""
    global _following, _arrival_signal
    apply_saved()
    register_snapshot()
    if not _following:
        signal.configChanged.connect(_settings_changed)
        _following = True
    try:
        _core().manager().set_device_hooks(
            before_power_off=_before_power_off, after_input=_after_input
        )
    except Exception:
        _log.exception("Screen Saver Mode: the device hooks could not be set")
    if _arrival_signal is None:
        try:
            from gremlin import event_handler

            _arrival_signal = event_handler.EventListener().device_change_event
            _arrival_signal.connect(_device_arrival)
        except Exception:
            _arrival_signal = None
            _log.exception("Screen Saver Mode: no device change listener")
    ensure_helper()


def shutdown() -> None:
    """At quit: only a Screen Saver Mode that was loaded."""
    import sys

    global _following, _arrival_signal
    if _following:
        try:
            signal.configChanged.disconnect(_settings_changed)
        except (RuntimeError, TypeError):
            pass
        _following = False
    if _arrival_signal is not None:
        try:
            _arrival_signal.disconnect(_device_arrival)
        except (RuntimeError, TypeError):
            pass
        _arrival_signal = None
    core = sys.modules.get("gremlin.screen_saver_mode")
    if core is not None:
        try:
            core.manager().set_device_hooks(None, None)
        except Exception:
            _log.exception("Screen Saver Mode: the device hooks could not be cleared")
        core.manager().shutdown()


def duration_text(seconds: float) -> str:
    """'45 s', '2 min 41 s', '5 min', '1 h 30 min'."""
    s = max(0, int(seconds))
    if s < 60:
        return f"{s} s"
    if s < 3600:
        m, rest = divmod(s, 60)
        return f"{m} min {rest} s" if rest else f"{m} min"
    h, rest = divmod(s, 3600)
    m = rest // 60
    return f"{h} h {m} min" if m else f"{h} h"


def _clock_text() -> str:
    return time.strftime("%H:%M")


def _hold_text(status: object) -> str:
    hold = str(getattr(status, "hold", "") or "")
    if hold == "display_request":
        who = str(getattr(status, "hold_program", "") or "")
        return (
            "On hold: a program is keeping the display on"
            + (f" ({who})" if who else "")
            + ". The countdown starts again when it stops."
        )
    if hold == "fullscreen":
        who = str(getattr(status, "hold_program", "") or "")
        return (
            "On hold: a full-screen program is in front"
            + (f" ({who})" if who else "")
            + ". The countdown starts again when it ends."
        )
    if hold == "locked":
        return (
            "On hold: the PC is locked. Windows looks after the screens "
            "while it is locked."
        )
    if hold == HOLD_NO_WAKE_DEVICE:
        return WAITING_TEXT
    return ""


def _last_reset_text(status: object) -> str:
    """S18: what last reset Gremlin's idle time; "" before the first input."""
    kind = str(getattr(status, "last_reset_kind", "") or "")
    if kind == "program":
        rate = int(getattr(status, "program_input_per_min", 0) or 0)
        if rate > 0:
            times = "once a minute" if rate == 1 else f"{rate} times a minute"
            return f"last reset by: input sent by a program, {times}"
        return "last reset by: input sent by a program, " + _ago(status)
    if kind in ("keyboard", "mouse"):
        name = str(getattr(status, "last_reset_by", "") or "").strip()
        who = f"{name} ({kind})" if name else f"a {kind}"
        return f"last reset by: {who}, " + _ago(status)
    return ""


def _ago(status: object) -> str:
    age = float(getattr(status, "last_reset_age_s", 0.0) or 0.0)
    return "just now" if age < 2 else f"{duration_text(age)} ago"


def _program_row(p: object) -> dict:
    """A Refresh Programs / Refresh System row for the window: the name, its
    kind (a driver's or service's word shown after the name), the detail
    line and whether it also keeps the PC awake (Programs rows)."""
    kind = str(getattr(p, "kind", "") or KIND_PROCESS).upper()
    return {
        "name": str(getattr(p, "name", "")),
        "path": str(getattr(p, "path", "") or ""),
        "kinds": ", ".join(str(k) for k in (getattr(p, "kinds", None) or [])),
        "ignored": bool(getattr(p, "ignored", False)),
        "kind": kind,
        "kindWord": _KIND_WORDS.get(kind, ""),
        "detail": str(getattr(p, "detail", "") or "").strip(),
        "alsoAwake": bool(getattr(p, "also_awake", False)),
    }


# The two elevated lists (S13, S17): which half of power_requests.split()
# each keeps, and its words.
PROGRAMS = "programs"
SYSTEM = "system"
_LISTS = {
    PROGRAMS: {
        "half": 0,
        "button": "Refresh Programs",
        "what": "programs",
        "kept": "ignored programs no longer keep the display on.",
        "none": "No program is asking Windows to keep the display on.",
        "ignored": "it no longer keeps the display on.",
    },
    SYSTEM: {
        "half": 1,
        "button": "Refresh System",
        "what": "system",
        "kept": "ignored ones no longer keep the PC awake.",
        "none": "Nothing is asking Windows to keep the PC awake.",
        "ignored": "it no longer keeps the PC awake.",
    },
}


def _problem_text(problem: str) -> str:
    """The problem that stops both timers (S9)."""
    if problem == "not_listening":
        return (
            "The keyboard and mouse can't be listened to, so Screen Saver Mode "
            "does nothing."
        )
    return ""


def _saver_problem_text(problem: str) -> str:
    """The Screen saver row's problem (S5, S8)."""
    if problem == "no_screen_saver":
        return "No screen saver is chosen in Windows."
    if problem == "windows_never":
        return "Windows never starts the screen saver: type a time to use this timer."
    return ""


def _off_problem_text(problem: str) -> str:
    """The Power off displays row's problem (S5)."""
    if problem == "windows_never":
        return "Windows never turns the display off: type a time to use this timer."
    return ""


def _minutes_text(seconds: int) -> str:
    """A typed wait as its box shows it, in minutes; "" when none."""
    if not seconds:
        return ""
    return str(seconds // 60) if seconds % 60 == 0 else f"{seconds / 60:g}"


def _parse_minutes(text: str) -> int | None:
    """Seconds for a typed time in minutes ("10", "10 min", "2.5"); 0 for
    "" (cleared); None for text that isn't a time."""
    raw = str(text or "").strip().lower()
    if raw.endswith("min"):
        raw = raw[:-3].strip()
    if not raw:
        return 0
    try:
        minutes = float(raw.replace(",", "."))
    except ValueError:
        return None
    if not (0 < minutes <= MAX_WAIT_MIN):
        return None
    return max(1, round(minutes * 60))


# The wake count from which the Wake-ups row points at Automatic (S20).
WAKES_HINT_AT = 3

_STALL_ENDED = re.compile(r"stall ended after (\d+) s")
_RING_TIME = re.compile(r"^(\d\d):(\d\d):(\d\d)\.\d+\s")


def _second_of_day(t: float) -> int:
    lt = time.localtime(t)
    return lt.tm_hour * 3600 + lt.tm_min * 60 + lt.tm_sec


def _freeze_text(start: float, end: float) -> str:
    """ "no freeze" or "window not responding N s": the watchdog's stall
    lines in trace.recent() between the away's start and end (read only)."""
    try:
        from gremlin import trace

        lines = trace.recent_lines()
    except Exception:
        return ""
    lo, hi = _second_of_day(start) - 1, _second_of_day(end) + 2
    longest, began = -1, False
    for line in lines:
        m = _RING_TIME.match(line)
        if m is None:
            continue
        at = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
        inside = lo <= at <= hi if lo <= hi else (at >= lo or at <= hi)
        if not inside:
            continue
        ended = _STALL_ENDED.search(line)
        if ended is not None:
            longest = max(longest, int(ended.group(1)))
        elif "stall began" in line:
            began = True
    if longest >= 0:
        return f"window not responding {longest} s"
    return "window not responding" if began else "no freeze"


def _last_away_text(away: dict, pending: int = 0) -> tuple[str, str]:
    """(value, detail) for Last time away from the core's last_away; the
    core leaves devices_back 0, so it is the devices switched off less the
    ones the journal still lists as to be enabled."""
    try:
        value = "Displays off " + duration_text(float(away.get("off_s", 0.0) or 0.0))
        parts: list[str] = []
        wakes = int(away.get("wakes", 0) or 0)
        parts.append(f"{wakes} wake-up" + ("" if wakes == 1 else "s"))
        off = int(away.get("devices_off", 0) or 0)
        back = max(int(away.get("devices_back", 0) or 0), off - max(0, pending))
        if off:
            word = "device" if off == 1 else "devices"
            parts.append(
                f"{off} {word} switched off and back on"
                if back >= off
                else f"{off} {word} switched off, {max(0, back)} back on"
            )
        freeze = _freeze_text(
            float(away.get("start", 0.0) or 0.0), float(away.get("end", 0.0) or 0.0)
        )
        if freeze:
            parts.append(freeze)
        return value, " · ".join(parts)
    except Exception:
        _log.exception("Screen Saver Mode: Last time away could not be built")
        return "unknown", ""


def _pending_device_names() -> list[str]:
    """The devices the journal lists as still to be enabled, by name; []
    when there is none or the journal can't be read."""
    try:
        journal = _disabler().journal()
        return [
            str(journal.entries.get(i, {}).get("name") or i)
            for i in journal.not_enabled()
        ]
    except Exception:
        return []


@ta.QmlElement
class ScreenSaverModeModel(QtCore.QObject):
    """The Screen Saver Mode window: settings, status and the two checks."""

    settingsChanged = QtCore.Signal()
    statusChanged = QtCore.Signal()
    devicesChanged = QtCore.Signal()
    programsChanged = QtCore.Signal()
    systemChanged = QtCore.Signal()
    busyChanged = QtCore.Signal()
    wakeRowsChanged = QtCore.Signal()

    # Worker results, queued to the main thread.
    _devicesDone = QtCore.Signal(object)
    _inputDevicesDone = QtCore.Signal(object)
    _requestsDone = QtCore.Signal(str, object)
    _ignoreDone = QtCore.Signal(str, str, bool, bool, str)

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        _ensure_options()
        register_snapshot()
        self._status: Any = None
        self._test_remaining = 0
        self._pending_devices: list[str] = []
        # S27: the remembered list.
        self._devices: list[dict] = saved_devices()
        self._devices_message = ""
        self._helper_message = ""
        self._rows: dict[str, list[dict]] = {PROGRAMS: [], SYSTEM: []}
        self._messages: dict[str, str] = {PROGRAMS: "", SYSTEM: ""}
        self._scanning: dict[str, bool] = {PROGRAMS: False, SYSTEM: False}
        self._scanning_devices = False
        self._pending_ignore = ""
        self._shown_problem: tuple[str, ...] = ()
        # S28: the keyboards and mice Windows reports (None until read),
        # whether the Wake PC tab is open, a read running / wanted again.
        self._input_devices: list[object] | None = None
        self._wake_open = False
        self._reading_inputs = False
        self._read_again = False
        self._device_signal: Any = None
        self._wake_rows = merge_wake_rows(saved_wake_rows(), None)
        # S33: physical id -> when its "in use now" ends (clock.monotonic);
        # one main-thread timer ends them all.
        self._in_use: dict[str, float] = {}
        self._in_use_timer = QtCore.QTimer(self)
        self._in_use_timer.setSingleShot(True)
        self._in_use_timer.timeout.connect(self._expire_in_use)
        self._stop = False
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self.refreshStatus)
        Queued = QtCore.Qt.ConnectionType.QueuedConnection
        self._devicesDone.connect(self._take_devices, Queued)
        self._requestsDone.connect(self._take_requests, Queued)
        self._ignoreDone.connect(self._take_ignore, Queued)
        self._inputDevicesDone.connect(self._take_input_devices, Queued)
        signal.configChanged.connect(self._on_config)

    # Settings ---------------------------------------------------------------

    @QtCore.Slot()
    def _on_config(self) -> None:
        # The saved list put back by History (S27) shows at once.
        saved = saved_devices()
        if saved != self._devices:
            self._devices = saved
            self.devicesChanged.emit()
        # The Wake PC list put back by History shows at once (S28).
        self._remerge()
        self.settingsChanged.emit()
        self.refreshStatus()

    def _changed(self) -> None:
        _settings_changed()
        snapshot_changed()
        self.settingsChanged.emit()
        self.refreshStatus()

    @QtCore.Property(bool, notify=settingsChanged)
    def enabled(self) -> bool:
        return bool(_value(ENABLED))

    @QtCore.Slot(bool)
    def setEnabled(self, on: bool) -> None:
        if bool(on) != self.enabled:
            _set(ENABLED, bool(on))
            self._changed()

    def _set_bool(self, name: str, on: bool) -> None:
        if bool(on) != bool(_value(name)):
            _set(name, bool(on))
            self._changed()

    @QtCore.Property(bool, notify=settingsChanged)
    def saverOn(self) -> bool:
        return bool(_value(SAVER_ON))

    @QtCore.Slot(bool)
    def setSaverOn(self, on: bool) -> None:
        self._set_bool(SAVER_ON, on)

    @QtCore.Property(bool, notify=settingsChanged)
    def offOn(self) -> bool:
        return bool(_value(OFF_ON))

    @QtCore.Slot(bool)
    def setOffOn(self, on: bool) -> None:
        self._set_bool(OFF_ON, on)

    @QtCore.Property(bool, notify=settingsChanged)
    def holdFullscreen(self) -> bool:
        return bool(_value(HOLD_FULLSCREEN))

    @QtCore.Slot(bool)
    def setHoldFullscreen(self, on: bool) -> None:
        if bool(on) != self.holdFullscreen:
            _set(HOLD_FULLSCREEN, bool(on))
            self._changed()

    @QtCore.Property(int, notify=settingsChanged)
    def devicesWaitS(self) -> int:
        """S21: at most how many seconds the displays wait for the devices
        to switch off (1-60)."""
        return saved_devices_wait_s()

    @QtCore.Slot(int)
    def setDevicesWaitS(self, seconds: int) -> None:
        try:
            value = int(seconds)
        except (TypeError, ValueError):
            return
        value = min(DEVICES_WAIT_MAX, max(DEVICES_WAIT_MIN, value))
        if value != saved_devices_wait_s():
            _trace(f"Wait for devices to switch off: {value} s")
            _set(DEVICES_WAIT, value)
            self._changed()
        else:
            # A typed value outside 1-60 shows the clamped one again.
            self.settingsChanged.emit()

    @QtCore.Slot()
    def testNow(self) -> None:
        """Test now: after a 5 s countdown the real sequence runs."""
        _trace("Test now pressed")
        try:
            _core().manager().start_test(5.0)
        except Exception:
            _log.exception("Screen Saver Mode: Test now could not start")
        self.refreshStatus()

    @QtCore.Slot()
    def cancelTest(self) -> None:
        _trace("Test now cancelled")
        try:
            _core().manager().cancel_test()
        except Exception:
            _log.exception("Screen Saver Mode: the test could not be cancelled")
        self.refreshStatus()

    @QtCore.Property(bool, notify=settingsChanged)
    def canTest(self) -> bool:
        """Test now and Turn displays off now work only while the mode is
        on (the core has no listener window otherwise)."""
        return bool(self.enabled)

    @QtCore.Property(int, notify=statusChanged)
    def testCountdown(self) -> int:
        """Whole seconds left before the test runs; 0 = no test pending."""
        return self._test_remaining

    def _set_wait(self, name: str, text: str) -> bool:
        seconds = _parse_minutes(text)
        if seconds is None:
            return False
        if seconds != saved_wait_s(name):
            _set(name, int(seconds))
            self._changed()
        return True

    @QtCore.Property(str, notify=settingsChanged)
    def saverWaitText(self) -> str:
        """The typed screen saver wait in minutes, "" when none (Windows'
        wait is used and shown greyed)."""
        return _minutes_text(saved_wait_s(SAVER_WAIT))

    @QtCore.Slot(str, result=bool)
    def setSaverWaitText(self, text: str) -> bool:
        """A typed time in minutes; "" clears it. False for text that isn't
        a time (nothing is changed)."""
        return self._set_wait(SAVER_WAIT, text)

    @QtCore.Slot()
    def clearSaverWait(self) -> None:
        self._set_wait(SAVER_WAIT, "")

    @QtCore.Property(str, notify=settingsChanged)
    def offWaitText(self) -> str:
        """The typed power off wait in minutes, "" when none."""
        return _minutes_text(saved_wait_s(OFF_WAIT))

    @QtCore.Slot(str, result=bool)
    def setOffWaitText(self, text: str) -> bool:
        return self._set_wait(OFF_WAIT, text)

    @QtCore.Slot()
    def clearOffWait(self) -> None:
        self._set_wait(OFF_WAIT, "")

    def _windows_s(self, field: str) -> int:
        return int(self._st(field, 0) or 0)

    @QtCore.Property(str, notify=statusChanged)
    def saverWindowsWaitText(self) -> str:
        """Windows' screen saver wait, for the greyed box: "10 min" or
        "Never"."""
        s = self._windows_s("saver_windows_wait_s")
        return duration_text(s) if s > 0 else "Never"

    @QtCore.Property(str, notify=statusChanged)
    def saverWindowsWaitLabel(self) -> str:
        s = self._windows_s("saver_windows_wait_s")
        return f"Windows' screen saver wait ({duration_text(s) if s > 0 else 'never'})"

    @QtCore.Property(str, notify=statusChanged)
    def offWindowsWaitText(self) -> str:
        s = self._windows_s("off_windows_wait_s")
        return duration_text(s) if s > 0 else "Never"

    @QtCore.Property(str, notify=statusChanged)
    def offWindowsWaitLabel(self) -> str:
        s = self._windows_s("off_windows_wait_s")
        return f"Windows' display-off time ({duration_text(s) if s > 0 else 'never'})"

    def _wait_in_use(self, name: str, windows_field: str) -> int:
        return saved_wait_s(name) or self._windows_s(windows_field)

    @QtCore.Property(str, notify=statusChanged)
    def orderWarning(self) -> str:
        """Both timers on and power off not later than the screen saver
        (contract-4): both still work, the screen saver just never shows."""
        if not (self.saverOn and self.offOn):
            return ""
        saver = self._wait_in_use(SAVER_WAIT, "saver_windows_wait_s")
        off = self._wait_in_use(OFF_WAIT, "off_windows_wait_s")
        if saver > 0 and 0 < off <= saver:
            return (
                "Power off comes at or before the screen saver: the screen "
                "saver won't show."
            )
        return ""

    # Status -----------------------------------------------------------------

    @QtCore.Slot(bool)
    def setOpen(self, is_open: bool) -> None:
        """Polls the status once a second while the window is open."""
        if is_open:
            self.refreshStatus()
            self._timer.start()
        else:
            self._timer.stop()
            # A devices check still reading stops early.
            self._stop = True
            # S30: detection runs only while the Wake PC tab is open.
            self.wakeTabOpen(False)

    @QtCore.Slot()
    def refreshStatus(self) -> None:
        try:
            self._status = _core().manager().status()
        except Exception:
            _log.exception("Screen Saver Mode: status could not be read")
            self._status = None
        self._helper_message = helper_message()
        self._test_remaining = self._read_test_remaining()
        self._pending_devices = _pending_device_names()
        problems = tuple(
            str(t)
            for t in (
                self.problemText,
                self.saverProblemText,
                self.offProblemText,
                self.orderWarning,
                self.wakeText,
                self._helper_message,
            )
            if t
        )
        for text in problems:
            if text not in self._shown_problem:
                _trace(f"Message shown: {text}")
        self._shown_problem = problems
        self.statusChanged.emit()

    def _read_test_remaining(self) -> int:
        try:
            read = getattr(_core().manager(), "test_remaining", None)
            return max(0, int(read())) if read is not None else 0
        except Exception:
            return 0

    def _st(self, name: str, default: object) -> Any:  # noqa: ANN401
        return (
            getattr(self._status, name, default)
            if self._status is not None
            else default
        )

    @QtCore.Property(bool, notify=statusChanged)
    def listening(self) -> bool:
        return bool(self._st("listening", False))

    @QtCore.Property(str, notify=statusChanged)
    def listeningText(self) -> str:
        if not self.enabled:
            return "Screen Saver Mode is off."
        if self.listening:
            return "Listening to the keyboard and mouse"
        return "Not listening to the keyboard and mouse"

    @QtCore.Property(str, notify=statusChanged)
    def idleText(self) -> str:
        return "Your idle time: " + duration_text(float(self._st("idle_s", 0.0) or 0.0))

    @QtCore.Property(str, notify=statusChanged)
    def lastResetText(self) -> str:
        """S18: "last reset by: …" next to the idle time."""
        if self._status is None:
            return ""
        return _last_reset_text(self._status)

    @QtCore.Property(str, notify=statusChanged)
    def windowsIdleText(self) -> str:
        win = float(self._st("windows_idle_s", 0.0) or 0.0)
        own = float(self._st("idle_s", 0.0) or 0.0)
        text = "Windows' idle time: " + duration_text(win)
        if self.enabled and own >= 10 and win < 2:
            text += " · devices are keeping Windows awake"
        return text

    @QtCore.Property(str, notify=statusChanged)
    def holdText(self) -> str:
        """On hold (S7, S11, S15): holds both timers."""
        if not self.enabled or self._status is None:
            return ""
        return _hold_text(self._status)

    @QtCore.Property(bool, notify=statusChanged)
    def onHold(self) -> bool:
        return bool(self.enabled and self._st("hold", ""))

    def _countdown(
        self, what: str, on: bool, problem: str, fired: str, remaining: str
    ) -> str:
        """A timer's line (S6): "<what> in 1 min 20 s" or "<what> done.";
        nothing while off, held or with a problem."""
        if not (self.enabled and on) or self._status is None:
            return ""
        if self.holdText or self.problemText or problem:
            return ""
        if bool(self._st(fired, False)):
            return f"{what} done. Nothing more until the keyboard or mouse is used."
        left = float(self._st(remaining, 0.0) or 0.0)
        if left > 0:
            return f"{what} in {duration_text(left)}"
        return ""

    @QtCore.Property(str, notify=statusChanged)
    def saverCountdownText(self) -> str:
        return self._countdown(
            "Screen saver",
            bool(self.saverOn),
            str(self.saverProblemText),
            "saver_fired",
            "saver_remaining_s",
        )

    @QtCore.Property(str, notify=statusChanged)
    def offCountdownText(self) -> str:
        return self._countdown(
            "Power off displays",
            bool(self.offOn),
            str(self.offProblemText),
            "off_fired",
            "off_remaining_s",
        )

    @QtCore.Property(str, notify=statusChanged)
    def wakeText(self) -> str:
        """S20: while keeping the displays off, or after, how often Windows
        turned them back on in this (or the last) idle period."""
        if not self.enabled:
            return ""
        wakes = int(self._st("wakes", 0) or 0)
        if wakes <= 0:
            return ""
        times = "once" if wakes == 1 else f"{wakes} times"
        return (
            f"Windows turned the displays back on {times}: devices that never "
            "go quiet (see Refresh Devices)."
        )

    @QtCore.Property(str, notify=statusChanged)
    def problemText(self) -> str:
        """The problem that stops both timers (not listening, S9)."""
        if not self.enabled:
            return ""
        return _problem_text(str(self._st("problem", "") or ""))

    @QtCore.Property(str, notify=statusChanged)
    def saverProblemText(self) -> str:
        if not (self.enabled and self.saverOn):
            return ""
        return _saver_problem_text(str(self._st("saver_problem", "") or ""))

    @QtCore.Property(str, notify=statusChanged)
    def offProblemText(self) -> str:
        if not (self.enabled and self.offOn):
            return ""
        return _off_problem_text(str(self._st("off_problem", "") or ""))

    # The status table (items 1-3, 10, 13) -----------------------------------

    @QtCore.Property(list, notify=statusChanged)
    def statusRows(self) -> list:
        """The window's status table: {"label", "value", "detail", "tone"}
        per row ("" | "ok" | "warn"), in the order Listener, Your idle time,
        Windows' idle time, Screen saver, Power off displays, Wake-ups, Hold,
        Last time away, Devices back on."""

        def row(label: str, value: str, detail: str = "", tone: str = "") -> dict:
            return {"label": label, "value": value, "detail": detail, "tone": tone}

        enabled = self.enabled
        rows = [
            self._listener_row(row),
            self._idle_row(row),
            self._windows_idle_row(row),
            self._timer_row(
                row, "Screen saver", bool(self.saverOn), "saverCountdownText"
            ),
            self._off_row(row),
            self._wakes_row(row),
            self._hold_row(row),
            self._away_row(row),
            self._devices_back_row(row),
        ]
        if not enabled:
            # A device still switched off matters whether or not the mode is on.
            for r in rows[:-1]:
                r["tone"] = ""
        return rows

    def _listener_row(self, row: Callable[..., dict]) -> dict:
        if not self.enabled:
            return row("Listener", "off")
        if self.listening:
            return row("Listener", "listening to the keyboard and mouse", "", "ok")
        return row(
            "Listener",
            "not listening to the keyboard and mouse",
            self.problemText,
            "warn",
        )

    def _idle_row(self, row: Callable[..., dict]) -> dict:
        idle = duration_text(float(self._st("idle_s", 0.0) or 0.0))
        detail = str(self.lastResetText)
        return row(
            "Your idle time", idle, detail[0].upper() + detail[1:] if detail else ""
        )

    def _windows_idle_row(self, row: Callable[..., dict]) -> dict:
        win = float(self._st("windows_idle_s", 0.0) or 0.0)
        own = float(self._st("idle_s", 0.0) or 0.0)
        detail = ""
        if self.enabled and own >= 10 and win < 2:
            detail = "devices are keeping Windows awake"
        return row("Windows' idle time", duration_text(win), detail)

    def _timer_row(
        self, row: Callable[..., dict], what: str, on: bool, countdown: str
    ) -> dict:
        if not (self.enabled and on):
            return row(what, "off")
        problem = (
            self.saverProblemText if what == "Screen saver" else self.offProblemText
        )
        if self.problemText or problem:
            return row(what, str(self.problemText or problem), "", "warn")
        if self.holdText:
            return row(what, "on hold")
        text = str(self.property(countdown) or "")
        if text.startswith(what + " "):
            text = text[len(what) + 1 :]
        return row(what, text or "waiting for the idle time")

    def _off_row(self, row: Callable[..., dict]) -> dict:
        if self.enabled and self.offOn and bool(self._st("waiting_for_devices", False)):
            return row("Power off displays", "switching devices off…")
        return self._timer_row(
            row, "Power off displays", bool(self.offOn), "offCountdownText"
        )

    def _wakes_row(self, row: Callable[..., dict]) -> dict:
        wakes = int(self._st("wakes", 0) or 0)
        if not self.enabled or wakes <= 0:
            return row("Wake-ups", "none this time")
        times = "once" if wakes == 1 else f"{wakes} times"
        if wakes >= WAKES_HINT_AT:
            return row(
                "Wake-ups",
                f"Windows turned the displays back on {times}",
                "a device may need to be Automatic (see Devices)",
                "warn",
            )
        return row("Wake-ups", f"Windows turned the displays back on {times}")

    def _hold_row(self, row: Callable[..., dict]) -> dict:
        text = self.holdText
        return row("Hold", text, "", "warn") if text else row("Hold", "none")

    def _away_row(self, row: Callable[..., dict]) -> dict:
        away = self._st("last_away", None)
        if not isinstance(away, dict):
            return row("Last time away", "none yet")
        return row("Last time away", *_last_away_text(away, len(self._pending_devices)))

    def _devices_back_row(self, row: Callable[..., dict]) -> dict:
        names = self._pending_devices
        if not names:
            return row("Devices back on", "all back on", "", "ok")
        who = names[0] if len(names) == 1 else f"{len(names)} devices"
        return row("Devices back on", f"{who} is still switched off", "", "warn")

    @QtCore.Property(bool, notify=statusChanged)
    def devicesBackRetry(self) -> bool:
        """Show Try again on the Devices back on row."""
        return bool(self._pending_devices)

    @QtCore.Slot()
    def retryDevices(self) -> None:
        """S23: Try again on the Devices back on row: the enable path runs
        once more."""
        _trace("Devices back on: Try again pressed")
        try:
            _disabler().enable_pending()
        except Exception:
            _log.exception("Screen Saver Mode: enabling the devices again failed")
        self.refreshStatus()

    # The helper (S25, S26) ----------------------------------------------------

    @QtCore.Property(str, notify=statusChanged)
    def helperMessage(self) -> str:
        """S26: "Devices can't be disabled: the helper isn't running" while
        the helper should run and doesn't; "" otherwise."""
        return self._helper_message

    @QtCore.Slot()
    def tryAgain(self) -> None:
        """S26's Try again: starts the helper once more."""
        try_again()
        self.refreshStatus()

    # Refresh Devices (S12) ---------------------------------------------------

    @QtCore.Property(bool, notify=busyChanged)
    def scanningDevices(self) -> bool:
        return self._scanning_devices

    @QtCore.Property(bool, notify=busyChanged)
    def scanningPrograms(self) -> bool:
        return self._scanning[PROGRAMS]

    @QtCore.Property(bool, notify=busyChanged)
    def scanningSystem(self) -> bool:
        return self._scanning[SYSTEM]

    @QtCore.Property(str, notify=busyChanged)
    def pendingIgnore(self) -> str:
        return self._pending_ignore

    @QtCore.Property(list, notify=devicesChanged)
    def devices(self) -> list:
        """The remembered devices: {"key", "name", "rate", "choice",
        "virtual", "found", "foundText"}."""
        return [_device_view(r) for r in self._devices]

    @QtCore.Property(str, notify=devicesChanged)
    def devicesSummary(self) -> str:
        """S12: the counts on Settings."""
        return devices_summary(self._devices)

    def _store_devices(self, rows: list[dict]) -> None:
        """Saves the list at once and shows it."""
        try:
            save_devices(rows)
            rows = saved_devices()
        except Exception:
            _log.exception("Screen Saver Mode: the Devices list could not be saved")
        self._devices = rows
        ensure_helper()
        snapshot_changed()

    @QtCore.Slot(str, str)
    def setDeviceChoice(self, key: str, choice: str) -> None:
        """S35: Automatic or Manual for a row; a virtual device is locked."""
        rows = saved_devices()
        hit = next((r for r in rows if r["key"] == key), None)
        if hit is None or hit["virtual"] or choice not in (AUTOMATIC, MANUAL):
            return
        if hit["choice"] == choice:
            return
        _trace(f"Devices: {hit['name']}, {choice}")
        hit["choice"] = choice
        self._store_devices(rows)
        self.devicesChanged.emit()

    @QtCore.Slot(str)
    def removeDevice(self, key: str) -> None:
        """S27: Remove forgets a row; found again, it is new."""
        rows = saved_devices()
        hit = next((r for r in rows if r["key"] == key), None)
        if hit is None:
            return
        _trace(f"Devices: {hit['name']}, removed")
        self._store_devices([r for r in rows if r is not hit])
        self.devicesChanged.emit()

    @QtCore.Property(str, notify=devicesChanged)
    def devicesMessage(self) -> str:
        return self._devices_message

    def _start(self, name: str, work: Callable[[], None]) -> bool:
        from gremlin import threads

        try:
            threads.start(name, work, stop=self._stop_work)
        except Exception:
            _log.exception(f"Screen Saver Mode: {name} could not start")
            return False
        return True

    def _stop_work(self, *_args: object) -> None:
        self._stop = True

    def _emit(self, sig: QtCore.SignalInstance, *args: object) -> None:
        try:
            sig.emit(*args)
        except RuntimeError:
            pass  # the window was closed

    @QtCore.Slot()
    def refreshDevices(self) -> None:
        if self._scanning_devices:
            _trace("Refresh Devices pressed: a check is already running")
            return
        _trace("Refresh Devices pressed")
        self._stop = False
        self._scanning_devices = True
        self.busyChanged.emit()

        def work() -> None:
            try:
                from gremlin import hid_report_scan

                found = hid_report_scan.scan(SCAN_SECONDS, lambda: self._stop)
                # Stopped early: nothing was checked, the list stays.
                result: Any = (
                    None
                    if self._stop
                    else [
                        (str(d.name), str(d.instance_id), float(d.reports_per_s))
                        for d in found
                    ]
                )
            except Exception as exc:
                _log.exception("Screen Saver Mode: Refresh Devices failed")
                result = f"The devices couldn't be checked: {exc}"
            self._emit(self._devicesDone, result)

        if not self._start("Screen Saver Mode devices", work):
            self._take_devices("The devices check couldn't start.")

    @QtCore.Slot(object)
    def _take_devices(self, result: object) -> None:
        self._scanning_devices = False
        if isinstance(result, str):
            # A failed check never loses the list (S27).
            self._devices_message = result
            _log.warning(f"Screen Saver Mode: {result}")
        elif isinstance(result, list):
            self._store_devices(merge_devices(saved_devices(), result))
            self._devices_message = checked_text(self._devices)
        _trace(f"Message shown: {self._devices_message}")
        self.busyChanged.emit()
        self.devicesChanged.emit()

    # Wake PC (S28-S31) ------------------------------------------------------

    @QtCore.Property(list, notify=wakeRowsChanged)
    def wakeRows(self) -> list:
        """The Wake PC rows: {"id", "name", "kinds" (text), "ticked",
        "note" (how it was ticked), "connected", "inUse" (S33)}."""
        return [_wake_view(r, r["id"] in self._in_use) for r in self._wake_rows]

    def _remerge(self) -> None:
        rows = merge_wake_rows(saved_wake_rows(), self._input_devices)
        if rows != self._wake_rows:
            self._wake_rows = rows
            self.wakeRowsChanged.emit()

    def _save_wake(self) -> None:
        """Saves the list; the core gets the ticked set (S28)."""
        try:
            changed = save_wake_rows(self._wake_rows)
        except Exception:
            _log.exception("Screen Saver Mode: the Wake PC list could not be saved")
            return
        self.wakeRowsChanged.emit()
        if changed:
            self._changed()

    def _find_wake(self, physical_id: str) -> dict | None:
        return next((r for r in self._wake_rows if r["id"] == physical_id), None)

    @QtCore.Slot(str, bool)
    def setWakeTicked(self, physical_id: str, ticked: bool) -> None:
        """A tick set or cleared by hand (S30: "ticked by you", "you
        unticked it")."""
        row = self._find_wake(str(physical_id))
        if row is None:
            return
        ticked = bool(ticked)
        _trace(
            f"Wake PC: {row['name'] or row['id']} "
            f"{'ticked' if ticked else 'unticked'} by hand"
        )
        row["ticked"] = ticked
        row["how"] = HOW_YOU if ticked else HOW_UNTICK
        self._save_wake()

    def _on_activity(self, physical_id: str) -> None:
        """S33: any input from a device while the tab is open (the core
        reports it on the main thread, at most twice a second per device)
        lights its row for IN_USE_S after the last one. Never ticks."""
        if not self._wake_open:
            return
        physical_id = str(physical_id or "").strip()
        if not physical_id or self._find_wake(physical_id) is None:
            return
        was = physical_id in self._in_use
        self._in_use[physical_id] = clock.monotonic() + IN_USE_S
        if not was:
            self.wakeRowsChanged.emit()
        if not self._in_use_timer.isActive():
            self._arm_in_use()

    def _arm_in_use(self) -> None:
        """Starts the one timer for the first row whose highlight ends."""
        if not self._in_use:
            self._in_use_timer.stop()
            return
        left = min(self._in_use.values()) - clock.monotonic()
        self._in_use_timer.start(max(50, int(left * 1000) + 1))

    @QtCore.Slot()
    def _expire_in_use(self) -> None:
        now = clock.monotonic()
        ended = [pid for pid, until in self._in_use.items() if until <= now]
        for pid in ended:
            del self._in_use[pid]
        if ended:
            self.wakeRowsChanged.emit()
        self._arm_in_use()

    def _clear_in_use(self) -> None:
        self._in_use_timer.stop()
        if self._in_use:
            self._in_use.clear()
            self.wakeRowsChanged.emit()

    def _on_press(self, physical_id: str, kind: str) -> None:
        """S30: a key or button pressed on a device while the tab is open
        (the core reports it on the main thread) ticks it. A device
        unticked by hand stays unticked: the click that unticks a mouse
        would tick it again."""
        if not self._wake_open:
            return
        physical_id = str(physical_id or "").strip()
        if not physical_id:
            return
        row = self._find_wake(physical_id)
        if row is not None:
            # S33: a press is input too.
            self._on_activity(physical_id)
        if row is None:
            # Not read yet: listed now, its name comes with the next read.
            row = {
                "id": physical_id,
                "name": "",
                "kinds": _kinds_of([kind]),
                "ticked": False,
                "how": "",
                "connected": True,
            }
            self._wake_rows.append(row)
            self._read_input_devices()
        if row["ticked"] or row["how"] == HOW_UNTICK:
            return
        row["ticked"] = True
        row["how"] = HOW_KEY if kind == "keyboard" else HOW_CLICK
        _trace(f"Wake PC: {row['name'] or row['id']} ticked by a {kind} press")
        self._save_wake()

    @QtCore.Slot(bool)
    def wakeTabOpen(self, is_open: bool) -> None:
        """The Wake PC tab shown or left (S30): presses are detected only
        while it is open; the device list is read when it opens and when
        a device is plugged in or out."""
        is_open = bool(is_open)
        if is_open == self._wake_open:
            return
        self._wake_open = is_open
        manager = None
        try:
            manager = _core().manager()
        except Exception:
            _log.exception("Screen Saver Mode: no manager for Wake PC")
        if is_open:
            _trace("Wake PC tab opened")
            if manager is not None:
                try:
                    manager.set_press_listener(self._on_press)
                    manager.set_activity_listener(self._on_activity)
                    if not manager.start_detection():
                        _log.warning(
                            "Screen Saver Mode: key and button presses can't "
                            "be detected for Wake PC"
                        )
                except Exception:
                    _log.exception("Screen Saver Mode: Wake PC detection failed")
            self._follow_devices(True)
            self._read_input_devices()
        else:
            _trace("Wake PC tab closed")
            if manager is not None:
                try:
                    manager.set_press_listener(None)
                    manager.set_activity_listener(None)
                    manager.stop_detection()
                except Exception:
                    _log.exception("Screen Saver Mode: Wake PC detection stop failed")
            self._follow_devices(False)
            self._clear_in_use()

    def _follow_devices(self, on: bool) -> None:
        """Re-reads the list when a device is plugged in or out, while the
        tab is open."""
        if on and self._device_signal is None:
            try:
                from gremlin import event_handler

                sig = event_handler.EventListener().device_change_event
                sig.connect(self._read_input_devices)
                self._device_signal = sig
            except Exception:
                _log.exception("Screen Saver Mode: no device change listener")
        elif not on and self._device_signal is not None:
            try:
                self._device_signal.disconnect(self._read_input_devices)
            except (RuntimeError, TypeError):
                pass
            self._device_signal = None

    @QtCore.Slot()
    def _read_input_devices(self) -> None:
        """Reads Windows' keyboards and mice on a program thread (never the
        main thread); one read at a time, one more if asked meanwhile."""
        if self._reading_inputs:
            self._read_again = True
            return
        self._reading_inputs = True
        self._read_again = False

        def work() -> None:
            try:
                result: Any = list(_core().WindowsApi().input_devices())
            except Exception:
                _log.exception("Screen Saver Mode: keyboards and mice not read")
                result = None
            self._emit(self._inputDevicesDone, result)

        if not self._start("Screen Saver Mode input devices", work):
            self._take_input_devices(None)

    @QtCore.Slot(object)
    def _take_input_devices(self, result: object) -> None:
        self._reading_inputs = False
        if isinstance(result, list):
            self._input_devices = result
            _trace(f"Wake PC: {len(result)} keyboards and mice found")
            self._remerge()
        if self._read_again and self._wake_open:
            self._read_input_devices()

    # Refresh Programs (S13), Refresh System (S17), Ignore (S14) ------------

    @QtCore.Property(list, notify=programsChanged)
    def programs(self) -> list:
        return list(self._rows[PROGRAMS])

    @QtCore.Property(str, notify=programsChanged)
    def programsMessage(self) -> str:
        return self._messages[PROGRAMS]

    @QtCore.Property(list, notify=systemChanged)
    def system(self) -> list:
        return list(self._rows[SYSTEM])

    @QtCore.Property(str, notify=systemChanged)
    def systemMessage(self) -> str:
        return self._messages[SYSTEM]

    def _changed_list(self, which: str) -> None:
        _ignored[which] = [
            str(r["name"]) for r in self._rows[which] if r.get("ignored")
        ]
        snapshot_changed()
        (self.programsChanged if which == PROGRAMS else self.systemChanged).emit()

    def _row(self, row: dict, name: str, kind: str) -> bool:
        return row["name"] == name and (not kind or row["kind"] == kind)

    def _list_of(self, name: str, kind: str) -> str:
        """Which list holds the row (Programs when neither does)."""
        for which in (PROGRAMS, SYSTEM):
            if any(self._row(r, name, kind) for r in self._rows[which]):
                return which
        return PROGRAMS

    @QtCore.Slot(str, result=bool)
    @QtCore.Slot(str, str, result=bool)
    def isIgnored(self, name: str, kind: str = "") -> bool:
        """Whether Windows has the row ignored, as last read or changed
        (kind "" matches any kind), in either list."""
        name, kind = str(name), str(kind or "")
        return any(
            self._row(r, name, kind) and r["ignored"]
            for rows in self._rows.values()
            for r in rows
        )

    @QtCore.Slot()
    def refreshPrograms(self) -> None:
        self._refresh(PROGRAMS)

    @QtCore.Slot()
    def refreshSystem(self) -> None:
        self._refresh(SYSTEM)

    def _refresh(self, which: str) -> None:
        """One button's own elevated check (its own administrator prompt):
        list_requests() once, its half of split() kept (S13, S17)."""
        words = _LISTS[which]
        if self._scanning[which]:
            _trace(f"{words['button']} pressed: a check is already running")
            return
        _trace(f"{words['button']} pressed")
        self._scanning[which] = True
        self.busyChanged.emit()

        def work() -> None:
            try:
                from gremlin import power_requests

                result: Any = power_requests.list_requests()
                if getattr(result, "ok", False):
                    halves = power_requests.split(list(result.programs))
                    result = (result, list(halves[words["half"]]))
            except Exception as exc:
                _log.exception(f"Screen Saver Mode: {words['button']} failed")
                result = f"The {words['what']} couldn't be listed: {exc}"
            self._emit(self._requestsDone, which, result)

        if not self._start(f"Screen Saver Mode {words['what']}", work):
            self._take_requests(which, f"The {words['what']} check couldn't start.")

    @QtCore.Slot(str, object)
    def _take_requests(self, which: str, result: object) -> None:
        words = _LISTS[which]
        self._scanning[which] = False
        if isinstance(result, str):
            self._messages[which] = result
            _log.warning(f"Screen Saver Mode: {result}")
        elif isinstance(result, tuple):
            self._rows[which] = [_program_row(p) for p in result[1]]
            self._messages[which] = (
                f"Checked {_clock_text()} · {words['kept']}"
                if self._rows[which]
                else f"Checked {_clock_text()} · {words['none']}"
            )
        else:
            # Refused: the window says so and nothing else happens (S13).
            self._messages[which] = str(
                getattr(result, "error", "")
                or f"The {words['what']} couldn't be listed."
            )
            _log.warning(
                f"Screen Saver Mode: {words['button']}: {self._messages[which]}"
            )
        _trace(f"Message shown: {self._messages[which]}")
        self.busyChanged.emit()
        self._changed_list(which)

    @QtCore.Slot(str, bool)
    @QtCore.Slot(str, bool, str)
    def setIgnored(self, name: str, ignored: bool, kind: str = KIND_PROCESS) -> None:
        """Ignore on/off for a row of any kind: a program (PROCESS), a
        driver or a service (S14); Windows checks the name."""
        name, kind = str(name), str(kind or KIND_PROCESS)
        _trace(f"Ignore {'on' if ignored else 'off'} pressed: {name} ({kind})")
        if self._pending_ignore:
            # One change at a time: the switch goes back.
            _trace(f"Ignore for {name} ({kind}) not sent: another change is running")
            self._changed_list(self._list_of(name, kind))
            return
        self._pending_ignore = name
        self.busyChanged.emit()

        def work() -> None:
            try:
                from gremlin import power_requests

                ok, error = power_requests.set_ignored(name, bool(ignored), kind=kind)
            except Exception as exc:
                _log.exception("Screen Saver Mode: Ignore failed")
                ok, error = False, str(exc)
            self._emit(
                self._ignoreDone, name, kind, bool(ignored), bool(ok), str(error or "")
            )

        if not self._start("Screen Saver Mode ignore", work):
            self._take_ignore(
                name, kind, bool(ignored), False, "The change couldn't start."
            )

    @QtCore.Slot(str, str, bool, bool, str)
    def _take_ignore(
        self, name: str, kind: str, ignored: bool, ok: bool, error: str
    ) -> None:
        self._pending_ignore = ""
        which = self._list_of(name, kind)
        if ok:
            for row in self._rows[which]:
                if self._row(row, name, kind):
                    row["ignored"] = ignored
            self._messages[which] = (
                f"{name} is ignored: {_LISTS[which]['ignored']}"
                if ignored
                else f"{name} is no longer ignored."
            )
        else:
            # The switch goes back to what Windows has and the window says
            # why (S14).
            self._messages[which] = error or "The change wasn't made."
            _log.warning(
                f"Screen Saver Mode: Ignore {'on' if ignored else 'off'} for "
                f"{name} ({kind}) failed: {self._messages[which]}"
            )
        _trace(f"Message shown: {self._messages[which]}")
        self.busyChanged.emit()
        self._changed_list(which)
