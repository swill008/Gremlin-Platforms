# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The OSC Monitor's list (D-09-OSC-MONITOR): the last 200 OSC messages in
and out, newest last, with Pause, Clear, a filter and Show outgoing.

While active it holds OSC's port open through OscRuntime().hold_open(token),
even with no Run, and releases it after. qml/OscMonitorPanel.qml sets active
while the panel is shown, unfolded and its page (or the Pop out window) is
open (OSC rewrite OP8)."""

from __future__ import annotations

import time
from typing import Any

from PySide6 import QtCore

import gremlin.ui.type_aliases as ta
from gremlin import osc_traffic
from gremlin.ui.device import QML_IMPORT_MAJOR_VERSION, QML_IMPORT_NAME

assert QML_IMPORT_NAME == "Gremlin.Device"
assert QML_IMPORT_MAJOR_VERSION == 1

NO_INPUT = "no input"
# What the runtime notes as the matched input of a message from a sender
# not on the allow-list (gremlin.osc.BLOCKED, S160).
BLOCKED = "blocked"

_ROLES = (
    "time", "direction", "address", "values", "peer", "matched", "noInput",
    "hoverText", "blocked", "senderHost",
)


def is_blocked(entry: dict[str, Any]) -> bool:
    """An incoming message refused by the sender allow-list (S160)."""
    return entry.get("direction") == "in" and list(entry.get("matched") or []) == [
        BLOCKED
    ]


def peer_host(entry: dict[str, Any]) -> str:
    """The sender's host from the peer text "host:port" ("" for outgoing)."""
    if entry.get("direction") == "out":
        return ""
    peer = str(entry.get("peer") or "")
    return peer.rsplit(":", 1)[0] if ":" in peer else peer


def _runtime() -> object | None:
    """OscRuntime(), or None when OSC can't load."""
    try:
        from gremlin.osc import OscRuntime  # noqa: PLC0415  lazy: keeps imports light

        return OscRuntime()
    except Exception:  # noqa: BLE001
        return None


def _value_text(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:g}"
    if isinstance(value, (bytes, bytearray)):
        return f"<{len(value)} bytes>"
    return str(value)


def values_text(args: list[Any]) -> str:
    return ", ".join(_value_text(v) for v in args)


def time_text(stamp: float) -> str:
    whole = time.localtime(stamp)
    return time.strftime("%H:%M:%S", whole) + f".{int((stamp % 1) * 1000):03d}"


def hover_text(entry: dict[str, Any]) -> str:
    """A row's hover text: everything the columns may cut short, in full."""
    outgoing = entry.get("direction") == "out"
    lines = [str(entry.get("address", ""))]
    values = values_text(list(entry.get("args") or []))
    if values:
        lines.append(f"Values: {values}")
    peer = str(entry.get("peer", ""))
    if peer:
        lines.append(f"{'To' if outgoing else 'From'}: {peer}")
    if not outgoing:
        lines.append(f"Input: {', '.join(entry.get('matched') or []) or NO_INPUT}")
    return "\n".join(lines)


def add_settings(entry: dict[str, Any]) -> dict[str, Any]:
    """The Add window's settings for a message no input matched.

    The mode follows the program's guess (gremlin.osc.guess_input_type): no
    value, 0/1 or a value past ±1 is a Button, anything else an Axis. Text
    values become the input's data (Message + data)."""
    args = list(entry.get("args") or [])
    settings: dict[str, Any] = {
        "address": str(entry.get("address") or ""),
        "mode": "button",
        "cmd_mode": "message",
        "data": [],
        "source": 0,
        "range_min": 0.0,
        "range_max": 1.0,
        "trigger": None,
        "delay_ms": None,
        "values": values_text(args),
    }
    if not args:
        return settings
    first = args[0]
    if isinstance(first, str):
        settings["cmd_mode"] = "data"
        settings["data"] = [str(v) for v in args if isinstance(v, str)]
        return settings
    try:
        value = float(first)
    except (TypeError, ValueError):
        return settings
    if value in (0.0, 1.0) or abs(value) > 1.0:
        return settings
    settings["mode"] = "axis"
    if value < 0:
        settings["range_min"] = -1.0
    return settings


@ta.QmlElement
class OscMonitorModel(QtCore.QAbstractListModel):

    pausedChanged = QtCore.Signal()
    filterTextChanged = QtCore.Signal()
    showOutgoingChanged = QtCore.Signal()
    activeChanged = QtCore.Signal()
    countChanged = QtCore.Signal()

    roles = {
        QtCore.Qt.ItemDataRole.UserRole + i: QtCore.QByteArray(name.encode())
        for i, name in enumerate(_ROLES, start=1)
    }

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._all: list[dict[str, Any]] = []
        self._shown: list[dict[str, Any]] = []
        self._paused = False
        self._filter = ""
        self._show_out = True
        self._active = False
        self._token = f"osc-monitor-{id(self)}"

    # -- list -----------------------------------------------------------

    def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._shown)

    def roleNames(self) -> dict[int, QtCore.QByteArray]:
        return self.roles

    def data(self, index: QtCore.QModelIndex, role: int = 0) -> object:
        if not index.isValid() or not 0 <= index.row() < len(self._shown):
            return None
        name = bytes(self.roles.get(role, QtCore.QByteArray()).data()).decode()
        return self._role(self._shown[index.row()], name)

    @staticmethod
    def _role(entry: dict[str, Any], name: str) -> object:
        if name == "time":
            return time_text(float(entry.get("time", 0.0)))
        if name == "direction":
            return entry.get("direction", "in")
        if name == "address":
            return entry.get("address", "")
        if name == "values":
            return values_text(list(entry.get("args") or []))
        if name == "peer":
            return entry.get("peer", "")
        if name == "noInput":
            return entry.get("direction") == "in" and not entry.get("matched")
        if name == "blocked":
            return is_blocked(entry)
        if name == "senderHost":
            return peer_host(entry)
        if name == "hoverText":
            return hover_text(entry)
        if name == "matched":
            if entry.get("direction") != "in":
                return ""
            return ", ".join(entry.get("matched") or []) or NO_INPUT
        return None

    def _wanted(self, entry: dict[str, Any]) -> bool:
        if not self._show_out and entry.get("direction") == "out":
            return False
        needle = self._filter.strip().casefold()
        if not needle:
            return True
        hay = " ".join((
            str(entry.get("address", "")),
            values_text(list(entry.get("args") or [])),
            str(entry.get("peer", "")),
            ", ".join(entry.get("matched") or []),
        )).casefold()
        return needle in hay

    def _rebuild(self) -> None:
        self.beginResetModel()
        self._shown = [e for e in self._all if self._wanted(e)]
        self.endResetModel()
        self.countChanged.emit()

    def _on_note(self, entry: dict[str, Any]) -> None:
        if self._paused:
            return
        self._all.append(entry)
        dropped = len(self._all) > osc_traffic.LIMIT
        if dropped:
            gone = self._all.pop(0)
            if self._shown and self._shown[0] is gone:
                self.beginRemoveRows(QtCore.QModelIndex(), 0, 0)
                self._shown.pop(0)
                self.endRemoveRows()
        if self._wanted(entry):
            row = len(self._shown)
            self.beginInsertRows(QtCore.QModelIndex(), row, row)
            self._shown.append(entry)
            self.endInsertRows()
        self.countChanged.emit()

    # -- open / close ---------------------------------------------------

    def _get_active(self) -> bool:
        return self._active

    def _set_active(self, on: bool) -> None:
        on = bool(on)
        if on == self._active:
            return
        self._active = on
        runtime = _runtime()
        if on:
            self._all = osc_traffic.recent()
            self._rebuild()
            osc_traffic.add_listener(self._on_note)
            hold = getattr(runtime, "hold_open", None)
            if callable(hold):
                hold(self._token)
        else:
            osc_traffic.remove_listener(self._on_note)
            release = getattr(runtime, "release_open", None)
            if callable(release):
                release(self._token)
        self.activeChanged.emit()

    active = QtCore.Property(bool, _get_active, _set_active, notify=activeChanged)

    # -- controls -------------------------------------------------------

    def _get_paused(self) -> bool:
        return self._paused

    def _set_paused(self, on: bool) -> None:
        if bool(on) != self._paused:
            self._paused = bool(on)
            self.pausedChanged.emit()

    paused = QtCore.Property(bool, _get_paused, _set_paused, notify=pausedChanged)

    def _get_filter(self) -> str:
        return self._filter

    def _set_filter(self, text: str) -> None:
        if str(text) != self._filter:
            self._filter = str(text)
            self._rebuild()
            self.filterTextChanged.emit()

    filterText = QtCore.Property(
        str, _get_filter, _set_filter, notify=filterTextChanged
    )

    def _get_show_out(self) -> bool:
        return self._show_out

    def _set_show_out(self, on: bool) -> None:
        if bool(on) != self._show_out:
            self._show_out = bool(on)
            self._rebuild()
            self.showOutgoingChanged.emit()

    showOutgoing = QtCore.Property(
        bool, _get_show_out, _set_show_out, notify=showOutgoingChanged
    )

    def _get_count(self) -> int:
        return len(self._shown)

    count = QtCore.Property(int, _get_count, notify=countChanged)

    @QtCore.Slot()
    def clear(self) -> None:
        osc_traffic.clear()
        self._all = []
        self._rebuild()

    @QtCore.Slot(int, result="QVariantMap")
    def addSettings(self, row: int) -> dict[str, Any]:
        """Add as input…: the Add window's settings for a "no input" row
        ({} for any other row)."""
        if not 0 <= row < len(self._shown):
            return {}
        entry = self._shown[row]
        if not self._role(entry, "noInput"):
            return {}
        return add_settings(entry)

    @QtCore.Slot(str, result=str)
    def allowSender(self, host: str) -> str:
        """The row menu's "Allow this sender" (S160): adds the host to the
        server's allow-list; "" when added or already there, else why."""
        from gremlin.ui import osc_option  # noqa: PLC0415  lazy: keeps imports light

        try:
            ok, why = osc_option.add_sender(host)
        except OSError:
            return "Not written. The OSC file could not be saved."
        return "" if ok else why
