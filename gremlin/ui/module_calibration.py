# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Calibration window's list of input modules."""

from __future__ import annotations

from PySide6 import QtCore

import gremlin.ui.type_aliases as ta
from gremlin.modules.calibration import _source_modules

QML_IMPORT_NAME = "Gremlin.Device"
QML_IMPORT_MAJOR_VERSION = 1


@ta.QmlElement
class CalibrationModuleModel(QtCore.QAbstractListModel):
    countChanged = QtCore.Signal()

    roles = {
        QtCore.Qt.ItemDataRole.UserRole + 1: QtCore.QByteArray(b"name"),
        QtCore.Qt.ItemDataRole.UserRole + 2: QtCore.QByteArray(b"slug"),
    }

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._rows = _source_modules()

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
        return None

    def roleNames(self) -> dict[int, QtCore.QByteArray]:
        return self.roles

    @QtCore.Property(int, notify=countChanged)
    def moduleCount(self) -> int:
        return len(self._rows)

    @QtCore.Slot(str, result=int)
    def indexOfSlug(self, slug: str) -> int:
        want = str(slug or "").strip().lower()
        for i, row in enumerate(self._rows):
            if row["slug"] == want:
                return i
        return -1
