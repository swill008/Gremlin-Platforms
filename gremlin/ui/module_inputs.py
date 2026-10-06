# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from PySide6 import QtCore

import gremlin.ui.type_aliases as ta
from gremlin import common, event_handler, shared_state
from gremlin.config import Configuration
from gremlin.input_cache import DeviceDatabase
from gremlin.signal import signal
from gremlin.ui.device import _description_from_item, _generate_action_sequence_descriptor
from gremlin.modules.claim import claim_friendly, claim_ids, read_claim, type_of
from gremlin.modules import hardware, store

QML_IMPORT_NAME = "Gremlin.Device"
QML_IMPORT_MAJOR_VERSION = 1


@ta.QmlElement
class ModuleClaimedInputModel(QtCore.QAbstractListModel):
    """Configuration left list: only controls the input module passes."""

    roles = {
        QtCore.Qt.ItemDataRole.UserRole + 1: QtCore.QByteArray(b"name"),
        QtCore.Qt.ItemDataRole.UserRole + 2: QtCore.QByteArray(b"actionSequenceCount"),
        QtCore.Qt.ItemDataRole.UserRole + 3: QtCore.QByteArray(
            b"actionSequenceDescriptor"
        ),
        QtCore.Qt.ItemDataRole.UserRole + 4: QtCore.QByteArray(
            b"actionSequenceDisplayMode"
        ),
        QtCore.Qt.ItemDataRole.UserRole + 5: QtCore.QByteArray(b"description"),
        QtCore.Qt.ItemDataRole.UserRole + 6: QtCore.QByteArray(b"deviceIndex"),
        QtCore.Qt.ItemDataRole.UserRole + 7: QtCore.QByteArray(b"kind"),
        QtCore.Qt.ItemDataRole.UserRole + 8: QtCore.QByteArray(b"hwId"),
    }

    guidChanged = QtCore.Signal()
    deviceNameChanged = QtCore.Signal()
    countChanged = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._guid = ""
        self._device_name = ""
        self._mode = "Default"
        self._device = None
        self._mapping = None
        self._rows: list[dict] = []
        signal.profileChanged.connect(self.reload)
        event_handler.EventListener().device_change_event.connect(
            self._device_list_changed
        )
        signal.inputItemChanged.connect(self._refresh_one)
        signal.configChanged.connect(self.reload)

    def _get_guid(self) -> str:
        return self._guid

    def _set_guid(self, guid: str) -> None:
        text = str(guid or "")
        if text == self._guid:
            return
        self._guid = text
        self._read_device()
        self.reload()
        self.guidChanged.emit()

    def _read_device(self) -> None:
        text = self._guid
        self._device = None
        self._mapping = None
        if text and text.lower() not in ("unknown", ""):
            try:
                self._device = hardware.device_info(text)
                self._mapping = DeviceDatabase().get_mapping(self._device)
            except Exception:
                self._device = None
                self._mapping = None

    def _device_list_changed(self) -> None:
        # Set while its stick was unplugged: read it now it is back.
        if self._device is None and self._guid:
            self._read_device()
            if self._device is not None:
                self.reload()

    def _get_device_name(self) -> str:
        return self._device_name

    def _set_device_name(self, name: str) -> None:
        text = str(name or "")
        if text == self._device_name:
            return
        self._device_name = text
        self.reload()
        self.deviceNameChanged.emit()

    @QtCore.Slot(str)
    def setMode(self, mode: str) -> None:
        text = str(mode or "Default")
        if text == self._mode:
            return
        self._mode = text
        self.reload()

    def _hid_index(self, kind: str, hw_id: int) -> int:
        if self._device is None:
            return -1
        if kind == "axis":
            for i, axis in enumerate(self._device.axis_map):
                if int(axis.axis_index) == int(hw_id):
                    return i
            return -1
        if kind == "button":
            if 1 <= int(hw_id) <= int(self._device.button_count):
                return int(self._device.axis_count) + int(hw_id) - 1
            return -1
        if 1 <= int(hw_id) <= int(self._device.hat_count):
            return (
                int(self._device.axis_count)
                + int(self._device.button_count)
                + int(hw_id)
                - 1
            )
        return -1

    def _label(self, kind: str, hw_id: int, claim: dict) -> str:
        custom = claim_friendly(claim, kind, hw_id)
        if custom:
            return custom
        input_type = type_of(kind)
        if self._mapping is not None:
            try:
                return self._mapping.input_name((input_type, int(hw_id)))
            except Exception:
                pass
        return common.input_to_ui_string(input_type, int(hw_id))

    @QtCore.Slot()
    def reload(self) -> None:
        self.beginResetModel()
        self._rows = []
        # By the device's id too: twins share a name (decision F4).
        doc = store.read(self._device_name, self._guid) if self._device_name else {}
        if not doc:
            self.endResetModel()
            self.countChanged.emit()
            return
        claim = read_claim(doc)
        ordered = [
            (kind, hid)
            for kind in ("axis", "button", "hat")
            for hid in claim_ids(claim, kind)
        ]
        for kind, hid in ordered:
            device_index = self._hid_index(kind, hid)
            if device_index < 0:
                continue
            self._rows.append(
                {
                    "kind": kind,
                    "hwId": int(hid),
                    "deviceIndex": device_index,
                    "name": self._label(kind, hid, claim),
                }
            )
        self.endResetModel()
        self.countChanged.emit()

    def _refresh_one(self, index: int) -> None:
        if not self._rows:
            return
        self.dataChanged.emit(
            self.index(0, 0),
            self.index(len(self._rows) - 1, 0),
        )

    def _input_item(self, row: dict):
        if self._device is None:
            return None
        profile = shared_state.current_profile
        if profile is None:
            return None
        return profile.get_input_item(
            self._device.device_guid.uuid,
            type_of(row["kind"]),
            int(row["hwId"]),
            self._mode,
        )

    def rowCount(self, parent: ta.ModelIndex = QtCore.QModelIndex()) -> int:
        return len(self._rows)

    def data(self, index: ta.ModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._rows)):
            return None
        row = self._rows[index.row()]
        key = bytes(self.roles.get(role, b"")).decode()
        if key == "name":
            return row["name"]
        if key == "deviceIndex":
            return row["deviceIndex"]
        if key == "kind":
            return row["kind"]
        if key == "hwId":
            return row["hwId"]
        if key == "actionSequenceDisplayMode":
            return Configuration().value(
                "global", "general", "action-sequence-information"
            )
        item = self._input_item(row)
        if key == "actionSequenceCount":
            return len(item.action_sequences) if item else 0
        if key == "actionSequenceDescriptor":
            return _generate_action_sequence_descriptor(item) if item else ""
        if key == "description":
            return _description_from_item(item) if item else ""
        return None

    def roleNames(self) -> dict[int, QtCore.QByteArray]:
        return self.roles

    @QtCore.Slot(int, result=int)
    def deviceIndexAt(self, row: int) -> int:
        if 0 <= row < len(self._rows):
            return int(self._rows[row]["deviceIndex"])
        return -1

    @QtCore.Slot(int, result=str)
    def kindAt(self, row: int) -> str:
        if 0 <= row < len(self._rows):
            return str(self._rows[row]["kind"])
        return ""

    @QtCore.Slot(int, result=int)
    def hwIdAt(self, row: int) -> int:
        if 0 <= row < len(self._rows):
            return int(self._rows[row]["hwId"])
        return 0

    @QtCore.Slot(int, result=str)
    def nameAt(self, row: int) -> str:
        if 0 <= row < len(self._rows):
            return str(self._rows[row]["name"])
        return ""

    @QtCore.Slot(int, result=int)
    def rowForDeviceIndex(self, device_index: int) -> int:
        for i, row in enumerate(self._rows):
            if int(row["deviceIndex"]) == int(device_index):
                return i
        return -1

    guid = QtCore.Property(str, fget=_get_guid, fset=_set_guid, notify=guidChanged)
    deviceName = QtCore.Property(
        str, fget=_get_device_name, fset=_set_device_name, notify=deviceNameChanged
    )

    @QtCore.Property(int, notify=countChanged)
    def count(self) -> int:
        return len(self._rows)
