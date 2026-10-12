# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
"""The Device Bindings page's rows on the shared control page base
(D-05-CFG-PAGE, 05 S121-S131).

HardwareLayoutModel is ControlLayoutModel for a hardware device: one parent
per input the device's input module claims (connected inputs only; Module
Setup owns the claims, so rows are never added or removed here), its action
sequences in the shown mode as child rows, groups, order and names kept in
the device's input module file (key "layout", names in the claim's friendly
names, 03 S121), held unsaved until File > Save (CS1, store.set_pending_layout).
Type and Output filters (S124), "No actions in this mode" (S123), one Undo
for OK, Delete and layout (S127), live decoration through deviceIndex
(S131)."""

from __future__ import annotations

import uuid
import weakref
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from PySide6 import QtCore

import gremlin.ui.type_aliases as ta
from gremlin import common
from gremlin.error import GremlinError
from gremlin.logical_device import _natural_key, _same_group
from gremlin.modules import hardware, store
from gremlin.modules.claim import claim_friendly, claim_ids, read_claim, type_of
from gremlin.modules.ids import guid_key
from gremlin.signal import signal
from gremlin.types import InputType
from gremlin.ui.binding_catalog import (
    _NAMED_FILTERS,
    _TYPE_FILTERS,
    collect_leaves,
    item_note,
    sequence_is_simple,
    sequences_for_item,
    type_filter_names,
)
from gremlin.ui.control_layout import (
    ROW_DEFAULTS,
    ControlLayoutModel,
    LayoutItem,
    group_key,
    kind_word,
    parent_key,
    parse_parent,
)

QML_IMPORT_NAME = "Gremlin.Device"
QML_IMPORT_MAJOR_VERSION = 1

KINDS = ("axis", "button", "hat")
# Axes first, as the Device Bindings page always listed them.
TYPE_ORDER = (InputType.JoystickAxis, InputType.JoystickButton, InputType.JoystickHat)
NO_DEST = ("all", "All devices", "")

# Roles the Device Bindings page adds to the shared ones.
EXTRA_DEFAULTS: dict[str, Any] = {
    # The parent's index in the page's DeviceLiveState: ControlTree's live
    # lights and bars (S131, scratchpad cfg_appear_contract); -1: none.
    "liveIndex": -1,
    "deviceIndex": -1,
    "kind": "",
    "hwId": 0,
    "note": "",
    "simple": True,
}


def _mapping_for(device: object) -> object | None:
    """The device database's names for the device's inputs, None when none."""
    try:
        from gremlin.input_cache import DeviceDatabase

        return DeviceDatabase().get_mapping(device)
    except Exception:  # noqa: BLE001 - no names: the plain ones are used
        return None


def _device_index(device: Any, kind: str, hid: int) -> int:  # noqa: ANN401
    """The input's index in the device's input list (axes, buttons, hats):
    what DeviceLiveState and jump-to-pressed use. -1: not on the device."""
    if kind == "axis":
        for index, axis in enumerate(device.axis_map):
            if int(axis.axis_index) == int(hid):
                return index
        return -1
    if kind == "button":
        if 1 <= int(hid) <= int(device.button_count):
            return int(device.axis_count) + int(hid) - 1
        return -1
    if 1 <= int(hid) <= int(device.hat_count):
        return int(device.axis_count) + int(device.button_count) + int(hid) - 1
    return -1


@dataclass(frozen=True)
class HardwareLayoutItem:
    """One claimed input as the shared base reads it (LayoutItem)."""

    kind: str
    id: int
    device_index: int
    group: str
    system_name: str
    second_name: str

    @property
    def type(self) -> InputType:
        return type_of(self.kind)

    @property
    def identifier(self) -> str:
        return store.input_key(self.kind, self.id)

    @property
    def label(self) -> str:
        return self.system_name

    @property
    def row_title(self) -> str:
        return self.second_name or self.system_name

    @property
    def choice_label(self) -> str:
        return self.second_name or self.system_name


class HardwareLayoutStore:
    """Groups, order and friendly names of one device's claimed inputs (the
    duck-typed store of control_layout). Every edit goes to
    store.set_pending_layout: saved at File > Save (CS1)."""

    def __init__(self) -> None:
        self.guid = ""
        self.device_name = ""
        self.device: Any = None
        self.writing = False
        # (kind, id) -> (device index, system name), claim order.
        self._inputs: dict[tuple[str, int], tuple[int, str]] = {}
        self._groups: list[str] = []
        self._order: list[str] = []
        self._group_of: dict[str, str] = {}
        self._names: dict[str, str] = {}

    # -- device and file ------------------------------------------------------

    def set_device(self, guid: str, device_name: str) -> None:
        self.guid = str(guid or "")
        self.device_name = str(device_name or "")
        self.load()

    def _path(self) -> Any:  # noqa: ANN401 - Path | None
        if not self.guid:
            return None
        if self.device_name:
            return store.module_file(self.device_name, self.guid)
        # By id only: the folder holding the id (03 S1), never one by name.
        folder = store.dir_of_id(self.guid)
        return store.module_file_in(folder) if folder is not None else None

    def _read_device(self) -> None:
        self.device = None
        if not self.guid or self.guid.lower() == "unknown":
            return
        try:
            self.device = hardware.device_info(self.guid)
        except Exception:  # noqa: BLE001 - not connected: no rows
            self.device = None

    def load(self) -> None:
        """Reads the claimed inputs, the layout and the names (unsaved ones
        first)."""
        self._read_device()
        path = self._path()
        doc = store.read_path(path) if path is not None and path.is_file() else {}
        claim = read_claim(doc) if doc else {}
        self._inputs = {}
        mapping = _mapping_for(self.device) if self.device is not None else None
        for kind in KINDS:
            for hid in claim_ids(claim, kind):
                if self.device is None:
                    continue
                index = _device_index(self.device, kind, hid)
                if index < 0:
                    continue
                system = self._system(mapping, kind, hid)
                self._inputs[(kind, int(hid))] = (index, system)
        layout = store.layout_for(self.guid, self.device_name) if self.guid else {}
        layout = store.normalize_layout(layout)
        self._groups = list(layout["groups"])
        self._order = list(layout["order"])
        self._group_of = dict(layout["group_of"])
        pending = store.pending_layout(self.guid) if self.guid else None
        held = (pending or {}).get("names", {})
        self._names = {}
        for kind, hid in self._inputs:
            key = store.input_key(kind, hid)
            name = held[key] if key in held else claim_friendly(claim, kind, hid)
            if str(name or "").strip():
                self._names[key] = str(name).strip()

    @staticmethod
    def _system(mapping: object | None, kind: str, hid: int) -> str:
        input_type = type_of(kind)
        if mapping is not None:
            try:
                return str(mapping.input_name((input_type, int(hid))))  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001 - the plain name instead
                pass
        return common.input_to_ui_string(input_type, int(hid))

    def device_uuid(self) -> uuid.UUID:
        nested = getattr(getattr(self.device, "device_guid", None), "uuid", None)
        if isinstance(nested, uuid.UUID):
            return nested
        try:
            return uuid.UUID(self.guid.strip("{}"))
        except ValueError:
            return uuid.UUID(int=0)

    def _layout_doc(self) -> dict:
        return store.normalize_layout(
            {"groups": self._groups, "order": self._order, "group_of": self._group_of}
        )

    def _all_names(self) -> dict[str, str]:
        return {
            store.input_key(kind, hid): self._names.get(store.input_key(kind, hid), "")
            for kind, hid in self._inputs
        }

    def _save(self) -> None:
        """Holds the layout and names unsaved until File > Save."""
        if not self.guid:
            return
        self.writing = True
        try:
            store.set_pending_layout(
                self.guid, self._layout_doc(), self._all_names(), self.device_name
            )
        finally:
            self.writing = False

    # -- Undo -----------------------------------------------------------------

    def memento(self) -> dict:
        return {
            "guid": self.guid,
            "layout": self._layout_doc(),
            "names": self._all_names(),
        }

    def restore(self, memo: dict) -> None:
        # Steps are cleared on a device switch; a step of another device
        # never plays here.
        if memo.get("guid") != self.guid:
            return
        layout = memo["layout"]
        self._groups = list(layout["groups"])
        self._order = list(layout["order"])
        self._group_of = dict(layout["group_of"])
        self._names = {key: name for key, name in memo["names"].items() if name}
        self._save()

    # -- reading --------------------------------------------------------------

    def group_names(self) -> list[str]:
        return list(self._groups)

    def _item(self, kind: str, hid: int) -> HardwareLayoutItem:
        key = store.input_key(kind, hid)
        index, system = self._inputs[(kind, hid)]
        group = self._group_of.get(key, "")
        return HardwareLayoutItem(
            kind=kind,
            id=hid,
            device_index=index,
            group=group if group in self._groups else "",
            system_name=system,
            second_name=self._names.get(key, ""),
        )

    @staticmethod
    def _split(key: str) -> tuple[str, int] | None:
        kind, _, number = str(key).partition(":")
        try:
            return kind, int(number)
        except ValueError:
            return None

    def _keys(self) -> list[str]:
        """Every claimed input's key in page order: the saved order, then the
        rest in claim order."""
        known = [store.input_key(kind, hid) for kind, hid in self._inputs]
        present = set(known)
        out = [key for key in dict.fromkeys(self._order) if key in present]
        seen = set(out)
        return out + [key for key in known if key not in seen]

    def ordered(self) -> list[HardwareLayoutItem]:
        items = []
        for key in self._keys():
            parts = self._split(key)
            if parts is not None and parts in self._inputs:
                items.append(self._item(*parts))
        return items

    def exists(self, identifier: object) -> bool:
        parts = self._split(str(identifier or ""))
        return parts is not None and parts in self._inputs

    def __getitem__(self, identifier: object) -> HardwareLayoutItem:
        parts = self._split(str(identifier or ""))
        if parts is None or parts not in self._inputs:
            raise KeyError(identifier)
        return self._item(*parts)

    def key_for_index(self, device_index: int) -> str:
        for (kind, hid), (index, _system) in self._inputs.items():
            if index == int(device_index):
                return store.input_key(kind, hid)
        return ""

    # -- edits ----------------------------------------------------------------

    def _ensure(self, name: str) -> str:
        text = " ".join((name or "").split())
        if not text:
            return text
        for existing in self._groups:
            if _same_group(existing, text):
                return existing
        self._groups.append(text)
        return text

    def ensure_group(self, name: str) -> str:
        text = self._ensure(name)
        self._save()
        return text

    def rename_group(self, old_name: str, new_name: str) -> None:
        old = (old_name or "").strip()
        new = " ".join((new_name or "").split())
        if not old or old not in self._groups:
            raise GremlinError(f"No group named '{old_name}' exists")
        if not new:
            raise GremlinError("A group needs a name")
        clash = next(
            (name for name in self._groups if name != old and _same_group(name, new)),
            None,
        )
        if clash is not None:
            raise GremlinError(f"A group named '{clash}' already exists")
        self._groups = [new if name == old else name for name in self._groups]
        self._group_of = {
            key: (new if name == old else name) for key, name in self._group_of.items()
        }
        self._save()

    def delete_group(self, name: str) -> None:
        text = (name or "").strip()
        self._groups = [entry for entry in self._groups if entry != text]
        self._group_of = {
            key: group for key, group in self._group_of.items() if group != text
        }
        self._save()

    def place(self, identifier: object, group: str, before: object = None) -> None:
        key = str(identifier)
        folder = self._ensure(group or "")
        if folder:
            self._group_of[key] = folder
        else:
            self._group_of.pop(key, None)
        order = [entry for entry in self._keys() if entry != key]
        if before is not None and str(before) in order:
            order.insert(order.index(str(before)), key)
        else:
            order.append(key)
        self._order = order
        self._save()

    def move_group_before(self, name: str, before: str | None) -> None:
        text = (name or "").strip()
        if text not in self._groups:
            return
        self._groups = [entry for entry in self._groups if entry != text]
        if before and before in self._groups:
            self._groups.insert(self._groups.index(before), text)
        else:
            self._groups.append(text)
        self._save()

    def sort_within(self, key_name: str) -> None:
        """Orders the inputs inside each group: "system" by system name,
        "user" by your name (else the system name)."""
        items = self.ordered()
        order: list[str] = []
        for folder in [""] + self._groups:
            bucket = [item for item in items if (item.group or "") == folder]
            if key_name == "user":
                bucket.sort(
                    key=lambda i: (_natural_key(i.second_name or i.system_name), i.id)
                )
            else:
                bucket.sort(key=lambda i: (_natural_key(i.system_name), i.id))
            order.extend(item.identifier for item in bucket)
        self._order = order
        self._save()

    def sort_groups(self) -> None:
        self._groups.sort(key=_natural_key)
        self._save()

    def set_user_label(self, identifier: object, text: str) -> None:
        """Rename (S129): the module's friendly name; blank or the system
        name removes it."""
        key = str(identifier)
        if not self.exists(key):
            return
        cleaned = (text or "").strip()
        if cleaned == self[key].system_name:
            cleaned = ""
        if cleaned:
            self._names[key] = cleaned
        else:
            self._names.pop(key, None)
        self._save()

    def delete(self, identifier: object) -> None:
        """Claimed inputs aren't removed here (Module Setup owns them)."""
        return None


def _pending_relay(model: HardwareLayoutModel) -> Callable[[str, str], None]:
    """A store listener that doesn't keep the model alive (and goes once the
    model is gone)."""
    ref = weakref.ref(model)

    def relay(what: str, guid: str) -> None:
        target = ref()
        if target is None:
            store.remove_pending_listener(relay)
            return
        try:
            target._on_pending(what, guid)
        except RuntimeError:  # the Qt object is gone
            store.remove_pending_listener(relay)

    return relay


@ta.QmlElement
class HardwareLayoutModel(ControlLayoutModel):
    """Rows for the Device Bindings page: group headers, one parent per
    claimed input, and its actions in the shown mode."""

    roles = {
        **ControlLayoutModel.roles,
        **{
            QtCore.Qt.ItemDataRole.UserRole
            + 1
            + len(ROW_DEFAULTS)
            + i: QtCore.QByteArray(name.encode())
            for i, name in enumerate(EXTRA_DEFAULTS)
        },
    }

    deviceChanged = QtCore.Signal()
    filtersChanged = QtCore.Signal()
    # paneKey's own signal: a property can't notify with a base
    # class's signal (QML crashed building the model).
    paneChanged = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        self._store: HardwareLayoutStore
        super().__init__(parent)
        # canUndo/canRedo follow the pane opening and closing (05 S36).
        self.paneModelChanged.connect(self.revisionChanged)
        self.paneModelChanged.connect(self.paneChanged)
        self._action_type = "all"
        self._dest_filter = "all"
        self._dest_choices: list[str] = ["All devices"]
        self._announcing = False
        self._relay = _pending_relay(self)
        store.add_pending_listener(self._relay)
        signal.inputItemChanged.connect(self._on_input_changed)
        signal.configChanged.connect(self.reload)
        try:
            from gremlin import event_handler

            event_handler.EventListener().device_change_event.connect(
                self._on_devices_changed
            )
        except Exception:  # noqa: BLE001 - no device events (tests)
            pass
        self._rebuild()

    # ControlLayoutModel hooks.

    def _make_store(self) -> HardwareLayoutStore:
        self._store = HardwareLayoutStore()
        return self._store

    def _device_guid(self) -> uuid.UUID:
        return self._store.device_uuid()

    def _identifier(self, kind: InputType, input_id: int) -> str:
        return store.input_key(kind_word(kind), input_id)

    def _emit_store_changed(self) -> None:
        # The store's own listeners hear each held change (the title's "*").
        return None

    def _type_order(self) -> tuple[InputType, ...]:
        return TYPE_ORDER

    def _can_remove(self, item: LayoutItem) -> bool:
        return False

    def _row(self, **fields: object) -> dict:
        return {**ROW_DEFAULTS, **EXTRA_DEFAULTS, **fields}

    def _real(self, item: LayoutItem) -> Any:  # noqa: ANN401 - InputItem | None
        profile = self._profile()
        if profile is None:
            return None
        return profile.get_input_item(
            self._device_guid(), item.type, item.id, self._mode, create_if_missing=False
        )

    def _real_item(self, item: LayoutItem) -> Any:  # noqa: ANN401 - InputItem | None
        return self._real(item)

    def _action_filtering(self) -> bool:
        return self._action_type not in ("all", "") or self._dest_filter not in NO_DEST

    def _leaf_ok(self, tag: str, dest: str) -> bool:
        kind = self._action_type
        if kind not in ("all", ""):
            allowed = _NAMED_FILTERS.get(kind)
            if allowed is not None and tag not in allowed:
                return False
            if allowed is None and kind == "other":
                if any(tag in tags for tags in _NAMED_FILTERS.values()):
                    return False
        return self._dest_filter in NO_DEST or dest == self._dest_filter

    def _shown(self, real: Any) -> list[tuple[int, str, str]]:  # noqa: ANN401
        """The input's sequences the Type and Output filters let through."""
        listed = sequences_for_item(real)
        if not self._action_filtering():
            return listed
        sequences = getattr(real, "action_sequences", None) or []
        shown = []
        for index, label, dest in listed:
            root = sequences[index].root_action
            leaves = collect_leaves(root) if root is not None else []
            if any(self._leaf_ok(tag, leaf_dest) for tag, _l, leaf_dest in leaves):
                shown.append((index, label, dest))
        return shown

    def _child_rows(self, item: LayoutItem) -> list[dict]:
        real = self._real(item)
        key = parent_key(item.type, item.id)
        rows = []
        for index, label, dest in self._shown(real):
            rows.append(
                self._row(
                    rowKind="child",
                    key=f"child:{kind_word(item.type)}:{item.id}:{index}",
                    title=label or "Action",
                    subtitle=dest or "",
                    parentKey=key,
                    groupKey=group_key(item.group),
                    groupName=item.group or "",
                    systemName=item.system_name,
                    sequenceIndex=index,
                    deviceIndex=getattr(item, "device_index", -1),
                    kind=kind_word(item.type),
                    hwId=item.id,
                    simple=sequence_is_simple(real, index),
                )
            )
        return rows

    def _parent_subtitle(self, item: LayoutItem, extra: list[dict]) -> str:
        return item_note(self._real(item))

    def _parent_fields(self, item: LayoutItem, extra: list[dict]) -> dict:
        real = self._real(item)
        shown = self._shown(real)
        index = getattr(item, "device_index", -1)
        return {
            "liveIndex": index,
            "deviceIndex": index,
            "kind": kind_word(item.type),
            "hwId": item.id,
            "note": item_note(real, [index for index, _l, _d in shown]),
        }

    def _filtering(self) -> bool:
        return self._action_filtering() or super()._filtering()

    def _visible_parent(
        self, item: LayoutItem, extra: list[dict], action_count: int
    ) -> bool:
        real = self._real(item)
        count = len(getattr(real, "action_sequences", None) or [])
        if self._ungrouped_only and (item.group or ""):
            return False
        if self._no_actions and count:
            return False
        if self._action_filtering() and not action_count:
            return False
        return self._matches(item, self._search, self._type_filter)

    def _rebuild(self) -> None:
        dests: list[str] = []
        profile = self._profile()
        if profile is not None:
            for item in self._layout.ordered():
                real = self._real(item)
                for seq in getattr(real, "action_sequences", None) or []:
                    root = getattr(seq, "root_action", None)
                    if root is None:
                        continue
                    for _tag, _label, dest in collect_leaves(root):
                        if dest and dest not in dests:
                            dests.append(dest)
        self._dest_choices = ["All devices"] + dests
        super()._rebuild()
        self.filtersChanged.emit()

    # Signals from the rest of the program.

    def _on_pending(self, what: str, guid: str) -> None:
        if self._store.writing:
            return
        if guid and guid_key(guid) != guid_key(self._store.guid):
            return
        self._store.load()
        if what in ("discarded", "replaced"):
            # Steps would replay the dropped edits (replaced: AD2, the
            # newer file won; the store said so).
            self._on_reloaded()
        else:
            self._rebuild()

    def _on_input_changed(self, _index: int) -> None:
        if not self._announcing:
            self._on_external()

    def _on_devices_changed(self) -> None:
        if self._store.device is None and self._store.guid:
            self.reload()

    def _announce(self, links: list[dict]) -> None:
        """Tells the other views (and the title's "*") an input's actions
        changed, as the page always did."""
        indices = []
        for link in links:
            if link.get("op") != "input":
                continue
            _guid, kind, number, _mode = link["key"]
            key = store.input_key(kind_word(kind), number)
            if self._store.exists(key):
                indices.append(self._store[key].device_index)
        self._announcing = True
        try:
            for index in dict.fromkeys(indices):
                signal.inputItemChanged.emit(index)
        finally:
            self._announcing = False

    def _apply(self, fn: Callable[[], list[dict] | None], label: str = "") -> bool:
        size = len(self._undo)
        done = super()._apply(fn, label)
        if done and self._undo and (len(self._undo) != size or not self._redo):
            self._announce(self._undo[-1]["links"])
        return done

    def _undo_waits(self) -> bool:
        # 05 S36: Undo/Redo wait while an action is open in the pane.
        return self._pane_model is not None

    @QtCore.Slot()
    def undo(self) -> None:
        entry = self._undo[-1] if self._undo else None
        super().undo()
        if entry is not None and self._redo and self._redo[-1] is entry:
            self._announce(entry["links"])

    @QtCore.Slot()
    def redo(self) -> None:
        entry = self._redo[-1] if self._redo else None
        super().redo()
        if entry is not None and self._undo and self._undo[-1] is entry:
            self._announce(entry["links"])

    # Slots.

    @QtCore.Slot()
    def reload(self) -> None:
        """Reads the module file again (claims, names, layout)."""
        self._store.load()
        self._rebuild()

    @QtCore.Slot(str, str)
    def setDevice(self, guid: str, device_name: str) -> None:
        """Shows another device: the pane closes and every Undo step goes
        (S127)."""
        guid = str(guid or "")
        device_name = str(device_name or "")
        if guid == self._store.guid and device_name == self._store.device_name:
            return
        self.endPane()
        self._store.set_device(guid, device_name)
        self._selected = []
        self.drop_steps()
        self._rebuild()
        self.deviceChanged.emit()

    def _get_guid(self) -> str:
        return self._store.guid

    def _set_guid(self, guid: str) -> None:
        self.setDevice(guid, self._store.device_name)

    def _get_device_name(self) -> str:
        return self._store.device_name

    def _set_device_name(self, name: str) -> None:
        self.setDevice(self._store.guid, name)

    guid = QtCore.Property(str, fget=_get_guid, fset=_set_guid, notify=deviceChanged)
    deviceName = QtCore.Property(
        str, fget=_get_device_name, fset=_set_device_name, notify=deviceChanged
    )

    @QtCore.Slot(str, str)
    def setActionFilters(self, type_key: str, dest: str) -> None:
        """The Type and Output boxes in the Find bar (S124)."""
        self._action_type = str(type_key or "all")
        self._dest_filter = str(dest or "all")
        self._rebuild()

    @QtCore.Property(str, notify=filtersChanged)
    def actionType(self) -> str:
        return self._action_type

    @QtCore.Property(list, constant=True)
    def typeFilterNames(self) -> list[str]:
        return type_filter_names()

    @QtCore.Property(list, constant=True)
    def typeFilterKeys(self) -> list[str]:
        return [key for key, _tag in _TYPE_FILTERS]

    @QtCore.Property(list, notify=filtersChanged)
    def destChoices(self) -> list[str]:
        return list(self._dest_choices)

    # Delete (S31: not the input the pane edits).

    def _pane_on(self, key: str) -> bool:
        if self._pane_model is None or not self._pane_key:
            return False
        if parse_parent(self._pane_key) != parse_parent(key):
            return False
        shadow = self._pane_shadow
        mode = str(shadow.mode) if shadow is not None else self._mode
        return mode == self._mode

    @QtCore.Slot(str, result=bool)
    def canDelete(self, parent_key: str) -> bool:
        return not self._pane_on(parent_key)

    @QtCore.Slot(str, int, result=bool)
    def deleteAction(self, parent_key: str, sequence_index: int) -> bool:
        if self._pane_on(parent_key):
            return False
        return super().deleteAction(parent_key, sequence_index)

    @QtCore.Slot(str, result=bool)
    def deleteActions(self, parent_key: str) -> bool:
        """Every action of the input in the shown mode, one Undo step."""
        if self._pane_on(parent_key):
            return False
        spec = self._spec(parent_key)
        if spec is None:
            return False
        profile, item, real = spec
        if real is None or not real.action_sequences:
            return False

        def fn() -> list[dict]:
            before = self._snapshot(real)
            for binding in list(real.action_sequences):
                real.remove_item_binding(binding)
                profile.library.release([binding.root_action])
            return [
                {
                    "op": "input",
                    "key": self._input_key(real),
                    "before": before,
                    "after": self._snapshot(real),
                }
            ]

        return self._apply(fn, f"Delete actions of {item.choice_label}")

    # Jump to the pressed input; the pane.

    @QtCore.Slot(int, result=str)
    def keyForDeviceIndex(self, device_index: int) -> str:
        key = self._store.key_for_index(int(device_index))
        if not key:
            return ""
        kind, _, number = key.partition(":")
        return parent_key(type_of(kind), int(number))

    @QtCore.Property(str, notify=paneChanged)
    def paneKey(self) -> str:
        return self._pane_key if self._pane_model is not None else ""

    @QtCore.Slot(result=int)
    def commitPane(self) -> int:
        index = super().commitPane()
        if index >= 0:
            item = self._item_for(self._pane_key)
            if item is not None:
                self._announcing = True
                try:
                    signal.inputItemChanged.emit(getattr(item, "device_index", -1))
                finally:
                    self._announcing = False
        return index
