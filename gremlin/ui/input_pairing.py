# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import uuid

from PySide6 import QtCore

import dill
from gremlin import device_initialization, shared_state
from gremlin.modules import wiring
from gremlin.signal import signal
from gremlin.types import InputType
import gremlin.ui.type_aliases as ta

QML_IMPORT_NAME = "Gremlin.Device"
QML_IMPORT_MAJOR_VERSION = 1

def _guid(value: object) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(value or "").strip().strip("{}"))
    except Exception:
        return None


def _walk_actions(action) -> list:
    found = [action]
    getter = getattr(action, "get_actions", None)
    if not callable(getter):
        return found
    try:
        buckets = getter()
    except Exception:
        return found
    if isinstance(buckets, (list, tuple)):
        for bucket in buckets:
            if isinstance(bucket, (list, tuple)):
                for child in bucket:
                    found.extend(_walk_actions(child))
    return found


def _maps_for_item(item) -> list[tuple[int, object, int]]:
    out: list[tuple[int, object, int]] = []
    if item is None:
        return out
    for seq in getattr(item, "action_sequences", []) or []:
        root = getattr(seq, "root_action", None)
        if root is None:
            continue
        for action in _walk_actions(root):
            tag = getattr(action, "tag", "")
            if tag == "map-to-vjoy":
                try:
                    out.append(
                        (
                            int(action.vjoy_device_id),
                            getattr(action, "vjoy_input_type", None),
                            int(action.vjoy_input_id),
                        )
                    )
                except Exception:
                    continue
            elif tag == "map-to-xbox":
                # Count as mapped so ViewerDeviceModel includes the device.
                try:
                    out.append((int(getattr(action, "xbox_device_id", 1)), None, 0))
                except Exception:
                    out.append((1, None, 0))
    return out


def _dest_labels_for_item(item) -> list[str]:
    labels: list[str] = []
    if item is None:
        return labels
    for seq in getattr(item, "action_sequences", []) or []:
        root = getattr(seq, "root_action", None)
        if root is None:
            continue
        for action in _walk_actions(root):
            text = wiring.dest_label(action, short=True)
            if text:
                labels.append(text)
    return labels


def _items_for_guid(guid: str):
    profile = shared_state.current_profile
    if profile is None:
        return []
    uid = _guid(guid)
    if uid is None:
        return []
    return profile.inputs.get(uid, []) or []


def _vjoy_guid(vjoy_id: int) -> str:
    try:
        for device in device_initialization.vjoy_devices():
            if int(getattr(device, "vjoy_id", -1)) == int(vjoy_id):
                return str(device.device_guid)
    except Exception:
        return ""
    return ""


def _device_name(guid: str) -> str:
    uid = _guid(guid)
    hardware = str(guid)
    try:
        if uid is not None:
            hardware = device_initialization.device_name(uid) or hardware
    except Exception:
        pass
    return hardware


def device_label(guid: str) -> str:
    """Name to show for a device. DILL only knows hardware, so the built-in
    devices are named here; _device_name stays for module file lookups."""
    from gremlin.osc import OSC_DEVICE_UUID

    uid = _guid(guid)
    builtin = {
        dill.UUID_LogicalDevice: "Logical Device",
        dill.UUID_Keyboard: "Keyboard",
        OSC_DEVICE_UUID: "OSC",
    }
    if uid in builtin:
        return builtin[uid]
    return _device_name(guid)


def _mapped_rows(guid: str, input_type: InputType) -> list[dict]:
    rows: list[dict] = []
    seen: set[int] = set()
    for item in _items_for_guid(guid):
        if getattr(item, "input_type", None) != input_type:
            continue
        try:
            identifier = int(item.input_id)
        except Exception:
            continue
        dests = _dest_labels_for_item(item)
        vjoy_maps = [
            m for m in _maps_for_item(item)
            if m[1] is not None
        ]
        if not dests and not vjoy_maps:
            continue
        if identifier in seen:
            continue
        seen.add(identifier)
        if input_type == InputType.JoystickAxis:
            src = wiring.AXIS_SHORT.get(identifier, f"A{identifier}")
        elif input_type == InputType.JoystickHat:
            src = f"H{identifier}"
        else:
            src = str(identifier)
        vjoy_id = int(vjoy_maps[0][0]) if vjoy_maps else 0
        vinput = int(vjoy_maps[0][2]) if vjoy_maps else 0
        rows.append(
            {
                "identifier": identifier,
                "label": src,
                "vjoyId": vjoy_id,
                "vjoyInput": vinput,
                "vjoyLabel": " + ".join(dests) if dests else "",
                "vjoyGuid": _vjoy_guid(vjoy_id) if vjoy_id else "",
            }
        )
    rows.sort(key=lambda row: (row["identifier"], row["vjoyId"], row["vjoyInput"]))
    return rows


class _MappedModel(QtCore.QAbstractListModel):
    roles = {
        QtCore.Qt.ItemDataRole.UserRole + 1: QtCore.QByteArray(b"identifier"),
        QtCore.Qt.ItemDataRole.UserRole + 2: QtCore.QByteArray(b"label"),
        QtCore.Qt.ItemDataRole.UserRole + 3: QtCore.QByteArray(b"vjoyId"),
        QtCore.Qt.ItemDataRole.UserRole + 4: QtCore.QByteArray(b"vjoyInput"),
        QtCore.Qt.ItemDataRole.UserRole + 5: QtCore.QByteArray(b"vjoyLabel"),
        QtCore.Qt.ItemDataRole.UserRole + 6: QtCore.QByteArray(b"vjoyGuid"),
    }

    guidChanged = QtCore.Signal()

    def __init__(self, input_type: InputType, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._input_type = input_type
        self._guid = ""
        self._rows: list[dict] = []
        try:
            signal.profileChanged.connect(self._reload)
        except Exception:
            pass

    def _reload(self) -> None:
        self.beginResetModel()
        self._rows = _mapped_rows(self._guid, self._input_type) if self._guid else []
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

    @QtCore.Slot(int, result=str)
    def destLabel(self, identifier: int) -> str:
        try:
            ident = int(identifier)
        except Exception:
            return ""
        for row in self._rows:
            if int(row.get("identifier", -1)) == ident:
                return str(row.get("vjoyLabel") or "")
        return ""


@ta.QmlElement
class MappedAxisModel(_MappedModel):
    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(InputType.JoystickAxis, parent)


@ta.QmlElement
class MappedButtonModel(_MappedModel):
    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(InputType.JoystickButton, parent)


@ta.QmlElement
class MappedHatModel(_MappedModel):
    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(InputType.JoystickHat, parent)

