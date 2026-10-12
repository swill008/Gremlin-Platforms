# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
"""The Keyboard page on the shared control layout (05 S128, CF-Q7).

Rows are the profile's keys and the keys on the Keyboard module file's list,
each listed once with the shown mode's actions (S72). Add Key and Delete are
page Undo steps (S73, S75, S127). The key list (the layout's order: a key
with no actions isn't in the profile file, AD4), groups and Rename live in
the Keyboard's input module file (S122; Rename is the claim's friendly name,
S129), held unsaved until File > Save (CS1, the store's pending layouts).
The pane is the shared draft pane (05 Q5).
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Hashable
from dataclasses import dataclass, replace
from typing import Any, cast

from PySide6 import QtCore

import dill
import gremlin.ui.type_aliases as ta
from gremlin import keyboard
from gremlin.error import GremlinError
from gremlin.modules import ids, store
from gremlin.modules.claim import key_id, key_id_of
from gremlin.profile import InputItem
from gremlin.types import InputType
from gremlin.ui.binding_catalog import item_note, sequences_for_item
from gremlin.ui.control_layout import (
    ROW_DEFAULTS,
    ControlLayoutModel,
    LayoutItem,
    group_key,
    parent_key,
)
from gremlin.ui.live_follow import LiveInputs, follows

QML_IMPORT_NAME = "Gremlin.Device"
QML_IMPORT_MAJOR_VERSION = 1

GUID = dill.UUID_Keyboard
# The store takes the device id as text.
GUID_TEXT = str(GUID)
DEVICE_NAME = "Keyboard"
KEY_PREFIX = "key:"

# Roles the Keyboard page adds to the shared ones.
EXTRA_DEFAULTS: dict[str, Any] = {
    # ControlTree's live tint (05 S131, D-05-FOLLOW-ALL-PAGES): the key's
    # place in the model's kindAt / valueAt; -1: none.
    "liveIndex": -1,
}


def key_name(code: tuple) -> str:
    """The key's name ("A", "Left Shift"); its scan code when unknown."""
    try:
        return str(keyboard.key_from_code(*code).name)
    except Exception:  # noqa: BLE001 - an unknown code still lists
        return f"Key {code[0]}"


def key_row(code: tuple) -> str:
    """The parent row key of a key ((scan code, extended))."""
    return parent_key(InputType.Keyboard, key_id(code[0], bool(code[1])))


def key_code(ident: int) -> tuple:
    """The profile's key ((scan code, extended)) of a key id."""
    return (ident & 0xFFFF, bool(ident & 0x10000))


def _natural_key(text: str) -> list:
    return [int(p) if p.isdigit() else p.casefold() for p in re.split(r"(\d+)", text)]


def _sort_code(code: tuple) -> tuple:
    try:
        return (0, keyboard.key_from_code(*code).virtual_code, code)
    except Exception:  # noqa: BLE001
        return (1, 0, code)


@dataclass(frozen=True)
class KeyItem:
    """One key as the shared base reads it (LayoutItem). id is the claim's
    key id (scan code, extended in bit 16); code is the profile's key."""

    type: InputType
    id: Any  # int in rows; the (scan, extended) code in the profile view
    code: tuple
    group: str
    second_name: str

    @property
    def identifier(self) -> int:
        return key_id(self.code[0], bool(self.code[1]))

    @property
    def system_name(self) -> str:
        return key_name(self.code)

    @property
    def label(self) -> str:
        return self.system_name

    @property
    def row_title(self) -> str:
        second = self.second_name
        return f"{self.system_name}   {second}" if second else self.system_name

    @property
    def choice_label(self) -> str:
        second = self.second_name
        return f"{self.system_name} — {second}" if second else self.system_name


class KeyboardLayoutStore:
    """Groups, order and friendly names of the Keyboard's keys (the
    duck-typed store of control_layout). The keys are the profile's plus
    the order list's (every key in order is listed: Add Key puts it there,
    Delete takes it off, AD4); the layout and names are the Keyboard's
    module file's, held unsaved in the store until File > Save."""

    def __init__(self) -> None:
        self._groups: list[str] = []
        self._order: list[int] = []
        self._group_of: dict[int, str] = {}
        self._names: dict[int, str] = {}

    # -- file ----------------------------------------------------------------

    def load(self) -> None:
        """Takes what the page shows: the unsaved layout, else the file's."""
        layout = store.layout_for(GUID_TEXT, DEVICE_NAME)

        def ident(key: str) -> int | None:
            if not key.startswith(KEY_PREFIX):
                return None
            try:
                return int(key[len(KEY_PREFIX) :])
            except ValueError:
                return None

        self._groups = list(layout["groups"])
        self._order = [i for k in layout["order"] if (i := ident(k)) is not None]
        self._group_of = {
            i: name
            for k, name in layout["group_of"].items()
            if (i := ident(k)) is not None
        }
        self._names = {}

    def _name_of(self, ident: int) -> str:
        if ident in self._names:
            return self._names[ident]
        return store.friendly_name_for(GUID_TEXT, KEY_PREFIX + str(ident), DEVICE_NAME)

    def _layout_doc(self) -> dict:
        return store.normalize_layout(
            {
                "groups": self._groups,
                "order": [KEY_PREFIX + str(i) for i in self._order],
                "group_of": {KEY_PREFIX + str(i): n for i, n in self._group_of.items()},
            }
        )

    def _save(self, back: dict[int, str] | None = None) -> None:
        names = {**(back or {}), **self._names}
        store.set_pending_layout(
            GUID_TEXT,
            self._layout_doc(),
            {KEY_PREFIX + str(i): n for i, n in names.items()},
            DEVICE_NAME,
        )

    # -- Undo ----------------------------------------------------------------

    def memento(self) -> dict:
        return {
            "groups": list(self._groups),
            "order": list(self._order),
            "group_of": dict(self._group_of),
            "names": dict(self._names),
        }

    def restore(self, memo: dict) -> None:
        # A name set since goes back to the file's.
        back = {
            ident: store.friendly_name(GUID_TEXT, KEY_PREFIX + str(ident), DEVICE_NAME)
            for ident in set(self._names) - set(memo["names"])
        }
        self._groups = list(memo["groups"])
        self._order = list(memo["order"])
        self._group_of = dict(memo["group_of"])
        self._names = dict(memo["names"])
        self._save(back)

    # -- reading -------------------------------------------------------------

    @staticmethod
    def _codes() -> dict[int, tuple]:
        """Every key of the profile, any mode, once: key id -> code."""
        from gremlin import shared_state

        profile = shared_state.current_profile
        items = profile.inputs.get(GUID, []) if profile is not None else []
        codes: dict[int, tuple] = {}
        for item in items:
            code = tuple(cast(Any, item.input_id))
            ident = key_id_of(code)
            if ident is not None:
                codes.setdefault(ident, code)
        return codes

    def _all_codes(self) -> dict[int, tuple]:
        """The page's keys: the profile's and the list's."""
        codes = self._codes()
        for ident in self._order:
            codes.setdefault(ident, key_code(ident))
        return codes

    def group_names(self) -> list[str]:
        return list(self._groups)

    def _item(self, ident: int, code: tuple) -> KeyItem:
        group = self._group_of.get(ident, "")
        return KeyItem(
            type=InputType.Keyboard,
            id=ident,
            code=code,
            group=group if group in self._groups else "",
            second_name=self._name_of(ident),
        )

    def _idents(self, codes: dict[int, tuple]) -> list[int]:
        out = [i for i in dict.fromkeys(self._order) if i in codes]
        seen = set(out)
        rest = sorted(
            (i for i in codes if i not in seen), key=lambda i: _sort_code(codes[i])
        )
        return out + rest

    def ordered(self) -> list[KeyItem]:
        codes = self._all_codes()
        return [self._item(i, codes[i]) for i in self._idents(codes)]

    def exists(self, identifier: object) -> bool:
        return identifier in self._all_codes()

    def __getitem__(self, identifier: object) -> KeyItem:
        codes = self._all_codes()
        if identifier not in codes:
            raise KeyError(identifier)
        return self._item(int(identifier), codes[int(identifier)])  # type: ignore[arg-type]

    # -- edits ---------------------------------------------------------------

    def _ensure(self, name: str) -> str:
        text = " ".join((name or "").split())
        if not text:
            return text
        for existing in self._groups:
            if existing.casefold() == text.casefold():
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
            (n for n in self._groups if n != old and n.casefold() == new.casefold()),
            None,
        )
        if clash is not None:
            raise GremlinError(f"A group named '{clash}' already exists")
        self._groups = [new if n == old else n for n in self._groups]
        self._group_of = {
            i: (new if n == old else n) for i, n in self._group_of.items()
        }
        self._save()

    def delete_group(self, name: str) -> None:
        text = (name or "").strip()
        self._groups = [n for n in self._groups if n != text]
        self._group_of = {i: n for i, n in self._group_of.items() if n != text}
        self._save()

    def place(self, identifier: object, group: str, before: object = None) -> None:
        ident = int(identifier)  # type: ignore[call-overload]
        folder = self._ensure(group or "")
        if folder:
            self._group_of[ident] = folder
        else:
            self._group_of.pop(ident, None)
        order = [i for i in self._idents(self._all_codes()) if i != ident]
        if before is not None and before in order and before != ident:
            order.insert(order.index(before), ident)  # type: ignore[arg-type]
        else:
            order.append(ident)
        self._order = order
        self._save()

    def move_group_before(self, name: str, before: str | None) -> None:
        text = (name or "").strip()
        if text not in self._groups:
            return
        self._groups = [n for n in self._groups if n != text]
        if before and before in self._groups:
            self._groups.insert(self._groups.index(before), text)
        else:
            self._groups.append(text)
        self._save()

    def sort_within(self, key_name_: str) -> None:
        """ "system": by key name; "user": by your name, else the key name."""
        items = self.ordered()
        order: list[int] = []
        for folder in [""] + self._groups:
            bucket = [item for item in items if (item.group or "") == folder]
            if key_name_ == "user":
                bucket.sort(key=lambda i: _natural_key(i.second_name or i.system_name))
            else:
                bucket.sort(key=lambda i: _natural_key(i.system_name))
            order.extend(item.identifier for item in bucket)
        self._order = order
        self._save()

    def sort_groups(self) -> None:
        self._groups.sort(key=_natural_key)
        self._save()

    def set_user_label(self, identifier: object, text: str) -> None:
        ident = int(identifier)  # type: ignore[call-overload]
        cleaned = (text or "").strip()
        codes = self._all_codes()
        if ident in codes and cleaned == key_name(codes[ident]):
            cleaned = ""
        self._names[ident] = cleaned
        self._save()

    def delete(self, identifier: object) -> None:
        # The key's name stays: it is the claim's, and the key comes back
        # to it (Add Key). Undo puts the place and group back.
        return None

    def listed(self, ident: int) -> bool:
        """The key is on the module file's list (AD4)."""
        return ident in self._order

    def add_key(self, ident: int) -> None:
        """Lists the key (Add Key, AD4): kept at Save with no actions."""
        if ident not in self._order:
            self._order.append(ident)
            self._save()

    def remove_key(self, ident: int) -> None:
        """Takes the key off the list (Delete, AD4)."""
        if ident in self._order or ident in self._group_of:
            self._order = [i for i in self._order if i != ident]
            self._group_of.pop(ident, None)
            self._save()


_STORE = KeyboardLayoutStore()


def keyboard_store() -> KeyboardLayoutStore:
    return _STORE


def _on_pending(what: str, guid: str) -> None:
    ours = not guid or ids.guid_key(guid) == ids.guid_key(GUID)
    if what in ("discarded", "replaced") and ours:
        _STORE.load()


@ta.QmlElement
class KeyboardLayoutModel(ControlLayoutModel):
    """Rows for the Keyboard page: group headers, one parent per key, and
    its actions in the current mode."""

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

    # A property notified by a base-class signal crashes when QML builds
    # the type (PySide), so this model's own signal follows groupsChanged.
    keyGroupsChanged = QtCore.Signal()
    stampChanged = QtCore.Signal()
    # A key was pressed and the page should show its row
    # (D-05-FOLLOW-ALL-PAGES): its parent key.
    followInput = QtCore.Signal(str)

    def __init__(self, parent: ta.OQO = None) -> None:
        # Live tint: keys by liveIndex, and the stamp ControlTree watches.
        self._live = LiveInputs()
        self._stamp = 0
        super().__init__(parent)
        # The keys the Keyboard input module passes (its claim).
        from gremlin.modules.runtime import InputModuleRuntime

        InputModuleRuntime().key_event.connect(self._on_key)
        self.groupsChanged.connect(self.keyGroupsChanged)
        store.add_pending_listener(self._pending_changed)
        self.destroyed.connect(
            lambda *_: store.remove_pending_listener(self._pending_changed)
        )
        self._rebuild()

    # -- hooks ---------------------------------------------------------------

    def _make_store(self) -> KeyboardLayoutStore:
        return _STORE

    def _device_guid(self) -> uuid.UUID:
        return GUID

    def _identifier(self, kind: InputType, input_id: int) -> Hashable:
        return int(input_id)

    def _emit_store_changed(self) -> None:
        # The store already handed its change to the unsaved layouts (the
        # title's "*"); nothing else reads the Keyboard's layout.
        return None

    def _type_order(self) -> tuple[InputType, ...]:
        return (InputType.Keyboard,)

    def _matches(self, item: LayoutItem, search: str, type_filter: str) -> bool:
        if not search:
            return True
        hay = " ".join((item.system_name, item.second_name, item.group or "")).lower()
        return search.lower() in hay

    def _counts(self, items: list) -> tuple[int, int, int]:
        return len(items), 0, 0

    def _row(self, **fields: object) -> dict:
        row = {**ROW_DEFAULTS, **EXTRA_DEFAULTS, **fields}
        if row["rowKind"] == "group":
            row["subtitle"] = _keys_text(int(row["childCount"]))
        return row

    def _parent_subtitle(self, item: LayoutItem, extra: list[dict]) -> str:
        # The binding's Note under the key's name (05 S43, D-05-S43-BOTHROWS).
        return item_note(self._mode_item(item))

    def _parent_fields(self, item: LayoutItem, extra: list[dict]) -> dict:
        return {"liveIndex": self._live.index(int(item.id), "button")}

    # Live tint and follow (05 S131, D-05-FOLLOW-ALL-PAGES).

    def _on_key(self, event: Any) -> None:  # noqa: ANN401
        ident = key_id_of(getattr(event, "identifier", None))
        if ident is None or not self._live.known(ident):
            return
        was = self._live.value_of(ident)
        value = 1.0 if event.is_pressed else 0.0
        self._live.set(ident, "button", value)
        self._stamp += 1
        self.stampChanged.emit()
        if follows("button", value, was, bool(getattr(event, "synthetic", False))):
            self.followInput.emit(parent_key(InputType.Keyboard, ident))

    @QtCore.Property(int, notify=stampChanged)
    def stamp(self) -> int:
        return self._stamp

    @QtCore.Slot(int, result=str)
    def kindAt(self, index: int) -> str:
        return self._live.kind_at(index)

    @QtCore.Slot(int, result=float)
    def valueAt(self, index: int) -> float:
        return self._live.value_at(index)

    def _can_remove(self, item: LayoutItem) -> bool:
        """Delete only where it does something (S75): this mode's actions,
        or a key with no actions in any mode."""
        mine = self._mode_item(item)
        if mine is None:
            # Only on the list (AD4): Delete takes it off. A key another
            # mode has isn't this mode's to delete.
            return not self._key_items(item)
        if mine.action_sequences:
            return True
        return not any(i.action_sequences for i in self._key_items(item))

    def _delete_parent(self, item: LayoutItem) -> list[dict]:
        profile = self._profile()
        mine = self._mode_item(item)
        links: list[dict] = []
        if profile is not None and mine is not None:
            snap = self._snapshot(mine)
            key = self._input_key(mine)
            profile.drop_inputs(GUID, [mine])
            if snap is not None:
                links = [{"op": "input", "key": key, "before": snap, "after": None}]
            else:
                links = [{"op": "key", "key": key, "before": True, "after": False}]
        # The row goes when nothing is left of the key (S75): off the list
        # too, in the same Undo step (AD4).
        if not self._key_items(item):
            _STORE.remove_key(cast(KeyItem, item).identifier)
        return links

    def _play_link(self, entry: dict, forward: bool) -> None:
        if entry.get("op") != "key":
            return
        profile = self._profile()
        if profile is None:
            return
        device, kind, code, mode = entry["key"]
        want = entry["after"] if forward else entry["before"]
        found = profile.get_input_item(device, kind, code, mode, False)
        if want and found is None:
            profile.get_input_item(device, kind, code, mode, True)
        elif not want and found is not None and not found.action_sequences:
            profile.drop_inputs(device, [found])

    # -- the profile view: the profile knows a key by its code ---------------

    def _profile_item(self, item: LayoutItem) -> KeyItem:
        return replace(item, id=item.code)  # type: ignore[type-var]

    def _key_items(self, item: LayoutItem) -> list[InputItem]:
        profile = self._profile()
        if profile is None:
            return []
        code = tuple(cast(KeyItem, item).code)
        return [
            i
            for i in profile.inputs.get(GUID, [])
            if tuple(cast(Any, i.input_id)) == code
        ]

    def _mode_item(self, item: LayoutItem) -> InputItem | None:
        profile = self._profile()
        if profile is None:
            return None
        return profile.get_input_item(
            GUID,
            InputType.Keyboard,
            cast(KeyItem, item).code,
            self._mode,
            False,
        )

    def _real_item(self, item: LayoutItem) -> InputItem | None:
        return self._mode_item(item)

    def _spec(self, key: str) -> tuple | None:
        item = self._item_for(key)
        profile = self._profile()
        if item is None or profile is None:
            return None
        view = self._profile_item(item)
        real = profile.get_input_item(
            GUID, InputType.Keyboard, view.id, self._mode, False
        )
        return profile, view, real

    def _child_rows(self, item: LayoutItem) -> list[dict]:
        rows: list[dict] = []
        real = self._mode_item(item)
        key = parent_key(item.type, item.id)
        group = group_key(item.group)
        for index, label, dest in sequences_for_item(real):
            rows.append(
                self._row(
                    rowKind="child",
                    key=f"child:button:{item.id}:{index}",
                    title=label or "Action",
                    subtitle=dest or "",
                    parentKey=key,
                    groupKey=group,
                    groupName=item.group or "",
                    systemName=item.system_name,
                    sequenceIndex=index,
                )
            )
        return rows

    def _pending_changed(self, what: str, guid: str) -> None:
        if what not in ("discarded", "replaced"):
            return
        if guid and ids.guid_key(guid) != ids.guid_key(GUID):
            return
        # The module listener read the file again already.
        self._on_reloaded()

    # -- slots ---------------------------------------------------------------

    @QtCore.Slot(list, str, result=str)
    def addKey(self, data: list, mode: str) -> str:
        """Adds the pressed key to the mode being viewed (S73), one Undo
        step. Returns its row key for the page to select ("" nothing)."""
        if not data:
            return ""
        code = tuple(getattr(data[0], "identifier", data[0]))
        profile = self._profile()
        if profile is None or len(code) < 2:
            return ""
        mode = str(mode or self._mode)
        ident = key_id(code[0], bool(code[1]))
        missing = (
            profile.get_input_item(GUID, InputType.Keyboard, code, mode, False) is None
        )
        if missing or not _STORE.listed(ident):

            def fn() -> list[dict]:
                # On the module file's list: kept at Save with no actions.
                _STORE.add_key(ident)
                if not missing:
                    return []
                profile.get_input_item(GUID, InputType.Keyboard, code, mode, True)
                return [
                    {
                        "op": "key",
                        "key": (GUID, InputType.Keyboard, code, mode),
                        "before": False,
                        "after": True,
                    }
                ]

            if not self._apply(fn, f"Add Key {key_name(code)}"):
                return ""
        return key_row(code)

    @QtCore.Slot(str, result=bool)
    def canDelete(self, key: str) -> bool:
        item = self._item_for(key)
        return item is not None and self._can_remove(item)

    @QtCore.Property(list, notify=keyGroupsChanged)
    def groups(self) -> list:
        counts: dict[str, int] = {}
        for item in self._layout.ordered():
            counts[item.group or ""] = counts.get(item.group or "", 0) + 1
        rows = [
            {"name": "", "title": "Ungrouped", "summary": _keys_text(counts.get("", 0))}
        ]
        for name in self._layout.group_names():
            rows.append(
                {
                    "name": name,
                    "title": name,
                    "summary": _keys_text(counts.get(name, 0)),
                }
            )
        return rows


def _keys_text(count: int) -> str:
    if count <= 0:
        return "Empty"
    return "1 key" if count == 1 else f"{count} keys"


store.add_pending_listener(_on_pending)
