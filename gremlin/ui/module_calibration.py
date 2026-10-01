# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Calibration stored on an input module and applied to the bound stick."""

from __future__ import annotations

import json
import uuid

from PySide6 import QtCore

import gremlin.ui.type_aliases as ta
from gremlin.config import Configuration
from gremlin.device_initialization import physical_devices
from gremlin.modules.ids import guid_key
from gremlin.ui.hardware_profile import _maps_dir
from gremlin.ui.live_debug import trace

QML_IMPORT_NAME = "Gremlin.Device"
QML_IMPORT_MAJOR_VERSION = 1

_DEFAULT = (-32768, 0, 0, 32767, True)
_SKIP_SLUGS = {"keyboard", "osc"}


def _as_tuple(raw: object) -> tuple[int, int, int, int, bool] | None:
    if not isinstance(raw, (list, tuple)) or len(raw) < 5:
        return None
    try:
        return (int(raw[0]), int(raw[1]), int(raw[2]), int(raw[3]), bool(raw[4]))
    except (TypeError, ValueError):
        return None


def _load(path) -> dict:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return doc if isinstance(doc, dict) else {}


def _source_modules() -> list[dict]:
    folder = _maps_dir()
    if not folder.is_dir():
        return []
    physical = {guid_key(dev.device_guid): dev for dev in physical_devices()}
    rows = []
    for path in sorted(folder.glob("*.json")):
        slug = path.stem.lower()
        if slug in _SKIP_SLUGS:
            continue
        doc = _load(path)
        direction = str(doc.get("direction") or "").strip().lower()
        if direction in ("dest", "target", "output"):
            continue
        guid = str(doc.get("boundGuidLocal") or "").strip()
        device = physical.get(guid_key(guid))
        if device is None:
            continue
        name = str(doc.get("device") or doc.get("boundName") or device.name).strip()
        rows.append(
            {
                "name": name or device.name,
                "slug": slug,
                "guid": str(device.device_guid),
                "path": path,
            }
        )
    rows.sort(key=lambda row: row["name"].lower())
    return rows


def module_for_slug(slug: str) -> dict | None:
    want = str(slug or "").strip().lower()
    if not want:
        return None
    for row in _source_modules():
        if row["slug"] == want:
            return row
    return None


def _module_for_guid(device_id: uuid.UUID) -> dict | None:
    want = guid_key(device_id)
    for row in _source_modules():
        if guid_key(row["guid"]) == want:
            return row
    return None


def _from_config(device_id: uuid.UUID, axis_id: int) -> tuple[int, int, int, int, bool]:
    stored = _as_tuple(Configuration().get_calibration(device_id, int(axis_id)))
    return stored if stored is not None else _DEFAULT


def values_for_device(device_id: uuid.UUID, axis_id: int) -> tuple[int, int, int, int, bool]:
    """The curve for a live stick. The module file wins. Older program data is used until then."""
    row = _module_for_guid(device_id)
    if row is not None:
        stored = _as_tuple((_load(row["path"]).get("calibration") or {}).get(str(int(axis_id))))
        if stored is not None:
            return stored
    return _from_config(device_id, axis_id)


def values_for_module(slug: str, device_id: uuid.UUID, axis_id: int) -> tuple[int, int, int, int, bool]:
    row = module_for_slug(slug)
    if row is not None:
        stored = _as_tuple((_load(row["path"]).get("calibration") or {}).get(str(int(axis_id))))
        if stored is not None:
            return stored
    return _from_config(device_id, axis_id)


def write_axis(slug: str, axis_id: int, data: tuple[int, int, int, int, bool]) -> bool:
    row = module_for_slug(slug)
    if row is None:
        return False
    doc = _load(row["path"])
    trace("READ", "Calibration", "write_axis", row["path"], "ok")
    calibration = dict(doc.get("calibration") or {})
    calibration[str(int(axis_id))] = [
        int(data[0]),
        int(data[1]),
        int(data[2]),
        int(data[3]),
        bool(data[4]),
    ]
    doc["calibration"] = calibration
    try:
        row["path"].write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    except OSError:
        trace("SAVE", "Calibration", "write_axis", row["path"], "error")
        return False
    trace("SAVE", "Calibration", "write_axis", row["path"], "ok")
    return True


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
