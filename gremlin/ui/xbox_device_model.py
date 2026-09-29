# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from PySide6 import QtCore

import gremlin.ui.type_aliases as ta
from gremlin import shared_state
from gremlin.signal import signal
from gremlin.ui.device import QML_IMPORT_MAJOR_VERSION, QML_IMPORT_NAME
from gremlin.ui.input_pairing import _device_name
from gremlin.ui.xbox_maps import xbox_maps_for_item
from vigem.ids import XBOX_TAB_GUID, vigem_client_error
from vigem.xbox import XboxProxy, XboxTarget

assert QML_IMPORT_NAME == "Gremlin.Device"
assert QML_IMPORT_MAJOR_VERSION == 1


def _incoming_for(pad_id: int, target: XboxTarget) -> str:
    profile = shared_state.current_profile
    if profile is None:
        return ""
    hits: list[str] = []
    for device_id, items in (profile.inputs or {}).items():
        for item in items or []:
            if not any(
                pid == pad_id and value == target.value
                for pid, value in xbox_maps_for_item(item)
            ):
                continue
            kind = getattr(item.input_type, "name", str(item.input_type))
            hits.append(f"{_device_name(str(device_id))} {kind} {item.input_id}")
    return "  ·  ".join(hits)


@ta.QmlElement
class XboxDeviceModel(QtCore.QAbstractListModel):
    roles = {
        QtCore.Qt.ItemDataRole.UserRole + 1: QtCore.QByteArray(b"label"),
        QtCore.Qt.ItemDataRole.UserRole + 2: QtCore.QByteArray(b"target"),
        QtCore.Qt.ItemDataRole.UserRole + 3: QtCore.QByteArray(b"kind"),
        QtCore.Qt.ItemDataRole.UserRole + 4: QtCore.QByteArray(b"incoming"),
    }

    padIdChanged = QtCore.Signal()
    statusChanged = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._pad_id = 1
        self._rows = list(XboxTarget)
        signal.profileChanged.connect(self.reload)
        signal.inputItemChanged.connect(self.reload)

    @QtCore.Slot()
    @QtCore.Slot(int)
    def reload(self, _index: int = 0) -> None:
        self.beginResetModel()
        self.endResetModel()
        self.statusChanged.emit()

    def rowCount(self, parent: ta.ModelIndex = QtCore.QModelIndex()) -> int:
        return len(self._rows)

    def data(self, index: ta.ModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._rows)):
            return None
        target = self._rows[index.row()]
        key = bytes(self.roles.get(role, b"")).decode()
        if key == "label":
            return target.label
        if key == "target":
            return target.value
        if key == "kind":
            return target.kind
        if key == "incoming":
            return _incoming_for(self._pad_id, target)
        return None

    def roleNames(self) -> dict[int, QtCore.QByteArray]:
        return self.roles

    def _get_pad_id(self) -> int:
        return self._pad_id

    def _set_pad_id(self, pad_id: int) -> None:
        ident = max(1, min(4, int(pad_id)))
        if ident == self._pad_id:
            return
        self._pad_id = ident
        self.reload()
        self.padIdChanged.emit()

    def _get_guid(self) -> str:
        return XBOX_TAB_GUID

    def _get_available(self) -> bool:
        return XboxProxy().available()

    def _get_status(self) -> str:
        if XboxProxy().available():
            return "ViGEmBus ready. Map hardware with Map to Xbox, then toggle Gremlin on."
        err = vigem_client_error()
        if err:
            return err
        return "ViGEmBus / ViGEmClient.dll not available."

    guid = QtCore.Property(str, fget=_get_guid, constant=True)
    padId = QtCore.Property(int, fget=_get_pad_id, fset=_set_pad_id, notify=padIdChanged)
    available = QtCore.Property(bool, fget=_get_available, notify=statusChanged)
    statusText = QtCore.Property(str, fget=_get_status, notify=statusChanged)
