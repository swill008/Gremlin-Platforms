# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""InputTesterModel: the tester window's data (API in model_api, D-02-INPUT-TESTER)."""

from __future__ import annotations

import datetime
import logging
import os
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from pathlib import Path

from PySide6 import QtCore, QtGui

from gremlin.input_tester import compare as cmp
from gremlin.input_tester import devices, logfiles, result, steam
from gremlin.input_tester.log import TesterLog, log_path

POLL_MS = 16
FILE_POLL_S = 1.0
ACTIVE_S = 0.3
# Follow input (item 7): axis moves under this never switch; after a switch,
# hold this long before switching to another device.
FOLLOW_AXIS = 0.05
FOLLOW_HOLD_S = 1.0

DENIED_TEXT = "access denied (5): refused, HidHide is hiding it from this program"
STALE_TEXT = (
    "HidHide changed after this tester started ({what}, {time}). HidHide only "
    "checks devices when they're opened, so what you see may be out of date."
)
STALE_LOG = (
    "HidHide changed after this tester started ({what} {time}): restart to see "
    "the current result"
)
PLAIN_LOG_NOTE = "Kept in this window only (not opened from Gremlin)"
TESTER_LOG_LIMIT = "1 MB"

_ICON = {
    "ok": ("✓", "ok"),
    "bad": ("✗", "no"),
    "missing": ("✗", "no"),
    "unknown": ("?", "q"),
}
_TAG_STYLE = {"ok": "ok", "bad": "bad", "missing": "bad", "unknown": "q"}


SOURCE_NOTE = (
    "Running from source: HidHide sees python.exe, the same as Gremlin — use "
    "the built tester (tools/build_input_tester.py) to test hiding."
)


def _exe_path() -> str:
    """The image HidHide matches: the tester exe when built, python.exe from
    source."""
    return sys.executable


def _from_source() -> bool:
    return not getattr(sys, "frozen", False)


def _default_scan() -> tuple[list, list]:
    scan = getattr(devices, "hid_scan", None)
    if scan is not None:
        return scan()
    return devices.hid_devices(), []


def _default_open_results() -> list:
    results = getattr(devices, "last_open_results", None)
    return list(results()) if results is not None else []


def restart_args(argv: Sequence[str] | None = None) -> list[str]:
    """The same program with the same arguments: the exe when built,
    python.exe + the script from source."""
    argv = list(sys.argv if argv is None else argv)
    args = argv[1:]
    if _from_source():
        script = os.path.abspath(argv[0]) if argv else ""
        return [sys.executable, script, *args]
    return [sys.executable, *args]


def _start_detached(args: list[str]) -> object:
    flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(
        subprocess, "CREATE_NEW_PROCESS_GROUP", 0
    )
    return subprocess.Popen(args, cwd=os.getcwd(), creationflags=flags, close_fds=True)


def _quit_app() -> object:
    app = QtCore.QCoreApplication.instance()
    if app is not None:
        app.quit()
    return None


def _open_folder(folder: str) -> bool:
    return QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(folder))


_starter_hook: Callable[[list[str]], object] | None = None
_quitter_hook: Callable[[], object] | None = None


def set_starter(fn: Callable[[list[str]], object] | None) -> None:
    """Test hook: what restartTester() calls to start the new tester."""
    global _starter_hook
    _starter_hook = fn


def set_quitter(fn: Callable[[], object] | None) -> None:
    """Test hook: what restartTester() calls to quit after starting it."""
    global _quitter_hook
    _quitter_hook = fn


def _valid_gremlin_dir(value: str | None) -> str | None:
    """--gremlin-dir when it names an existing folder by full path, else None
    (plain tester: no comparison, and nothing is written anywhere)."""
    if not value:
        return None
    path = Path(value)
    if not path.is_absolute() or not path.is_dir():
        return None
    return str(path)


def _content(expected: dict | None) -> dict | None:
    """expected.json without its write time: what a change is compared on."""
    if expected is None:
        return None
    return {k: v for k, v in expected.items() if k != "written"}


class InputTesterModel(QtCore.QObject):
    rowsChanged = QtCore.Signal()
    activityChanged = QtCore.Signal()
    selectedChanged = QtCore.Signal()
    liveChanged = QtCore.Signal()
    verdictChanged = QtCore.Signal()
    logSourcesChanged = QtCore.Signal()
    logChanged = QtCore.Signal()
    logFollowChanged = QtCore.Signal()
    staleChanged = QtCore.Signal()
    followInputChanged = QtCore.Signal()
    inputFollowed = QtCore.Signal(str)

    def __init__(
        self,
        gremlin_dir: str | None = None,
        parent: QtCore.QObject | None = None,
        *,
        snapshot: Callable[[], list[devices.SeenDevice]] = devices.snapshot,
        poll: Callable[[devices.SeenDevice], devices.LiveValues] = devices.poll,
        hid_list: Callable[[], list[devices.HidDevice]] | None = None,
        steam_running: Callable[[], bool] = steam.steam_running,
        clock: Callable[[], float] = time.monotonic,
        start_timers: bool = True,
        hid_scan: Callable[[], tuple[list, list]] | None = None,
        open_results: Callable[[], list] = _default_open_results,
        now: Callable[[], datetime.datetime] = datetime.datetime.now,
        starter: Callable[[list[str]], object] | None = None,
        quit_app: Callable[[], object] | None = None,
        open_folder: Callable[[str], bool] = _open_folder,
        argv: Sequence[str] | None = None,
        exe_dir: str | None = None,
    ) -> None:
        super().__init__(parent)
        self._gremlin_dir = _valid_gremlin_dir(gremlin_dir)
        self._snapshot = snapshot
        self._poll = poll
        if hid_scan is not None:
            self._hid_scan = hid_scan
        elif hid_list is not None:
            listed = hid_list
            self._hid_scan = lambda: (listed(), [])
        else:
            self._hid_scan = _default_scan
        self._hid_skips: list = []
        self._open_results = open_results
        self._started_at = now()
        self._starter = starter
        self._quit_app = quit_app
        self._open_folder = open_folder
        self._argv = argv
        self._exe_dir = exe_dir or os.path.dirname(_exe_path())
        self._stale: tuple[str, str] | None = None
        self._logged_opens: set[tuple] = set()
        # Follow input (item 7)
        self._follow_input = True
        self._all_shown = False
        self._follow_base: dict[str, devices.LiveValues] = {}
        self._follow_hold_until = -1e9
        self._steam_running = steam_running
        self._clock = clock
        self._seen: list[devices.SeenDevice] = []
        self._hid: list[devices.HidDevice] = []
        self._expected: dict | None = None
        self._expected_mtime: float | None = None
        self._verdict = cmp.Verdict("none", "", [])
        self._last_result: dict | None = None
        self._rows: list[dict] = []
        self._selected_key = ""
        self._values: dict[str, devices.LiveValues] = {}
        self._signatures: dict[str, tuple] = {}
        self._changed_at: dict[str, float] = {}
        self._activity: dict[str, bool] = {}
        self._exe = _exe_path()
        self._log = TesterLog(
            log_path(self._gremlin_dir) if self._gremlin_dir else None, now=now
        )
        self._log.listeners.append(self._on_tester_line)
        # Logs tab
        self._log_sources = logfiles.sources(
            self._gremlin_dir, self._exe_dir, os.getcwd()
        )
        self._log_source = logfiles.TESTER
        self._log_follow = True
        self._log_warn_only = False
        self._log_find = ""
        self._find_pos = -1
        self._log_raw: list[str] = []
        self._log_tail = logfiles.Tail([], 0, False, True)
        self._log_shown: list[dict] = []
        self._follower = logfiles.Follower(None)
        self._log_version = -1
        self._first_refresh = True
        self._log_start()
        self.refresh()
        self._load_log()
        self._poll_timer = QtCore.QTimer(self)
        self._poll_timer.setInterval(POLL_MS)
        self._poll_timer.timeout.connect(self.tick)
        self._file_timer = QtCore.QTimer(self)
        self._file_timer.setInterval(int(FILE_POLL_S * 1000))
        self._file_timer.timeout.connect(self.check_changes)
        self._log_timer = QtCore.QTimer(self)
        self._log_timer.setInterval(int(logfiles.FOLLOW_S * 1000))
        self._log_timer.timeout.connect(self.poll_log)
        if start_timers:
            self._poll_timer.start()
            self._file_timer.start()
            self._log_timer.start()

    # Work ------------------------------------------------------------------

    def _expected_file(self) -> Path | None:
        return cmp.expected_path(self._gremlin_dir) if self._gremlin_dir else None

    def _read_expected(self) -> None:
        path = self._expected_file()
        self._expected = cmp.load_expected(path) if path else None
        try:
            self._expected_mtime = path.stat().st_mtime if path else None
        except OSError:
            self._expected_mtime = None
        self._check_stale()

    def _check_stale(self) -> None:
        stale = cmp.stale_since(self._expected, self._started_at)
        if stale == self._stale:
            return
        self._stale = stale
        if stale is not None:
            self._log.warn(STALE_LOG.format(what=stale[0], time=stale[1]))
        self.staleChanged.emit()

    # tester.log lines (item 2) ------------------------------------------------

    def _log_start(self) -> None:
        mode = (
            "compared with Gremlin"
            if self._gremlin_dir
            else "not opened from Gremlin (this log is kept in the window only)"
        )
        self._log.add(f"Started · {self._exe} · {mode}")

    def _log_expected(self, first: bool) -> None:
        if not self._gremlin_dir:
            return
        if self._expected is None:
            self._log.warn("Gremlin's expected devices (expected.json) not found")
            return
        written = str(self._expected.get("written", ""))
        try:
            written = datetime.datetime.fromisoformat(written).strftime("%H:%M:%S")
        except ValueError:
            pass
        head = (
            "Gremlin's expected devices"
            if first
            else "Gremlin's expected devices changed"
        )
        self._log.add(f"{head} (written {written or 'unknown'})")
        hidhide = self._expected.get("hidhide") or {}
        if not hidhide.get("present"):
            state = "not installed"
        else:
            mode = str(hidhide.get("mode", "block")).casefold()
            state = " · ".join(
                [
                    "cloak on" if hidhide.get("cloak") else "cloak off",
                    "Allow list" if mode == "allow" else "Block list",
                    "this tester is on the list"
                    if hidhide.get("tester_on_list")
                    else "this tester isn't on the list",
                ]
            )
        self._log.add(f"HidHide (from Gremlin): {state}")

    def _log_open_results(self) -> None:
        try:
            results = list(self._open_results())
        except Exception:  # noqa: BLE001
            results = []
        denied_code = int(getattr(devices, "ACCESS_DENIED", 5))
        for res in results:
            kind = str(getattr(res, "kind", ""))
            name = str(getattr(res, "name", ""))
            instance = str(getattr(res, "instance", ""))
            ok = bool(getattr(res, "ok", False))
            code = int(getattr(res, "code", 0) or 0)
            text = str(getattr(res, "text", "") or "")
            left_out = str(getattr(res, "left_out", "") or "")
            key = (kind, instance, ok, code, text, left_out)
            if key in self._logged_opens:
                continue
            self._logged_opens.add(key)
            if kind == "directinput":
                line = f"DirectInput {name} · listed"
                if text and text not in ("listed", "ok"):
                    line += f" · {text}"
                self._log.add(line, warn=not ok)
                continue
            if ok:
                answer = "ok"
            elif code == denied_code:
                answer = DENIED_TEXT
            else:
                answer = text or f"error {code}"
            label = " ".join(part for part in (name, instance) if part)
            line = f"HID {label} · open → {answer}"
            if left_out:
                line += f" · left out: {left_out}"
            self._log.add(line, warn=not ok and code != denied_code)

    def _on_tester_line(self) -> None:
        if self._log_source == logfiles.TESTER and self._log_follow:
            self.poll_log()

    def _safe_snapshot(self) -> list[devices.SeenDevice]:
        try:
            return self._snapshot()
        except Exception:  # noqa: BLE001 - a driver failure shows as "nothing seen"
            logging.getLogger("input_tester").exception("Device list failed")
            return []

    @QtCore.Slot()
    def refresh(self) -> None:
        """Re-enumerates devices, re-reads expected.json and compares."""
        self._seen = self._safe_snapshot()
        try:
            kept, skipped = self._hid_scan()
            self._hid, self._hid_skips = list(kept), list(skipped)
        except Exception:  # noqa: BLE001
            self._hid, self._hid_skips = [], []
        before = self._expected
        self._read_expected()
        # Refresh re-reads the file; it says "changed" only when it did.
        if self._first_refresh or _content(before) != _content(self._expected):
            self._log_expected(self._first_refresh)
        self._first_refresh = False
        self._recompare()
        self._log_open_results()

    def check_changes(self) -> None:
        """1 s poll: expected.json mtime and the device list."""
        path = self._expected_file()
        mtime = None
        if path is not None:
            try:
                mtime = path.stat().st_mtime
            except OSError:
                mtime = None
        seen = self._safe_snapshot()
        file_changed = mtime != self._expected_mtime
        # The whole entry, not only the id: a device can come back under the
        # same id with another layout (an Xbox pad switched to DirectInput),
        # and the rows and the axes read follow it (02 S146).
        devices_changed = seen != self._seen
        if file_changed:
            before = self._expected
            self._read_expected()
            # Rewritten with the same devices and settings: not a change.
            file_changed = _content(before) != _content(self._expected)
            if file_changed:
                self._log_expected(False)
        if devices_changed:
            self._seen = seen
        if file_changed or devices_changed:
            self._recompare()
            self._log_open_results()
        else:
            # Steam may start or stop at any time.
            self._recompare(only_if_changed=True)

    def _recompare(self, only_if_changed: bool = False) -> None:
        try:
            steam_on = bool(self._steam_running())
        except Exception:  # noqa: BLE001
            steam_on = False
        verdict = cmp.compare(self._expected, self._seen, steam_on)
        data = result.result_data(verdict)
        if only_if_changed and data == self._last_result:
            return
        self._verdict = verdict
        self._rows = [self._row_dict(r) for r in verdict.rows]
        live_keys = {r["key"] for r in self._rows if r["live"]}
        if self._selected_key not in {r["key"] for r in self._rows}:
            self._selected_key = next(iter(sorted(live_keys)), "") if live_keys else ""
            if self._rows and not self._selected_key:
                self._selected_key = self._rows[0]["key"]
        if data != self._last_result:
            self._last_result = data
            head = cmp.top_line(verdict) or (
                f"no comparison · {len(verdict.rows)} devices"
            )
            self._log.add(f"Result: {head}", warn=verdict.verdict == "fail")
            if self._gremlin_dir:
                try:
                    result.write_result(Path(self._gremlin_dir) / "tester", verdict)
                except OSError:
                    logging.getLogger("input_tester").exception(
                        "Writing result.json failed"
                    )
        self.rowsChanged.emit()
        self.verdictChanged.emit()
        self.selectedChanged.emit()
        self.tick()

    def _row_dict(self, row: cmp.Row) -> dict:
        icon, icon_style = _ICON.get(row.verdict, ("", ""))
        tag_style = _TAG_STYLE.get(row.verdict, "")
        if row.verdict == "ok" and not row.used:
            tag_style = "e"
        sub = row.in_gremlin
        if row.kind == "stick":
            # Gremlin's name is the row name; Windows' name and what it feeds below.
            sub = row.windows_name
            if row.feeds:
                sub = f"{sub} · feeds {row.feeds}" if sub else f"feeds {row.feeds}"
        elif row.kind == "other" and row.ids:
            sub = f"{row.ids} · {row.in_gremlin}" if row.in_gremlin else row.ids
        elif not sub:
            sub = row.ids
        return {
            "key": row.key,
            "section": row.section,
            "kind": row.kind,
            "name": row.name,
            "sub": sub,
            "icon": icon,
            "iconStyle": icon_style,
            "tag": row.tag,
            "tagStyle": tag_style,
            "hint": row.hint,
            "detail": row.detail,
            "verdict": row.verdict,
            "seen": row.seen,
            "greyed": row.expect == "hidden" and not row.seen,
            "live": row.device is not None,
            "inGremlin": row.in_gremlin,
            "windowsName": row.windows_name,
            "ids": row.ids,
            "expected": row.should_be,
            "axisCount": row.device.axes if row.device else 0,
            "buttonCount": row.device.buttons if row.device else 0,
            "hatCount": row.device.hats if row.device else 0,
        }

    @QtCore.Slot()
    def tick(self) -> None:
        """~60 a second: live values and activity of every seen device."""
        now = self._clock()
        live_changed = False
        for device in self._seen:
            try:
                values = self._poll(device)
            except Exception:  # noqa: BLE001
                values = devices.LiveValues([], [], [])
            signature = values.signature()
            old = self._signatures.get(device.key)
            if old != signature:
                if old is not None:
                    self._changed_at[device.key] = now
                self._signatures[device.key] = signature
                live_changed = True
            self._values[device.key] = values
        self._follow(now)
        activity = {
            key: now - self._changed_at.get(key, -1e9) < ACTIVE_S
            for key in (d.key for d in self._seen)
        }
        if activity != self._activity:
            self._activity = activity
            self.activityChanged.emit()
        if live_changed:
            self.liveChanged.emit()

    def _moved(self, key: str, values: devices.LiveValues) -> bool:
        base = self._follow_base.get(key)
        if base is None:
            self._follow_base[key] = values
            return False
        if base.buttons != values.buttons or base.hats != values.hats:
            return True
        if len(base.axes) != len(values.axes):
            return True
        return any(abs(a - b) > FOLLOW_AXIS for a, b in zip(base.axes, values.axes))

    def _follow(self, now: float) -> None:
        """Item 7: selects the device the user moves (noise guard, 1 s hold);
        never while the All devices view is shown."""
        live = [r["key"] for r in self._rows if r["live"]]
        moved = [
            key
            for key in live
            if key in self._values and self._moved(key, self._values[key])
        ]
        for key in moved:
            self._follow_base[key] = self._values[key]
        if not moved or not self._follow_input or self._all_shown:
            return
        if self._selected_key in moved or now < self._follow_hold_until:
            return
        target = moved[0]
        self._follow_hold_until = now + FOLLOW_HOLD_S
        self._selected_key = target
        self.selectedChanged.emit()
        self.liveChanged.emit()
        self.inputFollowed.emit(target)

    # Logs tab (item 1) -------------------------------------------------------

    def _source(self) -> logfiles.LogSource:
        return next(
            (s for s in self._log_sources if s.id == self._log_source),
            self._log_sources[0],
        )

    def _source_path(self) -> Path | None:
        source = self._source()
        if source.id == logfiles.TESTER:
            return self._log.path  # None: window only (plain mode or not writable)
        return source.path

    def _load_log(self) -> None:
        """Reads the selected source again and rebuilds the shown lines."""
        path = self._source_path()
        if path is None:
            self._log_raw = self._log.lines()
            self._log_tail = logfiles.Tail(self._log_raw, 0, False, True)
            self._log_version = self._log.version
        else:
            self._log_tail = logfiles.read_tail(path)
            self._log_raw = self._log_tail.lines
        if self._follower.path != path:
            self._follower = logfiles.Follower(path)
        self._rebuild_shown()

    def _rebuild_shown(self) -> None:
        find = self._log_find.casefold()
        shown = []
        for n, line in enumerate(self._log_raw):
            warn = logfiles.is_warning(line)
            if self._log_warn_only and not warn:
                continue
            stamp, text = logfiles.split_line(line)
            shown.append(
                {
                    "n": n,
                    "time": stamp,
                    "text": text,
                    "warn": warn,
                    "match": bool(find) and find in line.casefold(),
                }
            )
        self._log_shown = shown
        matches = self._matches()
        if not matches:
            self._find_pos = -1
        elif self._find_pos not in matches:
            self._find_pos = matches[0]
        self.logChanged.emit()

    def _matches(self) -> list[int]:
        return [i for i, line in enumerate(self._log_shown) if line["match"]]

    @QtCore.Slot()
    def poll_log(self) -> None:
        """Every 0.5 s while Follow is on: reloads when the source changed."""
        if not self._log_follow:
            return
        if self._source_path() is None:
            if self._log.version != self._log_version:
                self._load_log()
        elif self._follower.changed():
            self._load_log()

    @QtCore.Slot()
    def reloadLog(self) -> None:
        self._load_log()

    @QtCore.Property(list, notify=logSourcesChanged)
    def logSources(self) -> list:
        return [
            {
                "id": s.id,
                "label": s.label,
                "path": str(s.path) if s.path else "",
                "exists": s.exists,
            }
            for s in self._log_sources
        ]

    def _get_log_source(self) -> str:
        return self._log_source

    def _set_log_source(self, value: str) -> None:
        if value == self._log_source or value not in {s.id for s in self._log_sources}:
            return
        self._log_source = value
        self._find_pos = -1
        self._load_log()
        self.logSourcesChanged.emit()

    logSource = QtCore.Property(
        str, _get_log_source, _set_log_source, notify=logChanged
    )

    @QtCore.Property(list, notify=logChanged)
    def logLines(self) -> list:
        return list(self._log_shown)

    @QtCore.Property(str, notify=logChanged)
    def logNote(self) -> str:
        path = self._source_path()
        if path is None:
            return PLAIN_LOG_NOTE
        if not self._log_tail.exists:
            return f"File not found: {path}"
        if self._log_tail.truncated:
            return (
                f"Showing the last {logfiles.size_text(logfiles.TAIL_BYTES)} of "
                f"{logfiles.size_text(self._log_tail.size)}"
            )
        return ""

    @QtCore.Property(str, notify=logChanged)
    def logStatus(self) -> str:
        path = self._source_path()
        count = f"{len(self._log_shown)} lines"
        if path is None:
            return f"Tester log (in this window) · {count}"
        size = logfiles.size_text(self._log_tail.size)
        if self._log_source == logfiles.TESTER:
            return (
                f"{path.name} {size} of {TESTER_LOG_LIMIT} (one older copy kept) "
                f"· {count}"
            )
        return f"{path.name} {size} · {count}"

    def _get_log_follow(self) -> bool:
        return self._log_follow

    def _set_log_follow(self, value: bool) -> None:
        if bool(value) == self._log_follow:
            return
        self._log_follow = bool(value)
        self.logFollowChanged.emit()
        if self._log_follow:
            self._load_log()

    logFollow = QtCore.Property(
        bool, _get_log_follow, _set_log_follow, notify=logFollowChanged
    )

    def _get_warn_only(self) -> bool:
        return self._log_warn_only

    def _set_warn_only(self, value: bool) -> None:
        if bool(value) != self._log_warn_only:
            self._log_warn_only = bool(value)
            self._find_pos = -1
            self._rebuild_shown()

    logWarningsOnly = QtCore.Property(
        bool, _get_warn_only, _set_warn_only, notify=logChanged
    )

    def _get_log_find(self) -> str:
        return self._log_find

    def _set_log_find(self, value: str) -> None:
        if value != self._log_find:
            self._log_find = value
            self._find_pos = -1
            self._rebuild_shown()

    logFind = QtCore.Property(str, _get_log_find, _set_log_find, notify=logChanged)

    @QtCore.Property(int, notify=logChanged)
    def logFindCount(self) -> int:
        return len(self._matches())

    @QtCore.Property(int, notify=logChanged)
    def logFindPos(self) -> int:
        return self._find_pos

    @QtCore.Property(str, notify=logSourcesChanged)
    def logFolder(self) -> str:
        path = self._source_path()
        return str(path.parent) if path is not None else ""

    def _step_find(self, step: int) -> int:
        matches = self._matches()
        if not matches:
            self._find_pos = -1
        elif self._find_pos not in matches:
            self._find_pos = matches[0] if step > 0 else matches[-1]
        else:
            at = matches.index(self._find_pos)
            self._find_pos = matches[(at + step) % len(matches)]
        self.logChanged.emit()
        return self._find_pos

    @QtCore.Slot(result=int)
    def findNext(self) -> int:
        return self._step_find(1)

    @QtCore.Slot(result=int)
    def findPrevious(self) -> int:
        return self._step_find(-1)

    @QtCore.Slot(result=str)
    def copyLog(self) -> str:
        text = "".join(
            (f"{line['time']}  {line['text']}" if line["time"] else line["text"])
            + "\n"
            for line in self._log_shown
        )
        _set_clipboard(text)
        return text

    @QtCore.Slot(result=bool)
    def openLogFolder(self) -> bool:
        path = self._source_path()
        folder = str(path.parent) if path is not None else ""
        if not folder or not os.path.isdir(folder):
            return False
        return bool(self._open_folder(folder))

    # Restart banner (item 3) -------------------------------------------------

    @QtCore.Property(str, notify=staleChanged)
    def staleBanner(self) -> str:
        if self._stale is None:
            return ""
        return STALE_TEXT.format(what=self._stale[0], time=self._stale[1])

    @QtCore.Slot()
    def restartTester(self) -> None:
        """Starts the same program with the same arguments, then quits."""
        args = restart_args(self._argv)
        starter = self._starter or _starter_hook or _start_detached
        quitter = self._quit_app or _quitter_hook or _quit_app
        self._log.add("Restarting: " + " ".join(args))
        try:
            starter(args)
        except OSError as error:
            self._log.warn(f"Restart failed: {error}")
            return
        quitter()

    # Follow input (item 7) ---------------------------------------------------

    def _get_follow_input(self) -> bool:
        return self._follow_input

    def _set_follow_input(self, value: bool) -> None:
        if bool(value) != self._follow_input:
            self._follow_input = bool(value)
            self.followInputChanged.emit()

    followInput = QtCore.Property(
        bool, _get_follow_input, _set_follow_input, notify=followInputChanged
    )

    def _get_all_shown(self) -> bool:
        return self._all_shown

    def _set_all_shown(self, value: bool) -> None:
        if bool(value) != self._all_shown:
            self._all_shown = bool(value)
            self.followInputChanged.emit()

    allDevicesShown = QtCore.Property(
        bool, _get_all_shown, _set_all_shown, notify=followInputChanged
    )

    @QtCore.Property(list, notify=rowsChanged)
    def hidSkipped(self) -> list:
        out = []
        for skip in self._hid_skips:
            denied = bool(getattr(skip, "denied", False))
            reason = str(getattr(skip, "reason", ""))
            vid = int(getattr(skip, "vid", 0) or 0)
            pid = int(getattr(skip, "pid", 0) or 0)
            out.append(
                {
                    "path": str(getattr(skip, "path", "")),
                    "name": str(getattr(skip, "name", "")),
                    "vid": f"{vid:04X}" if vid else "",
                    "pid": f"{pid:04X}" if pid else "",
                    "reason": reason,
                    "denied": denied,
                    "label": "left out: access denied (hidden from this program)"
                    if denied
                    else f"left out: {reason}",
                }
            )
        return out

    # Properties --------------------------------------------------------------

    @QtCore.Property(bool, notify=verdictChanged)
    def compareMode(self) -> bool:
        return self._expected is not None

    @QtCore.Property(str, notify=verdictChanged)
    def verdict(self) -> str:
        return self._verdict.verdict

    @QtCore.Property(str, notify=verdictChanged)
    def verdictText(self) -> str:
        return {"pass": cmp.PASS_HEAD, "fail": cmp.FAIL_HEAD}.get(
            self._verdict.verdict, ""
        )

    @QtCore.Property(str, notify=verdictChanged)
    def summary(self) -> str:
        """After verdictText on the top line: the counts in brackets on a
        pass (TW1), what's wrong on a fail (TW2)."""
        if self._verdict.verdict == "pass":
            return f"({self._verdict.summary})"
        return self._verdict.summary

    @QtCore.Property(str, notify=verdictChanged)
    def contextLine(self) -> str:
        return self._context()

    def _context(self) -> str:
        if _from_source():
            return f"{self._verdict.context} {SOURCE_NOTE}"
        return self._verdict.context

    @QtCore.Property(str, notify=verdictChanged)
    def steamWarning(self) -> str:
        return self._verdict.steam_warning

    @QtCore.Property(str, constant=True)
    def exePath(self) -> str:
        return self._exe

    @QtCore.Property(list, notify=rowsChanged)
    def rows(self) -> list:
        return [
            {
                k: v
                for k, v in r.items()
                if k
                in (
                    "key",
                    "section",
                    "kind",
                    "name",
                    "sub",
                    "icon",
                    "iconStyle",
                    "tag",
                    "tagStyle",
                    "hint",
                    "verdict",
                    "seen",
                    "greyed",
                    "live",
                )
            }
            for r in self._rows
        ]

    @QtCore.Property(dict, notify=activityChanged)
    def activity(self) -> dict:
        return dict(self._activity)

    def _get_selected_key(self) -> str:
        return self._selected_key

    def _set_selected_key(self, key: str) -> None:
        if key != self._selected_key:
            self._selected_key = key
            self.selectedChanged.emit()
            self.liveChanged.emit()

    selectedKey = QtCore.Property(
        str, _get_selected_key, _set_selected_key, notify=selectedChanged
    )

    @QtCore.Slot(str)
    def select(self, key: str) -> None:
        self._set_selected_key(key)

    def _selected_row(self) -> dict | None:
        return next((r for r in self._rows if r["key"] == self._selected_key), None)

    @QtCore.Property(dict, notify=selectedChanged)
    def selected(self) -> dict:
        row = self._selected_row()
        if row is None:
            return {}
        return {
            k: row[k]
            for k in (
                "key",
                "name",
                "kind",
                "tag",
                "tagStyle",
                "inGremlin",
                "windowsName",
                "ids",
                "expected",
                "detail",
                "axisCount",
                "buttonCount",
                "hatCount",
                "seen",
            )
        }

    def _selected_device(self) -> devices.SeenDevice | None:
        return next((d for d in self._seen if d.key == self._selected_key), None)

    def _selected_values(self) -> devices.LiveValues | None:
        device = self._selected_device()
        return self._values.get(device.key) if device else None

    @staticmethod
    def _axis_labels(device: devices.SeenDevice) -> list[str]:
        if device.kind == "xinput":
            return list(devices.XINPUT_AXES)
        return [devices.AXIS_NAMES.get(i, f"Axis {i}") for i in device.axis_ids]

    @QtCore.Property(list, notify=liveChanged)
    def axes(self) -> list:
        device = self._selected_device()
        values = self._selected_values()
        if device is None or values is None:
            return []
        return [
            {"label": label, "value": value}
            for label, value in zip(self._axis_labels(device), values.axes)
        ]

    @QtCore.Property(list, notify=liveChanged)
    def buttons(self) -> list:
        values = self._selected_values()
        return list(values.buttons) if values else []

    @QtCore.Property(list, notify=liveChanged)
    def hats(self) -> list:
        values = self._selected_values()
        return list(values.hats) if values else []

    @QtCore.Property(list, notify=liveChanged)
    def allDevices(self) -> list:
        section = {r["key"]: r["section"] for r in self._rows}
        out = []
        for device in self._seen:
            values = self._values.get(device.key) or devices.LiveValues([], [], [])
            out.append(
                {
                    "key": device.key,
                    "name": device.name,
                    "section": section.get(device.key, ""),
                    "axes": list(values.axes),
                    "buttons": list(values.buttons),
                    "hats": list(values.hats),
                }
            )
        return out

    @QtCore.Property(list, notify=rowsChanged)
    def hidDevices(self) -> list:
        return [
            {
                "path": h.path,
                "vid": f"{h.vid:04X}",
                "pid": f"{h.pid:04X}",
                "name": h.name,
            }
            for h in self._hid
        ]

    @QtCore.Property(str, notify=rowsChanged)
    def statusLine(self) -> str:
        di = sum(1 for d in self._seen if d.kind == "directinput")
        xi = sum(1 for d in self._seen if d.kind == "xinput")
        return (
            f"This window sees {_plural(di, 'joystick')} · "
            f"{_plural(xi, 'Xbox controller')} · "
            f"{_plural(len(self._hid), 'game device')} · "
            f"updating {round(1000 / POLL_MS)} times a second"
        )

    # Slots -------------------------------------------------------------------

    @QtCore.Slot(result=str)
    def resultText(self) -> str:
        return cmp.result_text(self._verdict, self._context())

    @QtCore.Slot(result=str)
    def copyResult(self) -> str:
        text = self.resultText()
        _set_clipboard(text)
        return text

    @QtCore.Slot()
    def copyPath(self) -> None:
        _set_clipboard(self._exe)


def _plural(n: int, noun: str) -> str:
    return f"{n} {noun}" if n == 1 else f"{n} {noun}s"


def _set_clipboard(text: str) -> None:
    app = QtGui.QGuiApplication.instance()
    if app is not None:
        QtGui.QGuiApplication.clipboard().setText(text)
