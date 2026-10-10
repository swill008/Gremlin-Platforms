# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Control tracing (Live Log Reader › Trace, D-01-TRACE): while it is on,
each ticked control is followed from the driver (RAW) through the wiring
(WIRING) to the vJoy write (OUTPUT/BLOCKED), with EVENT, HIDHIDE and OUT OF
STEP lines. Lines go to an in-memory ring for the tab and to trace.log.

Tracing is always off at start and is never saved on; the ticks are saved.
Off, every tap costs one bool check and no file is opened. Nothing here
raises into the caller. Axis lines are rate limited like the Input Monitor:
at most one per axis_interval() (Axis lines: 1 to 10 per second), the latest
value in between kept and written when the stick goes still (AXIS_INTERVAL
without a change)."""

from __future__ import annotations

import collections
import json
import logging
import logging.handlers
import math
import pathlib
import threading
import time
import uuid
from collections.abc import Callable
from typing import Any

from gremlin import clock, threads

# Points.
RAW = "RAW"
WIRING = "WIRING"
OUTPUT = "OUTPUT"
BLOCKED = "BLOCKED"
EVENT = "EVENT"
HIDHIDE = "HIDHIDE"
OUT_OF_STEP = "OUT OF STEP"

MAX_LINES = 5000
AXIS_INTERVAL = 0.1
# The Axis lines choices, lines per second per axis (the first is the default).
AXIS_RATE_CHOICES = (10, 8, 6, 4, 3, 2, 1)
# What may be typed instead: lines per second, decimals too.
AXIS_RATE_RANGE = (0.1, 50.0)
FILE_NAME = "trace.log"
# The Max size choices for trace.log, in MB (the first is the default).
MAX_MB_CHOICES = (5, 10, 25, 50, 100, 250)
# What may be typed instead: whole MB.
MAX_MB_RANGE = (1, 1000)
FILE_BACKUPS = 1

KINDS = ("axis", "button", "hat")

_CFG_SECTION = "debug"
_CFG_GROUP = "trace"
_CFG_TICKS = "ticks"
_CFG_OOS = "out-of-step"
_CFG_HIDHIDE = "hidhide"
_CFG_MAX_MB = "max-mb"
_CFG_AXIS_RATE = "axis-rate"

_LOCK = threading.RLock()
_enabled = False
_since: float | None = None
_lines: collections.deque[tuple[str, str, str, str, bool]] = collections.deque(
    maxlen=MAX_LINES
)
_version = 0
_notice = ""
_hooks: list[Callable[[], None]] = []

# Ticks: device uuid -> {"axis": set, "button": set, "hat": set, "all": bool}.
_ticks: dict[uuid.UUID, dict[str, Any]] | None = None
_oos: set[uuid.UUID] = set()
_hidhide_on = False

# Axis rate limit: key -> time last written; pending (line, arrival, count).
_axis_last: dict[tuple[Any, ...], float] = {}
_axis_pending: dict[tuple[Any, ...], tuple[str, str, str, float, int]] = {}
_flush_timer: threading.Timer | None = None

_last_raw: dict[tuple[Any, ...], tuple[float, float]] = {}
_last_written: dict[tuple[int, str, int], tuple[float, float]] = {}

_local = threading.local()

_logger: logging.Logger | None = None
_handler: logging.handlers.RotatingFileHandler | None = None


# --- state -----------------------------------------------------------------


def enabled() -> bool:
    return _enabled


def set_enabled(on: bool) -> None:
    """Turns tracing on or off (never saved). Writes an EVENT line and runs
    the on_change hooks."""
    global _enabled, _since
    on = bool(on)
    with _LOCK:
        if on == _enabled:
            return
        if on:
            axis_rate()
            _open_file()
            _since = clock.now()
            _enabled = True
            _add(EVENT, "", "Tracing on")
        else:
            _flush_pending(still=True)
            _add(EVENT, "", "Tracing off")
            _enabled = False
            _since = None
            _cancel_flush()
    for hook in list(_hooks):
        try:
            hook()
        except Exception:
            logging.getLogger("system").exception("Trace on_change hook failed")


def since() -> float | None:
    return _since


def on_change(callback: Callable[[], None]) -> None:
    """callback() runs after tracing turns on or off."""
    with _LOCK:
        if callback not in _hooks:
            _hooks.append(callback)


# --- ticks -----------------------------------------------------------------


def _key(device_uuid: object) -> uuid.UUID | None:
    uid = getattr(device_uuid, "uuid", device_uuid)
    if isinstance(uid, uuid.UUID):
        return uid
    try:
        return uuid.UUID(str(uid))
    except (ValueError, TypeError, AttributeError):
        return None


def _empty() -> dict[str, Any]:
    return {"axis": set(), "button": set(), "hat": set(), "all": False}


def _ensure_options() -> None:
    from gremlin import config
    from gremlin.types import PropertyType

    cfg = config.Configuration()
    for name, kind, initial, text, props in (
        (_CFG_TICKS, PropertyType.String, "{}",
         "Trace: ticked controls per device.", {}),
        (_CFG_OOS, PropertyType.String, "[]",
         "Trace: devices with the out-of-step check.", {}),
        (_CFG_HIDHIDE, PropertyType.String, "",
         "Trace: HidHide row ticked (on or empty).", {}),
        (_CFG_MAX_MB, PropertyType.Int, MAX_MB_CHOICES[0],
         "Trace: trace.log max size in MB.",
         {"min": MAX_MB_RANGE[0], "max": MAX_MB_RANGE[1]}),
        (_CFG_AXIS_RATE, PropertyType.Float, float(AXIS_RATE_CHOICES[0]),
         "Trace: axis lines per second.",
         {"min": AXIS_RATE_RANGE[0], "max": AXIS_RATE_RANGE[1]}),
    ):
        # Always registered, a saved value too: purge_unused at start drops
        # what isn't registered (the ticks would not survive a restart).
        cfg.register(
            _CFG_SECTION, _CFG_GROUP, name, kind, initial, text, props, False
        )


def _load() -> dict[uuid.UUID, dict[str, Any]]:
    """The tick cache, read from the config once."""
    global _ticks, _hidhide_on
    if _ticks is not None:
        return _ticks
    ticks: dict[uuid.UUID, dict[str, Any]] = {}
    oos: set[uuid.UUID] = set()
    hh = False
    try:
        from gremlin import config

        _ensure_options()
        cfg = config.Configuration()
        data = json.loads(str(cfg.value(_CFG_SECTION, _CFG_GROUP, _CFG_TICKS) or "{}"))
        if isinstance(data, dict):
            for dev, row in data.items():
                uid = _key(dev)
                if uid is None or not isinstance(row, dict):
                    continue
                entry = _empty()
                for kind in KINDS:
                    entry[kind] = {
                        int(i)
                        for i in row.get(kind, [])
                        if str(i).lstrip("-").isdigit()
                    }
                entry["all"] = bool(row.get("all"))
                ticks[uid] = entry
        rows = json.loads(str(cfg.value(_CFG_SECTION, _CFG_GROUP, _CFG_OOS) or "[]"))
        if isinstance(rows, list):
            oos = {u for r in rows if (u := _key(r)) is not None}
        hh = str(cfg.value(_CFG_SECTION, _CFG_GROUP, _CFG_HIDHIDE) or "") == "on"
    except Exception:
        logging.getLogger("system").exception("Could not read the trace ticks")
    _ticks = ticks
    _oos.clear()
    _oos.update(oos)
    _hidhide_on = hh
    return ticks


def _save() -> None:
    try:
        from gremlin import config

        _ensure_options()
        cfg = config.Configuration()
        data = {
            str(uid): {
                **{kind: sorted(row[kind]) for kind in KINDS},
                "all": bool(row["all"]),
            }
            for uid, row in (_ticks or {}).items()
            if row["all"] or any(row[k] for k in KINDS)
        }
        cfg.set(_CFG_SECTION, _CFG_GROUP, _CFG_TICKS, json.dumps(data, sort_keys=True))
        cfg.set(
            _CFG_SECTION, _CFG_GROUP, _CFG_OOS, json.dumps(sorted(str(u) for u in _oos))
        )
        cfg.set(_CFG_SECTION, _CFG_GROUP, _CFG_HIDHIDE, "on" if _hidhide_on else "")
    except Exception:
        logging.getLogger("system").exception("Could not save the trace ticks")


def ticked(device_uuid: object, kind: str, index: int) -> bool:
    try:
        row = _load().get(_key(device_uuid))  # type: ignore[arg-type]
        if row is None:
            return False
        return bool(row["all"]) or index in row.get(kind, ())
    except Exception:
        return False


def device_ticks(device_uuid: object) -> dict[str, Any]:
    with _LOCK:
        row = _load().get(_key(device_uuid))  # type: ignore[arg-type]
        if row is None:
            return _empty()
        return {k: set(row[k]) for k in KINDS} | {"all": bool(row["all"])}


def set_tick(device_uuid: object, kind: str, index: int, on: bool) -> None:
    uid = _key(device_uuid)
    if uid is None or kind not in KINDS:
        return
    with _LOCK:
        row = _load().setdefault(uid, _empty())
        if on:
            row[kind].add(int(index))
        else:
            row[kind].discard(int(index))
            row["all"] = False
        _save()


def set_device(device_uuid: object, on: bool) -> None:
    """A device tick: all its controls on, or every tick of it off."""
    uid = _key(device_uuid)
    if uid is None:
        return
    with _LOCK:
        ticks = _load()
        if on:
            ticks.setdefault(uid, _empty())["all"] = True
        else:
            ticks.pop(uid, None)
        _save()


def oos_ticked(device_uuid: object) -> bool:
    _load()
    return _key(device_uuid) in _oos


def set_oos(device_uuid: object, on: bool) -> None:
    uid = _key(device_uuid)
    if uid is None:
        return
    with _LOCK:
        _load()
        if on:
            _oos.add(uid)
        else:
            _oos.discard(uid)
        _save()


def hidhide_ticked() -> bool:
    _load()
    return _hidhide_on


def set_hidhide(on: bool) -> None:
    global _hidhide_on
    with _LOCK:
        _load()
        _hidhide_on = bool(on)
        _save()


def ticked_devices() -> list[uuid.UUID]:
    with _LOCK:
        return [
            uid
            for uid, row in _load().items()
            if row["all"] or any(row[k] for k in KINDS)
        ]


def _reset_for_tests() -> None:
    """Turns tracing off (hooks run) and forgets the tick cache, lines and
    file (tests only). on_change hooks are kept."""
    global _ticks, _enabled, _since, _notice, _version, _logger, _handler, _max_mb
    global _axis_rate, _axis_interval
    set_enabled(False)
    with _LOCK:
        _cancel_flush()
        _ticks = None
        _max_mb = None
        _axis_rate = None
        _axis_interval = AXIS_INTERVAL
        _oos.clear()
        _enabled = False
        _since = None
        _notice = ""
        _lines.clear()
        _version += 1
        _axis_last.clear()
        _axis_pending.clear()
        _last_raw.clear()
        _last_written.clear()
        if _handler is not None and _logger is not None:
            _logger.removeHandler(_handler)
            _handler.close()
        _handler = None
        _logger = None


# --- writing ---------------------------------------------------------------


def _stamp(t: float | None = None) -> str:
    t = clock.now() if t is None else t
    return time.strftime("%H:%M:%S", time.localtime(t)) + f".{int(t * 1000) % 1000:03d}"


def _add(
    point: str, control: str, detail: str, warning: bool = False, t: float | None = None
) -> None:
    """Appends one line (caller holds _LOCK or doesn't need ordering)."""
    global _version
    line = (_stamp(t), control, point, detail, warning)
    with _LOCK:
        _lines.append(line)
        _version += 1
    if _logger is not None:
        try:
            text = f"{line[0]}  {control or '-'}  {point}  {detail}"
            _logger.log(logging.WARNING if warning else logging.INFO, text)
        except Exception:
            pass


def _value_text(kind: str, value: object, raw_value: object = None) -> str:
    if kind == "axis" and isinstance(value, (int, float)):
        text = f"{float(value):+.3f}"
        if raw_value is not None:
            text = f"raw {raw_value}  calibrated {text}"
        return text
    if kind == "button":
        return "pressed" if value else "released"
    return str(value)


def raw(
    device_uuid: object,
    kind: str,
    index: int,
    value: object,
    raw_value: object = None,
    label: str = "",
) -> None:
    """The value as received from the driver; axes rate limited."""
    if not _enabled:
        return
    try:
        if not ticked(device_uuid, kind, index):
            return
        now = clock.monotonic()
        uid = _key(device_uuid)
        key = (uid, kind, int(index))
        if isinstance(value, (int, float)):
            _last_raw[key] = (float(value), clock.now())
        control = label or control_label(device_uuid, kind, index)
        detail = _value_text(kind, value, raw_value)
        with _LOCK:
            if kind == "axis":
                if now - _axis_last.get(key, 0.0) < _axis_interval:
                    count = _axis_pending[key][4] + 1 if key in _axis_pending else 1
                    _axis_pending[key] = (control, detail, _stamp(), now, count)
                    _schedule_flush()
                    return
                pending = _axis_pending.pop(key, None)
                _axis_last[key] = now
                if pending is not None and pending[4] > 1:
                    detail += f"  ({pending[4] - 1} values between)"
            _add(RAW, control, detail)
    except Exception:
        pass


def _schedule_flush() -> None:
    global _flush_timer
    if _flush_timer is not None and _flush_timer.is_alive():
        return
    try:
        _flush_timer = threads.timer("trace axis flush", AXIS_INTERVAL, _on_flush)
    except Exception:
        _flush_timer = None


def _cancel_flush() -> None:
    global _flush_timer
    if _flush_timer is not None:
        try:
            _flush_timer.cancel()
        except Exception:
            pass
    _flush_timer = None


def _on_flush() -> None:
    global _flush_timer
    try:
        with _LOCK:
            _flush_timer = None
            if not _enabled:
                _axis_pending.clear()
                return
            _flush_pending(still=False)
            if _axis_pending:
                _schedule_flush()
    except Exception:
        pass


def _flush_pending(still: bool) -> None:
    """Writes pending axis values: when the stick has been still for an
    interval (or still is True) and the interval since the last line passed."""
    now = clock.monotonic()
    for key, (control, detail, _stamp_text, arrived, count) in list(
        _axis_pending.items()
    ):
        quiet = still or now - arrived >= AXIS_INTERVAL
        if quiet:
            text = detail + "  (last value; stick still)"
        elif now - _axis_last.get(key, 0.0) >= _axis_interval:
            text = detail
        else:
            continue
        if count > 1:
            text += f"  ({count - 1} values between)"
        del _axis_pending[key]
        _axis_last[key] = now
        _add(RAW, control, text)


def wiring(
    device_uuid: object, kind: str, index: int, text: str, label: str = ""
) -> None:
    if not _enabled:
        return
    try:
        if ticked(device_uuid, kind, index):
            _add(WIRING, label or control_label(device_uuid, kind, index), str(text))
    except Exception:
        pass


def begin_input(device_uuid: object, kind: str, index: int) -> None:
    if not _enabled:
        return
    try:
        _local.current = (_key(device_uuid), kind, int(index))
    except Exception:
        pass


def end_input() -> None:
    try:
        _local.current = None
    except Exception:
        pass


def current_input() -> tuple[Any, ...] | None:
    return getattr(_local, "current", None)


_KIND_TEXT = {"axis": "axis", "button": "Button", "hat": "Hat"}


def output(vjoy_id: int, kind: str, index: int, value: object, result: str) -> None:
    """A vJoy write and its result; logged only for a ticked current input.
    "written" also records the value for the out-of-step watch."""
    if not _enabled:
        return
    try:
        if result == "written" and isinstance(value, (int, float)):
            _last_written[(int(vjoy_id), kind, int(index))] = (
                float(value),
                clock.now(),
            )
        cur = current_input()
        if cur is None or not ticked(cur[0], cur[1], cur[2]):
            return
        if kind == "axis":
            from gremlin import common
            from gremlin.types import InputType

            try:
                text = common.input_to_ui_string(InputType.JoystickAxis, int(index))
                name = "axis " + text.removesuffix(" Axis").strip()
            except Exception:
                name = f"axis {index}"
        else:
            name = f"{_KIND_TEXT.get(kind, kind)} {index}"
        head = result.split(" ")[0].rstrip(":") if result else ""
        point = BLOCKED if head in ("blocked", "missing") else OUTPUT
        shown = (
            f"{float(value):+.3f}"
            if kind == "axis" and isinstance(value, (int, float))
            else str(value)
        )
        _add(
            point,
            control_label(cur[0], cur[1], cur[2]),
            f"vJoy {vjoy_id} {name} = {shown} · {result}",
        )
    except Exception:
        pass


def mouse(text: str) -> None:
    """A Map to Mouse output (06 S86, G-c): one line per change (motion set
    or stopped, a button pressed or released), never per motion tick; logged
    only for a ticked current input, like a vJoy write."""
    if not _enabled:
        return
    try:
        cur = current_input()
        if cur is None or not ticked(cur[0], cur[1], cur[2]):
            return
        _add(OUTPUT, control_label(cur[0], cur[1], cur[2]), str(text))
    except Exception:
        pass


def last_written(vjoy_id: int, kind: str, index: int) -> tuple[float, float] | None:
    return _last_written.get((int(vjoy_id), kind, int(index)))


def rested(vjoy_ids: object) -> None:
    """These vJoy devices were put at rest when released (06 S17: Stop, a
    restart, a device re-read): rest is what was last written (S86), so the
    out-of-step watch compares with it, not the profile's last value."""
    try:
        ids = {int(i) for i in vjoy_ids}  # type: ignore[union-attr]
        now = clock.now()
        with _LOCK:
            for key in list(_last_written):
                if key[0] in ids:
                    _last_written[key] = (0.0, now)
    except Exception:
        pass


def last_raw(device_uuid: object, kind: str, index: int) -> tuple[float, float] | None:
    return _last_raw.get((_key(device_uuid), kind, int(index)))


def event(text: str) -> None:
    if not _enabled:
        return
    try:
        _add(EVENT, "", str(text))
    except Exception:
        pass


def hidhide(text: str, warning: bool = False) -> None:
    global _notice
    if not _enabled:
        return
    try:
        _add(HIDHIDE, "HidHide", str(text), warning)
        if warning:
            _notice = f"HidHide: {text}"
    except Exception:
        pass


def warn(point: str, control: str, text: str) -> None:
    """A warning line; it raises the notice at the top of the tab."""
    global _notice
    if not _enabled:
        return
    try:
        _add(point, control, str(text), True)
        _notice = f"{control}: {text}" if control else str(text)
    except Exception:
        pass


def notice() -> str:
    return _notice


def clear_notice() -> None:
    global _notice, _version
    with _LOCK:
        _notice = ""
        _version += 1


# --- view ------------------------------------------------------------------


def lines() -> list[tuple[str, str, str, str, bool]]:
    with _LOCK:
        return list(_lines)


def version() -> int:
    return _version


def clear_view() -> None:
    """Empties the ring only; the file is untouched."""
    global _version
    with _LOCK:
        _lines.clear()
        _version += 1


def file_path() -> pathlib.Path:
    try:
        from gremlin import util

        return pathlib.Path(util.logs_dir()) / FILE_NAME
    except Exception:
        return pathlib.Path(FILE_NAME)


def file_size() -> int:
    try:
        return file_path().stat().st_size
    except OSError:
        return 0


_max_mb: int | None = None
_axis_rate: float | None = None
_axis_interval = AXIS_INTERVAL

MAX_MB_TEXT = "Max size is 1 to 1000 MB"
AXIS_RATE_TEXT = "Axis lines is 0.1 to 50 per second"


def _number(text: object) -> float | None:
    try:
        value = float(str(text).strip())
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _saved(name: str) -> object:
    try:
        from gremlin import config

        _ensure_options()
        return config.Configuration().value(_CFG_SECTION, _CFG_GROUP, name)
    except Exception:
        return None


def _save_value(name: str, value: object) -> None:
    try:
        from gremlin import config

        _ensure_options()
        config.Configuration().set(_CFG_SECTION, _CFG_GROUP, name, value)
    except Exception:
        logging.getLogger("system").exception("Could not save the trace %s", name)


def axis_rate() -> float:
    """Axis lines per second per axis (AXIS_RATE_RANGE), read once."""
    global _axis_rate, _axis_interval
    if _axis_rate is None:
        value = _number(_saved(_CFG_AXIS_RATE))
        low, high = AXIS_RATE_RANGE
        if value is None or not low <= value <= high:
            value = float(AXIS_RATE_CHOICES[0])
        _axis_rate = value
        _axis_interval = 1.0 / value
    return _axis_rate


def set_axis_rate(rate: object) -> str:
    """Saves the Axis lines rate (0.1 to 50 per second, decimals too) and
    applies it at once. Returns "" or why it was refused (nothing changes)."""
    global _axis_rate, _axis_interval
    value = _number(rate)
    low, high = AXIS_RATE_RANGE
    if value is None or not low <= value <= high:
        return AXIS_RATE_TEXT
    value = round(value, 3)
    _save_value(_CFG_AXIS_RATE, value)
    with _LOCK:
        _axis_rate = value
        _axis_interval = 1.0 / value
    return ""


def max_mb() -> int:
    """trace.log's max size in MB (MAX_MB_RANGE), read once."""
    global _max_mb
    if _max_mb is None:
        value = _number(_saved(_CFG_MAX_MB))
        low, high = MAX_MB_RANGE
        if value is None or value != int(value) or not low <= value <= high:
            value = MAX_MB_CHOICES[0]
        _max_mb = int(value)
    return _max_mb


def set_max_mb(mb: object) -> str:
    """Saves the max size (1 to 1000 MB, whole numbers) and applies it at
    once, also while tracing is on (a file already over it rolls over at the
    next line). Returns "" or why it was refused (nothing changes)."""
    global _max_mb
    value = _number(mb)
    low, high = MAX_MB_RANGE
    if value is None or value != int(value) or not low <= value <= high:
        return MAX_MB_TEXT
    _save_value(_CFG_MAX_MB, int(value))
    with _LOCK:
        _max_mb = int(value)
        if _handler is not None:
            _handler.maxBytes = _max_mb * 1024 * 1024
    return ""


def clear_file() -> str:
    """Empties trace.log, deletes trace.log.1 and clears the view. Returns ""
    when done, else the file and the reason (nothing else changes then).
    Works while tracing is on: the handler's stream is closed first so the
    next line starts at the top of the empty file."""
    path = file_path()
    older = path.with_name(FILE_NAME + ".1")
    with _LOCK:
        handler = _handler
        if handler is not None:
            handler.acquire()
        try:
            if handler is not None and handler.stream is not None:
                try:
                    handler.stream.close()
                except OSError:
                    pass
                # FileHandler reopens (append) on the next line.
                handler.stream = None  # type: ignore[assignment]
            try:
                if path.exists():
                    with open(path, "w", encoding="utf-8"):
                        pass
            except OSError as error:
                return f"{path}: {error.strerror or error}"
            try:
                older.unlink(missing_ok=True)
            except OSError as error:
                return f"{older}: {error.strerror or error}"
        finally:
            if handler is not None:
                handler.release()
        clear_view()
    event("Trace file cleared")
    return ""


def _open_file() -> None:
    """Opens trace.log on the first turn-on."""
    global _logger, _handler
    if _handler is not None:
        return
    try:
        path = file_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.handlers.RotatingFileHandler(
            path,
            maxBytes=max_mb() * 1024 * 1024,
            backupCount=FILE_BACKUPS,
            encoding="utf-8",
        )
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger = logging.getLogger("trace")
        logger.propagate = False
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)
        _handler, _logger = handler, logger
    except Exception:
        logging.getLogger("system").exception("Could not open the trace file")


def control_label(device_uuid: object, kind: str, index: int) -> str:
    """Short device name plus "Axis n" / "Button n" / "Hat n"."""
    try:
        from gremlin import input_monitor

        name = input_monitor.device_name(_key(device_uuid) or device_uuid)  # type: ignore[arg-type]
    except Exception:
        name = "Unknown device"
    return f"{name} {_KIND_TEXT.get(kind, kind).capitalize()} {index}"
