# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Gremlin's side of the Input Tester (D-02-INPUT-TESTER, contract 5, 9).

Finds and starts the tester (Tools › Input Tester…), writes what Gremlin
expects it to see to <data>\\tester\\expected.json, and while a tester it
started runs: writes the file again on a device or HidHide change and
watches result.json (resultChanged). Gremlin's last HidHide change (time and
what) is kept here and written to expected.json (hidhide_changed_at,
hidhide_change) so a tester started before it can say to restart. HidHide is
only read here, never written; the driver is read only while Gremlin
control is on, otherwise the watch's last read or the saved setup is used.
"""

from __future__ import annotations

import json
import logging
import ntpath
import os
import re
import subprocess
import sys
import threading
import uuid
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6 import QtCore

import gremlin.ui.type_aliases as ta
from gremlin import threads

QML_IMPORT_NAME = "Gremlin.UI"
QML_IMPORT_MAJOR_VERSION = 1

syslog = logging.getLogger("system")

TESTER_EXE = "Gremlin Input Tester.exe"
TESTER_FOLDER = "Gremlin Input Tester"
NOT_BUILT = (
    "The Input Tester isn't built. From the program folder run: "
    "python tools/build_input_tester.py"
)
POLL = 1.0
VJOY_VID, VJOY_PID = 0x1234, 0xBEAD


# --- where things are ------------------------------------------------------------


def tester_path() -> Path | None:
    """The tester exe: next to the program when installed, the dev build in
    dist/ from source. None when it isn't there."""
    if getattr(sys, "frozen", False):
        path = Path(sys.executable).resolve().parent / TESTER_EXE
    else:
        path = Path(__file__).resolve().parents[1] / "dist" / TESTER_FOLDER / TESTER_EXE
    return path if path.is_file() else None


def _expected_tester_path() -> Path:
    """Where the tester is (or would be once built)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / TESTER_EXE
    return Path(__file__).resolve().parents[1] / "dist" / TESTER_FOLDER / TESTER_EXE


def gremlin_dir() -> Path:
    """The folder passed as --gremlin-dir (the user data folder)."""
    from gremlin import util

    return Path(util.data_folder())


def tester_dir() -> Path:
    return gremlin_dir() / "tester"


def expected_file() -> Path:
    return tester_dir() / "expected.json"


def result_file() -> Path:
    return tester_dir() / "result.json"


# --- expected.json -------------------------------------------------------------------


def _key(path: str) -> str:
    return ntpath.normcase(ntpath.normpath(str(path).strip()))


def _app_is(app: str, path: str) -> bool:
    """True when a HidHide app entry (DOS or volume path) is this file."""
    if not app or not path:
        return False
    a, p = _key(app), _key(path)
    if a == p:
        return True
    # HidHide keeps \Device\HarddiskVolumeN\...: compare past the drive.
    rest = ntpath.splitdrive(p)[1]
    return bool(rest) and a.startswith("\\device\\") and a.endswith(rest)


def _hidhide_state() -> dict[str, Any]:
    """cloak, inverse (True = Block list), apps, devices; None where unknown.
    The driver is read only while Gremlin control is on; otherwise the
    watch's last read, then the saved setup."""
    from gremlin import hidhide_driver, hidhide_watch
    from gremlin.ui import hidhide as hh

    state: dict[str, Any] = {
        "cloak": None, "inverse": None, "apps": None, "devices": None, "read": False,
    }
    managed = False
    try:
        managed = hh._hidhide_managed()
    except Exception:
        syslog.debug("Input Tester: HidHide setup not read", exc_info=True)
    read: dict | None = None
    if managed:
        try:
            read = hidhide_driver.read_state()
        except Exception:
            read = None
    if read is None:
        read = hidhide_watch.last_state()
    if read is not None:
        state.update({k: read.get(k) for k in ("cloak", "inverse", "apps", "devices")})
        state["read"] = True
    try:
        if state["cloak"] is None:
            state["cloak"] = hh._saved_cloak()
        if state["inverse"] is None:
            state["inverse"] = hh._saved_block_list()
        if state["devices"] is None:
            state["devices"] = hh._saved_hidden()
        if state["apps"] is None:
            games = hh._load_games()
            state["apps"] = [g["path"] for g in games] if games else None
    except Exception:
        syslog.debug("Input Tester: saved HidHide setup not read", exc_info=True)
    return state


def expect_hidden(
    on_hidden_list: bool, cloak: bool, block_mode: bool, tester_on_list: bool
) -> bool:
    """Contract 5: a stick is hidden from the tester."""
    if not (on_hidden_list and cloak):
        return False
    return tester_on_list if block_mode else not tester_on_list


_VJOY_LABEL = re.compile(r"vJoy\s+(\d+)")


def _feeds(device_uuid: uuid.UUID) -> list[str]:
    """"vJoy N" for each vJoy device this stick's Map to vJoy actions reach."""
    from gremlin.ui import trace_model

    ids: set[int] = set()
    try:
        for text in trace_model.targets(device_uuid).values():
            ids.update(int(n) for n in _VJOY_LABEL.findall(text))
    except Exception:
        syslog.debug("Input Tester: profile targets not read", exc_info=True)
    return [f"vJoy {n}" for n in sorted(ids)]


def _instance_ids(dev: Any, rows: list[dict]) -> list[str]:  # noqa: ANN401
    from gremlin import hidhide_watch

    out: list[str] = []
    for row in hidhide_watch._stick_rows(dev, rows):
        for i in row.get("instanceIds") or [row.get("instanceId")]:
            if i and str(i) not in out:
                out.append(str(i))
    return out


def _guid(dev: Any) -> str:  # noqa: ANN401
    return "{" + str(dev.device_guid).strip("{}") + "}"


def build_expected() -> dict[str, Any]:
    """The contents of expected.json now."""
    from gremlin import device_initialization, hidhide_driver, input_monitor
    from gremlin.modules import output

    hh = _hidhide_state()
    current = str(_expected_tester_path())
    apps = [str(a) for a in hh["apps"] or []]
    tester_on = any(_app_is(a, current) for a in apps)
    cloak = bool(hh["cloak"])
    block = bool(hh["inverse"])
    hidden = {str(d).upper() for d in hh["devices"] or []}
    present = bool(hh["read"]) or any(
        hh[k] is not None for k in ("cloak", "inverse", "devices")
    )
    try:
        rows = hidhide_driver.list_hid_devices(True)
    except Exception:
        rows = []

    sticks: list[dict[str, Any]] = []
    try:
        physical = list(device_initialization.physical_devices())
    except Exception:
        physical = []
    for dev in physical:
        try:
            uid = dev.device_guid.uuid
            vid, pid = int(dev.vendor_id), int(dev.product_id)
        except Exception:
            continue
        if (vid, pid) == (VJOY_VID, VJOY_PID):
            continue
        ids = _instance_ids(dev, rows)
        on_list = any(i.upper() in hidden for i in ids)
        try:
            name = input_monitor.device_name(uid)
        except Exception:
            name = str(dev.name)
        sticks.append({
            "name": name,
            "windows_name": str(dev.name),
            "vid": vid,
            "pid": pid,
            "guid": _guid(dev),
            "instance_ids": ids,
            "feeds": _feeds(uid),
            "expect": "hidden" if expect_hidden(on_list, cloak, block, tester_on)
            else "visible",
        })

    vjoy: list[dict[str, Any]] = []
    try:
        virtual = list(device_initialization.vjoy_devices())
    except Exception:
        virtual = []
    for dev in virtual:
        try:
            vid_n = int(dev.vjoy_id)
        except Exception:
            continue
        fed_by = [s["name"] for s in sticks if f"vJoy {vid_n}" in s["feeds"]]
        vjoy.append({
            "id": vid_n, "guid": _guid(dev), "fed_by": fed_by,
            "used": bool(fed_by), "expect": "visible",
        })

    xbox: list[dict[str, Any]] = []
    try:
        plugged = set(output.plugged_xbox_pads())
    except Exception:
        plugged = set()
    for pad in sorted(plugged | set(getattr(output, "_xbox_modules", {}) or {})):
        on = pad in plugged
        xbox.append({"pad": pad, "on": on, "expect": "visible" if on else ""})

    return {
        "version": 1,
        "written": datetime.now().isoformat(timespec="seconds"),
        "tester_path": current,
        "hidhide": {
            "present": present,
            "cloak": cloak,
            "mode": "block" if block else "allow",
            "tester_on_list": tester_on,
            "apps": apps,
        },
        "sticks": sticks,
        "vjoy": vjoy,
        "xbox": xbox,
        **_change_fields(),
    }


def _write_atomic(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(temp, path)


def write_expected() -> bool:
    """Writes expected.json (temp file, then swapped in). False on failure."""
    try:
        _write_atomic(expected_file(), build_expected())
        return True
    except Exception:
        syslog.warning("Input Tester: expected.json not written", exc_info=True)
        return False


# --- the last HidHide change ------------------------------------------------------

CHANGE_WHATS = ("program list", "cloak", "hidden devices", "mode", "settings")
# (local time, what): Gremlin's last HidHide change made or seen; None until one.
_last_change: tuple[datetime, str] | None = None


def record_hidhide_change(what: str = "settings", when: datetime | None = None) -> None:
    """Notes a HidHide change Gremlin made or saw (what: CHANGE_WHATS)."""
    global _last_change
    what = what if what in CHANGE_WHATS else "settings"
    _last_change = ((when or datetime.now()).replace(microsecond=0), what)


def last_hidhide_change() -> tuple[datetime, str] | None:
    """(time, what) of the last HidHide change; None when none is known."""
    return _last_change


def _change_fields() -> dict[str, str]:
    change = _last_change
    if change is None:
        return {}
    return {
        "hidhide_changed_at": change[0].isoformat(timespec="seconds"),
        "hidhide_change": change[1],
    }


# --- result.json ------------------------------------------------------------------


def last_result() -> dict | None:
    """The tester's last result.json; None when there is none (or unreadable)."""
    try:
        data = json.loads(result_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def result_text(result: dict | None) -> tuple[str, bool]:
    """("Input Tester: Fail · 1 stick visible…", is_fail)."""
    if not result:
        return "", False
    verdict = str(result.get("verdict") or "none")
    word = {"pass": "Pass", "fail": "Fail"}.get(verdict, "No verdict")
    summary = str(result.get("summary") or "").strip()
    text = f"Input Tester: {word}" + (f" · {summary}" if summary else "")
    return text, verdict == "fail"


# --- launching and watching ----------------------------------------------------


def _default_starter(exe: str, args: list[str]) -> Any:  # noqa: ANN401
    """Starts the tester detached, without a console. Off-screen (tests)
    nothing is started."""
    if os.environ.get("QT_QPA_PLATFORM", "").lower() == "offscreen":
        syslog.info("Input Tester not started (off-screen)")
        return None
    flags = 0
    if os.name == "nt":
        flags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
    return subprocess.Popen(
        [exe, *args], cwd=str(Path(exe).parent), creationflags=flags,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, close_fds=True,
    )


# Injectable for tests: starter(exe, args) -> process with poll() (or None).
_starter: Callable[[str, list[str]], Any] = _default_starter
_lock = threading.Lock()
_process: Any = None
_run = 0
_timer: threading.Timer | None = None
_result_stamp: float | None = None
_setup_stamp: str | None = None
_connected = False


def set_starter(starter: Callable[[str, list[str]], Any] | None) -> None:
    """Tests: replaces how the tester is started (None restores the real one)."""
    global _starter
    _starter = starter or _default_starter


class _Watcher(QtCore.QObject):
    """resultChanged: result.json changed while a launched tester runs (and
    once after launch when a result is already there)."""

    resultChanged = QtCore.Signal()  # noqa: N815 - Qt name


_watcher: _Watcher | None = None


def watcher() -> _Watcher:
    global _watcher
    if _watcher is None:
        _watcher = _Watcher()
        app = QtCore.QCoreApplication.instance()
        if app is not None and _watcher.thread() is not app.thread():
            _watcher.moveToThread(app.thread())
    return _watcher


def running() -> bool:
    """True while a tester this program started is still running."""
    proc = _process
    if proc is None:
        return False
    try:
        return proc.poll() is None
    except Exception:
        return False


def launch() -> str:
    """Writes expected.json and starts the tester; "" when started, else
    the message to show."""
    global _process
    exe = tester_path()
    if exe is None:
        return NOT_BUILT
    write_expected()
    args = ["--gremlin-dir", str(gremlin_dir())]
    try:
        proc = _starter(str(exe), args)
    except Exception as exc:
        syslog.warning("Input Tester could not start", exc_info=True)
        return f"The Input Tester could not start: {exc}"
    with _lock:
        _process = proc
    if proc is not None:
        _start_watch()
    return ""


def _result_mtime() -> float | None:
    try:
        return result_file().stat().st_mtime
    except OSError:
        return None


def _setup_fingerprint() -> str:
    """The saved HidHide setup (the program's own edits change it)."""
    try:
        from gremlin.ui import hidhide as hh

        return json.dumps([
            hh._hidhide_managed(), hh._saved_cloak(), hh._saved_block_list(),
            hh._saved_hidden(), hh._load_games(),
        ], default=str)
    except Exception:
        return ""


def _start_watch() -> None:
    global _run, _result_stamp, _setup_stamp, _timer
    with _lock:
        _run += 1
        run = _run
        old, _timer = _timer, None
    if old is not None:
        old.cancel()
    _result_stamp = _result_mtime()
    _setup_stamp = _setup_fingerprint()
    _connect(True)
    if _result_stamp is not None:
        _emit()
    with _lock:
        if run == _run:
            _timer = threads.timer("Input Tester watch", POLL, _tick, run)


def stop_watch() -> None:
    global _run, _timer
    with _lock:
        _run += 1
        old, _timer = _timer, None
    if old is not None:
        old.cancel()
    _connect(False)


def _emit() -> None:
    watcher().resultChanged.emit()
    try:
        from gremlin import hidhide_watch

        hidhide_watch.tester_result(last_result())
    except Exception:
        syslog.debug("Input Tester: trace line failed", exc_info=True)


def poll_once() -> None:
    """One look: result.json changed, the saved HidHide setup changed."""
    global _result_stamp, _setup_stamp
    stamp = _result_mtime()
    if stamp is not None and stamp != _result_stamp:
        _result_stamp = stamp
        _emit()
    else:
        _result_stamp = stamp
    setup = _setup_fingerprint()
    if setup != _setup_stamp:
        _setup_stamp = setup
        write_expected()


def _tick(run: int) -> None:
    global _timer
    if run != _run:
        return
    try:
        poll_once()
    except Exception:
        syslog.debug("Input Tester watch failed", exc_info=True)
    if not running():
        # A last look already done above; the tester has closed.
        stop_watch()
        return
    with _lock:
        if run == _run:
            _timer = threads.timer("Input Tester watch", POLL, _tick, run)


def device_changed(*_args: object) -> None:
    if running():
        write_expected()


def hidhide_changed(what: str = "settings") -> None:
    """HidHide changed (the program's own edit or seen by the watch): noted,
    and expected.json written again when a tester runs or has run."""
    record_hidhide_change(what)
    if running() or expected_file().is_file():
        write_expected()


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
        syslog.debug("Input Tester: device change hook failed", exc_info=True)


def _reset_for_tests() -> None:
    global _process, _result_stamp, _setup_stamp, _last_change
    stop_watch()
    _last_change = None
    _process = None
    _result_stamp = None
    _setup_stamp = None
    set_starter(None)


# --- QML -------------------------------------------------------------------------


@ta.QmlElement
class InputTesterLink(QtCore.QObject):
    """Tools › Input Tester… (main_commands.js)."""

    resultChanged = QtCore.Signal()  # noqa: N815 - Qt name

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        watcher().resultChanged.connect(self.resultChanged)

    @QtCore.Slot(result=str)
    def launch(self) -> str:
        return launch()

    @QtCore.Property(bool, notify=resultChanged)
    def built(self) -> bool:
        return tester_path() is not None

    @QtCore.Property(str, notify=resultChanged)
    def lastResultText(self) -> str:  # noqa: N802 - QML name
        return result_text(last_result())[0]


__all__ = [
    "InputTesterLink", "NOT_BUILT", "build_expected", "expect_hidden",
    "hidhide_changed", "last_hidhide_change", "last_result", "launch",
    "record_hidhide_change", "running", "set_starter", "tester_dir",
    "tester_path", "watcher", "write_expected",
]
