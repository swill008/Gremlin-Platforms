# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The Xbox Output View's pad sections (03 S139, D-XBOX-PADS): the chip rows
of one pad, one line per device that drives it, and the live source that
lights that pad's face and chips from what the Xbox output module sends."""

from __future__ import annotations

from PySide6 import QtCore

import gremlin.ui.type_aliases as ta
from gremlin import event_handler, shared_state
from gremlin.modules import output, wiring
from gremlin.modules.ids import guid_key
from gremlin.modules.runtime import InputModuleRuntime
from gremlin.signal import signal
from gremlin.types import InputType
from gremlin.ui import input_pairing as pairing
from gremlin.ui.xbox_maps import xbox_maps_for_item

QML_IMPORT_NAME = "Gremlin.Device"
QML_IMPORT_MAJOR_VERSION = 1

# The live poll's step.
POLL_MS = 50

_KINDS: dict[object, str] = {
    InputType.JoystickAxis: "axis",
    InputType.JoystickButton: "button",
    InputType.JoystickHat: "hat",
}


def _chip(target: str) -> str:
    key = str(target or "").strip().lower().replace("-", "_")
    return wiring.XBOX_SHORT.get(key, key[:3] or "xb")


def _source_label(input_type: InputType, identifier: int) -> str:
    if input_type == InputType.JoystickAxis:
        return wiring.AXIS_SHORT.get(identifier, f"A{identifier}")
    if input_type == InputType.JoystickHat:
        return f"H{identifier}"
    return str(identifier)


def pad_chips(pad: int) -> list[dict]:
    """One row per device that drives the pad (a Map to Xbox in any mode):
    its axes' and its buttons' (and hats') chips, in input order."""
    profile = shared_state.current_profile
    if profile is None:
        return []
    rows: list[dict] = []
    for device_id, items in (profile.inputs or {}).items():
        axes: list[dict] = []
        buttons: list[dict] = []
        seen: set[tuple] = set()
        for item in items or []:
            input_type = getattr(item, "input_type", None)
            kind = _KINDS.get(input_type)
            if kind is None or not isinstance(input_type, InputType):
                continue
            identifier = getattr(item, "input_id", None)
            if not isinstance(identifier, int):
                continue
            for pid, target in xbox_maps_for_item(item):
                key = (kind, identifier, target)
                if pid != pad or key in seen:
                    continue
                seen.add(key)
                chip = {
                    "identifier": identifier,
                    "label": _source_label(input_type, identifier),
                    "kind": kind,
                    "xboxTarget": str(target),
                    "xboxLabel": wiring.xbox_dest(pad, target),
                    "xboxChip": _chip(target),
                }
                (axes if kind == "axis" else buttons).append(chip)
        if not axes and not buttons:
            continue
        order = {"axis": 0, "button": 1, "hat": 2}
        for chips in (axes, buttons):
            chips.sort(
                key=lambda c: (order[c["kind"]], c["identifier"], c["xboxTarget"])
            )
        guid = str(device_id)
        rows.append(
            {
                "guid": guid,
                "name": pairing.device_label(guid),
                "axes": axes,
                "buttons": buttons,
            }
        )
    rows.sort(key=lambda row: str(row["name"]).lower())
    return rows


@ta.QmlElement
class XboxPadChipsModel(QtCore.QAbstractListModel):
    """The chip rows of one pad section: one row per driving device."""

    roles = {
        QtCore.Qt.ItemDataRole.UserRole + 1: QtCore.QByteArray(b"guid"),
        QtCore.Qt.ItemDataRole.UserRole + 2: QtCore.QByteArray(b"name"),
        QtCore.Qt.ItemDataRole.UserRole + 3: QtCore.QByteArray(b"axes"),
        QtCore.Qt.ItemDataRole.UserRole + 4: QtCore.QByteArray(b"buttons"),
    }
    padIdChanged = QtCore.Signal()
    countChanged = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._pad_id = 1
        self._rows: list[dict] = []
        # What drives what and the devices' shown names (D-01-OWNER-NOTICES).
        signal.bindingsChanged.connect(self.reload)
        signal.deviceNamesChanged.connect(self.reload)
        self.reload()

    @QtCore.Slot()
    def reload(self) -> None:
        self.beginResetModel()
        self._rows = pad_chips(self._pad_id)
        self.endResetModel()
        self.countChanged.emit()

    def rowCount(self, parent: ta.ModelIndex = QtCore.QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def data(
        self, index: ta.ModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole
    ) -> object:
        if not index.isValid() or not (0 <= index.row() < len(self._rows)):
            return None
        name = self.roles.get(role)
        if name is None:
            return None
        return self._rows[index.row()].get(name.toStdString())

    def roleNames(self) -> dict[int, QtCore.QByteArray]:
        return self.roles

    def _get_pad_id(self) -> int:
        return self._pad_id

    def _set_pad_id(self, pad_id: int) -> None:
        if int(pad_id) == self._pad_id:
            return
        self._pad_id = int(pad_id)
        self.reload()
        self.padIdChanged.emit()

    def _get_count(self) -> int:
        return len(self._rows)

    def _get_axis_lines(self) -> int:
        return sum(1 for row in self._rows if row["axes"])

    def _get_button_lines(self) -> int:
        return sum(1 for row in self._rows if row["buttons"])

    padId = QtCore.Property(
        int, fget=_get_pad_id, fset=_set_pad_id, notify=padIdChanged
    )
    count = QtCore.Property(int, fget=_get_count, notify=countChanged)
    axisLines = QtCore.Property(int, fget=_get_axis_lines, notify=countChanged)
    buttonLines = QtCore.Property(int, fget=_get_button_lines, notify=countChanged)


@ta.QmlElement
class XboxPadLive(QtCore.QObject):
    """Live values for one pad section: what the Xbox output module sends to
    the pad (output.xbox_state) and the claimed inputs of the devices that
    drive it (the input module feed, not raw hardware). Polls only while
    active (the profile runs)."""

    padIdChanged = QtCore.Signal()
    activeChanged = QtCore.Signal()
    axisStampChanged = QtCore.Signal()
    buttonStampChanged = QtCore.Signal()
    xboxStampChanged = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._pad_id = 1
        self._active = False
        self._hw_axis: dict[tuple[str, int], float] = {}
        self._hw_button: dict[tuple[str, int], float] = {}
        self._xbox: dict[str, float] = {}
        self._axis_stamp = 0
        self._button_stamp = 0
        self._xbox_stamp = 0
        self._axis_dirty = False
        self._axis_timer = QtCore.QTimer(self)
        self._axis_timer.setInterval(POLL_MS)
        self._axis_timer.setSingleShot(True)
        self._axis_timer.timeout.connect(self._flush_axes)
        self._poll = QtCore.QTimer(self)
        self._poll.setInterval(POLL_MS)
        self._poll.timeout.connect(self._poll_once)
        InputModuleRuntime().event.connect(self._on_event)

    # Hardware side.

    def _on_event(self, event: event_handler.Event) -> None:
        if not self._active:
            return
        identifier = event.identifier
        if not isinstance(identifier, int):
            return
        key = (guid_key(event.device_guid), identifier)
        if event.event_type == InputType.JoystickAxis:
            try:
                self._hw_axis[key] = float(event.value)
            except (TypeError, ValueError):
                return
            self._axis_dirty = True
            if not self._axis_timer.isActive():
                self._axis_timer.start()
        elif event.event_type == InputType.JoystickButton:
            self._hw_button[key] = 1.0 if event.is_pressed else 0.0
            self._bump_buttons()

    @QtCore.Slot()
    def _flush_axes(self) -> None:
        if self._axis_dirty:
            self._axis_dirty = False
            self._bump_axes()

    def _bump_axes(self) -> None:
        self._axis_stamp += 1
        self.axisStampChanged.emit()

    def _bump_buttons(self) -> None:
        self._button_stamp += 1
        self.buttonStampChanged.emit()

    @QtCore.Slot(str, int, result=float)
    def hwAxis(self, guid: str, identifier: int) -> float:
        return float(self._hw_axis.get((guid_key(guid), int(identifier)), 0.0))

    @QtCore.Slot(str, int, result=float)
    def hwButton(self, guid: str, identifier: int) -> float:
        return float(self._hw_button.get((guid_key(guid), int(identifier)), 0.0))

    # Xbox side.

    @QtCore.Slot()
    def _poll_once(self) -> None:
        snap = dict(output.xbox_state(self._pad_id))
        if snap != self._xbox:
            self._xbox = snap
            self._xbox_stamp += 1
            self.xboxStampChanged.emit()

    @QtCore.Slot(int, str, result=float)
    def xboxValue(self, pad_id: int, target: str) -> float:
        if int(pad_id) != self._pad_id:
            return 0.0
        key = str(target or "").strip().lower().replace("-", "_")
        return float(self._xbox.get(key, 0.0))

    def _clear(self) -> None:
        self._hw_axis.clear()
        self._hw_button.clear()
        self._xbox = {}
        self._bump_axes()
        self._bump_buttons()
        self._xbox_stamp += 1
        self.xboxStampChanged.emit()

    # Properties.

    def _get_pad_id(self) -> int:
        return self._pad_id

    def _set_pad_id(self, pad_id: int) -> None:
        if int(pad_id) == self._pad_id:
            return
        self._pad_id = int(pad_id)
        self._clear()
        if self._active:
            self._poll_once()
        self.padIdChanged.emit()

    def _get_active(self) -> bool:
        return self._active

    def _set_active(self, on: bool) -> None:
        on = bool(on)
        if on == self._active:
            return
        self._active = on
        if on:
            self._poll.start()
            self._poll_once()
        else:
            self._poll.stop()
            self._axis_timer.stop()
            self._clear()
        self.activeChanged.emit()

    def _get_axis_stamp(self) -> int:
        return self._axis_stamp

    def _get_button_stamp(self) -> int:
        return self._button_stamp

    def _get_xbox_stamp(self) -> int:
        return self._xbox_stamp

    padId = QtCore.Property(
        int, fget=_get_pad_id, fset=_set_pad_id, notify=padIdChanged
    )
    active = QtCore.Property(
        bool, fget=_get_active, fset=_set_active, notify=activeChanged
    )
    axisStamp = QtCore.Property(int, fget=_get_axis_stamp, notify=axisStampChanged)
    buttonStamp = QtCore.Property(
        int, fget=_get_button_stamp, notify=buttonStampChanged
    )
    xboxStamp = QtCore.Property(int, fget=_get_xbox_stamp, notify=xboxStampChanged)
