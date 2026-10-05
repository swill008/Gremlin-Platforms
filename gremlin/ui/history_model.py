# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The History window (Tools > History): every saved change, newest first,
with what it was before and after, and Restore.

Restore puts a version back through the normal save paths, so it is itself
a new entry. An input's actions go back into the open profile as an unsaved
change (save it to keep it). A module file or a setting is saved at once,
as its editor does. A whole profile is written as a copy next to the
profile, to open with File > Load Profile.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree

from PySide6 import QtCore

import gremlin.ui.type_aliases as ta
from gremlin import history, history_profile, shared_state

QML_IMPORT_NAME = "Gremlin.UI"
QML_IMPORT_MAJOR_VERSION = 1

_UUID = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
_ROLES = ("entryId", "when", "areaName", "title")


def _when(at: float) -> str:
    try:
        return datetime.fromtimestamp(float(at)).strftime("%Y-%m-%d %H:%M")
    except (TypeError, ValueError, OSError):
        return ""


def _norm(value: object) -> str:
    """For comparing: case, spacing and a GUID's braces don't matter."""
    return " ".join(str(value or "").split()).strip("{}").lower()


def _matches(entry: dict, wanted: dict) -> bool:
    subject = entry.get("subject") or {}
    for key, value in wanted.items():
        if key == "area":
            if value and entry.get("area") != value:
                return False
            continue
        if _norm(subject.get(key, "")) != _norm(value):
            return False
    return True


# --- readable before / after -------------------------------------------------


def _plugin_name(tag: str) -> str:
    try:
        from gremlin.plugin_manager import PluginManager

        return str(PluginManager().tag_map[tag].name)
    except Exception:
        return tag


def _action_lines(
    node: ElementTree.Element, actions: dict[str, ElementTree.Element], depth: int
) -> list[str]:
    props = []
    for prop in node.findall("property"):
        name = (prop.findtext("name") or "").strip()
        if name in ("action-label", "activation-mode") or not name:
            continue
        props.append(
            f"{name.replace('-', ' ')} {(prop.findtext('value') or '').strip()}"
        )
    line = "  " * depth + _plugin_name(node.get("type") or "")
    if props:
        line += " (" + ", ".join(props) + ")"
    lines = [line]
    for element in node.iter():
        if element is node:
            continue
        text = (element.text or "").strip().lower()
        if _UUID.match(text) and text in actions:
            lines.extend(_action_lines(actions[text], actions, depth + 1))
    return lines


def _input_text(doc: dict | None) -> str:
    if not doc:
        return "No actions."
    try:
        node = ElementTree.fromstring(doc["input"])
        actions = {}
        for block in doc.get("actions") or []:
            action = ElementTree.fromstring(block)
            actions[(action.get("id") or "").lower()] = action
    except (ElementTree.ParseError, KeyError, TypeError):
        return "Can't be read."
    lines = []
    for config in node.findall("action-configuration"):
        root_id = (config.findtext("root-action") or "").strip().lower()
        if root_id in actions:
            lines.extend(_action_lines(actions[root_id], actions, 0))
    return "\n".join(lines) or "No actions."


def _module_text(side: dict | None, parts: list[str]) -> str:
    if not side or side.get("text") is None:
        return "No file."
    try:
        doc = json.loads(side["text"])
    except ValueError:
        return "Can't be read."
    shown = {key: doc.get(key) for key in parts if key in doc} if parts else doc
    return json.dumps(shown, indent=2) if shown else "Not set."


def _settings_text(side: dict | None) -> str:
    if not side:
        return ""
    return "\n".join(
        f"{key.rsplit('/', 1)[-1].replace('-', ' ').capitalize()}: {value}"
        for key, value in side.items()
    )


def describe(entry: dict) -> dict:
    """What the window shows for an entry, and what can be put back."""
    kind = entry.get("kind")
    area = entry.get("area")
    before, after = entry.get("before"), entry.get("after")
    note = ""
    if area == "profile" and kind == "input":
        texts = (_input_text(before), _input_text(after))
        can = (True, True)
        note = "Goes back into the open profile, unsaved."
    elif area == "profile" and kind == "section":
        texts = (before or "Not there.", after or "Not there.")
        can = (False, False)
        note = "Put this back with Restore on the profile's save, below it in the list."
    elif area == "profile":
        size = [
            len(history_profile.unpack_text((side or {}).get("packed")) or "")
            for side in (before, after)
        ]
        texts = tuple(
            f"The whole profile ({round(n / 1024)} KB)." if n else "Not kept."
            for n in size
        )
        can = (size[0] > 0, size[1] > 0)
        note = (
            "Written as a copy next to the profile, to open with File > Load Profile."
        )
    elif area == "settings":
        texts = (_settings_text(before), _settings_text(after))
        can = (bool(before), bool(after))
        note = "Saved at once."
    else:
        parts = list((entry.get("subject") or {}).get("parts") or [])
        texts = (_module_text(before, parts), _module_text(after, parts))
        can = (
            bool(before and before.get("text") is not None),
            bool(after and after.get("text") is not None),
        )
        note = "Saved at once, with its pictures."
    return {
        "title": entry.get("title", ""),
        "when": _when(entry.get("at", 0)),
        "area": history.AREAS.get(str(area or ""), str(area or "")),
        "before": texts[0],
        "after": texts[1],
        "canRestoreBefore": can[0],
        "canRestoreAfter": can[1],
        "note": note,
    }


# --- restore -------------------------------------------------------------------


def _same_file(a: object, b: object) -> bool:
    if not a or not b:
        return False
    try:
        return Path(str(a)).resolve() == Path(str(b)).resolve()
    except OSError:
        return str(a) == str(b)


def _changed_everywhere() -> None:
    from gremlin.signal import signal

    signal.configChanged.emit()
    signal.profileChanged.emit()
    signal.reloadUi.emit()


def _restore_input(entry: dict, side: dict | None) -> tuple[bool, str]:
    from gremlin.types import InputType
    from gremlin.ui.input_pairing import _guid

    profile = shared_state.current_profile
    subject = entry.get("subject") or {}
    if profile is None:
        return False, "No profile is open."
    if not _same_file(profile.fpath, subject.get("profile")):
        return False, f"Open {subject.get('profileName') or 'that profile'} first."
    uid = _guid(str(subject.get("deviceId") or ""))
    if uid is None:
        return False, "That device isn't known."
    kind = InputType.to_enum(str(subject.get("inputType")))
    number = int(str(subject.get("inputId")))
    mode = str(subject.get("mode") or "Default")
    profile.put_input(uid, kind, number, mode, side)
    _changed_everywhere()
    return True, "Put back into the open profile. Save the profile to keep it."


def _restore_profile(entry: dict, side: dict | None) -> tuple[bool, str]:
    from gremlin.modules import module_file

    text = history_profile.unpack_text((side or {}).get("packed"))
    if not text:
        return False, "That version of the profile isn't kept any more."
    original = Path(str((entry.get("subject") or {}).get("profile") or "profile.xml"))
    stamp = datetime.fromtimestamp(float(entry.get("at") or 0)).strftime(
        "%Y-%m-%d %H.%M"
    )
    copy = original.with_name(f"{original.stem} (history {stamp}){original.suffix}")
    module_file.write_text(copy, text, encoding="utf-8-sig", newline="")
    return True, f"Written as {copy}. Open it with File > Load Profile."


def _restore_module(entry: dict, side: dict | None) -> tuple[bool, str]:
    from gremlin.modules import module_file
    from gremlin.util import modules_dir

    if not side or side.get("text") is None:
        return False, "There is no file to put back."
    path = Path(str((entry.get("subject") or {}).get("file") or ""))
    for picture in side.get("pictures") or []:
        dest = modules_dir() / str(picture.get("ref") or "").replace("\\", "/").lstrip(
            "/"
        )
        history.restore_file(str(picture.get("keptFile") or ""), dest)
    module_file.write_text(path, side["text"])
    _changed_everywhere()
    return True, f"Put back {path.name}."


def _restore_settings(side: dict | None) -> tuple[bool, str]:
    from gremlin.config import Configuration
    from gremlin.signal import signal
    from gremlin.util import property_from_string

    cfg = Configuration()
    for key, value in (side or {}).items():
        section, group, name = key.split("/", 2)
        if not cfg.exists(section, group, name):
            continue
        kind = cfg._data[(section, group, name)]["data_type"]
        text = json.dumps(value) if not isinstance(value, str) else value
        cfg.set(section, group, name, property_from_string(kind, text))
    signal.configChanged.emit()
    return True, "Settings put back."


def restore(entry_id: str, which: str) -> dict:
    """Puts back the "before" or "after" version of an entry."""
    entry = history.entry(entry_id)
    if entry is None:
        return {"ok": False, "message": "That change isn't in the history any more."}
    if not describe(entry)[
        "canRestoreBefore" if which == "before" else "canRestoreAfter"
    ]:
        return {"ok": False, "message": "That version can't be put back."}
    side = entry.get(which)
    area, kind = entry.get("area"), entry.get("kind")
    try:
        if area == "profile" and kind == "input":
            ok, message = _restore_input(entry, side)
        elif area == "profile":
            ok, message = _restore_profile(entry, side)
        elif area == "settings":
            ok, message = _restore_settings(side)
        else:
            ok, message = _restore_module(entry, side)
    except Exception as exc:
        return {"ok": False, "message": f"It couldn't be put back: {exc}"}
    return {"ok": ok, "message": message}


@ta.QmlElement
class HistoryModel(QtCore.QAbstractListModel):
    """The entries for the History window, filtered."""

    filterChanged = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._all: list[dict] = []
        self._rows: list[dict] = []
        self._filter: dict = {}
        self._search = ""

    def roleNames(self) -> dict[int, QtCore.QByteArray]:
        return {
            QtCore.Qt.ItemDataRole.UserRole + i: QtCore.QByteArray(name.encode())
            for i, name in enumerate(_ROLES, start=1)
        }

    def rowCount(self, parent: ta.ModelIndex = QtCore.QModelIndex()) -> int:
        return len(self._rows)

    def data(
        self, index: ta.ModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole
    ) -> object:
        if not index.isValid() or not 0 <= index.row() < len(self._rows):
            return None
        entry = self._rows[index.row()]
        name = (
            _ROLES[role - QtCore.Qt.ItemDataRole.UserRole - 1]
            if role > QtCore.Qt.ItemDataRole.UserRole
            else ""
        )
        if name == "entryId":
            return entry.get("id", "")
        if name == "when":
            return _when(entry.get("at", 0))
        if name == "areaName":
            return history.AREAS.get(str(entry.get("area") or ""), "")
        if name == "title":
            return entry.get("title", "")
        return None

    @QtCore.Slot()
    def reload(self) -> None:
        self._all = history.entries()
        self._apply()

    def _apply(self) -> None:
        self.beginResetModel()
        words = self._search.lower().split()
        self._rows = [
            e
            for e in self._all
            if _matches(e, self._filter)
            and all(
                w in (e.get("title", "") + " " + json.dumps(e.get("subject"))).lower()
                for w in words
            )
        ]
        self.endResetModel()

    @QtCore.Slot(str)
    def setFilter(self, text: str) -> None:
        """Which entries show: {"area", "device", "inputType", "inputId",
        "mode"}, each optional."""
        try:
            wanted = json.loads(text) if text else {}
        except ValueError:
            wanted = {}
        self._filter = wanted if isinstance(wanted, dict) else {}
        self._apply()
        self.filterChanged.emit()

    @QtCore.Slot(str)
    def setSearch(self, text: str) -> None:
        self._search = str(text or "")
        self._apply()

    @QtCore.Slot(str, result=str)
    def detail(self, entry_id: str) -> str:
        entry = next((e for e in self._all if e.get("id") == entry_id), None)
        return json.dumps(describe(entry) if entry else {})

    @QtCore.Slot(str, str, result=str)
    def restore(self, entry_id: str, which: str) -> str:
        result = restore(entry_id, which)
        return json.dumps(result)

    def _filter_text(self) -> str:
        return json.dumps(self._filter)

    filterText = QtCore.Property(str, fget=_filter_text, notify=filterChanged)
