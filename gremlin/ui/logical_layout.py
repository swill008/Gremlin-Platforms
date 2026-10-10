# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
"""Logical device layout: groups, names, hardware links, and the action pane."""

from __future__ import annotations

import uuid
import weakref
from typing import Any
from xml.etree import ElementTree

from PySide6 import QtCore

import gremlin.ui.type_aliases as ta
from gremlin import device_initialization, error, keyboard, shared_state
from gremlin.base_classes import AbstractActionData
from gremlin.error import GremlinError
from gremlin.logical_device import LogicalDevice
from gremlin.modules import store
from gremlin.modules.claim import claim_friendly, claim_ids, key_id, read_claim
from gremlin.modules.ids import guid_key
from gremlin.modules.registry import module_direction
from gremlin.profile import (
    InputItem,
    InputItemBinding,
    VirtualAxisButton,
    VirtualHatButton,
)
from gremlin.signal import signal
from gremlin.types import AxisMode, DataInsertionMode, InputType
from gremlin.ui.control_layout import (
    KIND_WORD as _KIND_WORD,
)
from gremlin.ui.control_layout import (
    ControlLayoutModel,
    LayoutItem,
)
from gremlin.ui.control_layout import (
    group_key as _group_key,
)
from gremlin.ui.control_layout import (
    kind_word as _kind_word,
)
from gremlin.ui.control_layout import (
    parent_key as _parent_key,
)
from gremlin.ui.control_layout import (
    parse_parent as _parse_parent,
)
from gremlin.ui.module_model import (
    KEYBOARD_GUID,
    LOGICAL_GUID,
    OSC_GUID,
)

QML_IMPORT_NAME = "Gremlin.Device"
QML_IMPORT_MAJOR_VERSION = 1


def _assign_input_modules() -> list[dict]:
    """Saved source input modules. Logical Device is never a writer source."""
    rows: list[dict] = []
    seen: set[str] = set()
    logical = guid_key(LOGICAL_GUID)

    def add(name: str, guid: str, bus: str) -> None:
        key = guid_key(guid) or name.lower()
        if key in seen or key == logical:
            return
        if bus == "osc":
            # OSC's inputs are the rows in its file (D-09-OSC-FILE), never a
            # claim.
            seen.add(key)
            rows.append({"name": name, "guid": guid, "bus": bus, "claim": {}})
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


def _is_osc(guid: object) -> bool:
    return guid_key(str(guid)) == guid_key(OSC_GUID)


def _osc_ref(
    record: dict, src_type: InputType, src_id: object
) -> tuple[InputType, Any, str | None] | None:
    """An Assign Hardware link from an OSC input, by its permanent id
    ("osc_uid"; D-09-OSC-FILE 2): its current type and number. None: OSC's
    file doesn't have it (never re-targeted by number)."""
    from gremlin.osc_persist import resolve_osc_reference

    ident, uid = resolve_osc_reference(
        record.get("osc_uid") or None, src_type, int(src_id)  # type: ignore[arg-type]
    )
    if ident is None:
        return None
    return ident.type, int(ident.id), uid


def _osc_uid_of(src_type: InputType, src_id: object) -> str | None:
    from gremlin.osc_persist import osc_rows

    try:
        return osc_rows().uid_of(src_type, int(src_id))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None



# The Logical pages open now, for drop_logical_steps.
_MODELS: weakref.WeakSet = weakref.WeakSet()


def drop_logical_steps() -> None:
    """The Logical Device was read again from its file (Discard, Restore):
    Undo / Redo steps would play edits that are gone, so they go."""
    for model in list(_MODELS):
        model.drop_steps()


@ta.QmlElement
class LogicalLayoutModel(ControlLayoutModel):
    """Rows for the logical page: group headers, parents, writers, and actions."""

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        _MODELS.add(self)
        signal.logicalDeviceModified.connect(self._on_external)
        signal.logicalDeviceReloaded.connect(self._on_reloaded)
        self._rebuild()

    # ControlLayoutModel hooks.

    def _make_store(self) -> LogicalDevice:
        self._logical = LogicalDevice()
        return self._logical

    def _device_guid(self) -> uuid.UUID:
        return self._logical.device_guid

    def _identifier(
        self, kind: InputType, input_id: int
    ) -> LogicalDevice.Input.Identifier:
        return LogicalDevice.Input.Identifier(kind, input_id)

    def _emit_store_changed(self) -> None:
        signal.logicalDeviceModified.emit()

    def _extra_rows(self, item: LayoutItem) -> list[dict]:
        return self._writer_rows(item)

    def _parent_subtitle(self, item: LayoutItem, extra: list[dict]) -> str:
        return extra[0]["title"] if extra else ""

    def _parent_fields(self, item: LayoutItem, extra: list[dict]) -> dict:
        lead = extra[0] if extra else None
        return {
            "writerId": lead["writerId"] if lead else "",
            "axisMode": lead["axisMode"] if lead else "",
            "axisScale": lead["axisScale"] if lead else 1.0,
            "inverted": lead["inverted"] if lead else False,
            "canInvert": bool(lead) and item.type == InputType.JoystickButton,
            "extraWriters": max(0, len(extra) - 1),
        }

    def _rows_before_actions(self, item: LayoutItem, extra: list[dict]) -> list[dict]:
        return extra[1:]

    def _delete_parent(self, item: LayoutItem) -> list[dict]:
        links = self._detach_links(item.type, item.id)
        links.extend(self._take_own_items(item.type, item.id))
        self._logical.delete(item.identifier)
        return links

    def _play_link(self, entry: dict, forward: bool) -> None:
        # Undo of an add removes it; Undo of a remove adds it back.
        op = entry.get("op")
        if op not in ("add", "remove"):
            return
        if (op == "add") == forward:
            self._add_link(entry)
        else:
            self._remove_link(entry)

    # Hardware links (Assign Hardware, writer rows).

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
        if _is_osc(item.device_id):
            record["osc_uid"] = getattr(item, "osc_uid", None) or _osc_uid_of(
                item.input_type, item.input_id
            )
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
        osc_uid = None
        if _is_osc(guid):
            found = _osc_ref(record, src_type, src_id)
            if found is None:
                return None
            src_type, src_id, osc_uid = found
        item = profile.get_input_item(
            guid, src_type, src_id, str(record["mode"]), create_if_missing=True
        )
        if item is None:
            return None
        if osc_uid:
            item.osc_uid = osc_uid  # type: ignore[attr-defined]
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
        src_type = record["src_type"]
        if _is_osc(guid):
            found = _osc_ref(record, src_type, src_id)
            if found is None:
                return False
            src_type, src_id, _uid = found
        item = profile.get_input_item(
            guid, src_type, src_id, str(record["mode"]), create_if_missing=False
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

    @QtCore.Slot(str, int, str, str)
    def addMany(self, type_name: str, count: int, group: str, user_name: str) -> None:
        kind = InputType.to_enum(type_name)

        def fn():
            self._logical.create_many(kind, int(count), group, user_name)
            return []

        n = int(count)
        plural = {"axis": "Axes", "button": "Buttons", "hat": "Hats"}
        word = str(type_name).capitalize() if n == 1 else plural.get(
            str(type_name).lower(), str(type_name).capitalize() + "s"
        )
        self._apply(fn, f"Add {word}" if n == 1 else f"Add {n} {word}")

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
            elif module["bus"] == "osc":
                from gremlin.osc_persist import osc_rows

                guid = module["guid"]
                guid_obj = uuid.UUID(str(guid))
                for row in sorted(osc_rows().rows(), key=lambda r: r.input_id):
                    if row.input_type != logical_kind:
                        continue
                    label = row.label
                    if needle and needle not in (label + " " + module["name"]).lower():
                        continue
                    controls.append(
                        {
                            "key": self._control_key(str(guid), word, row.input_id, 0),
                            "label": label,
                            "on": self._linked_now(
                                logical_kind, logical_id, guid_obj,
                                row.input_type, row.input_id,
                            ),
                        }
                    )
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
                if _is_osc(guid):
                    record["osc_uid"] = _osc_uid_of(src_type, src_id)
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

        owner = self._item_for(parent_key)
        self._apply(
            fn, f"Assign Hardware to {owner.choice_label}" if owner is not None else ""
        )


def keyboard_guid() -> uuid.UUID:
    import dill

    return dill.UUID_Keyboard
