# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
# Action summaries and filters shared by the control pages (Device Bindings,
# Keyboard, Logical Device, OSC) and the edit lock. The Device Bindings page's
# model is gremlin/ui/hardware_layout.py (05 S121, RB16).

from __future__ import annotations

import os
import sys

from PySide6 import QtCore

import gremlin.ui.type_aliases as ta
from gremlin import run_scope
from gremlin.modules import wiring

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


# The Type box, in order: (filter key, the action tag it picks). Its names
# are the plugins' action names (05 Q6, RB12). Inputs with no actions are
# found with the No actions in this mode filter, not here (05 S18, S123).
_TYPE_FILTERS = [
    ("all", ""),
    ("vjoy", "map-to-vjoy"),
    ("keyboard", "map-to-keyboard"),
    ("mouse", "map-to-mouse"),
    ("xbox", "map-to-xbox"),
    ("macro", "macro"),
    ("mode", "change-mode"),
    ("other", ""),
]
_TYPE_FILTER_TEXT = {"all": "All types", "other": "Other"}

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
    for its row on the Device Bindings list and the Keyboard page (05 S43,
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


def item_leaves(item: object) -> list[tuple[str, str, str]]:
    """Every action of every binding of an input: (tag, label, target)."""
    out: list[tuple[str, str, str]] = []
    for seq in getattr(item, "action_sequences", None) or []:
        root = getattr(seq, "root_action", None)
        if root is not None:
            out.extend(collect_leaves(root))
    return out


def binding_targets(leaves: list[tuple]) -> list[str]:
    """An input row's binding boxes (05 S142): one target text per action
    from its leaves (tag, label, target), in order. An action with no
    target has no box; it still counts in the row's number."""
    return [dest for _t, _l, dest in leaves if dest]


# --- The edit lock (06 S13, S82, RB14; 05 S32, S101) ------------------------


def editing_locked() -> bool:
    """The one locked-while-running rule: nothing in a profile is edited
    while it runs. The pages show it (EditLock) and the models refuse edits
    with it, so a page that misses it still can't change the profile."""
    return run_scope.running()


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
