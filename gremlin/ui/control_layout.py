# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
"""Shared row model for control pages (Logical Device, OSC, later Configuration).

ControlLayoutModel (gremlin/ui/control_layout.py) is the device-independent
row model behind a control page: groups, parents (inputs), child rows
(actions + subclass rows), Find/filters, page Undo (50 steps), selection,
order, and the shared action pane. It is NOT registered with QML itself;
each subclass carries @ta.QmlElement in its own module
(QML_IMPORT_NAME = "Gremlin.Device").

Public names (QML), unchanged from LogicalLayoutModel:
  signals   revisionChanged, groupsChanged, selectionChanged,
            paneModelChanged, paneLost
  props     canUndo, canRedo, lastChange, undone, undoTip, redoTip,
            paneModel, parentCount, selectionCount, selectionLabel, groups
  slots     undo(), redo(), setMode(str), deleteAction(str,int)->bool,
            addGroup(str), renameGroup(str,str), removeGroup(str),
            setUserName(str,str), hidesSystem(str)->bool,
            setRowLabel(str,str,bool), moveSelected(str),
            deleteParents(list), moveRow(str,str), moveParent(str,str,str),
            sortBySystem(), sortByName(), sortGroupNames(),
            moveGroupUp(str), moveGroupDown(str),
            setFilter(search, type, ungrouped, no_writer, no_actions),
            setSelection(list), keyAt(int)->str,
            beginPane(str,int)->int, beginNewAction(str)->int,
            paneDirty()->bool, commitPane()->int, discardPane(), endPane()
  roles     rowKind key title subtitle parentKey groupKey groupName
            systemName userName writerId axisMode axisScale inverted
            sequenceIndex indent canInvert childCount extraWriters
  keys      "group:<name>", "parent:<button|axis|hat>:<id>",
            "child:<word>:<id>:<seq>"; subclass rows pick their own prefix
            (Logical: "writer:<action id>"; OSC feedback e.g. "feedback:<uid>").
  setSelection keeps "parent:" keys only.

The layout store (self._layout, from _make_store()): duck-typed, the
LogicalDevice API. An OSC store over osc.json implements the same:
  memento() -> object (== comparable; equal means nothing changed)
  restore(memento) -> None
  group_names() -> list[str]               (order shown; "" not included)
  ordered() -> list[Item]                  (every input, page order)
  exists(identifier) -> bool
  __getitem__(identifier) -> Item
  ensure_group(name) -> str
  rename_group(old, new) -> None           (GremlinError: refused, message shown)
  delete_group(name) -> None               (members go to Ungrouped)
  place(identifier, group, before_identifier=None) -> None
  move_group_before(name, before_name | None) -> None   (None: last)
  sort_within("system" | "user") -> None   ("system": the sort-by-system key;
                                             OSC: by address)
  sort_groups() -> None
  set_user_label(identifier, text) -> None
  delete(identifier) -> None
Item (read only by the base):
  type: InputType, id: int, identifier (hashable, what the store takes),
  group: str | None, system_name: str, second_name: str (user name),
  label: str, row_title: str, choice_label: str (Undo labels),
  hide_system: bool (settable; optional, getattr default False)

The base does not rebuild in __init__: a subclass connects its signals,
then calls self._rebuild() at the end of its own __init__.

Hooks. Required (base raises NotImplementedError):
  _make_store(self) -> store                     called once in __init__
  _device_guid(self) -> uuid.UUID                the device the pane edits and
                                                 whose InputItems hold actions
                                                 (Logical: LOGICAL device guid;
                                                 OSC: OSC_GUID; Configuration:
                                                 the device shown, may change)
  _identifier(self, kind: InputType, input_id: int) -> identifier
  _emit_store_changed(self) -> None              tell the program the store
                                                 changed (Logical: emits
                                                 signal.logicalDeviceModified).
                                                 The base sets self._writing
                                                 around it, so connect your
                                                 "changed elsewhere" signal to
                                                 self._on_external and "file
                                                 read again" to self._on_reloaded.
Optional (default shown):
  _type_order(self) -> tuple[InputType, ...]     (Button, Axis, Hat)
  _extra_rows(self, item) -> list[dict]          [] ; rows owned by the
                                                 subclass, computed once per
                                                 parent per rebuild (Logical:
                                                 writer rows). Build with
                                                 self._row(**fields).
  _parent_title(self, item) -> str               item.row_title
                                                 (OSC: "Button 3 - /deck/1   Gear
                                                 Toggle")
  _parent_subtitle(self, item, extra) -> str     "" (Logical: first writer's
                                                 title; OSC: settings line)
  _parent_fields(self, item, extra) -> dict      {} ; more role values for the
                                                 parent row (Logical: writerId,
                                                 axisMode, axisScale, inverted,
                                                 canInvert, extraWriters)
  _rows_before_actions(self, item, extra) -> list[dict]   extra
                                                 (Logical: extra[1:])
  _rows_after_actions(self, item, extra) -> list[dict]    []
                                                 (OSC later: feedback rows,
                                                 "actions then feedback")
  _matches(self, item, search, type_filter) -> bool
                                                 type word == type_filter (or
                                                 "all"), then search in
                                                 system_name, second_name,
                                                 group, label
  _visible_parent(self, item, extra, action_count) -> bool
                                                 ungrouped-only / no_writer
                                                 (len(extra)) / no_actions,
                                                 then _matches
  _filtering(self) -> bool                       any base filter on; override
                                                 with your extra filters
                                                 (Configuration: Type/Output)
  _sort_system_label(self) -> str                "Sort by System Name"
                                                 (OSC: "Sort by Address")
  _can_remove(self, item) -> bool                True (Configuration: claimed
                                                 rows False)
  _delete_parent(self, item) -> list[dict]       own InputItems taken (Undo
                                                 copies) + store.delete;
                                                 returns link records
                                                 (Logical: detaches writer
                                                 links first)
  _play_link(self, entry, forward: bool) -> None no-op; plays a link record
                                                 whose op isn't "input"
                                                 (Logical: "add"/"remove")
  _steps_after_profile(self, steps) -> list[dict]
                                                 keeps the store part of each
                                                 step, drops its link records
                                                 (the store is shared by every
                                                 profile)
  _selection_name(self, item) -> str             item.system_name

Helpers a subclass may call:
  self._row(**fields) -> dict      a row with every role filled (defaults)
  self._apply(fn, label) -> bool   fn() edits the store and returns link
                                   records; one Undo step; False: refused
  self._rebuild(), self._refused(), self._profile(), self._item_for(key),
  self._snapshot(item), self._input_key(item), self._take_own_items(kind, id)
  self._mode, self._search, self._type_filter, self._ungrouped_only,
  self._no_writer, self._no_actions, self._selected
module helpers: kind_word(kind), parse_parent(key), parent_key(kind, id),
  group_key(name), count_text(buttons, axes, hats)
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable, Hashable
from typing import TYPE_CHECKING, Any, Protocol

from PySide6 import QtCore

import gremlin.ui.type_aliases as ta
from gremlin import error, shared_state
from gremlin.error import GremlinError
from gremlin.profile import Draft, DraftOutdated, InputItem, bindings_fingerprint
from gremlin.signal import signal
from gremlin.types import InputType
from gremlin.ui.binding_catalog import editing_locked, sequences_for_item

if TYPE_CHECKING:
    from gremlin.profile import Profile

TYPE_ORDER = (
    InputType.JoystickButton,
    InputType.JoystickAxis,
    InputType.JoystickHat,
)
KIND_WORD = {
    InputType.JoystickButton: "button",
    InputType.JoystickAxis: "axis",
    InputType.JoystickHat: "hat",
}


def kind_word(kind: InputType) -> str:
    return KIND_WORD.get(kind, "button")


def parse_parent(key: str) -> tuple[InputType, int] | None:
    text = str(key or "")
    if text.startswith("parent:"):
        text = text[len("parent:") :]
    parts = text.split(":")
    if len(parts) != 2:
        return None
    try:
        return InputType.to_enum(parts[0]), int(parts[1])
    except (GremlinError, ValueError):
        return None


def parent_key(kind: InputType, input_id: int) -> str:
    return f"parent:{kind_word(kind)}:{int(input_id)}"


def group_key(name: str | None) -> str:
    return "group:" + (name or "")


def count_text(buttons: int, axes: int, hats: int) -> str:
    parts = []
    if buttons:
        parts.append(f"{buttons} button" if buttons == 1 else f"{buttons} buttons")
    if axes:
        parts.append(f"{axes} axis" if axes == 1 else f"{axes} axes")
    if hats:
        parts.append(f"{hats} hat" if hats == 1 else f"{hats} hats")
    return " · ".join(parts) if parts else "Empty"


class LayoutItem(Protocol):
    """A parent as the base reads it (gremlin.logical_device's Input)."""

    @property
    def type(self) -> InputType: ...
    @property
    def id(self) -> int: ...
    @property
    def identifier(self) -> Hashable: ...
    @property
    def group(self) -> str | None: ...
    @property
    def system_name(self) -> str: ...
    @property
    def second_name(self) -> str: ...
    @property
    def label(self) -> str: ...
    @property
    def row_title(self) -> str: ...
    @property
    def choice_label(self) -> str: ...


# Every row has every role; _row fills what a caller leaves out.
ROW_DEFAULTS: dict[str, Any] = {
    "rowKind": "",
    "key": "",
    "title": "",
    "subtitle": "",
    "parentKey": "",
    "groupKey": "",
    "groupName": "",
    "systemName": "",
    "userName": "",
    "writerId": "",
    "axisMode": "",
    "axisScale": 1.0,
    "inverted": False,
    "sequenceIndex": -1,
    "indent": 0,
    "canInvert": False,
    "childCount": 0,
    "extraWriters": 0,
}


class ControlLayoutModel(QtCore.QAbstractListModel):
    """Rows for a control page: group headers, parents, and their child rows."""

    roles = {
        QtCore.Qt.ItemDataRole.UserRole + 1 + i: QtCore.QByteArray(name.encode())
        for i, name in enumerate(ROW_DEFAULTS)
    }

    revisionChanged = QtCore.Signal()
    groupsChanged = QtCore.Signal()
    selectionChanged = QtCore.Signal()
    paneModelChanged = QtCore.Signal()
    # The pane's mode was deleted: the page closes it.
    paneLost = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._layout = self._make_store()
        self._mode = "Default"
        self._rows: list[dict] = []
        self._search = ""
        self._type_filter = "all"
        self._ungrouped_only = False
        self._no_writer = False
        self._no_actions = False
        self._selected: list[str] = []
        self._undo: list[dict] = []
        self._redo: list[dict] = []
        # The newest step was an Undo: the Undo bar says what Redo puts back.
        self._just_undid = False
        self._writing = False
        self._pane_model = None
        # The pane's copy (gremlin.profile.Draft); _pane_shadow is its input.
        self._pane_draft: Draft | None = None
        self._pane_shadow: InputItem | None = None
        self._pane_real: InputItem | None = None
        self._pane_seq = -1
        self._pane_key = ""
        self._pane_base = ""
        self._pane_whole = False
        self._pane_new = False
        signal.profileChanged.connect(self._on_profile)
        signal.modeRenamed.connect(self._on_mode_renamed)
        signal.modeDeleted.connect(self._on_mode_deleted)

    # Hooks (see the module docstring).

    def _make_store(self) -> Any:  # noqa: ANN401 - duck-typed store
        raise NotImplementedError

    def _device_guid(self) -> uuid.UUID:
        raise NotImplementedError

    def _identifier(self, kind: InputType, input_id: int) -> Hashable:
        raise NotImplementedError

    def _emit_store_changed(self) -> None:
        raise NotImplementedError

    def _type_order(self) -> tuple[InputType, ...]:
        return TYPE_ORDER

    def _extra_rows(self, item: LayoutItem) -> list[dict]:
        return []

    def _parent_title(self, item: LayoutItem) -> str:
        return item.row_title

    def _parent_subtitle(self, item: LayoutItem, extra: list[dict]) -> str:
        return ""

    def _parent_fields(self, item: LayoutItem, extra: list[dict]) -> dict:
        return {}

    def _rows_before_actions(self, item: LayoutItem, extra: list[dict]) -> list[dict]:
        return extra

    def _rows_after_actions(self, item: LayoutItem, extra: list[dict]) -> list[dict]:
        return []

    def _rows_at_end(self) -> list[dict]:
        """Rows after every group (OSC: feedback not tied to an input)."""
        return []

    def _matches(self, item: LayoutItem, search: str, type_filter: str) -> bool:
        if type_filter not in ("", "all") and kind_word(item.type) != type_filter:
            return False
        if not search:
            return True
        hay = " ".join(
            (item.system_name, item.second_name, item.group or "", item.label)
        ).lower()
        return search.lower() in hay

    def _visible_parent(
        self, item: LayoutItem, extra: list[dict], action_count: int
    ) -> bool:
        if self._ungrouped_only and (item.group or ""):
            return False
        if self._no_writer and extra:
            return False
        if self._no_actions and action_count:
            return False
        return self._matches(item, self._search, self._type_filter)

    def _filtering(self) -> bool:
        return bool(
            self._search
            or self._type_filter not in ("", "all")
            or self._ungrouped_only
            or self._no_writer
            or self._no_actions
        )

    def _sort_system_label(self) -> str:
        return "Sort by System Name"

    def _can_remove(self, item: LayoutItem) -> bool:
        return True

    def _delete_parent(self, item: LayoutItem) -> list[dict]:
        links = self._take_own_items(item.type, item.id)
        self._layout.delete(item.identifier)
        return links

    def _play_link(self, entry: dict, forward: bool) -> None:
        return None

    def _steps_after_profile(self, steps: list[dict]) -> list[dict]:
        # The store is shared by every profile (D-04-LD-FILE), so its steps
        # stay when another profile loads (06 S83). What a step did to the
        # old profile's actions and links stays with that profile: those
        # parts go, and a step with nothing else goes too.
        kept = []
        for entry in steps:
            if entry["before"] == entry["after"]:
                continue
            kept.append({**entry, "links": []})
        return kept

    def _selection_name(self, item: LayoutItem) -> str:
        return item.system_name

    # Signals from the rest of the program.

    def _on_mode_renamed(self, old: str, new: str) -> None:
        # Steps and the open pane follow the new name.
        for entry in self._undo + self._redo:
            for link in entry["links"]:
                if link.get("op") == "input" and link["key"][3] == old:
                    guid, kind, number, _mode = link["key"]
                    link["key"] = (guid, kind, number, new)
                elif link.get("mode") == old:
                    link["mode"] = new
        if self._pane_shadow is not None and self._pane_shadow.mode == old:
            self._pane_shadow.mode = new

    def _on_mode_deleted(self, name: str) -> None:
        # Steps could bring inputs back into the deleted mode.
        if self._undo or self._redo:
            self._undo.clear()
            self._redo.clear()
            self.revisionChanged.emit()
        if self._pane_shadow is not None and self._pane_shadow.mode == name:
            self.endPane()
            self.paneLost.emit()
            signal.showNotification.emit(
                "Action Editor Closed",
                f"The mode {name} was deleted, so its action editor closed.",
            )

    def _on_profile(self) -> None:
        self._undo = self._steps_after_profile(self._undo)
        self._redo = self._steps_after_profile(self._redo)
        self._on_external()

    def drop_steps(self) -> None:
        self._undo.clear()
        self._redo.clear()
        self._just_undid = False
        self.revisionChanged.emit()

    def _on_reloaded(self) -> None:
        self.drop_steps()
        self._rebuild()

    def _on_external(self) -> None:
        if self._writing:
            return
        self._rebuild()

    def _profile(self) -> Profile | None:
        return shared_state.current_profile

    def _changed(self) -> None:
        self._writing = True
        try:
            self._emit_store_changed()
        finally:
            self._writing = False
        self._rebuild()

    # Undo.

    def _refused(self) -> bool:
        """The edit lock (binding_catalog.editing_locked): nothing changes
        while the profile runs (06 S82, RB14)."""
        if not editing_locked():
            return False
        logging.getLogger("system").info("Edit refused: the profile is running")
        return True

    def _apply(self, fn: Callable[[], list[dict] | None], label: str = "") -> bool:
        """Runs fn (an edit) as one Undo step named label (the Undo bar's
        "Last change: <label>"; empty: not named). False: refused (running)."""
        if self._refused():
            return False
        before = self._layout.memento()
        links = fn() or []
        after = self._layout.memento()
        if before == after and not links:
            # Nothing changed (the same name typed again): no step.
            self._changed()
            return True
        self._undo.append(
            {"before": before, "after": after, "links": links, "label": label}
        )
        self._just_undid = False
        if len(self._undo) > 50:
            self._undo.pop(0)
        self._redo.clear()
        self._changed()
        return True

    # An input's actions before and after a change, kept as copies (XML, as
    # the Configuration page keeps them: Library.snapshot / restore).
    # Live action objects were kept before; the library could drop or hand
    # them out again, and the saved profile then didn't load.

    @staticmethod
    def _input_key(item: InputItem) -> tuple:
        return (item.device_id, item.input_type, item.input_id, item.mode)

    def _snapshot(self, item: InputItem | None) -> dict | None:
        profile = self._profile()
        return profile.library.snapshot(item) if profile is not None else None

    def _play(self, links: list[dict], reverse: bool) -> None:
        entries = list(reversed(links)) if reverse else list(links)
        profile = self._profile()
        for entry in entries:
            if entry.get("op") == "input":
                if profile is not None:
                    side = entry["before"] if reverse else entry["after"]
                    profile.library.restore(entry["key"], side)
                continue
            self._play_link(entry, not reverse)

    def _replay(self, entry: dict, reverse: bool) -> bool:
        """Plays a step; False when it couldn't be (a damaged copy)."""
        try:
            # Every input copy is checked first: one that can't be put back
            # leaves the whole step unplayed, not half of it.
            profile = self._profile()
            for link in entry["links"]:
                if link.get("op") == "input" and profile is not None:
                    side = link["before"] if reverse else link["after"]
                    profile.library.restore(link["key"], side, check_only=True)
            self._layout.restore(entry["before"] if reverse else entry["after"])
            self._play(entry["links"], reverse)
        except error.ProfileError as e:
            logging.getLogger("system").warning(f"Undo step not played: {e}")
            signal.showNotification.emit("Undo", "That change couldn't be put back.")
            return False
        return True

    @QtCore.Slot()
    def undo(self) -> None:
        if not self._undo or self._refused():
            return
        entry = self._undo.pop()
        if self._replay(entry, True):
            self._redo.append(entry)
            self._just_undid = True
        else:
            self._undo.append(entry)
        self._changed()

    @QtCore.Slot()
    def redo(self) -> None:
        if not self._redo or self._refused():
            return
        entry = self._redo.pop()
        if self._replay(entry, False):
            self._undo.append(entry)
            self._just_undid = False
        else:
            self._redo.append(entry)
        self._changed()

    def _take_own_items(self, kind: InputType, input_id: int) -> list[dict]:
        """Drops the device's own inputs for a parent; returns their Undo
        copies."""
        profile = self._profile()
        if profile is None:
            return []
        guid = self._device_guid()
        items = list(profile.inputs.get(guid, []))
        taken = []
        doomed = []
        for item in items:
            if item.input_type == kind and item.input_id == input_id:
                # Undo puts its copy back; Redo takes it out again (it used
                # to put it back both ways, and a new row inherited it).
                taken.append(
                    {
                        "op": "input",
                        "key": self._input_key(item),
                        "before": self._snapshot(item),
                        "after": None,
                    }
                )
                doomed.append(item)
        if doomed:
            profile.drop_inputs(guid, doomed)
        return taken

    # Rows.

    def _row(self, **fields: object) -> dict:
        return {**ROW_DEFAULTS, **fields}

    def _child_rows(self, item: LayoutItem) -> list[dict]:
        profile = self._profile()
        rows: list[dict] = []
        if profile is None:
            return rows
        real = profile.get_input_item(
            self._device_guid(),
            item.type,
            item.id,
            self._mode,
            create_if_missing=False,
        )
        key = parent_key(item.type, item.id)
        group = group_key(item.group)
        for index, label, dest in sequences_for_item(real):
            rows.append(
                self._row(
                    rowKind="child",
                    key=f"child:{kind_word(item.type)}:{item.id}:{index}",
                    title=label or "Action",
                    subtitle=dest or "",
                    parentKey=key,
                    groupKey=group,
                    groupName=item.group or "",
                    systemName=item.system_name,
                    sequenceIndex=index,
                    indent=1,
                )
            )
        return rows

    def _counts(self, items: list) -> tuple[int, int, int]:
        buttons = sum(1 for item in items if item.type == InputType.JoystickButton)
        axes = sum(1 for item in items if item.type == InputType.JoystickAxis)
        hats = sum(1 for item in items if item.type == InputType.JoystickHat)
        return buttons, axes, hats

    def _rebuild(self) -> None:
        self.beginResetModel()
        rows: list[dict] = []
        folders = [""] + self._layout.group_names()
        filtering = self._filtering()
        order = self._type_order()
        # Nothing at all: no rows, so the page's empty-list text shows (01 S143).
        if len(folders) == 1 and not self._layout.ordered():
            folders = []
        for folder in folders:
            members = [
                item for item in self._layout.ordered() if (item.group or "") == folder
            ]
            shown = []
            for item in members:
                extra = self._extra_rows(item)
                children = self._child_rows(item)
                if not filtering or self._visible_parent(item, extra, len(children)):
                    shown.append((item, extra, children))
            if filtering and not shown:
                continue
            # The header counts the parents in the group, or what a filter
            # still shows.
            counted = [entry[0] for entry in shown] if filtering else members
            rows.append(
                self._row(
                    rowKind="group",
                    key=group_key(folder),
                    title=folder or "Ungrouped",
                    subtitle=count_text(*self._counts(counted)),
                    groupKey=group_key(folder),
                    groupName=folder,
                    childCount=len(shown),
                )
            )
            buckets: dict[InputType, list] = {kind: [] for kind in order}
            for entry in shown:
                if entry[0].type in buckets:
                    buckets[entry[0].type].append(entry)
            for kind in order:
                for item, extra, children in buckets[kind]:
                    key = parent_key(item.type, item.id)
                    rows.append(
                        self._row(
                            rowKind="parent",
                            key=key,
                            title=self._parent_title(item),
                            subtitle=self._parent_subtitle(item, extra),
                            parentKey=key,
                            groupKey=group_key(item.group),
                            groupName=item.group or "",
                            systemName=item.system_name,
                            userName=item.second_name,
                            indent=1,
                            childCount=len(children),
                            **self._parent_fields(item, extra),
                        )
                    )
                    rows.extend(self._rows_before_actions(item, extra))
                    rows.extend(children)
                    rows.extend(self._rows_after_actions(item, extra))
        rows.extend(self._rows_at_end())
        self._rows = rows
        alive = {row["key"] for row in rows}
        self._selected = [key for key in self._selected if key in alive]
        self.endResetModel()
        self.revisionChanged.emit()
        self.groupsChanged.emit()
        self.selectionChanged.emit()

    def rowCount(self, parent: ta.ModelIndex = QtCore.QModelIndex()) -> int:
        return len(self._rows)

    def data(
        self, index: ta.ModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole
    ) -> object:
        if not index.isValid() or not (0 <= index.row() < len(self._rows)):
            return None
        name = self.roles.get(role)
        if name is None:
            return None
        key = bytes(name.data()).decode()
        return self._rows[index.row()].get(key)

    def roleNames(self) -> dict[int, QtCore.QByteArray]:
        return self.roles

    def _item_for(self, key: str) -> LayoutItem | None:
        parsed = parse_parent(key)
        if parsed is None:
            return None
        ident = self._identifier(parsed[0], parsed[1])
        if not self._layout.exists(ident):
            return None
        return self._layout[ident]

    # Slots.

    @QtCore.Slot(str)
    def setMode(self, mode: str) -> None:
        self._mode = mode or "Default"
        self._rebuild()

    @QtCore.Slot(str, int, result=bool)
    def deleteAction(self, parent_key: str, sequence_index: int) -> bool:
        """Remove one action sequence from the parent in the current mode."""
        spec = self._spec(parent_key)
        if spec is None:
            return False
        _profile, _item, real = spec
        index = int(sequence_index)
        if real is None or not 0 <= index < len(real.action_sequences):
            return False
        binding = real.action_sequences[index]

        def fn() -> list[dict]:
            before = self._snapshot(real)
            real.remove_item_binding(binding)
            _profile.library.release([binding.root_action])
            return [
                {
                    "op": "input",
                    "key": self._input_key(real),
                    "before": before,
                    "after": self._snapshot(real),
                }
            ]

        return self._apply(fn, f"Delete action from {_item.choice_label}")

    @QtCore.Slot(str)
    def addGroup(self, name: str) -> None:
        def fn() -> list[dict]:
            self._layout.ensure_group(name)
            return []

        self._apply(fn, f"New Group {name}")

    @QtCore.Slot(str, str)
    def renameGroup(self, old_name: str, new_name: str) -> None:
        def fn() -> list[dict]:
            self._layout.rename_group(old_name, new_name)
            return []

        try:
            self._apply(fn, f"Rename Group {old_name} to {new_name}")
        except GremlinError as exc:
            signal.showNotification.emit("Rename Group", str(exc))

    @QtCore.Slot(str)
    def removeGroup(self, name: str) -> None:
        def fn() -> list[dict]:
            self._layout.delete_group(name)
            return []

        self._apply(fn, f"Delete Group {name}")

    @QtCore.Slot(str, str)
    def setUserName(self, key: str, name: str) -> None:
        self.setRowLabel(key, name, False)

    @QtCore.Slot(str, result=bool)
    def hidesSystem(self, key: str) -> bool:
        item = self._item_for(key)
        if item is None:
            return False
        return bool(getattr(item, "hide_system", False) and item.second_name)

    @QtCore.Slot(str, str, bool)
    def setRowLabel(self, key: str, name: str, hide_system: bool) -> None:
        item = self._item_for(key)
        if item is None:
            return

        def fn() -> list[dict]:
            self._layout.set_user_label(item.identifier, name)
            current = self._item_for(key)
            if current is not None and hasattr(current, "hide_system"):
                hide = bool(hide_system) and bool(current.second_name)
                setattr(current, "hide_system", hide)  # not every store has it
            return []

        self._apply(fn, f"Rename {item.system_name}")

    @QtCore.Slot(str)
    def moveSelected(self, group: str) -> None:
        keys = [key for key in self._selected if key.startswith("parent:")]
        if not keys:
            return

        def fn() -> list[dict]:
            for key in keys:
                item = self._item_for(key)
                if item is not None:
                    self._layout.place(item.identifier, group)
            return []

        self._apply(fn, f"Move to {group or 'Ungrouped'}")

    @QtCore.Slot("QStringList")
    def deleteParents(self, keys: list) -> None:
        parents = [key for key in keys if str(key).startswith("parent:")]
        parents = [
            key
            for key in parents
            if (item := self._item_for(key)) is None or self._can_remove(item)
        ]
        if not parents:
            return

        def fn() -> list[dict]:
            links = []
            for key in parents:
                item = self._item_for(key)
                if item is None:
                    continue
                links.extend(self._delete_parent(item))
            return links

        first = self._item_for(parents[0])
        if len(parents) == 1 and first is not None:
            label = f"Delete {first.choice_label}"
        else:
            label = f"Delete {len(parents)} rows"
        self._apply(fn, label)

    @QtCore.Slot(str, str)
    def moveRow(self, source: str, target: str) -> None:
        if not source or source == target:
            return
        if source.startswith("group:") and target.startswith("group:"):
            name = source[len("group:") :]
            before = target[len("group:") :]
            if not name or name == "Ungrouped":
                return

            def fn() -> list[dict]:
                self._layout.move_group_before(name, before or None)
                return []

            self._apply(fn, f"Move Group {name}")
            return
        if not source.startswith("parent:"):
            return
        item = self._item_for(source)
        if item is None:
            return
        if target.startswith("group:"):
            group = target[len("group:") :]

            def fn_group() -> list[dict]:
                self._layout.place(item.identifier, group)
                return []

            self._apply(fn_group, f"Move {item.choice_label}")
            return
        other = self._item_for(target)
        if other is None:
            return

        def fn_before() -> list[dict]:
            self._layout.place(item.identifier, other.group, other.identifier)
            return []

        self._apply(fn_before, f"Move {item.choice_label}")

    def _next_in_group(self, item: LayoutItem) -> Hashable | None:
        seen = False
        group = item.group or ""
        for entry in self._layout.ordered():
            if entry.identifier == item.identifier:
                seen = True
                continue
            if seen and (entry.group or "") == group:
                return entry.identifier
        return None

    @QtCore.Slot(str, str, str)
    def moveParent(self, source: str, target: str, method: str) -> None:
        """Move one parent before, after, or into the drop target.

        Dropping on a group appends to that group. Dropping on a parent
        uses the same before/after correction as an action sequence: the
        source is removed first, then inserted relative to the target.
        """
        if not str(source).startswith("parent:") or source == target:
            return
        item = self._item_for(source)
        if item is None:
            return
        if str(target).startswith("group:"):
            group = str(target)[len("group:") :]

            def fn_into() -> list[dict]:
                self._layout.place(item.identifier, group)
                return []

            self._apply(fn_into, f"Move {item.choice_label}")
            return
        other = self._item_for(target)
        if other is None:
            return
        before = other.identifier if method != "after" else self._next_in_group(other)
        if before == item.identifier:
            return
        if (
            method == "after"
            and before is None
            and (item.group or "") == (other.group or "")
            and self._next_in_group(item) is None
        ):
            return

        def fn_at() -> list[dict]:
            if before is None:
                self._layout.place(item.identifier, other.group)
            else:
                self._layout.place(item.identifier, other.group, before)
            return []

        self._apply(fn_at, f"Move {item.choice_label}")

    @QtCore.Slot()
    def sortBySystem(self) -> None:
        def fn() -> list[dict]:
            self._layout.sort_within("system")
            return []

        self._apply(fn, self._sort_system_label())

    @QtCore.Slot()
    def sortByName(self) -> None:
        def fn() -> list[dict]:
            self._layout.sort_within("user")
            return []

        self._apply(fn, "Sort by Your Name")

    @QtCore.Slot()
    def sortGroupNames(self) -> None:
        def fn() -> list[dict]:
            self._layout.sort_groups()
            return []

        self._apply(fn, "Sort Group Names A to Z")

    @QtCore.Slot(str)
    def moveGroupUp(self, name: str) -> None:
        names = self._layout.group_names()
        if name not in names:
            return
        index = names.index(name)
        if index == 0:
            return
        before = names[index - 1]

        def fn() -> list[dict]:
            self._layout.move_group_before(name, before)
            return []

        self._apply(fn, f"Move Group {name} Up")

    @QtCore.Slot(str)
    def moveGroupDown(self, name: str) -> None:
        names = self._layout.group_names()
        if name not in names:
            return
        index = names.index(name)
        if index >= len(names) - 1:
            return
        before = names[index + 2] if index + 2 < len(names) else ""

        def fn() -> list[dict]:
            self._layout.move_group_before(name, before or None)
            return []

        self._apply(fn, f"Move Group {name} Down")

    @QtCore.Slot(str, str, bool, bool, bool)
    def setFilter(
        self,
        search: str,
        type_name: str,
        ungrouped: bool,
        no_writer: bool,
        no_actions: bool,
    ) -> None:
        self._search = (search or "").strip()
        self._type_filter = type_name or "all"
        self._ungrouped_only = bool(ungrouped)
        self._no_writer = bool(no_writer)
        self._no_actions = bool(no_actions)
        self._rebuild()

    @QtCore.Slot("QStringList")
    def setSelection(self, keys: list) -> None:
        self._selected = [str(key) for key in keys if str(key).startswith("parent:")]
        self.selectionChanged.emit()

    # The action pane.

    def _spec(self, key: str) -> tuple[Profile, LayoutItem, InputItem | None] | None:
        item = self._item_for(key)
        profile = self._profile()
        if item is None or profile is None:
            return None
        real = profile.get_input_item(
            self._device_guid(),
            item.type,
            item.id,
            self._mode,
            create_if_missing=False,
        )
        return profile, item, real

    def _clear_pane(self) -> None:
        model = self._pane_model
        self._pane_model = None
        self.paneModelChanged.emit()
        if model is not None:
            model.deleteLater()

    @QtCore.Slot(str, int, result=int)
    def beginPane(self, parent_key: str, sequence_index: int) -> int:
        return self._begin_pane(parent_key, int(sequence_index), False)

    @QtCore.Slot(str, result=int)
    def beginNewAction(self, parent_key: str) -> int:
        """Open the pane on a blank action. Nothing is written until OK."""
        return self._begin_pane(parent_key, -1, True)

    def _begin_pane(self, parent_key: str, seq: int, new: bool) -> int:
        self.endPane()
        spec = self._spec(parent_key)
        if spec is None:
            return 0
        profile, item, real = spec
        if seq >= 0 and (real is None or seq >= len(real.action_sequences)):
            return 0
        draft = profile.library.draft(
            real,
            None if seq < 0 else seq,
            key=(self._device_guid(), item.type, item.id, self._mode),
            blank=new,
        )
        shadow = draft.item
        from gremlin.ui.profile import InputItemModel

        self._pane_real = real
        self._pane_draft = draft
        self._pane_shadow = shadow
        self._pane_seq = seq
        self._pane_key = parent_key
        self._pane_whole = draft.whole
        self._pane_new = new
        self._pane_base = bindings_fingerprint(shadow.action_sequences)
        self._pane_model = InputItemModel(shadow, 0, self)
        self.paneModelChanged.emit()
        return len(shadow.action_sequences) if draft.whole else 0

    @QtCore.Slot(result=bool)
    def paneDirty(self) -> bool:
        shadow = self._pane_shadow
        if shadow is None:
            return False
        if not shadow.action_sequences:
            # Every action removed in the pane: OK takes them off the input.
            real = self._pane_real
            return self._pane_whole and bool(real and real.action_sequences)
        return bindings_fingerprint(shadow.action_sequences) != self._pane_base

    def _set_sequences(
        self, real: InputItem, change: Callable[[], object], label: str = ""
    ) -> int:
        """Runs change (it edits real's actions) as one Undo step; returns
        what change returned when it is an index."""
        result: list[object] = []

        def fn() -> list[dict]:
            before = self._snapshot(real)
            result.append(change())
            return [
                {
                    "op": "input",
                    "key": self._input_key(real),
                    "before": before,
                    "after": self._snapshot(real),
                }
            ]

        self._apply(fn, label)
        value = result[0] if result else 0
        return value if isinstance(value, int) else 0

    @QtCore.Slot(result=int)
    def commitPane(self) -> int:
        draft = self._pane_draft
        if draft is None or not self.paneDirty():
            return self._pane_seq
        if self._refused():
            return -1
        shadow = draft.item
        real = self._pane_real
        if real is None:
            spec = self._spec(self._pane_key)
            if spec is None:
                return -1
            profile, item, _real = spec
            # The pane's own mode (the toolbar may show another by now).
            real = profile.get_input_item(
                self._device_guid(),
                item.type,
                item.id,
                str(shadow.mode or self._mode),
                create_if_missing=True,
            )
            self._pane_real = real
        if real is None:
            return -1
        owner = self._item_for(self._pane_key)
        item_label = owner.choice_label if owner is not None else ""
        library = real.library
        if self._pane_new:
            where: int | None = -1
        elif self._pane_whole or self._pane_seq < 0:
            where = None
        else:
            where = self._pane_seq
        try:
            index = self._set_sequences(
                real,
                lambda: library.commit(draft, real, where),
                f"Edit actions of {item_label}" if item_label else "",
            )
        except DraftOutdated:
            signal.showNotification.emit(
                "Action Editor",
                "This input was changed while its action editor was open, so "
                "OK didn't write over that change. Close the editor and open "
                "it again.",
            )
            return -1
        if where is None:
            self._pane_seq = -1
            self._pane_whole = True
            only = None
            index = 0
        else:
            self._pane_new = False
            self._pane_seq = index
            self._pane_whole = False
            only = index
        self._pane_draft = None
        self._show_saved(real, only)
        self._rebuild()
        signal.actionsChanged.emit()
        return index

    def _show_saved(self, real: InputItem, only_index: int | None = None) -> None:
        """Keep the pane on a fresh copy of what OK just wrote.

        One open action stays that action. The whole control reloads every sequence.
        """
        profile = self._profile()
        if profile is None or real is None:
            return
        draft = real.library.draft(real, only_index)
        from gremlin.ui.profile import InputItemModel

        old = self._pane_model
        self._pane_draft = draft
        self._pane_shadow = draft.item
        self._pane_real = real
        self._pane_base = bindings_fingerprint(draft.item.action_sequences)
        self._pane_model = InputItemModel(draft.item, 0, self)
        self.paneModelChanged.emit()
        if old is not None:
            old.deleteLater()

    def _drop_draft(self) -> None:
        draft, self._pane_draft = self._pane_draft, None
        self._pane_shadow = None
        if draft is not None:
            draft.library.discard(draft)

    @QtCore.Slot()
    def discardPane(self) -> None:
        self._drop_draft()
        self._pane_base = ""

    @QtCore.Slot()
    def endPane(self) -> None:
        self._drop_draft()
        self._pane_real = None
        self._pane_seq = -1
        self._pane_key = ""
        self._pane_base = ""
        self._pane_whole = False
        self._pane_new = False
        self._clear_pane()

    @QtCore.Property(QtCore.QObject, notify=paneModelChanged)
    def paneModel(self) -> QtCore.QObject | None:
        return self._pane_model

    @QtCore.Property(bool, notify=revisionChanged)
    def canUndo(self) -> bool:
        return bool(self._undo)

    @QtCore.Property(bool, notify=revisionChanged)
    def canRedo(self) -> bool:
        return bool(self._redo)

    # The rows listed (buttons, axes, hats): the search box's "N found".
    @QtCore.Property(int, notify=revisionChanged)
    def parentCount(self) -> int:
        return sum(1 for row in self._rows if row["rowKind"] == "parent")

    # 01 S143: the Undo bar's text and tips, from each step's label.
    def _top_label(self, steps: list[dict]) -> str:
        return str(steps[-1].get("label") or "") if steps else ""

    @QtCore.Property(str, notify=revisionChanged)
    def lastChange(self) -> str:
        label = self._top_label(self._undo)
        return f"Last change: {label}" if label else ""

    @QtCore.Property(str, notify=revisionChanged)
    def undone(self) -> str:
        label = self._top_label(self._redo)
        return f"Undone: {label}" if label and self._just_undid else ""

    @QtCore.Property(str, notify=revisionChanged)
    def undoTip(self) -> str:
        label = self._top_label(self._undo)
        return f"Undo {label}" if label else ""

    @QtCore.Property(str, notify=revisionChanged)
    def redoTip(self) -> str:
        label = self._top_label(self._redo)
        return f"Redo {label}" if label else ""

    @QtCore.Property(int, notify=selectionChanged)
    def selectionCount(self) -> int:
        return len(self._selected)

    @QtCore.Property(str, notify=selectionChanged)
    def selectionLabel(self) -> str:
        if not self._selected:
            return "No rows selected"
        if len(self._selected) == 1:
            item = self._item_for(self._selected[0])
            return self._selection_name(item) if item is not None else "1 row selected"
        return f"{len(self._selected)} rows selected"

    @QtCore.Slot(int, result=str)
    def keyAt(self, row: int) -> str:
        if 0 <= row < len(self._rows):
            return str(self._rows[row]["key"])
        return ""

    @QtCore.Property("QVariantList", notify=groupsChanged)
    def groups(self) -> list:
        layout = self._layout
        rows = [{"name": "", "title": "Ungrouped", "summary": ""}]
        counts = {name: [0, 0, 0] for name in [""] + layout.group_names()}
        for item in layout.ordered():
            bucket = counts.setdefault(item.group or "", [0, 0, 0])
            if item.type == InputType.JoystickButton:
                bucket[0] += 1
            elif item.type == InputType.JoystickAxis:
                bucket[1] += 1
            else:
                bucket[2] += 1
        rows[0]["summary"] = count_text(*counts.get("", [0, 0, 0]))
        for name in layout.group_names():
            rows.append(
                {
                    "name": name,
                    "title": name,
                    "summary": count_text(*counts.get(name, [0, 0, 0])),
                }
            )
        return rows
