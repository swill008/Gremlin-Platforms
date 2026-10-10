# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""InputTesterModel: the tester window's data (API in model_api, D-02-INPUT-TESTER)."""

from __future__ import annotations

import logging
import sys
import time
from collections.abc import Callable
from pathlib import Path

from PySide6 import QtCore, QtGui

from gremlin.input_tester import compare as cmp
from gremlin.input_tester import devices, result, steam

POLL_MS = 16
FILE_POLL_S = 1.0
ACTIVE_S = 0.3

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


def _valid_gremlin_dir(value: str | None) -> str | None:
    """--gremlin-dir when it names an existing folder by full path, else None
    (plain tester: no comparison, and nothing is written anywhere)."""
    if not value:
        return None
    path = Path(value)
    if not path.is_absolute() or not path.is_dir():
        return None
    return str(path)


class InputTesterModel(QtCore.QObject):
    rowsChanged = QtCore.Signal()
    activityChanged = QtCore.Signal()
    selectedChanged = QtCore.Signal()
    liveChanged = QtCore.Signal()
    verdictChanged = QtCore.Signal()

    def __init__(
        self,
        gremlin_dir: str | None = None,
        parent: QtCore.QObject | None = None,
        *,
        snapshot: Callable[[], list[devices.SeenDevice]] = devices.snapshot,
        poll: Callable[[devices.SeenDevice], devices.LiveValues] = devices.poll,
        hid_list: Callable[[], list[devices.HidDevice]] = devices.hid_devices,
        steam_running: Callable[[], bool] = steam.steam_running,
        clock: Callable[[], float] = time.monotonic,
        start_timers: bool = True,
    ) -> None:
        super().__init__(parent)
        self._gremlin_dir = _valid_gremlin_dir(gremlin_dir)
        self._snapshot = snapshot
        self._poll = poll
        self._hid_list = hid_list
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
        self.refresh()
        self._poll_timer = QtCore.QTimer(self)
        self._poll_timer.setInterval(POLL_MS)
        self._poll_timer.timeout.connect(self.tick)
        self._file_timer = QtCore.QTimer(self)
        self._file_timer.setInterval(int(FILE_POLL_S * 1000))
        self._file_timer.timeout.connect(self.check_changes)
        if start_timers:
            self._poll_timer.start()
            self._file_timer.start()

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
            self._hid = self._hid_list()
        except Exception:  # noqa: BLE001
            self._hid = []
        self._read_expected()
        self._recompare()

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
        devices_changed = [d.key for d in seen] != [d.key for d in self._seen]
        if file_changed:
            self._read_expected()
        if devices_changed:
            self._seen = seen
        if file_changed or devices_changed:
            self._recompare()
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
            "verdict": row.verdict,
            "seen": row.seen,
            "greyed": row.expect == "hidden" and not row.seen,
            "live": row.device is not None,
            "inGremlin": row.in_gremlin,
            "windowsName": row.windows_name,
            "ids": row.ids,
            "expected": {
                "hidden": "hidden from games",
                "visible": "visible to every program",
            }.get(row.expect, ""),
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
        activity = {
            key: now - self._changed_at.get(key, -1e9) < ACTIVE_S
            for key in (d.key for d in self._seen)
        }
        if activity != self._activity:
            self._activity = activity
            self.activityChanged.emit()
        if live_changed:
            self.liveChanged.emit()

    # Properties --------------------------------------------------------------

    @QtCore.Property(bool, notify=verdictChanged)
    def compareMode(self) -> bool:
        return self._expected is not None

    @QtCore.Property(str, notify=verdictChanged)
    def verdict(self) -> str:
        return self._verdict.verdict

    @QtCore.Property(str, notify=verdictChanged)
    def verdictText(self) -> str:
        return {"pass": "✓ Pass", "fail": "✗ Fail"}.get(self._verdict.verdict, "")

    @QtCore.Property(str, notify=verdictChanged)
    def summary(self) -> str:
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
            f"DirectInput {di} · XInput pads {xi} · HID {len(self._hid)} · "
            f"polling {round(1000 / POLL_MS)}/s"
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


def _set_clipboard(text: str) -> None:
    app = QtGui.QGuiApplication.instance()
    if app is not None:
        QtGui.QGuiApplication.clipboard().setText(text)
