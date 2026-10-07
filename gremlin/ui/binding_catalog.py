# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
# Device-Configuration-Macro Change — binding catalog for Configuration.

from __future__ import annotations

import logging
import os
import sys

from PySide6 import QtCore

import gremlin.ui.type_aliases as ta
from gremlin import error, run_scope, shared_state
from gremlin.modules import wiring
from gremlin.modules.claim import type_of
from gremlin.profile import (
    Draft,
    DraftOutdated,
    InputItem,
    InputItemBinding,
    binding_fingerprint,
    bindings_fingerprint,
)
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


def _fingerprint_item(item: InputItem) -> str:
    return bindings_fingerprint(item.action_sequences)


def _fingerprint(binding: InputItemBinding) -> str:
    return binding_fingerprint(binding)


# The Type box, in order: (filter key, the action tag it picks). Its names
# are the plugins' action names (05 Q6, RB12).
_TYPE_FILTERS = [
    ("all", ""),
    ("vjoy", "map-to-vjoy"),
    ("keyboard", "map-to-keyboard"),
    ("mouse", "map-to-mouse"),
    ("xbox", "map-to-xbox"),
    ("macro", "macro"),
    ("mode", "change-mode"),
    ("other", ""),
    ("unmapped", ""),
]
_TYPE_FILTER_TEXT = {"all": "All types", "other": "Other", "unmapped": "No actions"}

_NAMED_FILTERS = {key: {tag} for key, tag in _TYPE_FILTERS if tag}


def action_name(tag: str) -> str:
    """The plugin's name for an action tag ("Map to Keyboard"), or the tag."""
    from gremlin.plugin_manager import PluginManager

    plugin = PluginManager().tag_map.get(tag)
    return str(getattr(plugin, "name", "") or tag)


def type_filter_names() -> list[str]:
    """The Type box's entries, in _TYPE_FILTERS order."""
    return [_TYPE_FILTER_TEXT.get(key) or action_name(tag) for key, tag in _TYPE_FILTERS]


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
    # The action's own (plugin) name, as Add Action shows it.
    label = str(getattr(action, "name", None) or tag or "Action")
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
    if tag in _WRAPPERS:
        out: list[tuple[str, str, str]] = []
        for child in kids:
            out.extend(collect_leaves(child))
        return out
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
            out.append((index, f"{len(leaves)} actions", dest))
        else:
            # Nothing that acts yet (an empty Tempo, say): its name, and
            # "No actions" (05 S14, Q6).
            kids = _action_children(root) if root is not None else []
            label = str(getattr(kids[0], "name", "") or "") if kids else ""
            out.append((index, label or "No actions", "No actions"))
    return out


def binding_note(binding: object) -> str:
    """The binding's Note (its root action's label), "" when none was given
    (05 S43): a new binding's root keeps the plugin name, "Root"."""
    root = getattr(binding, "root_action", None)
    if root is None:
        return ""
    text = str(getattr(root, "action_label", "") or "").strip()
    return "" if text == str(getattr(type(root), "name", "")) else text


def item_note(item: object, indices: list[int] | None = None) -> str:
    """The Notes of an input's bindings (only those in indices, when given),
    for its row on the Configuration list and the Keyboard page (05 S43,
    D-05-S43-BOTHROWS)."""
    sequences = getattr(item, "action_sequences", None) or []
    notes: list[str] = []
    for index, seq in enumerate(sequences):
        if indices is not None and index not in indices:
            continue
        note = binding_note(seq)
        if note and note not in notes:
            notes.append(note)
    return ", ".join(notes)


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
    """("1 action — dest" / "N actions — dests", the dests)."""
    summary = ", ".join(dest for _t, _l, dest in shown)
    count = "1 action" if len(shown) == 1 else f"{len(shown)} actions"
    return f"{count} — {summary}", summary


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


# --- The edit lock (06 S13, S82, RB14; 05 S32, S101) ------------------------


def editing_locked() -> bool:
    """The one locked-while-running rule: nothing in a profile is edited
    while it runs. The pages show it (EditLock) and the models refuse edits
    with it, so a page that misses it still can't change the profile."""
    return run_scope.running()


def _refused() -> bool:
    if not editing_locked():
        return False
    logging.getLogger("system").info("Edit refused: the profile is running")
    return True


@ta.QmlElement
class EditLock(QtCore.QObject):
    """QML side of editing_locked(): locked is true while the profile runs.

    Output pages (vJoy, Xbox) are not locked (06 S13); they don't use it.
    """

    lockedChanged = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        # Run and Stop are announced by the backend (activityChanged).
        backend = sys.modules.get("gremlin.ui.backend")
        owner = getattr(getattr(backend, "Backend", None), "instance", None)
        if owner is not None:
            owner.activityChanged.connect(self.lockedChanged)

    @QtCore.Slot()
    def refresh(self) -> None:
        self.lockedChanged.emit()

    @QtCore.Property(bool, notify=lockedChanged)
    def locked(self) -> bool:
        return editing_locked()


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
        QtCore.Qt.ItemDataRole.UserRole + 13: QtCore.QByteArray(b"note"),
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
        # The pane's copy (gremlin.profile.Draft); _pane_shadow is its input.
        self._pane_draft: Draft | None = None
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
            # The Note shows on the input's row (05 S43).
            note = item_note(item, [index for index, _lab, _dest in shown])
            if note:
                summary = f"{note} · {summary}"
            self._rows.append(
                {
                    "rowKind": "group",
                    "name": name,
                    "note": note,
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
                    "name": "No actions",
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
        if key == "note":
            return row.get("note", "")
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

    @QtCore.Slot(int, int, result=bool)
    def removeSequence(self, device_index: int, sequence_index: int) -> bool:
        """Delete one action sequence from a control."""
        want = int(device_index)
        seq = int(sequence_index)
        if want < 0 or seq < 0 or _refused():
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
            profile.library.release([binding.root_action])
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
        return profile.library.snapshot(item)

    def _step(
        self, device_index: int, before: dict | None, key: tuple | None = None
    ) -> None:
        spec = self._spec_for(device_index, key)
        if spec is None:
            return
        profile, guid, kind, hw, mode, item = spec
        after = profile.library.snapshot(item)
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
        try:
            profile.library.restore(step["key"], step[side])
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
        if self._undo and self._pane_shadow is None and not _refused():
            step = self._undo.pop()
            if self._play(step, "before"):
                self._redo.append(step)
            else:
                self._undo.append(step)  # kept, not lost

    @QtCore.Slot()
    def redo(self) -> None:
        if self._redo and self._pane_shadow is None and not _refused():
            step = self._redo.pop()
            if self._play(step, "after"):
                self._undo.append(step)
            else:
                self._redo.append(step)

    def _can_undo(self) -> bool:
        return bool(self._undo) and self._pane_shadow is None

    def _can_redo(self) -> bool:
        return bool(self._redo) and self._pane_shadow is None

    # Through lambdas so a subclass's rule is the one used.
    canUndo = QtCore.Property(
        bool, fget=lambda self: self._can_undo(), notify=undoChanged
    )
    canRedo = QtCore.Property(
        bool, fget=lambda self: self._can_redo(), notify=undoChanged
    )

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

    def _show_draft(self, draft: Draft) -> None:
        """Make this draft the pane's (a new pane model on its input)."""
        from gremlin.ui.profile import InputItemModel

        self._pane_draft = draft
        self._pane_shadow = draft.item
        self._pane_base = _fingerprint_item(draft.item)
        old = self._pane_model
        self._pane_model = InputItemModel(draft.item, self._pane_hid, self)
        self.paneModelChanged.emit()
        if old is not None:
            old.deleteLater()

    def _retarget_draft(self, real: InputItem, only_index: int | None = None) -> None:
        """Keep editing a copy of the actions OK just wrote."""
        self._pane_real = real
        self._show_draft(real.library.draft(real, only_index))

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
        draft = profile.library.draft(
            real, None if seq < 0 else seq, key=(guid, kind, hw, mode)
        )
        self._pane_real = real
        self._pane_seq = seq
        self._pane_hid = int(device_index)
        self._pane_input = (guid, kind, hw, mode)
        self._pane_whole = draft.whole
        self._show_draft(draft)
        return len(draft.item.action_sequences) if draft.whole else 0

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
        """Write the draft onto the real control (Library.commit: an action
        other inputs share changes for all of them). Returns the child
        index, or -1 when nothing could be written."""
        draft = self._pane_draft
        if draft is None or not self.paneDirty():
            return self._pane_seq
        if _refused():
            return -1
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
        whole = self._pane_whole or self._pane_seq < 0
        try:
            index = real.library.commit(draft, real, None if whole else self._pane_seq)
        except DraftOutdated:
            # History Restore, Auto Mapper or a Device Pack import changed
            # this input after the pane opened: OK would write over it.
            signal.showNotification.emit(
                "Action Editor",
                "This input was changed while its action editor was open, so "
                "OK didn't write over that change. Close the editor and open "
                "it again.",
            )
            return -1
        if whole:
            self._pane_seq = -1
            self._pane_whole = True
            self._retarget_draft(real, None)
            index = 0
        else:
            self._pane_seq = index
            self._pane_whole = False
            self._retarget_draft(real, index)
        self._step(self._pane_hid, before, key)
        signal.inputItemChanged.emit(self._pane_hid)
        return index

    def _drop_draft(self) -> None:
        draft, self._pane_draft = self._pane_draft, None
        self._pane_shadow = None
        if draft is not None:
            draft.library.discard(draft)

    @QtCore.Slot()
    def discardPane(self) -> None:
        """Drop the open draft. A child already written by OK stays."""
        self._drop_draft()
        self._pane_base = ""

    @QtCore.Slot()
    def endPane(self) -> None:
        """Close the draft. An uncommitted draft is deleted. An OK'd child stays."""
        self._drop_draft()
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

    @QtCore.Property(list, constant=True)
    def typeFilterNames(self) -> list[str]:
        """The Type box's entries; typeFilterKeys holds their filter keys."""
        return type_filter_names()

    @QtCore.Property(list, constant=True)
    def typeFilterKeys(self) -> list[str]:
        return [key for key, _tag in _TYPE_FILTERS]

    @QtCore.Property("QStringList", notify=filtersChanged)
    def destChoices(self) -> list[str]:
        return list(self._dest_choices)

    @QtCore.Property(int, notify=countChanged)
    def count(self) -> int:
        return len(self._rows)


@ta.QmlElement
class KeyboardPaneModel(BindingCatalogModel):
    """The Keyboard page's action pane (05 Q5, replaces S78): the selected
    key's actions as a draft that OK writes, with Undo and Redo for each OK,
    the same as the Configuration page's pane (Library draft and commit).

    A key with no binding yet (a new Add Key) shows one empty binding to
    fill in (Library.draft, 05 Q4). The pane is always open on the key
    shown: Undo and Redo drop the draft, play the step and open it again.
    """

    paneInputChanged = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        # The key shown: (device guid, input type, key) and its mode.
        self._input: tuple | None = None
        self._kb_mode = "Default"
        self._row = -1
        super().__init__(parent)

    def _rebuild(self) -> None:
        # No rows: the page lists the keys itself.
        if self._rows:
            self.beginResetModel()
            self._rows = []
            self.endResetModel()

    @QtCore.Slot(QtCore.QObject, int, str)
    def showInput(self, identifier: QtCore.QObject | None, row: int, mode: str) -> None:
        """Opens the pane on this key in this mode (nothing is written
        until OK). No key: the pane closes."""
        import dill

        # Only a key: the editor can still hold another page's input.
        guid = getattr(identifier, "device_guid", None)
        valid = (
            bool(getattr(identifier, "isValid", False)) and guid == dill.UUID_Keyboard
        )
        self._input = (
            (guid, getattr(identifier, "input_type"), getattr(identifier, "input_id"))
            if valid
            else None
        )
        self._kb_mode = str(mode or "Default")
        self._row = int(row)
        if self._input is None:
            self.endPane()
        else:
            self.beginPane(self._row, -1)
        self.paneInputChanged.emit()

    def _control_spec(self, device_index: int) -> tuple | None:
        profile = shared_state.current_profile
        if profile is None or self._input is None:
            return None
        guid, kind, hw = self._input
        item = profile.get_input_item(
            guid, kind, hw, self._kb_mode, create_if_missing=False
        )
        return profile, guid, kind, hw, self._kb_mode, item

    def _reopen(self) -> None:
        if self._input is not None:
            self.beginPane(self._row, -1)
            self.paneInputChanged.emit()

    def _can_undo(self) -> bool:
        return bool(self._undo)

    def _can_redo(self) -> bool:
        return bool(self._redo)

    @QtCore.Slot()
    def undo(self) -> None:
        """The last OK taken back; an unsaved draft is dropped (the page
        asks first)."""
        if not self._undo or _refused():
            return
        self.endPane()
        step = self._undo.pop()
        if self._play(step, "before"):
            self._redo.append(step)
        else:
            self._undo.append(step)
        self.undoChanged.emit()
        self._reopen()

    @QtCore.Slot()
    def redo(self) -> None:
        if not self._redo or _refused():
            return
        self.endPane()
        step = self._redo.pop()
        if self._play(step, "after"):
            self._undo.append(step)
        else:
            self._redo.append(step)
        self.undoChanged.emit()
        self._reopen()

    @QtCore.Slot()
    def revert(self) -> None:
        """Cancel: the draft goes back to the key's saved actions."""
        self.endPane()
        self._reopen()

    @QtCore.Property(str, notify=paneInputChanged)
    def keyName(self) -> str:
        if self._input is None:
            return ""
        _guid, _kind, hw = self._input
        try:
            from gremlin import keyboard

            return str(keyboard.key_from_code(*hw).name)
        except Exception:
            return str(hw)
