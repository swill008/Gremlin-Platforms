# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from PySide6 import QtCore

import dill
from gremlin import device_initialization, event_handler, shared_state
from gremlin.signal import signal
from gremlin.types import InputType
from gremlin.ui import input_pairing as pairing
from gremlin.ui import xbox_maps
import gremlin.ui.type_aliases as ta
from vigem.xbox import XboxProxy, XboxTarget

QML_IMPORT_NAME = "Gremlin.Device"
QML_IMPORT_MAJOR_VERSION = 1

OSC_GUID = "a7c3e91b-4d2f-4e18-9b06-2f8c1d5a6e70"

_CHIP = {
    "left_stick_x": "LSX",
    "left_stick_y": "LSY",
    "right_stick_x": "RSX",
    "right_stick_y": "RSY",
    "left_trigger": "LT",
    "right_trigger": "RT",
    "a": "A",
    "b": "B",
    "x": "X",
    "y": "Y",
    "left_shoulder": "LB",
    "right_shoulder": "RB",
    "left_thumb": "LS",
    "right_thumb": "RS",
    "start": "Str",
    "back": "Bak",
    "guide": "G",
    "dpad_up": "U",
    "dpad_down": "D",
    "dpad_left": "L",
    "dpad_right": "R",
    "dpad": "Hat",
}


def _norm(value: object) -> str:
    if value is not None and hasattr(value, "uuid"):
        value = value.uuid
    return str(value or "").strip().strip("{}").lower()


def _connected_keys() -> set[str]:
    keys: set[str] = set()
    for getter in (
        device_initialization.joystick_devices,
        device_initialization.physical_devices,
        device_initialization.input_devices,
    ):
        try:
            devices = getter()
        except Exception:
            continue
        for device in devices or []:
            key = _norm(getattr(device, "device_guid", ""))
            if key:
                keys.add(key)
    for guid in (dill.UUID_Keyboard, dill.UUID_LogicalDevice, OSC_GUID):
        keys.add(_norm(guid))
    return keys


def _xbox_maps_for_item(item) -> list[tuple[int, str]]:
    return xbox_maps.xbox_maps_for_item(item)


def _xbox_label(target: str) -> str:
    try:
        return XboxTarget.from_string(target).label
    except Exception:
        return str(target or "Xbox")


def _chip(target: str) -> str:
    key = str(target or "").strip().lower().replace("-", "_")
    return _CHIP.get(key, key[:3] or "xb")


def _pair_label(items) -> str:
    pads = sorted({pad for item in items or [] for pad, _ in _xbox_maps_for_item(item)})
    return ", ".join(f"Xbox 360 {pad}" for pad in pads)


def _source_label(input_type: InputType, identifier: int) -> str:
    if input_type == InputType.JoystickAxis:
        return pairing.AXIS_LABELS.get(identifier, f"A{identifier}")
    if input_type == InputType.JoystickHat:
        return f"H{identifier}"
    return str(identifier)


def _mapped_xbox_rows(guid: str, input_type: InputType) -> list[dict]:
    rows: list[dict] = []
    seen: set[tuple] = set()
    for item in pairing._items_for_guid(guid):
        if getattr(item, "input_type", None) != input_type:
            continue
        try:
            identifier = int(item.input_id)
        except Exception:
            continue
        src = _source_label(input_type, identifier)
        for pad, target in _xbox_maps_for_item(item):
            key = (identifier, pad, target)
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "identifier": identifier,
                    "label": src,
                    "xboxPad": int(pad),
                    "xboxTarget": str(target),
                    "xboxLabel": f"Xbox {pad} {_xbox_label(target)}",
                    "xboxChip": _chip(target),
                }
            )
    rows.sort(key=lambda row: (row["identifier"], row["xboxPad"], row["xboxTarget"]))
    return rows


def _pads_for_guid(guid: str) -> list[int]:
    pads = {
        pad
        for item in pairing._items_for_guid(guid)
        for pad, _ in _xbox_maps_for_item(item)
    }
    return sorted(pads)


class _XboxMappedModel(QtCore.QAbstractListModel):
    roles = {
        QtCore.Qt.ItemDataRole.UserRole + 1: QtCore.QByteArray(b"identifier"),
        QtCore.Qt.ItemDataRole.UserRole + 2: QtCore.QByteArray(b"label"),
        QtCore.Qt.ItemDataRole.UserRole + 3: QtCore.QByteArray(b"xboxPad"),
        QtCore.Qt.ItemDataRole.UserRole + 4: QtCore.QByteArray(b"xboxTarget"),
        QtCore.Qt.ItemDataRole.UserRole + 5: QtCore.QByteArray(b"xboxLabel"),
        QtCore.Qt.ItemDataRole.UserRole + 6: QtCore.QByteArray(b"xboxChip"),
    }
    guidChanged = QtCore.Signal()

    def __init__(self, input_type: InputType, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._input_type = input_type
        self._guid = ""
        self._rows: list[dict] = []

    def _reload(self) -> None:
        self.beginResetModel()
        self._rows = _mapped_xbox_rows(self._guid, self._input_type) if self._guid else []
        self.endResetModel()

    def _get_guid(self) -> str:
        return self._guid

    def _set_guid(self, guid: str) -> None:
        text = str(guid or "")
        if text == self._guid:
            return
        self._guid = text
        self._reload()
        self.guidChanged.emit()

    def rowCount(self, parent: ta.ModelIndex = QtCore.QModelIndex()) -> int:
        return len(self._rows)

    def data(self, index: ta.ModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._rows)):
            return None
        row = self._rows[index.row()]
        key = bytes(self.roles.get(role, b"")).decode()
        return row.get(key)

    def roleNames(self) -> dict[int, QtCore.QByteArray]:
        return self.roles

    guid = QtCore.Property(str, fget=_get_guid, fset=_set_guid, notify=guidChanged)


@ta.QmlElement
class XboxMappedAxisModel(_XboxMappedModel):
    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(InputType.JoystickAxis, parent)


@ta.QmlElement
class XboxMappedButtonModel(_XboxMappedModel):
    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(InputType.JoystickButton, parent)


@ta.QmlElement
class XboxMappedHatModel(_XboxMappedModel):
    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(InputType.JoystickHat, parent)


@ta.QmlElement
class XboxPadListModel(QtCore.QAbstractListModel):
    roles = {
        QtCore.Qt.ItemDataRole.UserRole + 1: QtCore.QByteArray(b"padId"),
    }
    guidChanged = QtCore.Signal()
    countChanged = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._guid = ""
        self._rows: list[dict] = []

    def _reload(self) -> None:
        self.beginResetModel()
        self._rows = [{"padId": pad} for pad in _pads_for_guid(self._guid)]
        self.endResetModel()
        self.countChanged.emit()

    def _get_guid(self) -> str:
        return self._guid

    def _set_guid(self, guid: str) -> None:
        text = str(guid or "")
        if text == self._guid:
            return
        self._guid = text
        self._reload()
        self.guidChanged.emit()

    def rowCount(self, parent: ta.ModelIndex = QtCore.QModelIndex()) -> int:
        return len(self._rows)

    def data(self, index: ta.ModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._rows)):
            return None
        return self._rows[index.row()].get("padId")

    def roleNames(self) -> dict[int, QtCore.QByteArray]:
        return self.roles

    def _get_count(self) -> int:
        return len(self._rows)

    guid = QtCore.Property(str, fget=_get_guid, fset=_set_guid, notify=guidChanged)
    count = QtCore.Property(int, fget=_get_count, notify=countChanged)


@ta.QmlElement
class XboxViewerDeviceModel(QtCore.QAbstractListModel):
    countChanged = QtCore.Signal()
    roles = {
        QtCore.Qt.ItemDataRole.UserRole + 1: QtCore.QByteArray(b"guid"),
        QtCore.Qt.ItemDataRole.UserRole + 2: QtCore.QByteArray(b"name"),
        QtCore.Qt.ItemDataRole.UserRole + 3: QtCore.QByteArray(b"pairLabel"),
    }

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._rows: list[dict] = []
        self.reload()
        signal.profileChanged.connect(self.reload)
        event_handler.EventListener().device_change_event.connect(self.reload)

    @QtCore.Slot()
    def reload(self) -> None:
        self.beginResetModel()
        self._rows = []
        connected = _connected_keys()
        profile = shared_state.current_profile
        if profile is not None:
            for device_id, items in (profile.inputs or {}).items():
                if not any(_xbox_maps_for_item(item) for item in items or []):
                    continue
                guid = str(device_id)
                if _norm(guid) not in connected:
                    continue
                self._rows.append(
                    {
                        "guid": guid,
                        "name": pairing.device_label(guid),
                        "pairLabel": _pair_label(items),
                    }
                )
        self._rows.sort(key=lambda row: str(row["name"]).lower())
        self.endResetModel()
        self.countChanged.emit()

    def rowCount(self, parent: ta.ModelIndex = QtCore.QModelIndex()) -> int:
        return len(self._rows)

    def data(self, index: ta.ModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._rows)):
            return None
        row = self._rows[index.row()]
        key = bytes(self.roles.get(role, b"")).decode()
        return row.get(key)

    def roleNames(self) -> dict[int, QtCore.QByteArray]:
        return self.roles

    def _get_count(self) -> int:
        return len(self._rows)

    count = QtCore.Property(int, fget=_get_count, notify=countChanged)


@ta.QmlElement
class XboxLiveThrottle(QtCore.QObject):
    stampChanged = QtCore.Signal()
    axisStampChanged = QtCore.Signal()
    buttonStampChanged = QtCore.Signal()
    xboxStampChanged = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._guid = ""
        self._uid = None
        self._hw_axis: dict[int, float] = {}
        self._hw_button: dict[int, float] = {}
        self._xbox: dict[int, dict[str, float]] = {}
        self._xbox_pads: set[int] = set()
        self._stamp = 0
        self._axis_stamp = 0
        self._button_stamp = 0
        self._xbox_stamp = 0
        self._axis_dirty = False
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(50)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._flush)
        self._xbox_timer = QtCore.QTimer(self)
        self._xbox_timer.setInterval(50)
        self._xbox_timer.timeout.connect(self._poll_xbox)
        event_handler.EventListener().joystick_event.connect(self._on_event)

    def _bump(self) -> None:
        self._stamp += 1
        self.stampChanged.emit()

    def _bump_axis(self) -> None:
        self._axis_stamp += 1
        self.axisStampChanged.emit()

    def _bump_button(self) -> None:
        self._button_stamp += 1
        self.buttonStampChanged.emit()

    def _flush(self) -> None:
        if self._axis_dirty:
            self._axis_dirty = False
            self._bump_axis()

    def _get_guid(self) -> str:
        return self._guid

    def _set_guid(self, guid: str) -> None:
        self._guid = str(guid or "")
        self._uid = pairing._guid(self._guid)
        self._hw_axis.clear()
        self._hw_button.clear()
        self._xbox.clear()
        self._xbox_pads = set(_pads_for_guid(self._guid))
        if self._xbox_pads:
            if not self._xbox_timer.isActive():
                self._xbox_timer.start()
        else:
            self._xbox_timer.stop()
        self._bump()
        self._poll_xbox()

    def _on_event(self, event: event_handler.Event) -> None:
        if self._uid is None:
            return
        ev = _norm(event.device_guid)
        if ev != _norm(self._uid):
            return
        if event.event_type == InputType.JoystickAxis:
            try:
                self._hw_axis[int(event.identifier)] = float(event.value)
            except Exception:
                return
            self._axis_dirty = True
            if not self._timer.isActive():
                self._timer.start()
            return
        if event.event_type == InputType.JoystickButton:
            try:
                self._hw_button[int(event.identifier)] = (
                    1.0 if event.is_pressed else 0.0
                )
            except Exception:
                return
            self._bump_button()

    def _poll_xbox(self) -> None:
        changed = False
        proxy = XboxProxy()
        for pad_id in self._xbox_pads:
            snap = proxy.snapshot(pad_id) or {}
            if self._xbox.get(pad_id) != snap:
                self._xbox[pad_id] = snap
                changed = True
        if changed:
            self._xbox_stamp += 1
            self.xboxStampChanged.emit()
            self._bump_axis()
            self._bump_button()

    @QtCore.Slot(int, result=float)
    def axisValue(self, identifier: int) -> float:
        return float(self._hw_axis.get(int(identifier), 0.0))

    @QtCore.Slot(int, result=float)
    def buttonValue(self, identifier: int) -> float:
        return float(self._hw_button.get(int(identifier), 0.0))

    @QtCore.Slot(int, str, result=float)
    def xboxValue(self, pad_id: int, target: str) -> float:
        key = str(target or "").strip().lower().replace("-", "_")
        return float(self._xbox.get(int(pad_id), {}).get(key, 0.0))

    def _get_stamp(self) -> int:
        return self._stamp

    def _get_axis_stamp(self) -> int:
        return self._axis_stamp

    def _get_button_stamp(self) -> int:
        return self._button_stamp

    def _get_xbox_stamp(self) -> int:
        return self._xbox_stamp

    guid = QtCore.Property(str, fget=_get_guid, fset=_set_guid)
    stamp = QtCore.Property(int, fget=_get_stamp, notify=stampChanged)
    axisStamp = QtCore.Property(int, fget=_get_axis_stamp, notify=axisStampChanged)
    buttonStamp = QtCore.Property(int, fget=_get_button_stamp, notify=buttonStampChanged)
    xboxStamp = QtCore.Property(int, fget=_get_xbox_stamp, notify=xboxStampChanged)
