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
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree

from PySide6 import QtCore

import gremlin.ui.type_aliases as ta
from gremlin import history, history_profile, shared_state, text_diff
from gremlin.ui.option import entry_title

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


def _subjects(entry: dict) -> list[dict]:
    """The entry's subject and, for a group, each part's."""
    found = [entry.get("subject") or {}]
    if entry.get("kind") == "group":
        for side in (entry.get("after"), entry.get("before")):
            for part in side if isinstance(side, list) else []:
                if isinstance(part, dict) and isinstance(part.get("subject"), dict):
                    found.append(part["subject"])
    return found


def _about_device(subject: dict, want: dict) -> bool:
    """10 S56: a change to the device's module file, or a Device Library
    change that lists it (subject "devices": [{guid, name}]), by its id
    (by name only when either has no id)."""
    file_name = _norm(want.get("fileName"))
    if file_name and _norm(subject.get("fileName")) == file_name:
        return True
    guid, name = _norm(want.get("guid")), _norm(want.get("name"))
    for dev in subject.get("devices") or []:
        if not isinstance(dev, dict):
            continue
        theirs = _norm(dev.get("guid"))
        if guid and theirs:
            if theirs == guid:
                return True
        elif name and _norm(dev.get("name")) == name:
            return True
    return False


def _matches(entry: dict, wanted: dict) -> bool:
    subject = entry.get("subject") or {}
    for key, value in wanted.items():
        if key == "area":
            if value and entry.get("area") != value:
                return False
            continue
        if key == "profile":
            # A path however written (case, slashes, relative): GL-194.
            if not _same_file(subject.get("profile"), value):
                return False
            continue
        if key == "ofDevice":
            want = value if isinstance(value, dict) else {}
            if not any(_about_device(s, want) for s in _subjects(entry)):
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
    if not isinstance(doc, dict):
        return "Can't be read."
    # In the Device Pack's words, not raw JSON (08 Q13, GL-192).
    from gremlin.ui.device_pack import module_text

    shown = [key for key in parts if key in doc] if parts else None
    return module_text(doc, shown) or "Not set."


def _settings_text(side: dict | None) -> str:
    if not side:
        return ""
    from gremlin.ui.option import shown_choice

    def shown(key: str, value: object) -> object:
        parts = key.split("/")
        if len(parts) != 3:
            return value
        return shown_choice((parts[0], parts[1], parts[2]), value)

    # Each setting by the name and choice Options shows ("Plugins folder",
    # "Stop" for a stored "Disable").
    return "\n".join(
        f"{entry_title(key.rsplit('/', 1)[-1], key)}: {shown(key, value)}"
        for key, value in side.items()
    )


def _title(entry: dict) -> str:
    """An entry's title. A settings entry's is made from its keys, so one
    written before a name changed reads as a new one does."""
    keys = (entry.get("subject") or {}).get("keys")
    if entry.get("area") == "settings" and keys and isinstance(keys, list):
        from gremlin.config import settings_history_title

        return settings_history_title(keys)
    return str(entry.get("title", ""))


def describe(entry: dict) -> dict:
    """What the window shows for an entry, and what can be put back."""
    kind = entry.get("kind")
    area = entry.get("area")
    before, after = entry.get("before"), entry.get("after")
    note = ""
    panes = False
    if kind == history.GROUP_KIND:
        # One action of several steps (10 S51): each step under its title.
        parts = [describe(part) for part in _parts(entry)]
        texts = tuple(
            "\n\n".join(f"{p['title']}\n{p[which]}" for p in parts)
            for which in ("before", "after")
        )
        can = (
            any(p["canRestoreBefore"] for p in parts),
            any(p["canRestoreAfter"] for p in parts),
        )
        note = "Puts back every part of it at once."
        panes = any(p["closesPanes"] for p in parts)
    elif area == "profile" and kind == "input":
        texts = (_input_text(before), _input_text(after))
        can = (True, True)
        note = "Goes back into the open profile, unsaved."
        # The action panes close first (05 Q8): a pane's OK would write
        # its old copy back over the restored actions.
        panes = True
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
    elif kind == "library":
        # The Device Library's list and saved setups (10 S51, 08 S12a).
        from gremlin import device_library

        texts = (
            device_library.history_text(before),
            device_library.history_text(after),
        )
        can = (before is not None, after is not None)
        note = "Saved at once, with its saved setups."
    else:
        parts = list((entry.get("subject") or {}).get("parts") or [])
        texts = (_module_text(before, parts), _module_text(after, parts))
        can = (
            bool(before and before.get("text") is not None),
            bool(after and after.get("text") is not None),
        )
        note = "Saved at once, with its pictures."
    # What changed, row for row and word by word (08 S104).
    diff = text_diff.rows(texts[0], texts[1])
    return {
        "title": _title(entry),
        "when": _when(entry.get("at", 0)),
        "area": history.AREAS.get(str(area or ""), str(area or "")),
        "before": texts[0],
        "after": texts[1],
        "canRestoreBefore": can[0],
        "canRestoreAfter": can[1],
        "note": note,
        "closesPanes": panes,
        "diffRows": diff,
        "diffBlocks": text_diff.blocks(diff),
    }


# --- restore -------------------------------------------------------------------


def _same_file(a: object, b: object) -> bool:
    if not a or not b:
        return False
    try:
        first, second = Path(str(a)).resolve(), Path(str(b)).resolve()
    except OSError:
        first, second = Path(str(a)), Path(str(b))
    return os.path.normcase(str(first)) == os.path.normcase(str(second))


def _changed_everywhere() -> None:
    from gremlin.signal import signal

    signal.configChanged.emit()
    signal.profileChanged.emit()
    signal.reloadUi.emit()


def _restore_input(entry: dict, side: dict | None) -> tuple[bool, str]:
    from gremlin.types import InputType
    from gremlin.ui.input_pairing import parse_guid

    profile = shared_state.current_profile
    subject = entry.get("subject") or {}
    if profile is None:
        return False, "No profile is open."
    if not _same_file(profile.fpath, subject.get("profile")):
        return False, f"Open {subject.get('profileName') or 'that profile'} first."
    uid = parse_guid(str(subject.get("deviceId") or ""))
    if uid is None:
        return False, "That device isn't known."
    kind = InputType.to_enum(str(subject.get("inputType")))
    number = int(str(subject.get("inputId")))
    mode = str(subject.get("mode") or "Default")
    profile.put_input(uid, kind, number, mode, side)
    _changed_everywhere()
    return True, "Put back into the open profile. Save the profile to keep it."


def _restore_profile(entry: dict, side: dict | None, which: str) -> tuple[bool, str]:
    from gremlin.modules import module_file

    text = history_profile.unpack_text((side or {}).get("packed"))
    if not text:
        return False, "That version of the profile isn't kept any more."
    original = Path(str((entry.get("subject") or {}).get("profile") or "profile.xml"))
    stamp = datetime.fromtimestamp(float(entry.get("at") or 0)).strftime(
        "%Y-%m-%d %H.%M.%S"
    )
    # Its own name: Before and After (and two saves in one second) never
    # overwrite each other or another file.
    base = f"{original.stem} (history {stamp} {which})"
    copy = original.with_name(base + original.suffix)
    number = 2
    while copy.exists():
        copy = original.with_name(f"{base} {number}{original.suffix}")
        number += 1
    module_file.write_text(copy, text, encoding="utf-8-sig", newline="")
    # The copy is the user's: kept until they delete it (as Delete File
    # copies, 08 Q17; GL-277).
    return True, (
        f"Written as {copy}. Open it with File > Load Profile. "
        "It stays next to the profile until you delete it."
    )


def _restore_module(entry: dict, side: dict | None) -> tuple[bool, str]:
    from gremlin.modules import store

    if not side or side.get("text") is None:
        return False, "There is no file to put back."
    subject = entry.get("subject") or {}
    # Into the modules folder of today (the folder may have moved since).
    name = str(subject.get("fileName") or Path(str(subject.get("file") or "")).name)
    path = store.path_of(Path(name).stem)
    text = str(side["text"])
    missing = []
    for picture in side.get("pictures") or []:
        ref = str(picture.get("ref") or "")
        # "qml/maps/..." is in the modules folder, as the Button Map finds it.
        kept = history.kept_file(str(picture.get("keptFile") or ""))
        try:
            if kept is None:
                raise FileNotFoundError(ref)
            store.put_picture_at(store.picture_path(ref), kept)
        except OSError:
            missing.append(ref)
    try:
        # Exactly that version, also over a damaged file (one way to mend
        # it); History keeps the restore as a new entry.
        store.write_text(path, text, "History")
    except OSError as exc:
        return False, f"{path.name} could not be put back. {exc}"
    _bind_restored(path, text)
    _changed_everywhere()
    if missing:
        return True, (
            f"Put back {path.name}, without these pictures (no copy was "
            f"kept): {', '.join(missing)}."
        )
    return True, f"Put back {path.name}."


def _bind_restored(path: Path, text: str) -> None:
    """The device the restored file is for uses it again (08 Q14): a Delete
    File, a rename or another file chosen since may have moved it to another
    file. As Module Setup's Undo of an import binds the device again (S85)."""
    from gremlin.modules import store

    try:
        doc = json.loads(text)
    except ValueError:
        return
    if not isinstance(doc, dict):
        return
    device = " ".join(str(doc.get("boundName") or doc.get("device") or "").split())
    guid = str(doc.get("boundGuidLocal") or "").strip()
    if not device or store.slug_for(device, guid) == path.stem:
        return
    store.bind(device, guid, path.stem)


def _restore_settings(side: dict | None) -> tuple[bool, str]:
    from gremlin.config import Configuration
    from gremlin.signal import signal
    from gremlin.util import _property_from_string, property_from_string

    cfg = Configuration()
    # Every value is worked out first: one that can't be read puts back
    # nothing (it used to apply the ones before it).
    values = []
    for key, value in (side or {}).items():
        section, group, name = key.split("/", 2)
        if not cfg.exists(section, group, name):
            continue
        kind = cfg.data_type(section, group, name)
        if kind in _property_from_string:
            text = json.dumps(value) if not isinstance(value, str) else value
            value = property_from_string(kind, text)
        # A list or a dict (action priorities) is kept as itself.
        values.append((section, group, name, value))
    for section, group, name, value in values:
        if not _apply_at_once(section, group, name, value):
            cfg.set(section, group, name, value)
    signal.configChanged.emit()
    _names_changed()
    return True, "Settings put back."


def _names_changed() -> None:
    """Friendly names put back show at once (Home, the Library): what
    device_aliases.set_alias tells its listeners."""
    from gremlin import device_aliases

    for listener in list(getattr(device_aliases, "_LISTENERS", [])):
        try:
            listener()
        except Exception:  # noqa: BLE001 - one listener never stops Restore
            logging.getLogger("system").exception("History: a name listener failed")


def _apply_at_once(section: str, group: str, name: str, value: object) -> bool:
    """A setting that acts at once (Diagnostic logs, UI scale) is put back
    through its Options control, so it applies now as it does there (01 Q7,
    GL-115). False: an ordinary setting, for Configuration.set."""
    from gremlin.ui import log_option, ui_scale_option

    key = (section, group, name)
    if key == (log_option.LOG_SECTION, log_option.LOG_GROUP, log_option.LOG_NAME):
        log_option.LogLevelModel().setLevel(str(value))
        return True
    if key == (
        ui_scale_option.SCALE_SECTION,
        ui_scale_option.SCALE_GROUP,
        ui_scale_option.SCALE_NAME,
    ):
        try:
            scale = int(str(value))
        except ValueError:
            return False
        ui_scale_option.UiScaleModel().setScale(scale)
        return True
    return False


def _parts(entry: dict) -> list[dict]:
    """A group entry's parts as entries of their own, in the order made."""
    befores = entry.get("before") or []
    afters = entry.get("after") or []
    parts = []
    for first, second in zip(befores, afters, strict=False):
        parts.append({
            "id": entry.get("id"),
            "at": entry.get("at"),
            "area": first.get("area"),
            "kind": first.get("kind"),
            "title": first.get("title"),
            "subject": first.get("subject"),
            "before": first.get("side"),
            "after": second.get("side"),
        })
    return parts


def _restore_group(entry: dict, which: str) -> tuple[bool, str]:
    """Each part that can be put back, as one new entry: "before" from the
    last step back to the first, "after" from the first on."""
    parts = _parts(entry)
    if which == "before":
        parts.reverse()
    key = "canRestoreBefore" if which == "before" else "canRestoreAfter"
    token = history.begin_group(f"Put back from History: {entry.get('title', '')}")
    messages: list[str] = []
    try:
        for part in parts:
            if not describe(part)[key]:
                continue
            ok, message = _restore_one(part, which)
            if not ok:
                return False, message
            messages.append(message)
    finally:
        history.end_group(token)
    return True, " ".join(messages) or "Put back."


def _restore_one(entry: dict, which: str) -> tuple[bool, str]:
    side = entry.get(which)
    area, kind = entry.get("area"), entry.get("kind")
    if kind == history.GROUP_KIND:
        return _restore_group(entry, which)
    if area == "profile" and kind == "input":
        return _restore_input(entry, side)
    if area == "profile":
        return _restore_profile(entry, side, which)
    if area == "settings":
        return _restore_settings(side)
    if kind == "library":
        from gremlin import device_library

        return device_library.restore_history(entry, side)
    return _restore_module(entry, side)


def restore(entry_id: str, which: str) -> dict:
    """Puts back the "before" or "after" version of an entry."""
    entry = history.entry(entry_id)
    if entry is None:
        return {"ok": False, "message": "That change isn't in the history any more."}
    if not describe(entry)[
        "canRestoreBefore" if which == "before" else "canRestoreAfter"
    ]:
        return {"ok": False, "message": "That version can't be put back."}
    try:
        ok, message = _restore_one(entry, which)
    except Exception as exc:
        return {"ok": False, "message": f"It couldn't be put back: {exc}"}
    return {"ok": ok, "message": message}


@ta.QmlElement
class HistoryModel(QtCore.QAbstractListModel):
    """The entries for the History window, filtered."""

    filterChanged = QtCore.Signal()
    # The change detail() last read: its rows and blocks changed.
    diffChanged = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._diff_rows: list[dict] = []
        self._diff_blocks: list[int] = []
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
            return _title(entry)
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
                w in (_title(e) + " " + json.dumps(e.get("subject"))).lower()
                for w in words
            )
        ]
        self.endResetModel()

    @QtCore.Slot(str)
    def setFilter(self, text: str) -> None:
        """Which entries show: {"area", "device", "inputType", "inputId",
        "mode", "ofDevice"}, each optional."""
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
        shown = describe(entry) if entry else {}
        # Kept for diffRows / diffBlocks, the same rows as in the text.
        self._diff_rows = list(shown.get("diffRows") or [])
        self._diff_blocks = list(shown.get("diffBlocks") or [])
        self.diffChanged.emit()
        return json.dumps(shown)

    @QtCore.Slot(str, str, result=str)
    def restore(self, entry_id: str, which: str) -> str:
        result = restore(entry_id, which)
        return json.dumps(result)

    def _filter_text(self) -> str:
        return json.dumps(self._filter)

    filterText = QtCore.Property(str, fget=_filter_text, notify=filterChanged)

    def _rows_of_diff(self) -> list:
        return self._diff_rows

    def _blocks_of_diff(self) -> list:
        return self._diff_blocks

    # The change detail() last read, aligned row for row (text_diff.rows),
    # and the first row of each change block (text_diff.blocks).
    diffRows = QtCore.Property(list, fget=_rows_of_diff, notify=diffChanged)
    diffBlocks = QtCore.Property(list, fget=_blocks_of_diff, notify=diffChanged)
