# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
"""Logical device layout: groups, names, hardware links, and the action pane."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from typing import Any
from xml.etree import ElementTree

from PySide6 import QtCore

import gremlin.ui.type_aliases as ta
from gremlin import device_initialization, error, keyboard, shared_state
from gremlin.base_classes import AbstractActionData
from gremlin.error import GremlinError
from gremlin.logical_device import LogicalDevice
from gremlin.modules import store
from gremlin.modules.registry import module_direction
from gremlin.ui.module_model import (
    KEYBOARD_GUID,
    LOGICAL_GUID,
    OSC_GUID,
)
from gremlin.profile import (
    Draft,
    DraftOutdated,
    InputItem,
    InputItemBinding,
    VirtualAxisButton,
    VirtualHatButton,
    bindings_fingerprint,
)
from gremlin.signal import signal
from gremlin.types import AxisMode, DataInsertionMode, InputType
from gremlin.modules.ids import guid_key
from gremlin.modules.claim import claim_friendly, claim_ids, key_id, read_claim
from gremlin.ui.binding_catalog import editing_locked, sequences_for_item

QML_IMPORT_NAME = "Gremlin.Device"
QML_IMPORT_MAJOR_VERSION = 1

_TYPE_ORDER = (
    InputType.JoystickButton,
    InputType.JoystickAxis,
    InputType.JoystickHat,
)
_KIND_WORD = {
    InputType.JoystickButton: "button",
    InputType.JoystickAxis: "axis",
    InputType.JoystickHat: "hat",
}


def _assign_input_modules() -> list[dict]:
    """Saved source input modules. Logical Device is never a writer source."""
    rows: list[dict] = []
    seen: set[str] = set()
    logical = guid_key(LOGICAL_GUID)

    def add(name: str, guid: str, bus: str) -> None:
        key = guid_key(guid) or name.lower()
        if key in seen or key == logical:
            return
        # By name and id (twin sticks each have their own file, 03 S77).
        if not store.exists(name, guid):
            return
        doc = store.read(name, guid)
        if module_direction(doc, name=name) == "dest" and bus != "vjoy-input":
            return
        seen.add(key)
        rows.append(
            {
                "name": name,
                "guid": guid,
                "bus": bus,
                "claim": read_claim(doc),
            }
        )

    for dev in device_initialization.physical_devices():
        add(dev.name, str(dev.device_guid.uuid), "hid")
    add("Keyboard", KEYBOARD_GUID, "keyboard")
    add("OSC", OSC_GUID, "osc")
    vjoy_as_input = {}
    if shared_state.current_profile:
        vjoy_as_input = dict(shared_state.current_profile.settings.vjoy_as_input or {})
    for vdev in device_initialization.vjoy_devices():
        if not vjoy_as_input.get(vdev.vjoy_id, False):
            continue
        add(f"vJoy {vdev.vjoy_id}", str(vdev.device_guid.uuid), "vjoy-input")
    rows.sort(key=lambda row: row["name"].lower())
    return rows


def _kind_word(kind: InputType) -> str:
    return _KIND_WORD.get(kind, "button")


def _parse_parent(key: str) -> tuple[InputType, int] | None:
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


def _parent_key(kind: InputType, input_id: int) -> str:
    return f"parent:{_kind_word(kind)}:{int(input_id)}"


def _group_key(name: str) -> str:
    return "group:" + (name or "")


def _count_text(buttons: int, axes: int, hats: int) -> str:
    parts = []
    if buttons:
        parts.append(f"{buttons} button" if buttons == 1 else f"{buttons} buttons")
    if axes:
        parts.append(f"{axes} axis" if axes == 1 else f"{axes} axes")
    if hats:
        parts.append(f"{hats} hat" if hats == 1 else f"{hats} hats")
    return " · ".join(parts) if parts else "Empty"


def _matches(item, search: str, type_filter: str) -> bool:
    if type_filter not in ("", "all") and _kind_word(item.type) != type_filter:
        return False
    if not search:
        return True
    hay = " ".join(
        (item.system_name, item.second_name, item.group or "", item.label)
    ).lower()
    return search.lower() in hay


@ta.QmlElement
class LogicalLayoutModel(QtCore.QAbstractListModel):
    """Rows for the logical page: group headers, parents, writers, and actions."""

    roles = {
        QtCore.Qt.ItemDataRole.UserRole + 1: QtCore.QByteArray(b"rowKind"),
        QtCore.Qt.ItemDataRole.UserRole + 2: QtCore.QByteArray(b"key"),
        QtCore.Qt.ItemDataRole.UserRole + 3: QtCore.QByteArray(b"title"),
        QtCore.Qt.ItemDataRole.UserRole + 4: QtCore.QByteArray(b"subtitle"),
        QtCore.Qt.ItemDataRole.UserRole + 5: QtCore.QByteArray(b"parentKey"),
        QtCore.Qt.ItemDataRole.UserRole + 6: QtCore.QByteArray(b"groupKey"),
        QtCore.Qt.ItemDataRole.UserRole + 7: QtCore.QByteArray(b"groupName"),
        QtCore.Qt.ItemDataRole.UserRole + 8: QtCore.QByteArray(b"systemName"),
        QtCore.Qt.ItemDataRole.UserRole + 9: QtCore.QByteArray(b"userName"),
        QtCore.Qt.ItemDataRole.UserRole + 10: QtCore.QByteArray(b"writerId"),
        QtCore.Qt.ItemDataRole.UserRole + 11: QtCore.QByteArray(b"axisMode"),
        QtCore.Qt.ItemDataRole.UserRole + 12: QtCore.QByteArray(b"axisScale"),
        QtCore.Qt.ItemDataRole.UserRole + 13: QtCore.QByteArray(b"inverted"),
        QtCore.Qt.ItemDataRole.UserRole + 14: QtCore.QByteArray(b"sequenceIndex"),
        QtCore.Qt.ItemDataRole.UserRole + 15: QtCore.QByteArray(b"indent"),
        QtCore.Qt.ItemDataRole.UserRole + 16: QtCore.QByteArray(b"canInvert"),
        QtCore.Qt.ItemDataRole.UserRole + 17: QtCore.QByteArray(b"childCount"),
        QtCore.Qt.ItemDataRole.UserRole + 18: QtCore.QByteArray(b"extraWriters"),
    }

    revisionChanged = QtCore.Signal()
    groupsChanged = QtCore.Signal()
    selectionChanged = QtCore.Signal()
    paneModelChanged = QtCore.Signal()
    # The pane's mode was deleted: the page closes it.
    paneLost = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._logical = LogicalDevice()
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
        signal.logicalDeviceModified.connect(self._on_external)
        signal.profileChanged.connect(self._on_profile)
        signal.modeRenamed.connect(self._on_mode_renamed)
        signal.modeDeleted.connect(self._on_mode_deleted)
        self._rebuild()

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
        # Another profile: the steps belong to the old one.
        self._undo.clear()
        self._redo.clear()
        self._on_external()

    def _on_external(self) -> None:
        if self._writing:
            return
        self._rebuild()

    def _profile(self):
        return shared_state.current_profile

    def _changed(self) -> None:
        self._writing = True
        try:
            signal.logicalDeviceModified.emit()
        finally:
            self._writing = False
        self._rebuild()

    def _refused(self) -> bool:
        """The edit lock (binding_catalog.editing_locked): nothing changes
        while the profile runs (06 S82, RB14)."""
        if not editing_locked():
            return False
        logging.getLogger("system").info("Edit refused: the profile is running")
        return True

    def _apply(self, fn) -> bool:
        """Runs fn (an edit) as one Undo step. False: refused (running)."""
        if self._refused():
            return False
        before = self._logical.memento()
        links = fn() or []
        after = self._logical.memento()
        if before == after and not links:
            # Nothing changed (the same name typed again): no step.
            self._changed()
            return True
        self._undo.append({"before": before, "after": after, "links": links})
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

    def _play(self, links, reverse: bool) -> None:
        entries = list(reversed(links)) if reverse else list(links)
        profile = self._profile()
        for entry in entries:
            op = entry.get("op")
            if op == "input":
                if profile is not None:
                    side = entry["before"] if reverse else entry["after"]
                    profile.library.restore(entry["key"], side)
                continue
            if reverse and op == "add":
                self._remove_link(entry)
            elif reverse and op == "remove":
                self._add_link(entry)
            elif not reverse and op == "add":
                self._add_link(entry)
            elif not reverse and op == "remove":
                self._remove_link(entry)

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
            self._logical.restore(entry["before"] if reverse else entry["after"])
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
        else:
            self._redo.append(entry)
        self._changed()

    def _input_items(self):
        profile = self._profile()
        if profile is None:
            return []
        rows = []
        for items in profile.inputs.values():
            rows.extend(items)
        return rows

    def _links_for(self, kind: InputType, input_id: int) -> list[tuple]:
        found = []
        for item in self._input_items():
            if item.device_id == self._logical.device_guid:
                continue
            for binding in item.action_sequences or []:
                root = binding.root_action
                if root is None:
                    continue
                kids, _selectors = root.get_actions()
                for child in kids:
                    if getattr(child, "tag", "") != "map-to-logical-device":
                        continue
                    if child.logical_input_type != kind or int(child.logical_input_id) != int(input_id):
                        continue
                    found.append((item, binding, child))
        return found

    def _link_record(
        self, item, action, op: str, binding: InputItemBinding | None = None  # noqa: ANN001
    ) -> dict:
        record = {
            "op": op,
            "guid": str(item.device_id),
            "src_type": item.input_type,
            "src_id": item.input_id,
            "mode": item.mode,
            "logical_type": action.logical_input_type,
            "logical_id": int(action.logical_input_id),
            "axis_mode": getattr(action, "axis_mode", AxisMode.Absolute),
            "scale": float(getattr(action, "axis_scaling", 1.0) or 1.0),
            "invert": bool(getattr(action, "button_inverted", False)),
        }
        # Where the link sits: Undo puts it back into that binding, with its
        # behaviour (a button-behaviour link on an axis stays one).
        if (
            binding is not None
            and binding.root_action is not None
            and binding in item.action_sequences
        ):
            kids = binding.root_action.get_actions()[0]
            record["binding_index"] = item.action_sequences.index(binding)
            record["behavior"] = binding.behavior
            record["alone"] = len(kids) == 1
            record["child_index"] = next(
                (i for i, kid in enumerate(kids) if kid is action), len(kids)
            )
            if binding.virtual_button is not None:
                record["virtual_button"] = ElementTree.tostring(
                    binding.virtual_button.to_xml(), encoding="unicode"
                )
            node = action.to_xml(True)
            if node is not None:
                record["action"] = ElementTree.tostring(node, encoding="unicode")
        return record

    @staticmethod
    def _virtual_button(
        item: InputItem, behavior: InputType, text: str | None
    ) -> VirtualAxisButton | VirtualHatButton | None:
        """The binding's virtual button kept in a link record, or None."""
        if text is None or behavior != InputType.JoystickButton:
            return None
        if item.input_type == InputType.JoystickAxis:
            button = VirtualAxisButton()
        elif item.input_type == InputType.JoystickHat:
            button = VirtualHatButton()
        else:
            return None
        try:
            button.from_xml(ElementTree.fromstring(text))
        except (ElementTree.ParseError, error.GremlinError, ValueError):
            return None
        return button

    def _add_link(self, record: dict):
        profile = self._profile()
        if profile is None:
            return None
        try:
            guid = uuid.UUID(str(record["guid"]))
        except ValueError:
            return None
        src_type = record["src_type"]
        src_id = record["src_id"]
        if isinstance(src_id, list):
            src_id = tuple(src_id)
        item = profile.get_input_item(
            guid, src_type, src_id, str(record["mode"]), create_if_missing=True
        )
        if item is None:
            return None
        logical_type = record["logical_type"]
        logical_id = int(record["logical_id"])
        for _item, _binding, action in self._links_for(logical_type, logical_id):
            if (
                _item.device_id == item.device_id
                and _item.input_type == item.input_type
                and _item.input_id == item.input_id
                and _item.mode == item.mode
            ):
                return None
        # The binding it was taken from: still there unless the link was
        # its only action; else a new one with the old behaviour.
        index = record.get("binding_index")
        behavior = record.get("behavior") or src_type
        virtual = self._virtual_button(item, behavior, record.get("virtual_button"))
        if behavior != src_type and virtual is None:
            behavior = src_type
        binding = None
        if (
            index is not None
            and not record.get("alone")
            and 0 <= index < len(item.action_sequences)
            and item.action_sequences[index].behavior == behavior
        ):
            binding = item.action_sequences[index]
        # In the library of the input it goes on (GL-102).
        action: Any = item.library.create(
            "Map to Logical Device", behavior, item=item
        )
        if action is None:
            return None
        action.logical_input_type = logical_type
        action.logical_input_id = logical_id
        if logical_type == InputType.JoystickAxis:
            action.axis_mode = record.get("axis_mode", AxisMode.Absolute)
            action.axis_scaling = float(record.get("scale", 1.0))
        if logical_type == InputType.JoystickButton:
            action.button_inverted = bool(record.get("invert", False))
        if record.get("action"):
            # Everything the link had (its label too), under the new id.
            try:
                node = ElementTree.fromstring(record["action"])
                node.set("id", str(action.id))
                action.from_xml(node, profile.library)
            except (ElementTree.ParseError, error.GremlinError, ValueError):
                pass
        if binding is None:
            binding = item.add_item_binding()
            binding.behavior = behavior
            binding.virtual_button = virtual
            if index is not None:
                item.action_sequences.remove(binding)
                item.action_sequences.insert(
                    min(max(int(index), 0), len(item.action_sequences)), binding
                )
            binding.root_action.insert_action(action, "children")
        elif binding.root_action is not None:
            kids = binding.root_action.get_actions()[0]
            position = min(max(int(record.get("child_index", len(kids))), 0), len(kids))
            binding.root_action.insert_action(
                action, "children", DataInsertionMode.Prepend, position
            )
        return action

    def _remove_link(self, record: dict) -> bool:
        profile = self._profile()
        if profile is None:
            return False
        try:
            guid = uuid.UUID(str(record["guid"]))
        except ValueError:
            return False
        src_id = record["src_id"]
        if isinstance(src_id, list):
            src_id = tuple(src_id)
        item = profile.get_input_item(
            guid, record["src_type"], src_id, str(record["mode"]), create_if_missing=False
        )
        if item is None:
            return False
        logical_type = record["logical_type"]
        logical_id = int(record["logical_id"])
        for binding in list(item.action_sequences or []):
            root = binding.root_action
            if root is None:
                continue
            kids, selectors = root.get_actions()
            for index in range(len(kids) - 1, -1, -1):
                child = kids[index]
                if getattr(child, "tag", "") != "map-to-logical-device":
                    continue
                if child.logical_input_type != logical_type or int(child.logical_input_id) != logical_id:
                    continue
                root.remove_action(index, selectors[index])
                profile.library.release([child])
                if not root.get_actions()[0]:
                    item.remove_item_binding(binding)
                    profile.library.release([root])
                return True
        return False

    def _detach_links(self, kind: InputType, input_id: int) -> list[dict]:
        records = []
        for item, binding, action in list(self._links_for(kind, input_id)):
            records.append(self._link_record(item, action, "remove", binding))
            root = binding.root_action
            kids, selectors = root.get_actions()
            for index, child in enumerate(list(kids)):
                if child is action:
                    root.remove_action(index, selectors[index])
                    profile = self._profile()
                    if profile is not None:
                        profile.library.release([child])
                    break
            if root is not None and not root.get_actions()[0]:
                item.remove_item_binding(binding)
                profile = self._profile()
                if profile is not None:
                    profile.library.release([root])
        return records

    def _take_own_items(self, kind: InputType, input_id: int) -> list[dict]:
        profile = self._profile()
        if profile is None:
            return []
        guid = self._logical.device_guid
        items = list(profile.inputs.get(guid, []))
        kept = []
        taken = []
        doomed = []
        for item in items:
            if item.input_type == kind and item.input_id == input_id:
                # Undo puts its copy back; Redo takes it out again (it used
                # to put it back both ways, and a new row inherited it).
                taken.append({
                    "op": "input", "key": self._input_key(item),
                    "before": self._snapshot(item), "after": None,
                })
                doomed.append(item)
        if doomed:
            profile.drop_inputs(guid, doomed)
        return taken

    def _device_name(self, guid) -> str:
        if guid == keyboard_guid():
            return "Keyboard"
        try:
            device = device_initialization.device_for_uuid(guid)
        except Exception:
            return "Device"
        return device.name or "Device"

    def _control_name(self, item) -> str:
        if item.input_type == InputType.Keyboard and isinstance(item.input_id, tuple):
            try:
                return keyboard.key_from_code(item.input_id[0], bool(item.input_id[1])).name
            except Exception:
                return "Key"
        word = _kind_word(item.input_type).capitalize()
        return f"{word} {item.input_id}"

    def _writer_rows(self, item) -> list[dict]:
        rows = []
        key = _parent_key(item.type, item.id)
        group = _group_key(item.group)
        for source, _binding, action in self._links_for(item.type, item.id):
            mode = source.mode or ""
            mode_bit = "" if mode == self._mode else f" · {mode}"
            title = f"Written by {self._device_name(source.device_id)} · {self._control_name(source)}{mode_bit}"
            rows.append(
                {
                    "rowKind": "writer",
                    "key": f"writer:{action.id}",
                    "title": title,
                    "subtitle": "",
                    "parentKey": key,
                    "groupKey": group,
                    "groupName": item.group or "",
                    "systemName": item.system_name,
                    "userName": "",
                    "writerId": str(action.id),
                    "axisMode": AxisMode.to_string(getattr(action, "axis_mode", AxisMode.Absolute))
                    if item.type == InputType.JoystickAxis
                    else "",
                    "axisScale": float(getattr(action, "axis_scaling", 1.0) or 1.0),
                    "inverted": bool(getattr(action, "button_inverted", False)),
                    "sequenceIndex": -1,
                    "indent": 1,
                    "canInvert": item.type == InputType.JoystickButton,
                    "childCount": 0,
                    "extraWriters": 0,
                }
            )
        return rows

    def _child_rows(self, item) -> list[dict]:
        profile = self._profile()
        rows = []
        if profile is None:
            return rows
        real = profile.get_input_item(
            self._logical.device_guid,
            item.type,
            item.id,
            self._mode,
            create_if_missing=False,
        )
        key = _parent_key(item.type, item.id)
        group = _group_key(item.group)
        for index, label, dest in sequences_for_item(real):
            rows.append(
                {
                    "rowKind": "child",
                    "key": f"child:{_kind_word(item.type)}:{item.id}:{index}",
                    "title": label or "Action",
                    "subtitle": dest or "",
                    "parentKey": key,
                    "groupKey": group,
                    "groupName": item.group or "",
                    "systemName": item.system_name,
                    "userName": "",
                    "writerId": "",
                    "axisMode": "",
                    "axisScale": 1.0,
                    "inverted": False,
                    "sequenceIndex": index,
                    "indent": 1,
                    "canInvert": False,
                    "childCount": 0,
                    "extraWriters": 0,
                }
            )
        return rows

    def _visible_parent(self, item, writer_count: int, action_count: int) -> bool:
        if self._ungrouped_only and (item.group or ""):
            return False
        if self._no_writer and writer_count:
            return False
        if self._no_actions and action_count:
            return False
        return _matches(item, self._search, self._type_filter)

    def _rebuild(self) -> None:
        self.beginResetModel()
        rows: list[dict] = []
        folders = [""] + self._logical.group_names()
        filtering = bool(
            self._search or self._type_filter not in ("", "all") or self._ungrouped_only or self._no_writer or self._no_actions
        )
        for folder in folders:
            members = [item for item in self._logical.ordered() if (item.group or "") == folder]
            visible = []
            cached = []
            for item in members:
                writers = self._writer_rows(item)
                children = self._child_rows(item)
                if self._visible_parent(item, len(writers), len(children)):
                    visible.append(item)
                    cached.append((item, writers, children))
            if folder == "" and filtering and not visible:
                continue
            if folder and filtering and not visible:
                continue
            buttons = sum(1 for item in visible if item.type == InputType.JoystickButton)
            axes = sum(1 for item in visible if item.type == InputType.JoystickAxis)
            hats = sum(1 for item in visible if item.type == InputType.JoystickHat)
            # Counts on the header are the parents in the group, not the filtered slice,
            # unless a filter is hiding rows. Then the header counts what is still shown.
            if not filtering:
                buttons = sum(1 for item in members if item.type == InputType.JoystickButton)
                axes = sum(1 for item in members if item.type == InputType.JoystickAxis)
                hats = sum(1 for item in members if item.type == InputType.JoystickHat)
            rows.append(
                {
                    "rowKind": "group",
                    "key": _group_key(folder),
                    "title": folder or "Ungrouped",
                    "subtitle": _count_text(buttons, axes, hats),
                    "parentKey": "",
                    "groupKey": _group_key(folder),
                    "groupName": folder,
                    "systemName": "",
                    "userName": "",
                    "writerId": "",
                    "axisMode": "",
                    "axisScale": 1.0,
                    "inverted": False,
                    "sequenceIndex": -1,
                    "indent": 0,
                    "canInvert": False,
                    "childCount": len(visible),
                    "extraWriters": 0,
                }
            )
            shown = cached if filtering else [
                (item, self._writer_rows(item), self._child_rows(item)) for item in members
            ]
            if filtering:
                shown = cached
            else:
                shown = [(item, self._writer_rows(item), self._child_rows(item)) for item in members]
            buckets = {kind: [] for kind in _TYPE_ORDER}
            for entry in shown:
                buckets[entry[0].type].append(entry)
            for kind in _TYPE_ORDER:
                for item, writers, children in buckets[kind]:
                    lead = writers[0] if writers else None
                    rows.append(
                        {
                            "rowKind": "parent",
                            "key": _parent_key(item.type, item.id),
                            "title": item.row_title,
                            "subtitle": lead["title"] if lead else "",
                            "parentKey": _parent_key(item.type, item.id),
                            "groupKey": _group_key(item.group),
                            "groupName": item.group or "",
                            "systemName": item.system_name,
                            "userName": item.second_name,
                            "writerId": lead["writerId"] if lead else "",
                            "axisMode": lead["axisMode"] if lead else "",
                            "axisScale": lead["axisScale"] if lead else 1.0,
                            "inverted": lead["inverted"] if lead else False,
                            "sequenceIndex": -1,
                            "indent": 1,
                            "canInvert": bool(lead) and item.type == InputType.JoystickButton,
                            "childCount": len(children),
                            "extraWriters": max(0, len(writers) - 1),
                        }
                    )
                    rows.extend(writers[1:])
                    rows.extend(children)
        self._rows = rows
        alive = {row["key"] for row in rows}
        self._selected = [key for key in self._selected if key in alive]
        self.endResetModel()
        self.revisionChanged.emit()
        self.groupsChanged.emit()
        self.selectionChanged.emit()

    def rowCount(self, parent: ta.ModelIndex = QtCore.QModelIndex()) -> int:
        return len(self._rows)

    def data(self, index: ta.ModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._rows)):
            return None
        key = bytes(self.roles.get(role, b"")).decode()
        if not key:
            return None
        return self._rows[index.row()].get(key)

    def roleNames(self) -> dict[int, QtCore.QByteArray]:
        return self.roles

    def _item_for(self, key: str):
        parsed = _parse_parent(key)
        if parsed is None:
            return None
        ident = LogicalDevice.Input.Identifier(parsed[0], parsed[1])
        if not self._logical.exists(ident):
            return None
        return self._logical[ident]

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

        def fn():
            before = self._snapshot(real)
            real.remove_item_binding(binding)
            _profile.library.release([binding.root_action])
            return [{
                "op": "input", "key": self._input_key(real),
                "before": before, "after": self._snapshot(real),
            }]

        return self._apply(fn)

    @QtCore.Slot(str, int, str, str)
    def addMany(self, type_name: str, count: int, group: str, user_name: str) -> None:
        kind = InputType.to_enum(type_name)

        def fn():
            self._logical.create_many(kind, int(count), group, user_name)
            return []

        self._apply(fn)

    @QtCore.Slot(str)
    def addGroup(self, name: str) -> None:
        def fn():
            self._logical.ensure_group(name)
            return []

        self._apply(fn)

    @QtCore.Slot(str, str)
    def renameGroup(self, old_name: str, new_name: str) -> None:
        def fn():
            self._logical.rename_group(old_name, new_name)
            return []

        try:
            self._apply(fn)
        except GremlinError as exc:
            signal.showNotification.emit("Rename Group", str(exc))

    @QtCore.Slot(str)
    def removeGroup(self, name: str) -> None:
        def fn():
            self._logical.delete_group(name)
            return []

        self._apply(fn)

    @QtCore.Slot(str, str)
    def setUserName(self, key: str, name: str) -> None:
        self.setRowLabel(key, name, False)

    @QtCore.Slot(str, result=bool)
    def hidesSystem(self, key: str) -> bool:
        item = self._item_for(key)
        return bool(item is not None and item.hide_system and item.second_name)

    @QtCore.Slot(str, str, bool)
    def setRowLabel(self, key: str, name: str, hide_system: bool) -> None:
        item = self._item_for(key)
        if item is None:
            return

        def fn():
            self._logical.set_user_label(item.identifier, name)
            current = self._item_for(key)
            if current is not None:
                current.hide_system = bool(hide_system) and bool(current.second_name)
            return []

        self._apply(fn)

    @QtCore.Slot(str)
    def moveSelected(self, group: str) -> None:
        keys = [key for key in self._selected if key.startswith("parent:")]
        if not keys:
            return

        def fn():
            for key in keys:
                item = self._item_for(key)
                if item is not None:
                    self._logical.place(item.identifier, group)
            return []

        self._apply(fn)

    @QtCore.Slot("QStringList")
    def deleteParents(self, keys: list) -> None:
        parents = [key for key in keys if str(key).startswith("parent:")]
        if not parents:
            return

        def fn():
            links = []
            for key in parents:
                item = self._item_for(key)
                if item is None:
                    continue
                links.extend(self._detach_links(item.type, item.id))
                links.extend(self._take_own_items(item.type, item.id))
                self._logical.delete(item.identifier)
            return links

        self._apply(fn)

    @QtCore.Slot(str, str)
    def moveRow(self, source: str, target: str) -> None:
        if not source or source == target:
            return
        if source.startswith("group:") and target.startswith("group:"):
            name = source[len("group:") :]
            before = target[len("group:") :]
            if not name or name == "Ungrouped":
                return

            def fn():
                self._logical.move_group_before(name, before or None)
                return []

            self._apply(fn)
            return
        if not source.startswith("parent:"):
            return
        item = self._item_for(source)
        if item is None:
            return
        if target.startswith("group:"):
            group = target[len("group:") :]

            def fn_group():
                self._logical.place(item.identifier, group)
                return []

            self._apply(fn_group)
            return
        other = self._item_for(target)
        if other is None:
            return

        def fn_before():
            self._logical.place(item.identifier, other.group, other.identifier)
            return []

        self._apply(fn_before)

    def _next_in_group(self, item):
        seen = False
        group = item.group or ""
        for entry in self._logical.ordered():
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

            def fn_into():
                self._logical.place(item.identifier, group)
                return []

            self._apply(fn_into)
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

        def fn_at():
            if before is None:
                self._logical.place(item.identifier, other.group)
            else:
                self._logical.place(item.identifier, other.group, before)
            return []

        self._apply(fn_at)

    @QtCore.Slot()
    def sortBySystem(self) -> None:
        def fn():
            self._logical.sort_within("system")
            return []

        self._apply(fn)

    @QtCore.Slot()
    def sortByName(self) -> None:
        def fn():
            self._logical.sort_within("user")
            return []

        self._apply(fn)

    @QtCore.Slot()
    def sortGroupNames(self) -> None:
        def fn():
            self._logical.sort_groups()
            return []

        self._apply(fn)

    @QtCore.Slot(str)
    def moveGroupUp(self, name: str) -> None:
        names = self._logical.group_names()
        if name not in names:
            return
        index = names.index(name)
        if index == 0:
            return
        before = names[index - 1]

        def fn():
            self._logical.move_group_before(name, before)
            return []

        self._apply(fn)

    @QtCore.Slot(str)
    def moveGroupDown(self, name: str) -> None:
        names = self._logical.group_names()
        if name not in names:
            return
        index = names.index(name)
        if index >= len(names) - 1:
            return
        before = names[index + 2] if index + 2 < len(names) else ""

        def fn():
            self._logical.move_group_before(name, before or None)
            return []

        self._apply(fn)

    @QtCore.Slot(str, str, bool, bool, bool)
    def setFilter(self, search: str, type_name: str, ungrouped: bool, no_writer: bool, no_actions: bool) -> None:
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

    def _action_by_id(self, action_id: str) -> AbstractActionData | None:
        profile = self._profile()
        if profile is None or not action_id:
            return None
        try:
            return profile.library.get_action(uuid.UUID(action_id))
        except Exception:
            return None

    @QtCore.Slot(str, str)
    def setAxisMode(self, writer_id: str, mode: str) -> None:
        action = self._action_by_id(writer_id)
        if action is None or self._refused():
            return
        try:
            action.axis_mode = AxisMode.to_enum(mode)
        except GremlinError:
            return
        self._rebuild()

    @QtCore.Slot(str, float)
    def setAxisScale(self, writer_id: str, scale: float) -> None:
        action = self._action_by_id(writer_id)
        if action is None or self._refused():
            return
        action.axis_scaling = float(scale)
        self._rebuild()

    @QtCore.Slot(str, bool)
    def setInverted(self, writer_id: str, inverted: bool) -> None:
        action = self._action_by_id(writer_id)
        if action is None or self._refused():
            return
        action.button_inverted = bool(inverted)
        self._rebuild()

    def _control_key(self, guid: str, kind: str, input_id: int, extended: int) -> str:
        return f"{guid}|{kind}|{int(input_id)}|{int(extended)}"

    def _parse_control(self, key: str) -> tuple[str, InputType, int | tuple] | None:
        parts = str(key or "").split("|")
        if len(parts) != 4:
            return None
        guid, kind, raw_id, raw_ext = parts
        try:
            if kind == "key":
                return guid, InputType.Keyboard, (int(raw_id), bool(int(raw_ext)))
            return guid, InputType.to_enum(kind), int(raw_id)
        except (GremlinError, ValueError):
            return None

    def _linked_now(self, logical_kind: InputType, logical_id: int, guid, src_type, src_id) -> bool:
        for item, _binding, _action in self._links_for(logical_kind, logical_id):
            if (
                str(item.device_id) == str(guid)
                and item.input_type == src_type
                and item.input_id == src_id
                and item.mode == self._mode
            ):
                return True
        return False

    @QtCore.Slot(str, str, result="QVariantList")
    def hardware(self, parent_key: str, search: str) -> list:
        parsed = _parse_parent(parent_key)
        if parsed is None:
            return []
        logical_kind, logical_id = parsed
        needle = (search or "").strip().lower()
        word = _KIND_WORD.get(logical_kind, "button")
        devices = []
        for module in _assign_input_modules():
            claim = module["claim"]
            controls = []
            if module["bus"] == "keyboard":
                if logical_kind != InputType.JoystickButton:
                    continue
                saved = set(claim_ids(claim, "key"))
                for key in keyboard.g_name_to_key.values():
                    hid = key_id(key.scan_code, key.is_extended)
                    if saved and hid not in saved and int(key.scan_code) not in saved:
                        continue
                    if not saved:
                        continue
                    label = claim_friendly(claim, "key", hid) or key.name
                    if needle and needle not in label.lower() and needle not in module["name"].lower():
                        continue
                    src_id = (key.scan_code, key.is_extended)
                    controls.append(
                        {
                            "key": self._control_key(str(keyboard_guid()), "key", key.scan_code, 1 if key.is_extended else 0),
                            "label": label,
                            "on": self._linked_now(logical_kind, logical_id, keyboard_guid(), InputType.Keyboard, src_id),
                        }
                    )
                controls.sort(key=lambda row: row["label"].lower())
            else:
                src_type = logical_kind
                for number in claim_ids(claim, word):
                    label = claim_friendly(claim, word, number) or f"{word.capitalize()} {number}"
                    if needle and needle not in label.lower() and needle not in module["name"].lower():
                        continue
                    guid = module["guid"]
                    try:
                        guid_obj = uuid.UUID(str(guid))
                    except ValueError:
                        guid_obj = guid
                    controls.append(
                        {
                            "key": self._control_key(str(guid), word, number, 0),
                            "label": label,
                            "on": self._linked_now(logical_kind, logical_id, guid_obj, src_type, number),
                        }
                    )
            if controls or not needle:
                devices.append({"name": module["name"], "controls": controls})
        return devices

    @QtCore.Slot(str, "QStringList", bool)
    def setLinks(self, parent_key: str, control_keys: list, on: bool) -> None:
        parsed = _parse_parent(parent_key)
        if parsed is None:
            return
        logical_kind, logical_id = parsed

        def fn():
            delta = []
            for control_key in control_keys:
                spec = self._parse_control(control_key)
                if spec is None:
                    continue
                guid, src_type, src_id = spec
                record = {
                    "guid": guid,
                    "src_type": src_type,
                    "src_id": list(src_id) if isinstance(src_id, tuple) else src_id,
                    "mode": self._mode,
                    "logical_type": logical_kind,
                    "logical_id": logical_id,
                    "axis_mode": AxisMode.Absolute,
                    "scale": 1.0,
                    "invert": False,
                }
                linked = self._linked_now(
                    logical_kind,
                    logical_id,
                    uuid.UUID(guid),
                    src_type,
                    src_id,
                )
                if on and not linked:
                    record["op"] = "add"
                    if self._add_link(record) is not None:
                        delta.append(record)
                elif not on and linked:
                    record["op"] = "remove"
                    # Capture the current axis settings before the link is removed.
                    for item, _binding, action in self._links_for(logical_kind, logical_id):
                        if str(item.device_id) == guid and item.input_type == src_type and item.input_id == src_id and item.mode == self._mode:
                            record = self._link_record(item, action, "remove", _binding)
                            if isinstance(record["src_id"], tuple):
                                record["src_id"] = list(record["src_id"])
                            break
                    if self._remove_link(record):
                        delta.append(record)
            return delta

        self._apply(fn)

    def _spec(self, key: str):
        item = self._item_for(key)
        profile = self._profile()
        if item is None or profile is None:
            return None
        real = profile.get_input_item(
            self._logical.device_guid,
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
            key=(self._logical.device_guid, item.type, item.id, self._mode),
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

    def _set_sequences(self, real: InputItem, change: Callable[[], object]) -> int:
        """Runs change (it edits real's actions) as one Undo step; returns
        what change returned when it is an index."""
        result: list[object] = []

        def fn() -> list[dict]:
            before = self._snapshot(real)
            result.append(change())
            return [{
                "op": "input", "key": self._input_key(real),
                "before": before, "after": self._snapshot(real),
            }]

        self._apply(fn)
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
                self._logical.device_guid,
                item.type,
                item.id,
                str(shadow.mode or self._mode),
                create_if_missing=True,
            )
            self._pane_real = real
        if real is None:
            return -1
        library = real.library
        if self._pane_new:
            where: int | None = -1
        elif self._pane_whole or self._pane_seq < 0:
            where = None
        else:
            where = self._pane_seq
        try:
            index = self._set_sequences(
                real, lambda: library.commit(draft, real, where)
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
    def paneModel(self):
        return self._pane_model

    @QtCore.Property(bool, notify=revisionChanged)
    def canUndo(self) -> bool:
        return bool(self._undo)

    @QtCore.Property(bool, notify=revisionChanged)
    def canRedo(self) -> bool:
        return bool(self._redo)

    @QtCore.Property(int, notify=selectionChanged)
    def selectionCount(self) -> int:
        return len(self._selected)

    @QtCore.Property(str, notify=selectionChanged)
    def selectionLabel(self) -> str:
        if not self._selected:
            return "No rows selected"
        if len(self._selected) == 1:
            item = self._item_for(self._selected[0])
            return item.system_name if item is not None else "1 row selected"
        return f"{len(self._selected)} rows selected"

    @QtCore.Slot(int, result=str)
    def keyAt(self, row: int) -> str:
        if 0 <= row < len(self._rows):
            return str(self._rows[row]["key"])
        return ""

    @QtCore.Property("QVariantList", notify=groupsChanged)
    def groups(self) -> list:
        logical = self._logical
        rows = [{"name": "", "title": "Ungrouped", "summary": ""}]
        counts = {name: [0, 0, 0] for name in [""] + logical.group_names()}
        for item in logical.ordered():
            bucket = counts.setdefault(item.group or "", [0, 0, 0])
            if item.type == InputType.JoystickButton:
                bucket[0] += 1
            elif item.type == InputType.JoystickAxis:
                bucket[1] += 1
            else:
                bucket[2] += 1
        rows[0]["summary"] = _count_text(*counts.get("", [0, 0, 0]))
        for name in logical.group_names():
            rows.append(
                {
                    "name": name,
                    "title": name,
                    "summary": _count_text(*counts.get(name, [0, 0, 0])),
                }
            )
        return rows


def keyboard_guid() -> uuid.UUID:
    import dill

    return dill.UUID_Keyboard
