# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
# Device-Configuration-Macro Change — binding catalog for Configuration.

from __future__ import annotations

import logging
import os
import uuid
import xml.etree.ElementTree as ElementTree

from PySide6 import QtCore

import gremlin.ui.type_aliases as ta
from gremlin import error, shared_state
from gremlin.base_classes import AbstractActionData
from gremlin.modules import wiring
from gremlin.modules.claim import type_of
from gremlin.profile import InputItem, InputItemBinding, Library
from gremlin.signal import signal
from gremlin.ui.module_inputs import ModuleClaimedInputModel

QML_IMPORT_NAME = "Gremlin.Device"
QML_IMPORT_MAJOR_VERSION = 1

_WRAPPERS = {
    "root",
    "chain",
    "tempo",
    "condition",
    "double-tap",
    "smart-toggle",
    "description",
    "reference",
}

def _remap_ids(node: ElementTree.Element, id_map: dict[uuid.UUID, uuid.UUID]) -> None:
    Library.remap_ids(node, id_map)


def _clone_action(
    action: AbstractActionData | None,
    library: Library,
    id_map: dict[uuid.UUID, uuid.UUID],
) -> AbstractActionData | None:
    """Copy one action tree into the library under new ids. Unfinished
    actions too: pane edits must not reach the real input before OK."""
    return library.clone_action(action, id_map, draft=True)


def _clone_binding(binding: InputItemBinding, shadow: InputItem) -> InputItemBinding:
    id_map: dict[uuid.UUID, uuid.UUID] = {}
    _clone_action(binding.root_action, shadow.library, id_map)
    node = binding.to_xml()
    _remap_ids(node, id_map)
    copy = InputItemBinding(shadow)
    copy.from_xml(node)
    shadow.action_sequences.append(copy)
    return copy


def _shadow_item(source: InputItem) -> InputItem:
    shadow = InputItem(source.library)
    shadow.device_id = source.device_id
    shadow.input_type = source.input_type
    shadow.input_id = source.input_id
    shadow.mode = source.mode
    return shadow


def _drop_shadow(shadow: InputItem | None) -> None:
    """Delete a draft tree that was never written onto the real control."""
    if shadow is None:
        return
    roots = [
        binding.root_action
        for binding in shadow.action_sequences
        if binding.root_action is not None
    ]
    shadow.action_sequences.clear()
    for root in roots:
        shadow.library.remove_unused(root)


def _fingerprint_item(item: InputItem) -> str:
    return "\n--\n".join(_fingerprint(binding) for binding in item.action_sequences)


def _unwritable_state(action) -> str:
    """The fields of an action to_xml can't write yet, as text."""

    def plain(value: object) -> object:
        if hasattr(value, "device_guid") and hasattr(value, "input_id"):
            return tuple(
                getattr(value, name) for name in ("device_guid", "input_type", "input_id")
            )
        if hasattr(value, "tag") and hasattr(value, "id"):
            return str(getattr(value, "id"))
        if isinstance(value, (list, tuple)):
            return [plain(entry) for entry in value]
        return value

    try:
        fields = sorted(vars(action).items())
    except TypeError:
        return ""
    return repr([(name, plain(value)) for name, value in fields])


def _fingerprint(binding: InputItemBinding) -> str:
    chunks: list[str] = []

    def walk(action) -> None:
        if action is None:
            return
        # Unfinished ones too: the pane edits a copy, so an edit to one (a
        # first axis picked) must make OK write it.
        node = action.to_xml(True)
        if node is not None:
            chunks.append(ElementTree.tostring(node, encoding="unicode"))
        else:
            chunks.append(f"{getattr(action, 'tag', '')}:{_unwritable_state(action)}")
        for child in action.get_actions()[0] or []:
            walk(child)

    walk(binding.root_action)
    node = binding.to_xml()
    if node is not None:
        chunks.append(ElementTree.tostring(node, encoding="unicode"))
    return "\n".join(chunks)


def _or(value: int | str | None, default: int) -> int | str:
    """value, or default when it is None (0 is a real index)."""
    return default if value is None else value


def _attach_binding(real: InputItem, shadow: InputItem, sequence_index: int) -> int:
    """Move the draft binding onto the real control. Returns its index."""
    binding = shadow.action_sequences[0]
    binding.input_item = real
    if sequence_index < 0:
        real.action_sequences.append(binding)
        return len(real.action_sequences) - 1
    old = real.action_sequences[sequence_index]
    real.action_sequences[sequence_index] = binding
    if (
        old is not binding
        and old.root_action is not None
        and old.root_action is not binding.root_action
    ):
        real.library.remove_unused(old.root_action)
    return sequence_index


_TYPE_LABELS = {
    "map-to-vjoy": "Map to vJoy",
    "map-to-keyboard": "Map to keyboard",
    "map-to-mouse": "Map to mouse",
    "map-to-xbox": "Map to Xbox",
    "map-to-logical-device": "Map to logical device",
    "macro": "Macro",
    "change-mode": "Change mode",
    "load-profile": "Load profile",
    "text-to-speech": "Text to speech",
    "run-command": "Run command",
    "play-sound": "Play sound",
    "response-curve": "Response curve",
    "merge-axis": "Merge axis",
    "split-axis": "Split axis",
    "axis-delta": "Axis delta",
    "dual-axis-deadzone": "Dual axis deadzone",
    "hat-buttons": "Hat buttons",
    "pause-resume": "Pause / resume",
}

_NAMED_FILTERS = {
    "vjoy": {"map-to-vjoy"},
    "keyboard": {"map-to-keyboard"},
    "mouse": {"map-to-mouse"},
    "xbox": {"map-to-xbox"},
    "macro": {"macro"},
    "mode": {"change-mode"},
}


def _action_children(action) -> list:
    kids = getattr(action, "children", None)
    if kids:
        return list(kids)
    try:
        acts, _containers = action.get_actions()
        return list(acts or [])
    except Exception:
        return []


def _key_name(key) -> str:
    name = getattr(key, "name", None)
    if name:
        return str(name)
    return str(key)


def summarize_action(action) -> tuple[str, str]:
    """Return (type label, destination) for a leaf action."""
    tag = str(getattr(action, "tag", "") or "")
    label = _TYPE_LABELS.get(tag, getattr(action, "name", None) or tag or "Action")
    dest = ""
    if tag in ("map-to-vjoy", "map-to-xbox"):
        dest = wiring.dest_label(action)
    elif tag == "map-to-keyboard":
        keys = getattr(action, "keys", None) or []
        dest = " + ".join(_key_name(k) for k in keys) if keys else "Keyboard"
    elif tag == "map-to-mouse":
        mode = getattr(action, "mode", None)
        button = getattr(action, "button", None)
        # A motion mapping keeps a default button it never uses.
        if getattr(mode, "name", "") == "Motion":
            dest = "Motion"
        else:
            dest = str(getattr(button, "name", None) or button or "Mouse")
    elif tag == "map-to-logical-device":
        dest = str(getattr(action, "action_label", None) or "Logical device")
    elif tag == "macro":
        al = str(getattr(action, "action_label", "") or "")
        dest = al if al and al != "Macro" else "Macro"
    elif tag == "change-mode":
        modes = getattr(action, "_target_modes", None) or []
        dest = ", ".join(str(m) for m in modes) if modes else "Mode"
    elif tag == "load-profile":
        path = str(getattr(action, "profile_filename", "") or "")
        dest = os.path.basename(path) if path else "Profile"
    elif tag == "text-to-speech":
        dest = str(getattr(action, "text", None) or "Speech")[:40]
    elif tag == "run-command":
        exe = str(getattr(action, "executable", "") or "")
        dest = os.path.basename(exe) if exe else "Command"
    elif tag == "play-sound":
        sound = str(getattr(action, "sound_filename", "") or "")
        dest = os.path.basename(sound) if sound else "Sound"
    else:
        dest = str(getattr(action, "action_label", None) or label)
    return label, dest


def collect_leaves(action) -> list[tuple[str, str, str]]:
    """Walk wrappers; return (tag, type label, dest) for leaves."""
    tag = str(getattr(action, "tag", "") or "")
    kids = _action_children(action)
    if tag in _WRAPPERS or (kids and tag in _WRAPPERS):
        out: list[tuple[str, str, str]] = []
        for child in kids:
            out.extend(collect_leaves(child))
        if out:
            return out
        if tag in _WRAPPERS:
            return []
    if kids and tag in ("chain", "tempo", "condition", "double-tap", "smart-toggle"):
        out = []
        for child in kids:
            out.extend(collect_leaves(child))
        return out or [(tag, _TYPE_LABELS.get(tag, tag), _TYPE_LABELS.get(tag, tag))]
    label, dest = summarize_action(action)
    return [(tag, label, dest)]


def sequences_for_item(item) -> list[tuple[int, str, str]]:
    """One catalog child per action sequence: (index, type label, destination)."""
    out: list[tuple[int, str, str]] = []
    sequences = getattr(item, "action_sequences", None) or []
    for index, seq in enumerate(sequences):
        root = getattr(seq, "root_action", None)
        leaves = collect_leaves(root) if root is not None else []
        if len(leaves) == 1:
            _tag, lab, dest = leaves[0]
            out.append((index, lab, dest))
        elif len(leaves) > 1:
            dest = ", ".join(item_dest for _tag, _lab, item_dest in leaves if item_dest)
            out.append((index, f"{len(leaves)} actions", dest or "Sequence"))
        else:
            label = str(getattr(root, "action_label", "") or "") if root is not None else ""
            out.append((index, "Sequence", label or "Empty"))
    return out


def sequence_is_simple(item, index: int) -> bool:
    """True when the sequence is empty or one plain map, with no container."""
    sequences = getattr(item, "action_sequences", None) or []
    if not (0 <= int(index) < len(sequences)):
        return True
    root = getattr(sequences[int(index)], "root_action", None)
    kids = _action_children(root) if root is not None else []
    if len(kids) == 0:
        return True
    if len(kids) != 1:
        return False
    tag = str(getattr(kids[0], "tag", "") or "")
    if tag not in ("map-to-vjoy", "map-to-keyboard", "map-to-mouse"):
        return False
    return not _action_children(kids[0])


def assignment_summary(shown: list[tuple]) -> tuple[str, str]:
    summary = ", ".join(dest for _t, _l, dest in shown)
    text = (
        f"{len(shown)} assignment"
        + ("s" if len(shown) != 1 else "")
        + " — "
        + summary
    )
    return text, summary


def leaves_for_item(item) -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []
    if item is None:
        return out
    for seq in getattr(item, "action_sequences", None) or []:
        root = getattr(seq, "root_action", None)
        if root is None:
            continue
        out.extend(collect_leaves(root))
    return out


@ta.QmlElement
class BindingCatalogModel(QtCore.QAbstractListModel):
    """Grouped binding rows for the Configuration catalog (Device-Configuration-Macro Change)."""

    roles = {
        QtCore.Qt.ItemDataRole.UserRole + 1: QtCore.QByteArray(b"rowKind"),
        QtCore.Qt.ItemDataRole.UserRole + 2: QtCore.QByteArray(b"name"),
        QtCore.Qt.ItemDataRole.UserRole + 3: QtCore.QByteArray(b"summary"),
        QtCore.Qt.ItemDataRole.UserRole + 4: QtCore.QByteArray(b"typeLabel"),
        QtCore.Qt.ItemDataRole.UserRole + 5: QtCore.QByteArray(b"destLabel"),
        QtCore.Qt.ItemDataRole.UserRole + 6: QtCore.QByteArray(b"kind"),
        QtCore.Qt.ItemDataRole.UserRole + 7: QtCore.QByteArray(b"hwId"),
        QtCore.Qt.ItemDataRole.UserRole + 8: QtCore.QByteArray(b"deviceIndex"),
        QtCore.Qt.ItemDataRole.UserRole + 9: QtCore.QByteArray(b"bindingCount"),
        QtCore.Qt.ItemDataRole.UserRole + 10: QtCore.QByteArray(b"indent"),
        QtCore.Qt.ItemDataRole.UserRole + 11: QtCore.QByteArray(b"sequenceIndex"),
        QtCore.Qt.ItemDataRole.UserRole + 12: QtCore.QByteArray(b"simple"),
    }

    guidChanged = QtCore.Signal()
    deviceNameChanged = QtCore.Signal()
    countChanged = QtCore.Signal()
    filtersChanged = QtCore.Signal()
    paneModelChanged = QtCore.Signal()
    parkEmptyChanged = QtCore.Signal()
    undoChanged = QtCore.Signal()
    # The pane's mode was deleted: the page closes it.
    paneLost = QtCore.Signal()

    # Undo steps kept: each OK or Delete, with the input before and after.
    UNDO_STEPS = 50

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._claimed = ModuleClaimedInputModel(self)
        self._type_filter = "all"
        self._dest_filter = "all"
        self._rows: list[dict] = []
        self._dest_choices: list[str] = ["All devices"]
        self._park_empty = False
        self._undo: list[dict] = []
        self._redo: list[dict] = []
        signal.profileChanged.connect(self.reload)
        # Another profile (or one changed under the page): no steps. A mode
        # renamed or deleted: the steps and the open pane follow (adding a
        # mode used to clear every step).
        signal.profileChanged.connect(self._forget_steps)
        signal.modeRenamed.connect(self._on_mode_renamed)
        signal.modeDeleted.connect(self._on_mode_deleted)
        # Undo waits while an action is open in the pane.
        self.paneModelChanged.connect(self.undoChanged)
        self._claimed.countChanged.connect(self.reload)
        self._pane_model = None
        self._pane_shadow: InputItem | None = None
        self._pane_real: InputItem | None = None
        self._pane_seq = -1
        self._pane_hid = -1
        self._pane_base = ""
        self._pane_whole = False
        # The input the pane edits (guid, kind, hw, mode): OK writes there and
        # records its Undo step there, whatever mode is shown by then.
        self._pane_input: tuple | None = None

    def _get_guid(self) -> str:
        return self._claimed.guid

    def _set_guid(self, guid: str) -> None:
        self._claimed.guid = guid
        self._forget_steps()
        self.guidChanged.emit()

    def _get_device_name(self) -> str:
        return self._claimed.deviceName

    def _set_device_name(self, name: str) -> None:
        self._claimed.deviceName = name
        self.deviceNameChanged.emit()

    @QtCore.Slot(str)
    def setMode(self, mode: str) -> None:
        self._claimed.setMode(mode)
        self.reload()

    def _get_type_filter(self) -> str:
        return self._type_filter

    def _set_type_filter(self, value: str) -> None:
        text = str(value or "all")
        if text == self._type_filter:
            return
        self._type_filter = text
        self.reload()
        self.filtersChanged.emit()

    def _get_dest_filter(self) -> str:
        return self._dest_filter

    def _set_dest_filter(self, value: str) -> None:
        text = str(value or "all")
        if text == self._dest_filter:
            return
        self._dest_filter = text
        self.reload()
        self.filtersChanged.emit()

    def _leaf_ok(self, tag: str, dest: str) -> bool:
        tf = self._type_filter
        if tf == "unmapped":
            return False
        if tf != "all":
            allowed = _NAMED_FILTERS.get(tf)
            if allowed is not None:
                if tag not in allowed:
                    return False
            elif tf == "other":
                named = set()
                for s in _NAMED_FILTERS.values():
                    named |= s
                if tag in named:
                    return False
        if self._dest_filter not in ("all", "All devices", ""):
            if dest != self._dest_filter:
                return False
        return True

    def _sequence_ok(self, leaves: list) -> bool:
        if not leaves:
            return self._type_filter in ("all", "") and self._dest_filter in (
                "all",
                "All devices",
                "",
            )
        return any(self._leaf_ok(tag, dest) for tag, _lab, dest in leaves)

    def _shown_sequences(self, item) -> list[tuple[int, str, str]]:
        shown: list[tuple[int, str, str]] = []
        sequences = getattr(item, "action_sequences", None) or []
        for index, lab, dest in sequences_for_item(item):
            root = sequences[index].root_action if 0 <= index < len(sequences) else None
            leaves = collect_leaves(root) if root is not None else []
            if self._sequence_ok(leaves):
                shown.append((index, lab, dest))
        return shown

    @QtCore.Slot()
    def reload(self) -> None:
        self._rebuild()

    def _rebuild(self) -> None:
        self.beginResetModel()
        self._rows = []
        dests: list[str] = []
        mapped = 0
        unmapped: list[dict] = []
        n = self._claimed.rowCount()
        for i in range(n):
            kind = self._claimed.kindAt(i)
            hw = self._claimed.hwIdAt(i)
            name = self._claimed.nameAt(i)
            didx = self._claimed.deviceIndexAt(i)
            item = self._claimed._input_item(
                {"kind": kind, "hwId": hw, "deviceIndex": didx, "name": name}
            )
            seqs = sequences_for_item(item)
            for seq in getattr(item, "action_sequences", None) or []:
                root = getattr(seq, "root_action", None)
                if root is None:
                    continue
                for _tag, _lab, dest in collect_leaves(root):
                    if dest and dest not in dests:
                        dests.append(dest)
            shown = self._shown_sequences(item)
            if self._type_filter == "unmapped":
                if seqs:
                    continue
                unmapped.append(
                    {
                        "rowKind": "unmapped",
                        "name": name,
                        "summary": "",
                        "typeLabel": "",
                        "destLabel": "No actions",
                        "kind": kind,
                        "hwId": hw,
                        "deviceIndex": didx,
                        "bindingCount": 0,
                        "indent": 0,
                        "sequenceIndex": -1,
                        "simple": True,
                    }
                )
                continue
            if not seqs:
                if self._type_filter == "all" and self._dest_filter in (
                    "all",
                    "All devices",
                    "",
                ):
                    if self._park_empty:
                        unmapped.append(
                            {
                                "rowKind": "unmapped",
                                "name": name,
                                "summary": "",
                                "typeLabel": "",
                                "destLabel": "No actions",
                                "kind": kind,
                                "hwId": hw,
                                "deviceIndex": didx,
                                "bindingCount": 0,
                                "indent": 0,
                                "sequenceIndex": -1,
                                "simple": True,
                            }
                        )
                    else:
                        self._rows.append(
                            {
                                "rowKind": "group",
                                "name": name,
                                "summary": "No actions",
                                "typeLabel": "",
                                "destLabel": "No actions",
                                "kind": kind,
                                "hwId": hw,
                                "deviceIndex": didx,
                                "bindingCount": 0,
                                "indent": 0,
                                "sequenceIndex": -1,
                                "simple": True,
                            }
                        )
                continue
            if not shown:
                continue
            summary, dests_text = assignment_summary(shown)
            self._rows.append(
                {
                    "rowKind": "group",
                    "name": name,
                    "summary": summary,
                    "typeLabel": "",
                    "destLabel": dests_text,
                    "kind": kind,
                    "hwId": hw,
                    "deviceIndex": didx,
                    "bindingCount": len(shown),
                    "indent": 0,
                    "sequenceIndex": -1,
                    "simple": True,
                }
            )
            mapped += 1
            for seq_index, lab, dest in shown:
                self._rows.append(
                    {
                        "rowKind": "leaf",
                        "name": name,
                        "summary": dest,
                        "typeLabel": lab,
                        "destLabel": dest,
                        "kind": kind,
                        "hwId": hw,
                        "deviceIndex": didx,
                        "bindingCount": 1,
                        "indent": 1,
                        "sequenceIndex": seq_index,
                        "simple": sequence_is_simple(item, seq_index),
                    }
                )
        if unmapped:
            self._rows.append(
                {
                    "rowKind": "unmapped-header",
                    "name": "Unmapped",
                    "summary": f"{len(unmapped)} controls — click to add",
                    "typeLabel": "",
                    "destLabel": "",
                    "kind": "",
                    "hwId": 0,
                    "deviceIndex": -1,
                    "bindingCount": len(unmapped),
                    "indent": 0,
                    "sequenceIndex": -1,
                    "simple": True,
                }
            )
            self._rows.extend(unmapped)
        self._dest_choices = ["All devices"] + dests
        self.endResetModel()
        self.countChanged.emit()
        self.filtersChanged.emit()

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

    @QtCore.Slot(int, result=int)
    def deviceIndexAt(self, row: int) -> int:
        if 0 <= row < len(self._rows):
            return int(self._rows[row]["deviceIndex"])
        return -1

    def _parent_row(self, device_index: int) -> dict | None:
        want = int(device_index)
        for row in self._rows:
            if int(row["deviceIndex"]) != want:
                continue
            if row["rowKind"] in ("group", "unmapped"):
                return row
        return None

    @QtCore.Slot(int, result=str)
    def controlLabel(self, device_index: int) -> str:
        row = self._parent_row(device_index)
        return str(row["name"]) if row else ""

    @QtCore.Slot(int, result=int)
    def leafRun(self, row: int) -> int:
        """How many child rows follow this parent."""
        if row < 0 or row >= len(self._rows):
            return 0
        if self._rows[row]["rowKind"] != "group":
            return 0
        count = 0
        i = row + 1
        while i < len(self._rows) and self._rows[i]["rowKind"] == "leaf":
            count += 1
            i += 1
        return count

    @QtCore.Slot(int, result=bool)
    def lastLeaf(self, row: int) -> bool:
        if row < 0 or row >= len(self._rows):
            return False
        if self._rows[row]["rowKind"] != "leaf":
            return False
        nxt = row + 1
        return nxt >= len(self._rows) or self._rows[nxt]["rowKind"] != "leaf"

    def _shown_for_device(self, device_index: int):
        want = int(device_index)
        n = self._claimed.rowCount()
        for i in range(n):
            if int(self._claimed.deviceIndexAt(i)) != want:
                continue
            kind = self._claimed.kindAt(i)
            hw = self._claimed.hwIdAt(i)
            name = self._claimed.nameAt(i)
            item = self._claimed._input_item(
                {"kind": kind, "hwId": hw, "deviceIndex": want, "name": name}
            )
            shown = self._shown_sequences(item)
            return name, kind, hw, want, shown
        return None

    def _emit_row(self, row: int) -> None:
        idx = self.index(row, 0)
        self.dataChanged.emit(idx, idx, list(self.roles.keys()))

    def _leaf_row(self, name, kind, hw, didx, seq_index, lab, dest, simple: bool) -> dict:
        return {
            "rowKind": "leaf",
            "name": name,
            "summary": dest,
            "typeLabel": lab,
            "destLabel": dest,
            "kind": kind,
            "hwId": hw,
            "deviceIndex": didx,
            "bindingCount": 1,
            "indent": 1,
            "sequenceIndex": int(seq_index),
            "simple": bool(simple),
        }

    def _replace_leaves(self, row: int, name, kind, hw, didx, shown) -> None:
        existing = self.leafRun(row)
        item = None
        found_item = self._input_item_for(didx, False)
        if found_item is not None:
            item = found_item
        fresh = [
            self._leaf_row(
                name,
                kind,
                hw,
                didx,
                seq_index,
                lab,
                dest,
                sequence_is_simple(item, seq_index),
            )
            for seq_index, lab, dest in shown
        ]
        if existing == len(fresh):
            for offset, leaf in enumerate(fresh):
                self._rows[row + 1 + offset] = leaf
            if existing:
                top = self.index(row + 1, 0)
                bottom = self.index(row + existing, 0)
                self.dataChanged.emit(top, bottom, list(self.roles.keys()))
            return
        if existing:
            self.beginRemoveRows(QtCore.QModelIndex(), row + 1, row + existing)
            del self._rows[row + 1 : row + 1 + existing]
            self.endRemoveRows()
        if fresh:
            self.beginInsertRows(QtCore.QModelIndex(), row + 1, row + len(fresh))
            self._rows[row + 1 : row + 1] = fresh
            self.endInsertRows()
        self.countChanged.emit()

    def _apply_summary(self, row: int, shown) -> None:
        text, summary = assignment_summary(shown)
        current = self._rows[row]
        if (
            current.get("summary") == text
            and int(current.get("bindingCount") or 0) == len(shown)
        ):
            return
        current["summary"] = text
        current["destLabel"] = summary
        current["bindingCount"] = len(shown)
        self._emit_row(row)

    @QtCore.Slot(int, result=bool)
    def noteOpenRow(self, device_index: int) -> bool:
        """Update the open parent summary. Do not insert or remove rows."""
        found = self._shown_for_device(device_index)
        if found is None:
            return False
        _name, _kind, _hw, didx, shown = found
        row = self.rowForDeviceIndex(didx)
        if row < 0:
            return False
        current = self._rows[row]
        if current["rowKind"] != "group" or not shown:
            return False
        self._apply_summary(row, shown)
        return False

    @QtCore.Slot(int, result=bool)
    def refreshOpenRow(self, device_index: int) -> bool:
        """Update one control without resetting the list.

        Returns True when the row had to move between mapped and unmapped,
        which rebuilds the list.
        """
        found = self._shown_for_device(device_index)
        if found is None:
            return False
        name, kind, hw, didx, shown = found
        row = self.rowForDeviceIndex(didx)
        if row < 0:
            self._rebuild()
            return True
        current = self._rows[row]
        kind_now = current["rowKind"]
        if kind_now == "unmapped" and not shown:
            return False
        if kind_now != "group" or not shown:
            self._rebuild()
            return True
        text, summary = assignment_summary(shown)
        same = (
            current.get("summary") == text
            and int(current.get("bindingCount") or 0) == len(shown)
            and self.leafRun(row) == len(shown)
        )
        if same:
            for offset, (seq_index, lab, dest) in enumerate(shown):
                leaf = self._rows[row + 1 + offset]
                if (
                    int(_or(leaf.get("sequenceIndex"), -1)) != int(seq_index)
                    or leaf.get("typeLabel") != lab
                    or leaf.get("destLabel") != dest
                ):
                    same = False
                    break
        if same:
            return False
        current["summary"] = text
        current["destLabel"] = summary
        current["bindingCount"] = len(shown)
        self._emit_row(row)
        self._replace_leaves(row, name, kind, hw, didx, shown)
        return False

    @QtCore.Slot(int, result=int)
    def rowForDeviceIndex(self, device_index: int) -> int:
        want = int(device_index)
        fallback = -1
        for i, row in enumerate(self._rows):
            if int(row["deviceIndex"]) != want:
                continue
            if row["rowKind"] in ("group", "unmapped"):
                return i
            if fallback < 0:
                fallback = i
        return fallback

    def _input_item_for(self, device_index: int, create: bool):
        want = int(device_index)
        if want < 0:
            return None
        profile = shared_state.current_profile
        dev = getattr(self._claimed, "_device", None)
        if profile is None or dev is None:
            return None
        mode = str(getattr(self._claimed, "_mode", None) or "Default")
        n = self._claimed.rowCount()
        for i in range(n):
            if int(self._claimed.deviceIndexAt(i)) != want:
                continue
            return profile.get_input_item(
                dev.device_guid.uuid,
                type_of(self._claimed.kindAt(i)),
                int(self._claimed.hwIdAt(i)),
                mode,
                create_if_missing=create,
            )
        return None

    @QtCore.Slot(result=list)
    def vjoyDevices(self) -> list:
        """Output vJoy devices for the quick editor. Each entry is id|name."""
        from gremlin.device_initialization import output_vjoy_devices

        rows = []
        for dev in output_vjoy_devices():
            rows.append(f"{int(dev.vjoy_id)}|{dev.name}")
        return rows

    @QtCore.Slot(int, result=int)
    def addSequence(self, device_index: int) -> int:
        """ADD on a catalog row: new action sequence for that control."""
        want = int(device_index)
        if want < 0:
            return -1
        profile = shared_state.current_profile
        dev = getattr(self._claimed, "_device", None)
        if profile is None or dev is None:
            return -1
        mode = str(getattr(self._claimed, "_mode", None) or "Default")
        n = self._claimed.rowCount()
        for i in range(n):
            if self._claimed.deviceIndexAt(i) != want:
                continue
            kind = self._claimed.kindAt(i)
            hw = self._claimed.hwIdAt(i)
            item = profile.get_input_item(
                dev.device_guid.uuid,
                type_of(kind),
                int(hw),
                mode,
                create_if_missing=True,
            )
            if item is None:
                return -1
            item.add_item_binding()
            seq = len(item.action_sequences) - 1
            signal.inputItemChanged.emit(want)
            signal.reloadCurrentInputItem.emit()
            return seq
        return -1

    @QtCore.Slot(int, int, result=bool)
    def removeSequence(self, device_index: int, sequence_index: int) -> bool:
        """Delete one action sequence from a control."""
        want = int(device_index)
        seq = int(sequence_index)
        if want < 0 or seq < 0:
            return False
        shown = str(getattr(self._claimed, "_mode", None) or "Default")
        if (
            self._pane_shadow is not None
            and want == self._pane_hid
            and self._get_pane_mode() == shown
        ):
            return False
        profile = shared_state.current_profile
        dev = getattr(self._claimed, "_device", None)
        if profile is None or dev is None:
            return False
        mode = str(getattr(self._claimed, "_mode", None) or "Default")
        n = self._claimed.rowCount()
        for i in range(n):
            if int(self._claimed.deviceIndexAt(i)) != want:
                continue
            item = profile.get_input_item(
                dev.device_guid.uuid,
                type_of(self._claimed.kindAt(i)),
                int(self._claimed.hwIdAt(i)),
                mode,
                create_if_missing=False,
            )
            sequences = getattr(item, "action_sequences", None) or []
            if seq >= len(sequences):
                return False
            before = self._snapshot(want)
            binding = sequences[seq]
            item.remove_item_binding(binding)
            if binding.root_action is not None:
                profile.drop_unused_actions([binding.root_action])
            self._step(want, before)
            signal.inputItemChanged.emit(want)
            signal.reloadCurrentInputItem.emit()
            return True
        return False

    # --- Undo / Redo: an input as it was before and after each OK or Delete

    def _spec_for(self, device_index: int, key: tuple | None = None) -> tuple | None:
        """The input shown at device_index, or the given (guid, kind, hw,
        mode) one."""
        if key is None:
            return self._control_spec(device_index)
        profile = shared_state.current_profile
        if profile is None:
            return None
        guid, kind, hw, mode = key
        item = profile.get_input_item(guid, kind, hw, mode, create_if_missing=False)
        return profile, guid, kind, hw, mode, item

    def _snapshot(self, device_index: int, key: tuple | None = None) -> dict | None:
        spec = self._spec_for(device_index, key)
        if spec is None:
            return None
        profile, _guid, _kind, _hw, _mode, item = spec
        return profile.input_snapshot(item)

    def _step(
        self, device_index: int, before: dict | None, key: tuple | None = None
    ) -> None:
        spec = self._spec_for(device_index, key)
        if spec is None:
            return
        profile, guid, kind, hw, mode, item = spec
        after = profile.input_snapshot(item)
        if before == after:
            return
        self._undo.append({
            "hid": device_index, "key": (guid, kind, hw, mode),
            "before": before, "after": after,
        })
        del self._undo[: -self.UNDO_STEPS]
        self._redo.clear()
        self.undoChanged.emit()

    def _on_mode_renamed(self, old: str, new: str) -> None:
        for step in self._undo + self._redo:
            guid, kind, hw, mode = step["key"]
            if mode == old:
                step["key"] = (guid, kind, hw, new)
        if self._pane_input is not None and self._pane_input[3] == old:
            guid, kind, hw, _mode = self._pane_input
            self._pane_input = (guid, kind, hw, new)
            if self._pane_shadow is not None:
                self._pane_shadow.mode = new
            self.paneModelChanged.emit()

    def _on_mode_deleted(self, name: str) -> None:
        before = len(self._undo) + len(self._redo)
        self._undo = [s for s in self._undo if s["key"][3] != name]
        self._redo = [s for s in self._redo if s["key"][3] != name]
        if len(self._undo) + len(self._redo) != before:
            self.undoChanged.emit()
        if self._pane_input is not None and self._pane_input[3] == name:
            # OK would write into a mode that is gone.
            self.endPane()
            self.paneLost.emit()
            signal.showNotification.emit(
                "Action Editor Closed",
                f"The mode {name} was deleted, so its action editor closed.",
            )

    def _get_pane_mode(self) -> str:
        return str(self._pane_input[3]) if self._pane_input is not None else ""

    # The mode the open pane edits (the page names it when it differs).
    paneMode = QtCore.Property(str, fget=_get_pane_mode, notify=paneModelChanged)

    @QtCore.Slot()
    def _forget_steps(self) -> None:
        if self._undo or self._redo:
            self._undo.clear()
            self._redo.clear()
            self.undoChanged.emit()

    def _play(self, step: dict, side: str) -> bool:
        profile = shared_state.current_profile
        if profile is None:
            return False
        guid, kind, hw, mode = step["key"]
        try:
            profile.put_input(guid, kind, hw, mode, step[side])
        except error.ProfileError as e:
            logging.getLogger("system").warning(f"Undo step not played: {e}")
            signal.showNotification.emit("Undo", "That change couldn't be put back.")
            return False
        signal.inputItemChanged.emit(step["hid"])
        signal.reloadCurrentInputItem.emit()
        self.reload()
        self.undoChanged.emit()
        return True

    @QtCore.Slot()
    def undo(self) -> None:
        # Not while an action is open in the pane: it is edited there.
        if self._undo and self._pane_shadow is None:
            step = self._undo.pop()
            if self._play(step, "before"):
                self._redo.append(step)
            else:
                self._undo.append(step)  # kept, not lost

    @QtCore.Slot()
    def redo(self) -> None:
        if self._redo and self._pane_shadow is None:
            step = self._redo.pop()
            if self._play(step, "after"):
                self._undo.append(step)
            else:
                self._redo.append(step)

    def _can_undo(self) -> bool:
        return bool(self._undo) and self._pane_shadow is None

    def _can_redo(self) -> bool:
        return bool(self._redo) and self._pane_shadow is None

    canUndo = QtCore.Property(bool, fget=_can_undo, notify=undoChanged)
    canRedo = QtCore.Property(bool, fget=_can_redo, notify=undoChanged)

    def _control_spec(self, device_index: int):
        want = int(device_index)
        profile = shared_state.current_profile
        dev = getattr(self._claimed, "_device", None)
        if profile is None or dev is None or want < 0:
            return None
        mode = str(getattr(self._claimed, "_mode", None) or "Default")
        for i in range(self._claimed.rowCount()):
            if int(self._claimed.deviceIndexAt(i)) != want:
                continue
            kind = type_of(self._claimed.kindAt(i))
            hw = int(self._claimed.hwIdAt(i))
            item = profile.get_input_item(
                dev.device_guid.uuid,
                kind,
                hw,
                mode,
                create_if_missing=False,
            )
            return profile, dev.device_guid.uuid, kind, hw, mode, item
        return None

    def _binding(self) -> InputItemBinding | None:
        shadow = self._pane_shadow
        if shadow is None or not shadow.action_sequences:
            return None
        return shadow.action_sequences[0]

    def _clear_pane_model(self) -> None:
        model = self._pane_model
        self._pane_model = None
        self.paneModelChanged.emit()
        if model is not None:
            model.deleteLater()

    def _retarget_draft(self, real: InputItem, only_index: int | None = None) -> None:
        """Keep editing a copy of the actions OK just wrote."""
        draft = _shadow_item(real)
        bindings = real.action_sequences
        if only_index is not None and 0 <= only_index < len(bindings):
            bindings = [bindings[only_index]]
        for binding in bindings:
            _clone_binding(binding, draft)
        self._pane_shadow = draft
        self._pane_real = real
        self._pane_base = _fingerprint_item(draft)
        from gremlin.ui.profile import InputItemModel

        old = self._pane_model
        self._pane_model = InputItemModel(draft, self._pane_hid, self)
        self.paneModelChanged.emit()
        if old is not None:
            old.deleteLater()

    def _replace_sequences(self, real: InputItem, shadow: InputItem) -> None:
        old = list(real.action_sequences)
        moved = list(shadow.action_sequences)
        real.action_sequences = []
        for binding in moved:
            binding.input_item = real
            real.action_sequences.append(binding)
        for binding in old:
            if binding.root_action is None or binding in moved:
                continue
            real.library.remove_unused(binding.root_action)

    @QtCore.Slot(int, int, result=int)
    def beginPane(self, device_index: int, sequence_index: int) -> int:
        """Open the parent's actions, or one child when sequence_index is set."""
        self.endPane()
        spec = self._control_spec(int(device_index))
        if spec is None:
            return 0
        profile, guid, kind, hw, mode, real = spec
        seq = int(sequence_index)
        if seq >= 0 and (real is None or seq >= len(real.action_sequences)):
            return 0
        shadow = InputItem(profile.library)
        shadow.device_id = guid
        shadow.input_type = kind
        shadow.input_id = hw
        shadow.mode = mode
        whole = False
        if seq < 0 and real is not None and real.action_sequences:
            for binding in real.action_sequences:
                _clone_binding(binding, shadow)
            whole = True
        elif seq < 0:
            shadow.add_item_binding()
        else:
            _clone_binding(real.action_sequences[seq], shadow)
        from gremlin.ui.profile import InputItemModel

        self._pane_real = real
        self._pane_shadow = shadow
        self._pane_seq = seq
        self._pane_hid = int(device_index)
        self._pane_input = (guid, kind, hw, mode)
        self._pane_whole = whole
        self._pane_base = _fingerprint_item(shadow)
        self._pane_model = InputItemModel(shadow, int(device_index), self)
        self.paneModelChanged.emit()
        return len(shadow.action_sequences) if whole else 0

    @QtCore.Slot(result=bool)
    def paneDirty(self) -> bool:
        shadow = self._pane_shadow
        if shadow is None:
            return False
        if not shadow.action_sequences:
            # Every action removed in the pane: OK takes them off the input.
            real = self._pane_real
            return self._pane_whole and bool(real and real.action_sequences)
        return _fingerprint_item(shadow) != self._pane_base

    @QtCore.Slot(result=int)
    def commitPane(self) -> int:
        """Write the draft onto the real control. Returns the child index."""
        shadow = self._pane_shadow
        if shadow is None or not self.paneDirty():
            return self._pane_seq
        key = self._pane_input
        before = self._snapshot(self._pane_hid, key)
        real = self._pane_real
        if real is None:
            spec = self._spec_for(self._pane_hid, key)
            if spec is None:
                return -1
            profile, guid, kind, hw, mode, _item = spec
            real = profile.get_input_item(guid, kind, hw, mode, create_if_missing=True)
            self._pane_real = real
        if real is None:
            return -1
        if self._pane_whole or self._pane_seq < 0:
            self._replace_sequences(real, shadow)
            self._pane_seq = -1
            self._pane_whole = True
            self._retarget_draft(real, None)
            index = 0
        else:
            index = _attach_binding(real, shadow, self._pane_seq)
            self._pane_seq = index
            self._pane_whole = False
            self._retarget_draft(real, index)
        self._step(self._pane_hid, before, key)
        signal.inputItemChanged.emit(self._pane_hid)
        return index

    @QtCore.Slot()
    def discardPane(self) -> None:
        """Drop the open draft. A child already written by OK stays."""
        _drop_shadow(self._pane_shadow)
        self._pane_shadow = None
        self._pane_base = ""

    @QtCore.Slot()
    def endPane(self) -> None:
        """Close the draft. An uncommitted draft is deleted. An OK'd child stays."""
        _drop_shadow(self._pane_shadow)
        self._pane_shadow = None
        self._pane_real = None
        self._pane_seq = -1
        self._pane_hid = -1
        self._pane_input = None
        self._pane_base = ""
        self._pane_whole = False
        self._clear_pane_model()

    @QtCore.Property(QtCore.QObject, notify=paneModelChanged)
    def paneModel(self):
        return self._pane_model


    def _get_park_empty(self) -> bool:
        return self._park_empty

    def _set_park_empty(self, value: bool) -> None:
        flag = bool(value)
        if flag == self._park_empty:
            return
        self._park_empty = flag
        self.reload()
        self.parkEmptyChanged.emit()

    guid = QtCore.Property(str, fget=_get_guid, fset=_set_guid, notify=guidChanged)
    deviceName = QtCore.Property(
        str, fget=_get_device_name, fset=_set_device_name, notify=deviceNameChanged
    )
    typeFilter = QtCore.Property(
        str, fget=_get_type_filter, fset=_set_type_filter, notify=filtersChanged
    )
    destFilter = QtCore.Property(
        str, fget=_get_dest_filter, fset=_set_dest_filter, notify=filtersChanged
    )
    parkEmptyInUnmapped = QtCore.Property(
        bool, fget=_get_park_empty, fset=_set_park_empty, notify=parkEmptyChanged
    )

    @QtCore.Property("QStringList", notify=filtersChanged)
    def destChoices(self) -> list[str]:
        return list(self._dest_choices)

    @QtCore.Property(int, notify=countChanged)
    def count(self) -> int:
        return len(self._rows)
