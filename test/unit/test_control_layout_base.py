# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
"""ControlLayoutModel (gremlin/ui/control_layout.py) with a stand-in store:
the base gives any control page Undo, groups, order and the action pane
through its hooks, with no Logical Device in sight."""

from __future__ import annotations

import sys
import uuid
from collections.abc import Hashable, Iterator

sys.path.append(".")

import pytest

from gremlin import shared_state
from gremlin.common import InputType
from gremlin.profile import Profile
from gremlin.ui.control_layout import ControlLayoutModel, LayoutItem

_GUID = uuid.UUID("0b5e0b5e-0000-4000-8000-00000000c0de")


class _Item:
    def __init__(self, kind: InputType, number: int, address: str) -> None:
        self.type = kind
        self.id = number
        self.address = address
        self.group: str | None = ""
        self.second_name = ""

    @property
    def identifier(self) -> Hashable:
        return (self.type, self.id)

    @property
    def system_name(self) -> str:
        return self.address

    @property
    def label(self) -> str:
        return self.second_name or self.address

    @property
    def row_title(self) -> str:
        return f"{self.address}   {self.second_name}".rstrip()

    @property
    def choice_label(self) -> str:
        return self.label


class _Store:
    """The LogicalDevice-shaped API the base reads, over plain lists."""

    def __init__(self) -> None:
        self.items = [
            _Item(InputType.JoystickButton, 1, "/b"),
            _Item(InputType.JoystickButton, 2, "/a"),
            _Item(InputType.JoystickAxis, 1, "/fader"),
        ]
        self.groups: list[str] = []

    def memento(self) -> tuple:
        return (
            tuple(self.groups),
            tuple(
                (i.type, i.id, i.address, i.group, i.second_name) for i in self.items
            ),
        )

    def restore(self, memo: tuple) -> None:
        groups, rows = memo
        self.groups = list(groups)
        self.items = []
        for kind, number, address, group, name in rows:
            item = _Item(kind, number, address)
            item.group, item.second_name = group, name
            self.items.append(item)

    def group_names(self) -> list[str]:
        return list(self.groups)

    def ordered(self) -> list[_Item]:
        return list(self.items)

    def exists(self, ident: Hashable) -> bool:
        return any(i.identifier == ident for i in self.items)

    def __getitem__(self, ident: Hashable) -> _Item:
        return next(i for i in self.items if i.identifier == ident)

    def ensure_group(self, name: str) -> str:
        if name and name not in self.groups:
            self.groups.append(name)
        return name

    def rename_group(self, old: str, new: str) -> None:
        self.groups[self.groups.index(old)] = new
        for item in self.items:
            if item.group == old:
                item.group = new

    def delete_group(self, name: str) -> None:
        self.groups.remove(name)
        for item in self.items:
            if item.group == name:
                item.group = ""

    def place(
        self, ident: Hashable, group: str | None, before: Hashable | None = None
    ) -> None:
        item = self[ident]
        self.ensure_group(group or "")
        item.group = group or ""
        self.items.remove(item)
        index = len(self.items)
        if before is not None:
            index = next(n for n, i in enumerate(self.items) if i.identifier == before)
        self.items.insert(index, item)

    def move_group_before(self, name: str, before: str | None) -> None:
        self.groups.remove(name)
        index = self.groups.index(before) if before else len(self.groups)
        self.groups.insert(index, name)

    def sort_within(self, key_name: str) -> None:
        self.items.sort(key=lambda i: i.address if key_name == "system" else i.label)

    def sort_groups(self) -> None:
        self.groups.sort()

    def set_user_label(self, ident: Hashable, text: str) -> None:
        self[ident].second_name = text

    def delete(self, ident: Hashable) -> None:
        self.items.remove(self[ident])


class _Model(ControlLayoutModel):
    def __init__(self) -> None:
        self.changes = 0
        super().__init__()
        self._rebuild()

    def _make_store(self) -> _Store:
        return _Store()

    def _device_guid(self) -> uuid.UUID:
        return _GUID

    def _identifier(self, kind: InputType, input_id: int) -> Hashable:
        return (kind, input_id)

    def _emit_store_changed(self) -> None:
        self.changes += 1

    def _parent_subtitle(self, item: LayoutItem, extra: list[dict]) -> str:
        return "settings line"

    def _sort_system_label(self) -> str:
        return "Sort by Address"


@pytest.fixture
def model(qapp: object) -> Iterator[_Model]:
    old = shared_state.current_profile
    shared_state.current_profile = Profile()
    made = _Model()
    yield made
    made.endPane()
    made.deleteLater()
    shared_state.current_profile = old


def _rows(model: _Model) -> list[tuple[str, str, str]]:
    return [(r["rowKind"], r["key"], r["subtitle"]) for r in model._rows]


def test_rows_come_from_the_hooks(model: _Model) -> None:
    rows = _rows(model)
    assert rows[0] == ("group", "group:", "2 buttons · 1 axis")
    assert ("parent", "parent:button:1", "settings line") in rows
    # Buttons before axes, as Logical.
    keys = [key for _kind, key, _sub in rows]
    assert keys.index("parent:button:2") < keys.index("parent:axis:1")
    assert model.parentCount == 3


def test_groups_order_and_undo(model: _Model) -> None:
    model.addGroup("Deck")
    model.setSelection(["parent:button:2", "group:"])
    assert model.selectionCount == 1
    model.moveSelected("Deck")
    assert [g["name"] for g in model.groups] == ["", "Deck"]
    assert model._layout[(InputType.JoystickButton, 2)].group == "Deck"
    assert model.lastChange == "Last change: Move to Deck"
    model.sortBySystem()
    assert model.undoTip == "Undo Sort by Address"
    model.undo()
    model.undo()
    assert model._layout[(InputType.JoystickButton, 2)].group == ""
    assert model.undone == "Undone: Move to Deck"
    model.redo()
    assert model._layout[(InputType.JoystickButton, 2)].group == "Deck"
    assert model.changes > 0
    model.renameGroup("Deck", "Desk")
    model.removeGroup("Desk")
    assert model._layout[(InputType.JoystickButton, 2)].group == ""


def test_user_name_and_find(model: _Model) -> None:
    model.setUserName("parent:axis:1", "Volume")
    assert model._layout[(InputType.JoystickAxis, 1)].second_name == "Volume"
    model.setFilter("volume", "all", False, False, False)
    assert model.parentCount == 1
    model.setFilter("", "button", False, False, False)
    assert model.parentCount == 2


def test_delete_parent_is_one_undo_step(model: _Model) -> None:
    model.deleteParents(["parent:button:1"])
    assert not model._layout.exists((InputType.JoystickButton, 1))
    model.undo()
    assert model._layout.exists((InputType.JoystickButton, 1))


def test_pane_writes_to_the_hooked_device(model: _Model) -> None:
    profile = shared_state.current_profile
    assert profile is not None
    model.beginNewAction("parent:button:1")
    assert model.paneModel is not None
    assert model._pane_shadow is not None
    model._pane_shadow.add_item_binding()
    assert model.paneDirty()
    model.commitPane()
    real = profile.get_input_item(
        _GUID, InputType.JoystickButton, 1, "Default", create_if_missing=False
    )
    assert real is not None and len(real.action_sequences) == 1
    assert model.lastChange == "Last change: Edit actions of /b"
    # The action shows as a child row under its parent.
    assert any(kind == "child" for kind, _key, _sub in _rows(model))
    model.endPane()
    model.undo()
    # Undo puts the input's copy back (Library.restore): read it again.
    real = profile.get_input_item(
        _GUID, InputType.JoystickButton, 1, "Default", create_if_missing=False
    )
    assert real is None or len(real.action_sequences) == 0


def test_an_empty_page_has_no_rows_so_its_message_shows(model: _Model) -> None:
    # 01 S143: with no inputs and no groups the list is empty, so the page's
    # "nothing here yet" text shows (an empty Ungrouped header hid it).
    model._layout.items.clear()
    model._rebuild()
    assert model.rowCount() == 0
    model._layout.groups.append("Deck")
    model._rebuild()
    assert [r["key"] for r in model._rows] == ["group:", "group:Deck"]
