# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import json

from PySide6 import QtCore

from gremlin import event_handler
from gremlin.signal import signal
import gremlin.ui.type_aliases as ta
from gremlin.ui.hardware_profile import _maps_dir, _slug, resolve_module_slug
from gremlin.ui.live_debug import trace
from gremlin.ui.module_model import _claim_from_doc
from gremlin.ui.output_modules import _resolve_vjoy_id

QML_IMPORT_NAME = "Gremlin.Device"
QML_IMPORT_MAJOR_VERSION = 1


def _norm_guid(value: object) -> str:
    return str(value or "").strip().strip("{}")


def _is_dest(doc: dict, slug: str) -> bool:
    direction = str(doc.get("direction") or "").strip().lower()
    if direction in ("dest", "target", "output"):
        return True
    if direction in ("source", "input"):
        return False
    return slug.startswith("vjoy") or slug.startswith("xbox")


def _scan_modules() -> list[dict]:
    folder = _maps_dir()
    if not folder.is_dir():
        return []
    rows: list[dict] = []
    for path in sorted(folder.glob("*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(doc, dict):
            continue
        slug = path.stem.lower()
        name = str(doc.get("device") or doc.get("boundName") or path.stem).strip()
        if not name:
            continue
        claim = _claim_from_doc(doc)
        rows.append(
            {
                "slug": slug,
                "name": name,
                "path": path,
                "doc": doc,
                "claim": claim,
                "guid": _norm_guid(doc.get("boundGuidLocal")),
                "boundName": str(doc.get("boundName") or name).strip(),
                "isDest": _is_dest(doc, slug),
                "vjoyId": _resolve_vjoy_id(
                    name, str(doc.get("boundGuidLocal") or "")
                ),
            }
        )
    return rows


def _display_key(name: str) -> str:
    return " ".join(str(name or "").casefold().split())


def _guid_key(value: object) -> str:
    return str(value or "").strip().strip("{}").replace("-", "").lower()


def _same_device(left: dict, right: dict) -> bool:
    name = _display_key(left.get("name") or "")
    if name and name == _display_key(right.get("name") or ""):
        return True
    guid = _guid_key(left.get("guid"))
    return bool(guid and guid == _guid_key(right.get("guid")))


def _choose_input(group: list[dict]) -> dict:
    """Keep the file the input module is bound to. Do not delete the others."""
    for row in group:
        wanted = resolve_module_slug(row["name"], row.get("guid") or "")
        if wanted and wanted == row["slug"]:
            return row
    for row in group:
        if row["slug"] == _slug(row["name"]):
            return row
    return group[0]


def _collapse_inputs(rows: list[dict]) -> list[dict]:
    parent = list(range(len(rows)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        root_left = find(left)
        root_right = find(right)
        if root_left != root_right:
            parent[root_right] = root_left

    for left in range(len(rows)):
        for right in range(left + 1, len(rows)):
            if _same_device(rows[left], rows[right]):
                union(left, right)
    groups: dict[int, list[dict]] = {}
    for index, row in enumerate(rows):
        groups.setdefault(find(index), []).append(row)
    kept = [_choose_input(group) for group in groups.values()]
    kept.sort(key=lambda row: str(row["name"]).lower())
    return kept


def input_modules() -> list[dict]:
    rows = []
    for row in _scan_modules():
        if row["isDest"]:
            continue
        claim = row["claim"]
        if not (claim.get("buttons") or claim.get("axes") or claim.get("hats")):
            continue
        rows.append(row)
    return _collapse_inputs(rows)


def output_modules() -> list[dict]:
    rows = []
    seen: set[int] = set()
    for row in _scan_modules():
        if not row["isDest"]:
            continue
        vjoy_id = int(row["vjoyId"] or 0)
        if not vjoy_id or vjoy_id in seen:
            continue
        seen.add(vjoy_id)
        rows.append(row)
    rows.sort(key=lambda row: (int(row["vjoyId"]), str(row["name"]).lower()))
    return rows


def merge_claim_into_output(dest: dict, claim: dict) -> dict:
    """Write the input-module selection onto the output module so they match."""
    path = dest.get("path")
    doc = dest.get("doc") if isinstance(dest.get("doc"), dict) else {}
    current = dest.get("claim") or {}
    buttons = sorted(
        {int(x) for x in (current.get("buttons") or [])}
        | {int(x) for x in (claim.get("buttons") or [])}
    )
    axes = sorted(
        {int(x) for x in (current.get("axes") or [])}
        | {int(x) for x in (claim.get("axes") or [])}
    )
    hats = sorted(
        {int(x) for x in (current.get("hats") or [])}
        | {int(x) for x in (claim.get("hats") or [])}
    )
    friendly = dict(current.get("friendly") or {})
    friendly.update(dict(claim.get("friendly") or {}))
    merged = {
        "buttons": buttons,
        "axes": axes,
        "hats": hats,
        "keys": list(current.get("keys") or []),
        "friendly": friendly,
    }
    if path is None:
        dest["claim"] = merged
        return merged
    doc = dict(doc)
    doc["claim"] = merged
    try:
        path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    except OSError:
        trace("SAVE", "Auto Mapper", "merge_claim_into_output", path, "error")
        dest["claim"] = merged
        return merged
    trace("SAVE", "Auto Mapper", "merge_claim_into_output", path, "ok")
    dest["doc"] = doc
    dest["claim"] = merged
    return merged


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
