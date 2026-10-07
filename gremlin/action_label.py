# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from PySide6 import QtCore

import gremlin.ui.type_aliases as ta
from gremlin.signal import signal
from gremlin import shared_state
from gremlin.ui.device import (
    QML_IMPORT_MAJOR_VERSION,
    QML_IMPORT_NAME,
)
from gremlin.ui.osc_device_model import OscDeviceManagementModel

assert QML_IMPORT_NAME == "Gremlin.Device"
assert QML_IMPORT_MAJOR_VERSION == 1

_osc_data = OscDeviceManagementModel.data


def _description_from_item(item) -> str:
    if item is None:
        return ""
    return item.action_name


def _set_item_name(item, name: str, index: int) -> None:
    if item is None:
        return
    item.action_name = (name or "").strip()
    signal.inputItemChanged.emit(index)


def _read_item(model: object, index: int, create: bool):
    profile = shared_state.current_profile
    if profile is None or index < 0:
        return None
    if hasattr(model, "_convert_index") and hasattr(model, "_device"):
        if getattr(model, "_device", None) is None:
            return None
        info = model._convert_index(index)
        return profile.get_input_item(
            model._device.device_guid.uuid,
            info[0],
            info[1],
            getattr(model, "_mode", "Default"),
            create,
        )
    if hasattr(model, "_index_to_input") and hasattr(model, "_osc"):
        info = model._index_to_input(index)
        return profile.get_input_item(
            model._osc.device_guid,
            info.type,
            info.id,
            getattr(model, "_mode", "Default"),
            create,
        )
    if hasattr(model, "inputIdentifier"):
        identifier = model.inputIdentifier(index)
        if identifier is None:
            return None
        return profile.get_input_item(
            identifier.device_guid,
            identifier.input_type,
            identifier.input_id,
            getattr(model, "_mode", "Default"),
            create,
        )
    return None


def apply_action_name(model: object, index: int, name: str) -> None:
    item = _read_item(model, index, True)
    _set_item_name(item, name, index)
    if hasattr(model, "refreshInput"):
        model.refreshInput(index)
    elif hasattr(model, "dataChanged") and hasattr(model, "createIndex"):
        model.dataChanged.emit(model.createIndex(index, 0), model.createIndex(index, 0))


def read_action_name(model: object, index: int) -> str:
    return _description_from_item(_read_item(model, index, False))


def _patch_description(original, resolve_item):
    def data(self, index, role=QtCore.Qt.ItemDataRole.DisplayRole):
        raw = self.roles.get(role)
        role_name = raw.data().decode() if hasattr(raw, "data") else str(raw or "")
        if role_name == "description":
            try:
                item = resolve_item(self, index.row())
            except Exception:
                item = None
            return _description_from_item(item)
        return original(self, index, role)

    return data


def _osc_item(self, row: int):
    return _read_item(self, row, False)


# The stick, Keyboard and Logical Device lists give the input name in their
# own "description" role (ui/device.py). OSC is parked: its list keeps this.
OscDeviceManagementModel.data = _patch_description(_osc_data, _osc_item)


@ta.QmlElement
class ActionNames(QtCore.QObject):
    @QtCore.Slot("QVariant", int, str)
    def setOnModel(self, model: object, index: int, name: str) -> None:
        apply_action_name(model, index, name)

    @QtCore.Slot("QVariant", int, result=str)
    def getOnModel(self, model: object, index: int) -> str:
        return read_action_name(model, index)
