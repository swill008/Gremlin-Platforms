# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Live Log Reader's Trace tab (D-01-TRACE): the tracing switch, the
tree of connected devices and their controls to tick (each with where it
goes in the open profile), and the trace lines with their filters, notice
and status bar (gremlin.trace). TraceSwitch is the light on/off the Debug
menu's Tracing item uses."""

from __future__ import annotations

import time
import uuid
from datetime import datetime
from typing import Any

from PySide6 import QtCore, QtGui

import gremlin.ui.type_aliases as ta
from gremlin import trace

QML_IMPORT_NAME = "Gremlin.UI"
QML_IMPORT_MAJOR_VERSION = 1

# The Points filter: what each choice shows (Output takes Blocked too).
POINTS = {
    "Raw": (trace.RAW,),
    "Wiring": (trace.WIRING,),
    "Output": (trace.OUTPUT, trace.BLOCKED),
    "Event": (trace.EVENT,),
    "HidHide": (trace.HIDHIDE,),
    "Out of step": (trace.OUT_OF_STEP,),
}


class _Signals(QtCore.QObject):
    changed = QtCore.Signal()


_SIGNALS: _Signals | None = None


def signals() -> _Signals:
    """One hook on trace.on_change for every switch and tab (the hook list
    keeps what it is given)."""
    global _SIGNALS
    if _SIGNALS is None:
        _SIGNALS = _Signals()
        trace.on_change(_SIGNALS.changed.emit)
    return _SIGNALS


def _size_text(size: int) -> str:
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    if size >= 1024:
        return f"{size // 1024} KB"
    return f"{size} bytes"


def _running_text(seconds: float) -> str:
    seconds = max(0, int(seconds))
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def since_text() -> str:
    """"since 17:24:31 · 0:47 running" while tracing, else ""."""
    start = trace.since()
    if not trace.enabled() or start is None:
        return ""
    shown = datetime.fromtimestamp(start).strftime("%H:%M:%S")
    return f"since {shown} · {_running_text(time.time() - start)} running"


# --- the device tree -----------------------------------------------------


def _devices() -> list[tuple[uuid.UUID, str, list[int], int, int]]:
    """(uuid, name, axis indices, buttons, hats) per connected joystick
    device (not the keyboard: its keys aren't traced)."""
    from gremlin import device_initialization, input_monitor

    found: list[tuple[uuid.UUID, str, list[int], int, int]] = []
    try:
        devices = device_initialization.physical_devices()
    except Exception:
        devices = []
    for dev in devices:
        try:
            uid = dev.device_guid.uuid
            axes = [dev.axis_map[i].axis_index for i in range(dev.axis_count)]
            found.append((
                uid, input_monitor.device_name(uid), axes,
                int(dev.button_count), int(dev.hat_count),
            ))
        except Exception:
            continue
    found.sort(key=lambda d: d[1].casefold())
    return found


def targets(device_uuid: uuid.UUID) -> dict[tuple[str, int], str]:
    """{("axis", 1): "→ vJoy 3 X"}: where each control goes in the open
    profile, from its Map to vJoy actions in any mode."""
    from gremlin import shared_state
    from gremlin.modules import wiring
    from gremlin.types import InputType
    from gremlin.ui.input_pairing import walk_actions

    kinds: dict[Any, str] = {
        InputType.JoystickAxis: "axis",
        InputType.JoystickButton: "button",
        InputType.JoystickHat: "hat",
    }
    profile = shared_state.current_profile
    found: dict[tuple[str, int], list[str]] = {}
    try:
        items = profile.inputs.get(device_uuid, []) if profile is not None else []
    except Exception:
        items = []
    for item in items or []:
        kind = kinds.get(getattr(item, "input_type", None))
        if kind is None:
            continue
        try:
            key = (kind, int(getattr(item, "input_id", 0)))
        except (TypeError, ValueError):
            continue
        for seq in getattr(item, "action_sequences", []) or []:
            root = getattr(seq, "root_action", None)
            if root is None:
                continue
            for action in walk_actions(root):
                if getattr(action, "tag", "") != "map-to-vjoy":
                    continue
                label = wiring.dest_label(action, short=True)
                if label:
                    found.setdefault(key, []).append(label)
    return {
        key: "→ " + ", ".join(dict.fromkeys(labels)) for key, labels in found.items()
    }


def _check(n: int, total: int) -> int:
    """0 off, 1 partly, 2 all (Qt.CheckState)."""
    if total <= 0:
        return 0
    if n <= 0:
        return 0
    return 2 if n >= total else 1


class TraceTree(QtCore.QAbstractListModel):
    """The left list: device rows, their Out-of-step check, and when opened
    their axes, buttons and hats; the HidHide row at the end. Changes are
    told row by row so the list keeps its place."""

    Kind = QtCore.Qt.ItemDataRole.UserRole + 1
    Text = Kind + 1
    Target = Kind + 2
    Check = Kind + 3
    Count = Kind + 4
    Expanded = Kind + 5
    Device = Kind + 6
    Control = Kind + 7
    Index = Kind + 8

    _ROLES = {
        Kind: b"rowKind", Text: b"rowText", Target: b"target", Check: b"check",
        Count: b"countText", Expanded: b"expanded", Device: b"device",
        Control: b"controlKind", Index: b"controlIndex",
    }
    _KEYS = {
        Kind: "kind", Text: "text", Target: "target", Check: "check",
        Count: "count", Expanded: "expanded", Device: "device",
        Control: "control", Index: "index",
    }

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._rows: list[dict[str, Any]] = []
        self._open: set[str] = set()
        self.devices = 0
        self.controls = 0

    def roleNames(self) -> dict[int, bytes]:  # noqa: N802 - Qt name
        return dict(self._ROLES)

    def rowCount(  # noqa: N802 - Qt name
        self, parent: QtCore.QModelIndex = QtCore.QModelIndex()  # noqa: B008
    ) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def data(
        self, index: QtCore.QModelIndex,
        role: int = QtCore.Qt.ItemDataRole.DisplayRole,
    ) -> Any:  # noqa: ANN401
        if not index.isValid() or not 0 <= index.row() < len(self._rows):
            return None
        key = self._KEYS.get(role)
        return self._rows[index.row()].get(key) if key else None

    def toggle_open(self, device: str) -> None:
        if device in self._open:
            self._open.discard(device)
        else:
            self._open.add(device)
        self.rebuild()

    def _build(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        devices = controls = 0

        def row(**values: Any) -> dict[str, Any]:  # noqa: ANN401
            base = {
                "kind": "", "text": "", "target": "", "check": 0, "count": "",
                "expanded": False, "device": "", "control": "", "index": 0,
            }
            base.update(values)
            return base

        for uid, name, axes, buttons, hats in _devices():
            dev = str(uid)
            ticks = trace.device_ticks(uid)
            total = len(axes) + buttons + hats
            if ticks["all"]:
                n = total
            else:
                n = (
                    len([a for a in axes if a in ticks["axis"]])
                    + len([b for b in ticks["button"] if 1 <= b <= buttons])
                    + len([h for h in ticks["hat"] if 1 <= h <= hats])
                )
            empty = total == 0
            on = ticks["all"] or n > 0
            if on:
                devices += 1
                controls += n
            opened = dev in self._open and not empty
            rows.append(row(
                kind="device", text=name, device=dev, expanded=opened,
                check=(2 if ticks["all"] else 0) if empty else _check(n, total),
                count="" if empty else f"{n} of {total}",
            ))
            if empty:
                continue
            rows.append(row(
                kind="oos", device=dev, check=2 if trace.oos_ticked(uid) else 0,
                text="Out-of-step check (stick vs vJoy, every 1 s)",
            ))
            if not opened:
                continue
            goes = targets(uid)

            def control(kind: str, index: int, text: str) -> dict[str, Any]:
                return row(
                    kind="control", device=dev, control=kind, index=index,  # noqa: B023
                    text=text, target=goes.get((kind, index), ""),  # noqa: B023
                    check=2 if (ticks["all"] or index in ticks[kind])  # noqa: B023
                    else 0,
                )

            if axes:
                rows.append(row(kind="header", text="Axes", device=dev))
                rows.extend(control("axis", a, f"Axis {a}") for a in axes)
            if buttons or hats:
                rows.append(row(kind="header", text="Buttons and hats", device=dev))
                rows.extend(
                    control("button", b, f"Button {b}") for b in range(1, buttons + 1)
                )
                rows.extend(control("hat", h, f"Hat {h}") for h in range(1, hats + 1))
        rows.append(row(kind="sep"))
        rows.append(row(
            kind="hidhide", text="HidHide (calls, changes, sticks not hidden)",
            check=2 if trace.hidhide_ticked() else 0,
        ))
        self.devices, self.controls = devices, controls
        return rows

    def rebuild(self) -> None:
        new = self._build()
        old = self._rows
        # Rows the same at both ends stay; the middle is replaced.
        head = 0
        while head < min(len(old), len(new)) and _same_row(old[head], new[head]):
            head += 1
        tail = 0
        while (
            tail < min(len(old), len(new)) - head
            and _same_row(old[-1 - tail], new[-1 - tail])
        ):
            tail += 1
        old_mid = len(old) - head - tail
        new_mid = len(new) - head - tail
        if old_mid == new_mid:
            # Same rows, other ticks.
            self._rows = new
            if new:
                self.dataChanged.emit(self.index(0), self.index(len(new) - 1))
            return
        if old_mid:
            self.beginRemoveRows(QtCore.QModelIndex(), head, head + old_mid - 1)
            self._rows = old[:head] + old[len(old) - tail:]
            self.endRemoveRows()
        if new_mid:
            self.beginInsertRows(QtCore.QModelIndex(), head, head + new_mid - 1)
            self._rows = new
            self.endInsertRows()
        self._rows = new
        self.dataChanged.emit(self.index(0), self.index(len(new) - 1))


def _same_row(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return (a["kind"], a["device"], a["control"], a["index"], a["text"]) == (
        b["kind"], b["device"], b["control"], b["index"], b["text"]
    )


class TraceLines(QtCore.QAbstractListModel):
    """The lines shown: time, control, point, detail, warning."""

    Time = QtCore.Qt.ItemDataRole.UserRole + 1
    Control = Time + 1
    Point = Time + 2
    Detail = Time + 3
    Warning = Time + 4

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self.rows: list[tuple[str, str, str, str, bool]] = []

    def roleNames(self) -> dict[int, bytes]:  # noqa: N802 - Qt name
        return {
            self.Time: b"time", self.Control: b"control", self.Point: b"point",
            self.Detail: b"detail", self.Warning: b"warning",
        }

    def rowCount(  # noqa: N802 - Qt name
        self, parent: QtCore.QModelIndex = QtCore.QModelIndex()  # noqa: B008
    ) -> int:
        return 0 if parent.isValid() else len(self.rows)

    def data(
        self, index: QtCore.QModelIndex,
        role: int = QtCore.Qt.ItemDataRole.DisplayRole,
    ) -> Any:  # noqa: ANN401
        if not index.isValid() or not 0 <= index.row() < len(self.rows):
            return None
        col = role - self.Time
        if 0 <= col <= 4:
            return self.rows[index.row()][col]
        return None

    def show(self, rows: list[tuple[str, str, str, str, bool]]) -> None:
        old = self.rows
        if len(rows) >= len(old) and rows[: len(old)] == old:
            if len(rows) > len(old):
                self.beginInsertRows(QtCore.QModelIndex(), len(old), len(rows) - 1)
                self.rows = rows
                self.endInsertRows()
            return
        self.beginResetModel()
        self.rows = rows
        self.endResetModel()


@ta.QmlElement
class TraceSwitch(QtCore.QObject):
    """Tracing on or off (the Debug menu's Tracing item and the tab's
    switch). Never saved: tracing is off at every start."""

    changed = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        signals().changed.connect(self.changed)

    def _set_on(self, on: bool) -> None:
        trace.set_enabled(bool(on))

    on = QtCore.Property(bool, lambda self: trace.enabled(), _set_on, notify=changed)

    @QtCore.Slot()
    def toggle(self) -> None:
        trace.set_enabled(not trace.enabled())


@ta.QmlElement
class TraceView(QtCore.QObject):
    """The Trace tab. refresh() is polled while the tab shows."""

    changed = QtCore.Signal()
    linesAdded = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._tree = TraceTree(self)
        self._lines = TraceLines(self)
        self._version = -1
        self._find = ""
        self._warnings_only = False
        self._points = set(POINTS)
        self._all: list[tuple[str, str, str, str, bool]] = []
        self._since = ""
        self._notice = ""
        self._file = ""
        signals().changed.connect(self._switched)
        self._tree.rebuild()

    @QtCore.Slot()
    def _switched(self) -> None:
        self._version = -1
        self.refresh()
        self.changed.emit()

    # --- state ---------------------------------------------------------------

    def _set_on(self, on: bool) -> None:
        trace.set_enabled(bool(on))

    tracing = QtCore.Property(
        bool, lambda self: trace.enabled(), _set_on, notify=changed
    )

    @QtCore.Property(QtCore.QObject, constant=True)
    def tree(self) -> TraceTree:
        return self._tree

    @QtCore.Property(QtCore.QObject, constant=True)
    def lines(self) -> TraceLines:
        return self._lines

    @QtCore.Property(str, notify=changed)
    def sinceText(self) -> str:  # noqa: N802 - QML name
        return self._since

    @QtCore.Property(str, notify=changed)
    def notice(self) -> str:
        return self._notice

    @QtCore.Property(bool, notify=changed)
    def hidhide(self) -> bool:
        return trace.hidhide_ticked()

    @QtCore.Property(int, notify=changed)
    def deviceCount(self) -> int:  # noqa: N802 - QML name
        return self._tree.devices

    @QtCore.Property(int, notify=changed)
    def controlCount(self) -> int:  # noqa: N802 - QML name
        return self._tree.controls

    @QtCore.Property(int, notify=changed)
    def lineCount(self) -> int:  # noqa: N802 - QML name
        return len(self._all)

    @QtCore.Property(int, notify=changed)
    def shownCount(self) -> int:  # noqa: N802 - QML name
        return len(self._lines.rows)

    @QtCore.Property(str, notify=changed)
    def fileText(self) -> str:  # noqa: N802 - QML name
        return self._file

    @QtCore.Property(list, constant=True)
    def pointNames(self) -> list:  # noqa: N802 - QML name
        return list(POINTS)

    @QtCore.Property(list, notify=changed)
    def points(self) -> list:
        return [p for p in POINTS if p in self._points]

    @QtCore.Property(str, notify=changed)
    def pointsText(self) -> str:  # noqa: N802 - QML name
        if len(self._points) == len(POINTS):
            return "All"
        if not self._points:
            return "None"
        return " · ".join(p for p in POINTS if p in self._points)

    find = QtCore.Property(
        str, lambda self: self._find, lambda self, v: self._filter("_find", str(v)),
        notify=changed,
    )
    warningsOnly = QtCore.Property(  # noqa: N815 - QML name
        bool, lambda self: self._warnings_only,
        lambda self, v: self._filter("_warnings_only", bool(v)), notify=changed,
    )

    def _filter(self, name: str, value: object) -> None:
        if getattr(self, name) != value:
            setattr(self, name, value)
            self._apply()
            self.changed.emit()

    def _apply(self) -> None:
        shown_points = {p for name in self._points for p in POINTS[name]}
        needle = self._find.strip().casefold()
        rows = [
            line for line in self._all
            if line[2] in shown_points
            and (not self._warnings_only or line[4])
            and (not needle or needle in " ".join(line[:4]).casefold())
        ]
        before = len(self._lines.rows)
        self._lines.show(rows)
        if len(rows) > before:
            self.linesAdded.emit()

    # --- slots ---------------------------------------------------------------

    @QtCore.Slot()
    def refresh(self) -> None:
        notify = False
        since = since_text()
        notice = trace.notice()
        size = trace.file_size()
        older = trace.file_path().with_name(trace.FILE_NAME + ".1").is_file()
        file_text = (
            f"{trace.FILE_NAME} {_size_text(size)} of "
            f"{trace.FILE_MAX_BYTES // (1024 * 1024)} MB"
            + (" (one older copy kept)" if older else "")
        )
        fresh = (("_since", since), ("_notice", notice), ("_file", file_text))
        for name, value in fresh:
            if getattr(self, name) != value:
                setattr(self, name, value)
                notify = True
        current = trace.version()
        if current != self._version:
            self._version = current
            self._all = trace.lines()
            self._apply()
            notify = True
        if notify:
            self.changed.emit()

    @QtCore.Slot()
    def reloadTree(self) -> None:  # noqa: N802 - QML name
        """Devices plugged or the profile changed: the list again."""
        self._tree.rebuild()
        self.changed.emit()

    @QtCore.Slot(str)
    def toggleOpen(self, device: str) -> None:  # noqa: N802 - QML name
        self._tree.toggle_open(device)

    @QtCore.Slot(str, bool)
    def setDevice(self, device: str, on: bool) -> None:  # noqa: N802 - QML name
        trace.set_device(device, on)
        self.reloadTree()

    @QtCore.Slot(str, str, int, bool)
    def setTick(  # noqa: N802 - QML name
        self, device: str, kind: str, index: int, on: bool
    ) -> None:
        trace.set_tick(device, kind, index, on)
        self.reloadTree()

    @QtCore.Slot(str, bool)
    def setOutOfStep(self, device: str, on: bool) -> None:  # noqa: N802 - QML name
        trace.set_oos(device, on)
        self.reloadTree()

    @QtCore.Slot(bool)
    def setHidhide(self, on: bool) -> None:  # noqa: N802 - QML name
        trace.set_hidhide(on)
        self.reloadTree()

    @QtCore.Slot(str, bool)
    def setPoint(self, name: str, on: bool) -> None:  # noqa: N802 - QML name
        if name not in POINTS:
            return
        if on:
            self._points.add(name)
        else:
            self._points.discard(name)
        self._apply()
        self.changed.emit()

    @QtCore.Slot(result=int)
    def noticeLine(self) -> int:  # noqa: N802 - QML name
        """The shown row of the latest warning (-1 when none is shown)."""
        rows = self._lines.rows
        for i in range(len(rows) - 1, -1, -1):
            if rows[i][4]:
                return i
        return -1

    @QtCore.Slot()
    def dismissNotice(self) -> None:  # noqa: N802 - QML name
        trace.clear_notice()
        self.refresh()

    @QtCore.Slot()
    def clearView(self) -> None:  # noqa: N802 - QML name
        """The view only; trace.log keeps every line."""
        trace.clear_view()
        self.refresh()

    @QtCore.Slot()
    def showFile(self) -> None:  # noqa: N802 - QML name
        path = trace.file_path()
        target = path if path.is_file() else path.parent
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(target)))

    @QtCore.Slot()
    def copyShown(self) -> None:  # noqa: N802 - QML name
        clipboard = QtGui.QGuiApplication.clipboard()
        if clipboard is not None:
            clipboard.setText("\n".join(
                "  ".join(row[:4]) for row in self._lines.rows
            ))
