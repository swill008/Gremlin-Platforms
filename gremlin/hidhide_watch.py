# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""HidHide watch for control tracing (D-01-TRACE, contract item 7b-d).

While tracing is on and the HidHide row is ticked, every 5 s (and at once
on a device change): reads HidHide's real state (cloak, mode, app list,
device list), compares it with the last read and with the program's saved
setup, and checks every ticked stick is on the hidden list under its
current Windows instance path. A change the program made itself (the driver
tap marks it) is named "by Gremlin-Platforms"; any other is a HIDHIDE
warning. HidHide held by another program (its window open) gives one line
and is read again when free. Reading only; never raises.
"""

from __future__ import annotations

import logging
import threading
import uuid
from typing import Any

from gremlin import hidhide_driver, threads, trace

syslog = logging.getLogger("system")

INTERVAL = 5.0
DEVICE_CHANGE_DELAY = 0.5
PROGRAM = "Gremlin-Platforms"
CONTROL = "HidHide"

_lock = threading.Lock()
# Serialises check() (timer, device change, tests); waits are bounded.
_check_lock = threading.Lock()
_timer: threading.Timer | None = None
_running = False
# Bumped at every start and stop: a timer from an earlier run does nothing.
_run = 0
_connected = False
# The state read last (None before the first read of a watch run).
_last: dict | None = None
# Warnings standing now (key -> text): said once, again only after cleared.
_standing: dict[str, str] = {}
# HidHide device rows (list_hid_devices), read again after a device change.
_rows: list[dict] | None = None
# Game paths already warned about this watch run (D-02-INPUT-TESTER 9d).
_said_paths: set[str] = set()
# Programs (path, start) already warned as started before the last HidHide
# change this watch run (addendum 2026-10-10 item 4).
_said_stale: set[tuple[str, str]] = set()


# --- start / stop --------------------------------------------------------------


def running() -> bool:
    return _running


def _reset() -> None:
    global _last, _rows
    _last = None
    _rows = None
    _standing.clear()
    _said_paths.clear()
    _said_stale.clear()


def last_state() -> dict | None:
    """The state the watch read last (None before its first read)."""
    state = _last
    return dict(state) if state is not None else None


def start() -> None:
    global _running, _run
    with _lock:
        if _running:
            return
        _running = True
        _run += 1
        _reset()
        _schedule(0.0)
    _connect(True)


def stop() -> None:
    global _running, _timer, _run
    with _lock:
        _running = False
        _run += 1
        timer, _timer = _timer, None
    if timer is not None:
        timer.cancel()
    _connect(False)


def _schedule(delay: float = INTERVAL) -> None:
    global _timer
    # Caller holds _lock.
    _timer = threads.timer("HidHide watch", delay, _tick, _run)


def _tick(run: int) -> None:
    if run != _run:
        return
    _safe_check()
    with _lock:
        if _running and run == _run:
            _schedule()


def _on_change(*_args: object) -> None:
    if trace.enabled():
        start()
    else:
        stop()


def install() -> None:
    """Follows tracing on/off from now on (the watch runs while it is on).
    Safe to call again; never raises. HidHide is only read while tracing is
    on with the HidHide row ticked."""
    try:
        trace.on_change(_on_change)
        _on_change()
    except Exception:
        syslog.debug("HidHide watch not installed", exc_info=True)


def _connect(on: bool) -> None:
    global _connected
    try:
        from gremlin import event_handler

        signal = event_handler.EventListener().device_change_event
        if on and not _connected:
            signal.connect(device_changed)
            _connected = True
        elif not on and _connected:
            signal.disconnect(device_changed)
            _connected = False
    except Exception:
        syslog.debug("HidHide watch: device change hook failed", exc_info=True)


def device_changed(*_args: object) -> None:
    """A device came or went: the instance paths are read again and the
    sticks checked soon."""
    global _rows
    _rows = None
    if _running:
        threads.timer("HidHide watch (device change)", DEVICE_CHANGE_DELAY, _safe_check)


def _safe_check() -> None:
    try:
        check()
    except Exception:
        syslog.debug("HidHide watch failed", exc_info=True)


# --- Input Tester (D-02-INPUT-TESTER 9c, 9d) -------------------------------------


def tester_result(result: dict | None) -> None:
    """A new Input Tester result: one HIDHIDE line while tracing with the
    HidHide row (a warning on Fail)."""
    if not result or not trace.enabled() or not trace.hidhide_ticked():
        return
    from gremlin import input_tester_link

    text, fail = input_tester_link.result_text(result)
    if text:
        trace.hidhide(text, warning=fail)


def _check_game_paths() -> None:
    """A listed game's exe running from another folder: one warning per path."""
    from gremlin import process_paths
    from gremlin.ui import hidhide as hh

    games = hh._load_games()
    if not games:
        return
    for text in process_paths.game_path_problems(games, process_paths.running_images()):
        key = text.casefold()
        if key not in _said_paths:
            _said_paths.add(key)
            _warn(text)


def _check_stale_programs() -> None:
    """A program on the list (a game, the Input Tester) started before
    Gremlin's last HidHide change: one warning per process. Processes are
    only looked at when a change is known and something is listed, and only
    those with a listed exe name."""
    from gremlin import input_tester_link, process_paths
    from gremlin.ui import hidhide as hh

    change = input_tester_link.last_hidhide_change()
    if change is None:
        return
    listed = [str(g["path"]) for g in hh._load_games() if g.get("path")]
    if not listed:
        return
    stale = process_paths.started_before(
        process_paths.running_programs(listed), listed, change[0]
    )
    for path, start in stale:
        key = (path.casefold(), start.isoformat())
        if key not in _said_stale:
            _said_stale.add(key)
            _warn(process_paths.stale_text(path, start, change[0]))


def _what_changed(old: dict, new: dict) -> str:
    """"program list", "cloak", "hidden devices", "mode", or "settings" when
    more than one changed."""
    names = {
        "apps": "program list", "cloak": "cloak",
        "devices": "hidden devices", "inverse": "mode",
    }
    changed = [
        name for key, name in names.items()
        if old.get(key) is not None and new.get(key) is not None
        and (
            _upper(old[key]) != _upper(new[key]) if key in ("apps", "devices")
            else old[key] != new[key]
        )
    ]
    return changed[0] if len(changed) == 1 else "settings"


def _tell_tester(what: str = "settings") -> None:
    try:
        from gremlin import input_tester_link

        input_tester_link.hidhide_changed(what)
    except Exception:
        syslog.debug("HidHide watch: Input Tester not told", exc_info=True)


# --- the check -----------------------------------------------------------------


def _warn(text: str) -> None:
    trace.warn(trace.HIDHIDE, CONTROL, text)


def _said_by(program: bool) -> str:
    return f" by {PROGRAM}" if program else f" (not by {PROGRAM})"


def _upper(items: list[str] | None) -> set[str]:
    return {str(i).upper() for i in items or []}


def _tell(text: str, program: bool) -> None:
    if program:
        trace.hidhide(text)
    else:
        _warn(text)


def _compare_changes(old: dict, new: dict, marks: dict[str, object]) -> None:
    if (
        old["cloak"] is not None
        and new["cloak"] is not None
        and old["cloak"] != new["cloak"]
    ):
        by_us = marks.get("cloak") == new["cloak"]
        _tell(
            f"Cloak turned {'on' if new['cloak'] else 'off'}" + _said_by(by_us), by_us
        )
    if (
        old["inverse"] is not None
        and new["inverse"] is not None
        and old["inverse"] != new["inverse"]
    ):
        by_us = marks.get("inverse") == new["inverse"]
        _tell(
            f"mode changed to {hidhide_driver.mode_name(new['inverse'])}"
            + _said_by(by_us),
            by_us,
        )
    for key, list_name, name in (
        ("apps", "the list", hidhide_driver.app_name),
        ("devices", "the hidden list", str),
    ):
        if old[key] is None or new[key] is None:
            continue
        before, after = _upper(old[key]), _upper(new[key])
        if before == after:
            continue
        mark = marks.get(key)
        by_us = isinstance(mark, list) and _upper(mark) == after
        for item in old[key]:
            if item.upper() not in after:
                _tell(f"{name(item)} no longer on {list_name}" + _said_by(by_us), by_us)
        for item in new[key]:
            if item.upper() not in before:
                _tell(f"{name(item)} added to {list_name}" + _said_by(by_us), by_us)


def _saved_differences(state: dict) -> dict[str, str]:
    """Where HidHide differs from the setup the program saved (only while
    Gremlin control is on: otherwise the saved setup isn't applied)."""
    from gremlin.ui import hidhide as hh

    if not hh._hidhide_managed():
        return {}
    out: dict[str, str] = {}
    cloak = hh._saved_cloak()
    if cloak is not None and state["cloak"] is not None and cloak != state["cloak"]:
        out["saved-cloak"] = (
            f"Cloak is {'on' if state['cloak'] else 'off'}, but {PROGRAM} "
            f"has it saved {'on' if cloak else 'off'}"
        )
    block = hh._saved_block_list()
    if block is not None and state["inverse"] is not None and block != state["inverse"]:
        out["saved-mode"] = (
            f"HidHide is in {hidhide_driver.mode_name(state['inverse'])} mode, but "
            f"{PROGRAM} has {hidhide_driver.mode_name(block)} saved"
        )
    if state["apps"] is not None:
        on_list = {hidhide_driver.app_name(a).upper() for a in state["apps"]}
        for game in hh._load_games():
            exe = hidhide_driver.app_name(game["path"])
            if exe.upper() not in on_list:
                out["saved-app:" + exe.upper()] = (
                    f"{exe} is not on HidHide's app list (saved in {PROGRAM})"
                )
    if state["devices"] is not None:
        hidden = _upper(state["devices"])
        for item in hh._saved_hidden() or []:
            if item.upper() not in hidden:
                out["saved-device:" + item.upper()] = (
                    f"{item} is saved as hidden in {PROGRAM}, "
                    "but isn't on HidHide's list"
                )
    return out


def _stick(device_uuid: uuid.UUID) -> Any | None:  # noqa: ANN401
    from gremlin import device_initialization

    for dev in device_initialization.physical_devices():
        if dev.device_guid.uuid == device_uuid:
            return dev
    return None


def _stick_rows(dev: Any, rows: list[dict]) -> list[dict]:  # noqa: ANN401
    """HidHide's device rows for this stick: same VID/PID, narrowed by the
    HidHide window's link to the device name when two sticks match."""
    from gremlin.ui import hidhide as hh

    try:
        vid, pid = int(dev.vendor_id), int(dev.product_id)
    except (TypeError, ValueError, AttributeError):
        return []
    hits = []
    for row in rows:
        ids = row.get("instanceIds") or [row.get("instanceId")]
        if any(hidhide_driver._vid_pid(str(i)) == (vid, pid) for i in ids if i):
            hits.append(row)
    if len(hits) > 1:
        links = {k.upper(): v for k, v in hh._load_links().items()}
        named = [
            row
            for row in hits
            if any(
                links.get(str(i).upper()) == dev.name
                for i in row.get("instanceIds") or [row.get("instanceId")]
                if i
            )
        ]
        if named:
            hits = named
    return hits


def _not_hidden(devices: list[str] | None) -> dict[str, str]:
    """Each ticked stick that isn't on the hidden list under its current
    instance path."""
    global _rows
    if devices is None:
        return {}
    if _rows is None:
        _rows = hidhide_driver.list_hid_devices(True)
    hidden = _upper(devices)
    out: dict[str, str] = {}
    for device_uuid in trace.ticked_devices():
        dev = _stick(device_uuid)
        if dev is None:
            continue
        for row in _stick_rows(dev, _rows):
            ids = [
                str(i) for i in row.get("instanceIds") or [row.get("instanceId")] if i
            ]
            missing = [i for i in ids if i.upper() not in hidden]
            if missing:
                out[f"stick:{device_uuid}:{missing[0].upper()}"] = (
                    f"{dev.name} is NOT hidden: it is {missing[0]}, "
                    "which isn't on the list"
                )
                break
    return out


def _stand(now: dict[str, str]) -> None:
    """Says each standing warning once; a cleared one may be said again."""
    for key, text in now.items():
        if key not in _standing:
            _warn(text)
    _standing.clear()
    _standing.update(now)


def _summary(state: dict) -> str:
    def flag(value: object, yes: str, no: str) -> str:
        return "?" if value is None else (yes if value else no)

    apps = state["apps"]
    devices = state["devices"]
    return (
        f"HidHide now: cloak {flag(state['cloak'], 'on', 'off')}, "
        f"{flag(state['inverse'], 'Block list', 'Allow list')}, "
        f"{'?' if apps is None else len(apps)} apps, "
        f"{'?' if devices is None else len(devices)} hidden devices"
    )


def check() -> None:
    """One look at HidHide (the watch runs it every INTERVAL)."""
    global _last
    if not trace.enabled() or not trace.hidhide_ticked():
        _reset()
        return
    if not _check_lock.acquire(timeout=INTERVAL):
        return
    try:
        try:
            _check_game_paths()
        except Exception:
            syslog.debug("HidHide watch: game path check failed", exc_info=True)
        state = hidhide_driver.read_state()
        if state is None:
            if hidhide_driver.last_open_error() == hidhide_driver.ERROR_ACCESS_DENIED:
                if hidhide_driver.in_use_once():
                    trace.hidhide("HidHide in use by another program", warning=True)
            elif "missing" not in _standing:
                _standing["missing"] = ""
                trace.hidhide(f"HidHide {hidhide_driver.open_result()}")
            return
        _standing.pop("missing", None)
        marks = hidhide_driver.take_program_marks()
        if _last is None:
            trace.hidhide(_summary(state))
        else:
            _compare_changes(_last, state, marks)
        changed = _last is not None and _last != state
        what = _what_changed(_last, state) if changed and _last is not None else ""
        _last = state
        if changed:
            _tell_tester(what)
        try:
            _check_stale_programs()
        except Exception:
            syslog.debug("HidHide watch: start time check failed", exc_info=True)
        standing = _saved_differences(state)
        standing.update(_not_hidden(state["devices"]))
        _stand(standing)
    finally:
        _check_lock.release()
