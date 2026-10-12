# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The Xbox Output View's list (03 S115-S139, 05 S121-S135): one parent row
per pad control in pad order, one child line per source bound to it. View
only: the shared ControlTree draws it read-only, so there is no undo, no
move and no action pane here. Live bars and dots come from what the Xbox
output module really sends (output.xbox_state)."""

from __future__ import annotations

from typing import Any

from PySide6 import QtCore

import gremlin.ui.type_aliases as ta
from gremlin import shared_state
from gremlin.modules import output
from gremlin.signal import signal
from gremlin.ui.control_layout import ROW_DEFAULTS
from gremlin.ui.device import QML_IMPORT_MAJOR_VERSION, QML_IMPORT_NAME
from gremlin.ui.input_pairing import device_label
from gremlin.ui.xbox_device_model import incoming_list
from gremlin.ui.xbox_maps import xbox_maps_for_item
from vigem.xbox import XboxTarget

assert QML_IMPORT_NAME == "Gremlin.Device"
assert QML_IMPORT_MAJOR_VERSION == 1

_ROLES = {**ROW_DEFAULTS, "fixedGroup": True, "liveIndex": -1, "sending": False}

TYPE_CHOICES = [
    {"label": "All types", "value": "all"},
    {"label": "Sticks", "value": "stick"},
    {"label": "Triggers", "value": "trigger"},
    {"label": "Buttons", "value": "button"},
    {"label": "D-Pad", "value": "dpad"},
]
FILTERS = [{"label": "Only controls with something sending", "name": "sending"}]

_DPAD = {
    XboxTarget.DPAD_UP,
    XboxTarget.DPAD_DOWN,
    XboxTarget.DPAD_LEFT,
    XboxTarget.DPAD_RIGHT,
    XboxTarget.DPAD,
}

# The live poll's step (the pad sections' rate, xbox_viewer.XboxPadLive).
POLL_MS = 50


def type_of(target: XboxTarget) -> str:
    """The Find bar's type word: stick, trigger, button or dpad."""
    if target in _DPAD:
        return "dpad"
    return target.kind  # stick, trigger, button


def kind_of(target: XboxTarget) -> str:
    """The row's icon and live kind: axis, button or hat."""
    word = type_of(target)
    if word in ("stick", "trigger"):
        return "axis"
    return "hat" if word == "dpad" else "button"


@ta.QmlElement
class XboxOutputListModel(QtCore.QAbstractListModel):
    """Rows for the shared ControlTree: parents in pad order, children per
    source. Keys: "parent:<axis|button|hat>:<target>", "child:<target>:<n>"."""

    roles = {
        QtCore.Qt.ItemDataRole.UserRole + 1 + i: QtCore.QByteArray(name.encode())
        for i, name in enumerate(_ROLES)
    }

    padIdChanged = QtCore.Signal()
    revisionChanged = QtCore.Signal()
    stampChanged = QtCore.Signal()
    liveActiveChanged = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._pad_id = 1
        self._targets = list(XboxTarget)
        self._rows: list[dict] = []
        self._search = ""
        self._type_filter = "all"
        self._sending_only = False
        self._selected: list[str] = []
        self._values: dict[str, float] = {}
        self._stamp = 0
        self._live_active = False
        # One read for a burst: a Logical Device edit sends two notices.
        self._soon = QtCore.QTimer(self)
        self._soon.setSingleShot(True)
        self._soon.setInterval(0)
        self._soon.timeout.connect(self.reload)
        self._poll = QtCore.QTimer(self)
        self._poll.setInterval(POLL_MS)
        self._poll.timeout.connect(self._poll_once)
        signal.bindingsChanged.connect(self._reload_soon)
        signal.deviceNamesChanged.connect(self._reload_soon)
        signal.logicalDeviceModified.connect(self._reload_soon)
        self._rebuild()

    # Rows.

    @QtCore.Slot()
    def _reload_soon(self) -> None:
        self._soon.start()

    @QtCore.Slot()
    def reload(self) -> None:
        self._rebuild()

    def _matches(self, target: XboxTarget, sources: list[str]) -> bool:
        type_filter = self._type_filter
        if type_filter not in ("", "all") and type_of(target) != type_filter:
            return False
        if self._sending_only and not sources:
            return False
        words = self._search.lower().split()
        if not words:
            return True
        hay = " ".join([target.label, *sources]).lower()
        return all(word in hay for word in words)

    def _rebuild(self) -> None:
        rows: list[dict] = []
        for index, target in enumerate(self._targets):
            sources = incoming_list(self._pad_id, target)
            if not self._matches(target, sources):
                continue
            key = f"parent:{kind_of(target)}:{target.value}"
            rows.append(
                {
                    **_ROLES,
                    "rowKind": "parent",
                    "key": key,
                    "title": target.label,
                    "systemName": target.label,
                    "childCount": len(sources),
                    "liveIndex": index,
                    "sending": bool(sources),
                }
            )
            for n, text in enumerate(sources):
                rows.append(
                    {
                        **_ROLES,
                        "rowKind": "child",
                        "key": f"child:{target.value}:{n}",
                        "title": text,
                        "parentKey": key,
                        "sequenceIndex": n,
                        "sending": True,
                    }
                )
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()
        self.revisionChanged.emit()

    def rowCount(self, parent: ta.ModelIndex = QtCore.QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def data(
        self, index: ta.ModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole
    ) -> Any:  # noqa: ANN401
        if not index.isValid() or not (0 <= index.row() < len(self._rows)):
            return None
        name = self.roles.get(role)
        if name is None:
            return None
        return self._rows[index.row()].get(name.toStdString())

    def roleNames(self) -> dict[int, QtCore.QByteArray]:
        return self.roles

    # The Find bar.

    @QtCore.Slot(str, str, bool)
    def setFilter(self, search: str, type_name: str, sending_only: bool) -> None:
        self._search = (search or "").strip()
        self._type_filter = type_name or "all"
        self._sending_only = bool(sending_only)
        self._rebuild()

    @QtCore.Slot(bool)
    def setCantSendOnly(self, _on: bool) -> None:
        """Not on this view (no "Can't be sent" tick); kept for the shared bar."""

    @QtCore.Slot()
    def undo(self) -> None:
        """View only: nothing to undo."""

    @QtCore.Slot()
    def redo(self) -> None:
        """View only: nothing to redo."""

    @QtCore.Slot("QStringList")
    def setSelection(self, keys: list) -> None:
        self._selected = [str(key) for key in keys if str(key).startswith("parent:")]

    @QtCore.Slot(int, result=str)
    def keyAt(self, row: int) -> str:
        if 0 <= row < len(self._rows):
            return str(self._rows[row]["key"])
        return ""

    def selected(self) -> list[str]:
        return list(self._selected)

    @QtCore.Property(int, notify=revisionChanged)
    def parentCount(self) -> int:
        return sum(1 for row in self._rows if row["rowKind"] == "parent")

    @QtCore.Property(bool, notify=revisionChanged)
    def canUndo(self) -> bool:
        return False

    @QtCore.Property(bool, notify=revisionChanged)
    def canRedo(self) -> bool:
        return False

    @QtCore.Property(str, notify=revisionChanged)
    def undoTip(self) -> str:
        return ""

    @QtCore.Property(str, notify=revisionChanged)
    def redoTip(self) -> str:
        return ""

    @QtCore.Property(str, notify=revisionChanged)
    def lastChange(self) -> str:
        return ""

    @QtCore.Property(str, notify=revisionChanged)
    def undone(self) -> str:
        return ""

    @QtCore.Property(list, constant=True)
    def typeChoices(self) -> list:
        return [dict(choice) for choice in TYPE_CHOICES]

    @QtCore.Property(list, constant=True)
    def filters(self) -> list:
        return [dict(tick) for tick in FILTERS]

    # The pad.

    def _get_pad_id(self) -> int:
        return self._pad_id

    def _set_pad_id(self, pad_id: int) -> None:
        ident = max(1, min(4, int(pad_id)))
        if ident == self._pad_id:
            return
        self._pad_id = ident
        self._values = {}
        self._rebuild()
        self._bump()
        self.padIdChanged.emit()

    padId = QtCore.Property(
        int, fget=_get_pad_id, fset=_set_pad_id, notify=padIdChanged
    )

    # Live (05 S131): what the Xbox output module sends, read on a timer
    # only while the page says the profile runs with Live on.

    def _get_live_active(self) -> bool:
        return self._live_active

    def _set_live_active(self, on: bool) -> None:
        on = bool(on)
        if on == self._live_active:
            return
        self._live_active = on
        if on:
            self._poll.start()
            self._poll_once()
        else:
            self._poll.stop()
            if self._values:
                self._values = {}
                self._bump()
        self.liveActiveChanged.emit()

    liveActive = QtCore.Property(
        bool, fget=_get_live_active, fset=_set_live_active, notify=liveActiveChanged
    )

    @QtCore.Slot()
    def _poll_once(self) -> None:
        snap = output.xbox_state(self._pad_id)
        if snap != self._values:
            self._values = dict(snap)
            self._bump()

    def _bump(self) -> None:
        self._stamp += 1
        self.stampChanged.emit()

    @QtCore.Property(int, notify=stampChanged)
    def stamp(self) -> int:
        return self._stamp

    @QtCore.Slot(int, result=str)
    def kindAt(self, index: int) -> str:
        if 0 <= index < len(self._targets):
            return kind_of(self._targets[index])
        return ""

    @QtCore.Slot(int, result=float)
    def valueAt(self, index: int) -> float:
        if not 0 <= index < len(self._targets):
            return 0.0
        target = self._targets[index]
        value = float(self._values.get(target.value, 0.0))
        # A trigger sends 0..1; the row's bar reads -1..1 from the left.
        if type_of(target) == "trigger":
            return value * 2.0 - 1.0
        return value



def pad_bindings() -> dict[int, dict[str, set[str]]]:
    """Pad -> device guid -> the pad's controls that device sends to: every
    Map to Xbox in the open profile, any mode."""
    profile = shared_state.current_profile
    if profile is None:
        return {}
    found: dict[int, dict[str, set[str]]] = {}
    for device_id, items in (profile.inputs or {}).items():
        for item in items or []:
            for pad, target in xbox_maps_for_item(item):
                devices = found.setdefault(int(pad), {})
                devices.setdefault(str(device_id), set()).add(str(target))
    return found


@ta.QmlElement
class XboxPadSectionsModel(QtCore.QAbstractListModel):
    """The Output View's pad sections (D-XBOX-PADS): one row per pad that is
    on (Xbox Setup) and has a Map to Xbox binding in any mode, pad order."""

    roles = {
        QtCore.Qt.ItemDataRole.UserRole + 1: QtCore.QByteArray(b"padId"),
        QtCore.Qt.ItemDataRole.UserRole + 2: QtCore.QByteArray(b"title"),
        QtCore.Qt.ItemDataRole.UserRole + 3: QtCore.QByteArray(b"drivenBy"),
        QtCore.Qt.ItemDataRole.UserRole + 4: QtCore.QByteArray(b"boundCount"),
    }
    countChanged = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._rows: list[dict] = []
        # One read for a burst: a Logical Device edit sends two notices.
        self._soon = QtCore.QTimer(self)
        self._soon.setSingleShot(True)
        self._soon.setInterval(0)
        self._soon.timeout.connect(self.reload)
        signal.bindingsChanged.connect(self._reload_soon)
        signal.deviceNamesChanged.connect(self._reload_soon)
        signal.logicalDeviceModified.connect(self._reload_soon)
        signal.xboxPadsChanged.connect(self._reload_soon)
        self.reload()

    @QtCore.Slot()
    def _reload_soon(self) -> None:
        self._soon.start()

    @QtCore.Slot()
    def reload(self) -> None:
        bound = pad_bindings()
        rows: list[dict] = []
        for pad in output.xbox_pads_on():
            devices = bound.get(int(pad))
            if not devices:
                continue
            names = sorted({device_label(guid) for guid in devices}, key=str.lower)
            controls = set().union(*devices.values())
            rows.append(
                {
                    "padId": int(pad),
                    "title": f"Xbox 360 {int(pad)}",
                    "drivenBy": ", ".join(names),
                    "boundCount": len(controls),
                }
            )
        if [r["padId"] for r in rows] == [r["padId"] for r in self._rows]:
            # The same pads: their sections stay (fold, scroll, live), only
            # the header facts change.
            if rows != self._rows:
                self._rows = rows
                self.dataChanged.emit(
                    self.index(0, 0), self.index(len(rows) - 1, 0)
                )
            return
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()
        self.countChanged.emit()

    def rowCount(self, parent: ta.ModelIndex = QtCore.QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def data(
        self, index: ta.ModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole
    ) -> Any:  # noqa: ANN401
        if not index.isValid() or not (0 <= index.row() < len(self._rows)):
            return None
        name = self.roles.get(role)
        if name is None:
            return None
        return self._rows[index.row()].get(name.toStdString())

    def roleNames(self) -> dict[int, QtCore.QByteArray]:
        return self.roles

    @QtCore.Property(int, notify=countChanged)
    def count(self) -> int:
        return len(self._rows)

    @QtCore.Property(list, constant=True)
    def typeChoices(self) -> list:
        """The page's one Find bar: the same choices as every pad's list."""
        return [dict(choice) for choice in TYPE_CHOICES]

    @QtCore.Property(list, constant=True)
    def filters(self) -> list:
        return [dict(tick) for tick in FILTERS]
