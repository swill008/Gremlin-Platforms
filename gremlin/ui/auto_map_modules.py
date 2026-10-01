# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The Auto Mapper's input and output module lists."""

from __future__ import annotations

from PySide6 import QtCore

import gremlin.ui.type_aliases as ta
from gremlin import event_handler
from gremlin.modules.auto_map import input_modules, output_modules
from gremlin.signal import signal

QML_IMPORT_NAME = "Gremlin.Device"
QML_IMPORT_MAJOR_VERSION = 1


class _SlugListModel(QtCore.QAbstractListModel):
    roles = {
        QtCore.Qt.ItemDataRole.UserRole + 1: QtCore.QByteArray(b"name"),
        QtCore.Qt.ItemDataRole.UserRole + 2: QtCore.QByteArray(b"slug"),
        QtCore.Qt.ItemDataRole.UserRole + 3: QtCore.QByteArray(b"guid"),
        QtCore.Qt.ItemDataRole.UserRole + 4: QtCore.QByteArray(b"vjoyId"),
    }

    countChanged = QtCore.Signal()

    def __init__(self, loader, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._loader = loader
        self._rows: list[dict] = []
        self.reload()
        signal.profileChanged.connect(self.reload)
        signal.configChanged.connect(self.reload)
        event_handler.EventListener().device_change_event.connect(self.reload)

    @QtCore.Slot()
    def reload(self) -> None:
        self.beginResetModel()
        self._rows = self._loader()
        self.endResetModel()
        self.countChanged.emit()

    def rowCount(self, parent: ta.ModelIndex = QtCore.QModelIndex()) -> int:
        return len(self._rows)

    def data(self, index: ta.ModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._rows)):
            return None
        row = self._rows[index.row()]
        key = bytes(self.roles.get(role, b"")).decode()
        if key == "name":
            return row["name"]
        if key == "slug":
            return row["slug"]
        if key == "guid":
            return row.get("guid") or ""
        if key == "vjoyId":
            return int(row.get("vjoyId") or 0)
        return None

    def roleNames(self) -> dict[int, QtCore.QByteArray]:
        return self.roles

    @QtCore.Property(int, notify=countChanged)
    def count(self) -> int:
        return len(self._rows)


@ta.QmlElement
class AutoMapInputModel(_SlugListModel):
    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(input_modules, parent)


@ta.QmlElement
class AutoMapOutputModel(_SlugListModel):
    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(output_modules, parent)
