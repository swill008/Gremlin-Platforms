# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from PySide6 import QtCore

from gremlin import device_initialization, event_handler, shared_state
from gremlin.modules import registry
from gremlin.modules.ids import guid_key
from gremlin.signal import signal
from gremlin.types import InputType
import gremlin.ui.type_aliases as ta
from gremlin.ui import input_pairing as pairing
from gremlin.ui.module_model import _load_module_doc, module_exists
from gremlin.ui.hardware_profile import _slug
from gremlin.modules.claim import (
    claim_allows,
    claim_friendly,
    claim_ids,
    empty_claim,
    kind_of,
    read_claim,
)

QML_IMPORT_NAME = "Gremlin.Device"
QML_IMPORT_MAJOR_VERSION = 1


def _source_claim(device_name: str) -> dict:
    doc = _load_module_doc(device_name)
    if not doc:
        return empty_claim()
    return read_claim(doc)


def _source_title(device_name: str, fallback: str) -> str:
    doc = _load_module_doc(device_name)
    raw = str((doc or {}).get("device") or "").strip()
    return raw or str(fallback or device_name).strip()


def _dest_for_vjoy(vjoy_id: int) -> dict:
    name = f"vJoy {int(vjoy_id)}"
    module = registry.output_for_vjoy(int(vjoy_id))
    doc = module.doc if module else _load_module_doc(name)
    claim = read_claim(doc) if doc else empty_claim()
    return {
        "name": str((doc or {}).get("device") or name).strip() or name,
        "slug": _slug(name),
        "guid": pairing._vjoy_guid(int(vjoy_id)),
        "claim": claim,
        "exists": bool(doc),
    }


def _vjoy_maps_only(item) -> list[tuple[int, object, int]]:
    return [m for m in pairing._maps_for_item(item) if m[1] is not None]


def _src_label(input_type: InputType, hid: int, claim: dict) -> str:
    custom = claim_friendly(claim, kind_of(input_type), hid)
    if custom:
        return custom
    if input_type == InputType.JoystickAxis:
        return pairing.AXIS_LABELS.get(int(hid), f"A{int(hid)}")
    if input_type == InputType.JoystickHat:
        return f"H{int(hid)}"
    return str(int(hid))


def _module_pair_rows(guid: str, device_name: str, input_type: InputType) -> list[dict]:
    src_claim = _source_claim(device_name)
    allowed = set(claim_ids(src_claim, kind_of(input_type)))
    if not allowed:
        return []
    rows: list[dict] = []
    seen: set[int] = set()
    for item in pairing._items_for_guid(guid):
        if getattr(item, "input_type", None) != input_type:
            continue
        try:
            identifier = int(item.input_id)
        except Exception:
            continue
        if identifier not in allowed or identifier in seen:
            continue
        vjoy_maps = _vjoy_maps_only(item)
        if not vjoy_maps:
            continue
        seen.add(identifier)
        vjoy_id = int(vjoy_maps[0][0])
        vinput = int(vjoy_maps[0][2])
        dest = _dest_for_vjoy(vjoy_id)
        dest_kind = kind_of(vjoy_maps[0][1] or input_type)
        dest_claimed = claim_allows(dest["claim"], dest_kind, vinput)
        dest_custom = claim_friendly(dest["claim"], dest_kind, vinput)
        if dest_claimed:
            if dest_custom:
                vjoy_label = dest_custom
            elif input_type == InputType.JoystickAxis or vjoy_maps[0][1] == InputType.JoystickAxis:
                vjoy_label = f"{dest['name']} {pairing.AXIS_LABELS.get(vinput, f'A{vinput}')}"
            elif vjoy_maps[0][1] == InputType.JoystickHat:
                vjoy_label = f"{dest['name']} H{vinput}"
            else:
                vjoy_label = f"{dest['name']} B{vinput}"
        else:
            vjoy_label = ""
        rows.append(
            {
                "identifier": identifier,
                "label": _src_label(input_type, identifier, src_claim),
                "vjoyId": vjoy_id,
                "vjoyInput": vinput,
                "vjoyLabel": vjoy_label,
                "vjoyGuid": dest["guid"] or pairing._vjoy_guid(vjoy_id),
                "destClaimed": dest_claimed,
            }
        )
    rows.sort(key=lambda row: (row["identifier"], row["vjoyId"], row["vjoyInput"]))
    return rows


@ta.QmlElement
class ModulePairDeviceModel(QtCore.QAbstractListModel):
    """Source modules that have vJoy wires. Names come from the module pack."""

    roles = {
        QtCore.Qt.ItemDataRole.UserRole + 1: QtCore.QByteArray(b"guid"),
        QtCore.Qt.ItemDataRole.UserRole + 2: QtCore.QByteArray(b"name"),
        QtCore.Qt.ItemDataRole.UserRole + 3: QtCore.QByteArray(b"pairLabel"),
        QtCore.Qt.ItemDataRole.UserRole + 4: QtCore.QByteArray(b"mapped"),
        QtCore.Qt.ItemDataRole.UserRole + 5: QtCore.QByteArray(b"deviceName"),
        QtCore.Qt.ItemDataRole.UserRole + 6: QtCore.QByteArray(b"destEmpty"),
    }

    countChanged = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._rows: list[dict] = []
        self.reload()
        signal.profileChanged.connect(self.reload)
        signal.configChanged.connect(self.reload)
        event_handler.EventListener().device_change_event.connect(self.reload)

    @QtCore.Slot()
    def reload(self) -> None:
        self.beginResetModel()
        self._rows = []
        seen: set[str] = set()
        profile = shared_state.current_profile
        devices = []
        try:
            devices = list(device_initialization.physical_devices() or [])
        except Exception:
            devices = []
        extras = []
        try:
            extras = list(device_initialization.input_devices() or [])
        except Exception:
            extras = []
        roster = []
        for device in devices + extras:
            name = str(getattr(device, "name", "") or "")
            if name.lower().startswith("vjoy"):
                continue
            guid = str(getattr(device, "device_guid", "") or "")
            key = guid_key(guid)
            if not key or key in seen:
                continue
            seen.add(key)
            roster.append((guid, name))
        if profile is not None:
            for device_id, items in (profile.inputs or {}).items():
                key = guid_key(device_id)
                if not key or key in seen:
                    continue
                if not any(_vjoy_maps_only(item) for item in items or []):
                    continue
                guid = str(device_id)
                name = pairing._device_name(guid)
                seen.add(key)
                roster.append((guid, name))
        for guid, raw_name in roster:
            if not module_exists(raw_name):
                continue
            items = pairing._items_for_guid(guid)
            dest_ids = sorted(
                {
                    int(vid)
                    for item in items
                    for vid, vtype, _ in _vjoy_maps_only(item)
                    if vtype is not None
                }
            )
            if not dest_ids:
                continue
            dests = [_dest_for_vjoy(vid) for vid in dest_ids]
            dest_empty = all(
                not (d["claim"]["buttons"] or d["claim"]["axes"] or d["claim"]["hats"])
                for d in dests
            )
            self._rows.append(
                {
                    "guid": guid,
                    "name": _source_title(raw_name, raw_name),
                    "deviceName": raw_name,
                    "pairLabel": ", ".join(d["name"] for d in dests),
                    "mapped": True,
                    "destEmpty": dest_empty,
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

    @QtCore.Property(int, notify=countChanged)
    def count(self) -> int:
        return len(self._rows)


class _ModulePairMappedModel(QtCore.QAbstractListModel):
    roles = {
        QtCore.Qt.ItemDataRole.UserRole + 1: QtCore.QByteArray(b"identifier"),
        QtCore.Qt.ItemDataRole.UserRole + 2: QtCore.QByteArray(b"label"),
        QtCore.Qt.ItemDataRole.UserRole + 3: QtCore.QByteArray(b"vjoyId"),
        QtCore.Qt.ItemDataRole.UserRole + 4: QtCore.QByteArray(b"vjoyInput"),
        QtCore.Qt.ItemDataRole.UserRole + 5: QtCore.QByteArray(b"vjoyLabel"),
        QtCore.Qt.ItemDataRole.UserRole + 6: QtCore.QByteArray(b"vjoyGuid"),
        QtCore.Qt.ItemDataRole.UserRole + 7: QtCore.QByteArray(b"destClaimed"),
    }

    guidChanged = QtCore.Signal()
    deviceNameChanged = QtCore.Signal()
    countChanged = QtCore.Signal()

    def __init__(self, input_type: InputType, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._input_type = input_type
        self._guid = ""
        self._device_name = ""
        self._rows: list[dict] = []
        signal.profileChanged.connect(self._reload)
        signal.configChanged.connect(self._reload)

    def _reload(self) -> None:
        self.beginResetModel()
        if self._guid and self._device_name:
            self._rows = _module_pair_rows(self._guid, self._device_name, self._input_type)
        else:
            self._rows = []
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

    def _get_device_name(self) -> str:
        return self._device_name

    def _set_device_name(self, name: str) -> None:
        text = str(name or "")
        if text == self._device_name:
            return
        self._device_name = text
        self._reload()
        self.deviceNameChanged.emit()

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
    deviceName = QtCore.Property(
        str, fget=_get_device_name, fset=_set_device_name, notify=deviceNameChanged
    )

    @QtCore.Property(int, notify=countChanged)
    def count(self) -> int:
        return len(self._rows)


@ta.QmlElement
class ModulePairAxisModel(_ModulePairMappedModel):
    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(InputType.JoystickAxis, parent)


@ta.QmlElement
class ModulePairButtonModel(_ModulePairMappedModel):
    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(InputType.JoystickButton, parent)


import gremlin.ui.module_inputs  # noqa: F401
import gremlin.ui.output_modules  # noqa: F401
import gremlin.ui.auto_map_modules  # noqa: F401
