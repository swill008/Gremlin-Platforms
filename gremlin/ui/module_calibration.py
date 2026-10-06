# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Calibration window's list of input modules."""

from __future__ import annotations

from PySide6 import QtCore

import gremlin.ui.type_aliases as ta
from gremlin import event_handler
from gremlin.modules.calibration import _source_modules

QML_IMPORT_NAME = "Gremlin.Device"
QML_IMPORT_MAJOR_VERSION = 1


@ta.QmlElement
class CalibrationModuleModel(QtCore.QAbstractListModel):
    """One row per connected stick. A row is picked by its "key": the file's
    slug for the first stick on a file, "slug@id" for another stick on the
    same file (03 S100, S110), so each one can be shown and saved."""

    countChanged = QtCore.Signal()

    roles = {
        QtCore.Qt.ItemDataRole.UserRole + 1: QtCore.QByteArray(b"name"),
        QtCore.Qt.ItemDataRole.UserRole + 2: QtCore.QByteArray(b"slug"),
        QtCore.Qt.ItemDataRole.UserRole + 3: QtCore.QByteArray(b"key"),
    }

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._rows = _source_modules()
        event_handler.EventListener().device_change_event.connect(self.reload)

    @QtCore.Slot()
    def reload(self) -> None:
        """The connected sticks changed: list them again (only on a change,
        so an open drop-down is left alone otherwise)."""
        rows = _source_modules()
        if rows == self._rows:
            return
        self.beginResetModel()
        self._rows = rows
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
        if key == "key":
            return row["key"]
        return None

    def roleNames(self) -> dict[int, QtCore.QByteArray]:
        return self.roles

    @QtCore.Property(int, notify=countChanged)
    def moduleCount(self) -> int:
        return len(self._rows)

    @QtCore.Slot(str, result=int)
    def indexOfSlug(self, slug: str) -> int:
        """The row picked by a key (a card's slug picks the first stick)."""
        want = str(slug or "").strip().lower()
        for i, row in enumerate(self._rows):
            if row["key"].lower() == want:
                return i
        return -1
