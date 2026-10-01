# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from PySide6 import QtCore

import dill
from gremlin import device_initialization, event_handler, shared_state
from gremlin.signal import signal
import gremlin.ui.type_aliases as ta
from gremlin.ui import input_pairing as pairing
from gremlin.modules.ids import guid_key
from gremlin.modules import ids

QML_IMPORT_NAME = "Gremlin.Device"
QML_IMPORT_MAJOR_VERSION = 1

OSC_GUID = str(ids.OSC)


def _is_vjoy_name(name: str) -> bool:
    return str(name or "").lower().startswith("vjoy")


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
            key = guid_key(getattr(device, "device_guid", ""))
            if key:
                keys.add(key)
    for guid in (
        dill.UUID_Keyboard,
        dill.UUID_LogicalDevice,
        OSC_GUID,
    ):
        keys.add(guid_key(guid))
    return keys


def _pair_label(items: list) -> str:
    """Outputs a device's inputs are wired to. _maps_for_item lists Xbox pads
    with no input type; they are Xbox pads, not vJoy devices."""
    vjoy: set[int] = set()
    xbox: set[int] = set()
    for item in items or []:
        for target, input_type, _ in pairing._maps_for_item(item):
            (xbox if input_type is None else vjoy).add(target)
    labels = [f"vJoy Device {vid}" for vid in sorted(vjoy)]
    labels += [f"Xbox 360 {pad}" for pad in sorted(xbox)]
    return ", ".join(labels)


@ta.QmlElement
class ViewerDeviceModel(QtCore.QAbstractListModel):
    roles = {
        QtCore.Qt.ItemDataRole.UserRole + 1: QtCore.QByteArray(b"guid"),
        QtCore.Qt.ItemDataRole.UserRole + 2: QtCore.QByteArray(b"name"),
        QtCore.Qt.ItemDataRole.UserRole + 3: QtCore.QByteArray(b"pairLabel"),
        QtCore.Qt.ItemDataRole.UserRole + 4: QtCore.QByteArray(b"mapped"),
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
        seen: set[str] = set()
        connected = _connected_keys()
        profile = shared_state.current_profile
        if profile is not None:
            for device_id, items in (profile.inputs or {}).items():
                if not any(pairing._maps_for_item(item) for item in items or []):
                    continue
                guid = str(device_id)
                key = guid_key(guid)
                if key not in connected:
                    continue
                self._rows.append(
                    {
                        "guid": guid,
                        "name": pairing.device_label(guid),
                        "pairLabel": _pair_label(items),
                        "mapped": True,
                    }
                )
                seen.add(key)
        try:
            devices = device_initialization.physical_devices()
        except Exception:
            devices = []
        for device in devices:
            guid = str(getattr(device, "device_guid", ""))
            name = str(getattr(device, "name", guid))
            if _is_vjoy_name(name):
                continue
            key = guid_key(guid)
            if not key or key not in connected or key in seen:
                continue
            self._rows.append(
                {
                    "guid": guid,
                    "name": pairing.device_label(guid) if guid else name,
                    "pairLabel": "",
                    "mapped": False,
                }
            )
            seen.add(key)
        extras = [
            (str(dill.UUID_Keyboard), "Keyboard"),
            (str(dill.UUID_LogicalDevice), "Logical Device"),
            (OSC_GUID, "OSC"),
        ]
        for guid, label in extras:
            key = guid_key(guid)
            if key in seen:
                continue
            self._rows.append(
                {
                    "guid": guid,
                    "name": label,
                    "pairLabel": "",
                    "mapped": False,
                }
            )
            seen.add(key)
        self._rows.sort(key=lambda row: (not row["mapped"], str(row["name"]).lower()))
        self.endResetModel()

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

    @QtCore.Slot(result="QVariant")
    def listRows(self):
        return list(self._rows)

    @QtCore.Slot(str, result=str)
    def guidForDeviceName(self, wanted: str) -> str:
        """Return device-id for a DILL name. Exact match first, then EVO R."""
        wanted = str(wanted or "").strip()

        def _is_target(name: object) -> bool:
            text = str(name or "").strip()
            low = text.lower()
            if not text:
                return False
            if wanted and text == wanted:
                return True
            if "evo l" in low or "ot l" in low:
                return False
            return "gladiator" in low and ("evo r" in low or "ot r" in low)

        for row in self._rows:
            if _is_target(row.get("name")):
                return str(row.get("guid") or "")
        try:
            devices = device_initialization.physical_devices()
        except Exception:
            devices = []
        for device in devices or []:
            name = str(getattr(device, "name", "") or "")
            if not _is_target(name):
                continue
            guid = getattr(device, "device_guid", "")
            if hasattr(guid, "uuid"):
                guid = guid.uuid
            return str(guid or "")
        return ""
