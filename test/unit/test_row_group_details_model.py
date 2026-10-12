# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
"""Group details and Row details roles of the shared control layout model
(gremlin/ui/control_layout.py), batch L: what ControlTree's group line and
row details draw on all four list pages (Device Bindings, Keyboard, Logical
Device, OSC). Counted in the shown mode; Binding output not found is the same rule
as the red ⚠ (D-05-CANT-SEND, output.cant_send_action_texts).

Spec: 05 Group details / Row details (batch L contract).
"""

from __future__ import annotations

import uuid
from collections.abc import Hashable, Iterator
from pathlib import Path
from typing import Any, cast

import pytest

import dill
from gremlin import shared_state
from gremlin.modules import output
from gremlin.profile import Profile
from gremlin.types import InputType
from gremlin.ui.control_layout import ControlLayoutModel

B = InputType.JoystickButton
A = InputType.JoystickAxis
_GUID = uuid.UUID("0b5e0b5e-0000-4000-8000-00000000d0e7")


class _Item:
    def __init__(self, kind: InputType, number: int, group: str = "") -> None:
        self.type = kind
        self.id = number
        self.group = group
        self.second_name = ""

    @property
    def identifier(self) -> Hashable:
        return (self.type, self.id)

    @property
    def system_name(self) -> str:
        return f"{self.type.name} {self.id}"

    @property
    def label(self) -> str:
        return self.second_name or self.system_name

    @property
    def row_title(self) -> str:
        return self.label

    @property
    def choice_label(self) -> str:
        return self.label


class _Store:
    def __init__(self) -> None:
        self.items = [
            _Item(B, 1, "Stick"),
            _Item(B, 2, "Stick"),
            _Item(B, 3, "Stick"),
            _Item(A, 1, "Stick"),
        ]

    def memento(self) -> tuple:
        return tuple((i.type, i.id, i.group, i.second_name) for i in self.items)

    def group_names(self) -> list[str]:
        return ["Stick"]

    def ordered(self) -> list[_Item]:
        return list(self.items)

    def exists(self, ident: Hashable) -> bool:
        return any(i.identifier == ident for i in self.items)

    def __getitem__(self, ident: Hashable) -> _Item:
        return next(i for i in self.items if i.identifier == ident)


class _Model(ControlLayoutModel):
    def __init__(self) -> None:
        super().__init__()
        self._rebuild()

    def _make_store(self) -> _Store:
        return _Store()

    def _device_guid(self) -> uuid.UUID:
        return _GUID

    def _identifier(self, kind: InputType, input_id: int) -> Hashable:
        return (kind, input_id)

    def _emit_store_changed(self) -> None:
        pass


def _vjoy(vjoy_id: int, input_id: int) -> Any:  # noqa: ANN401
    from action_plugins.map_to_vjoy import MapToVjoyData

    action = MapToVjoyData(B)
    action.vjoy_device_id = vjoy_id
    action.vjoy_input_type = B
    action.vjoy_input_id = input_id
    return action


def _xbox(pad: int) -> Any:  # noqa: ANN401
    from action_plugins.map_to_xbox import MapToXboxData

    action = MapToXboxData(B)
    action.xbox_device_id = pad
    return action


def _condition(*actions: Any) -> Any:  # noqa: ANN401
    from action_plugins.condition import ConditionData

    action = ConditionData(B)
    action.true_actions.extend(actions)
    return action


def _bind(
    profile: Profile,
    kind: InputType,
    number: object,
    mode: str,
    *actions: Any,  # noqa: ANN401
    guid: uuid.UUID = _GUID,
) -> None:
    """One binding per action, each under the binding's own Root."""
    from gremlin.profile import reachable

    item = profile.get_input_item(guid, kind, cast(Any, number), mode, True)
    assert item is not None
    for action in actions:
        root = item.add_item_binding().root_action
        cast(Any, root).children.append(action)
        for each in reachable([action]):
            profile.library.add_action(each)


@pytest.fixture
def profile(qapp: object, monkeypatch: pytest.MonkeyPatch) -> Iterator[Profile]:
    # The ⚠ rule's owner: vJoy 3 can't be sent; everything else can.
    def texts(action: Any, memo: dict | None = None) -> list[str]:  # noqa: ANN401
        if getattr(action, "vjoy_device_id", 0) == 3:
            return ["vJoy 3 is not Found."]
        return []

    monkeypatch.setattr(output, "cant_send_action_texts", texts)
    made = Profile()
    made.modes.add_mode("Combat")
    made.modes.add_mode("Landing")
    old = shared_state.current_profile
    shared_state.current_profile = made
    yield made
    shared_state.current_profile = old


@pytest.fixture
def model(profile: Profile) -> Iterator[_Model]:
    # Button 1: Map to vJoy 1 and Map to Xbox 1 under a Condition, also bound
    # in Combat. Button 2: Map to vJoy 3 (can't be sent), custom name.
    # Button 3 and Axis 1: nothing in Default; Axis 1 bound in Landing.
    _bind(profile, B, 1, "Default", _vjoy(1, 1), _condition(_xbox(1)))
    _bind(profile, B, 1, "Combat", _vjoy(1, 2))
    _bind(profile, B, 2, "Default", _vjoy(3, 4))
    _bind(profile, A, 1, "Landing", _vjoy(1, 5))
    made = _Model()
    made._layout[(B, 2)].second_name = "Fire"
    made._rebuild()
    yield made
    made.deleteLater()


def _row(model: _Model, key: str) -> dict:
    return next(r for r in model._rows if r["key"] == key)


def test_every_row_has_the_new_roles(model: _Model) -> None:
    names = {bytes(n.data()).decode() for n in model.roleNames().values()}
    assert {
        "actionTypes",
        "outputNotFound",
        "otherModes",
        "hasCondition",
        "customName",
        "groupCounts",
        "groupNoBindings",
        "groupOutputNotFound",
        "groupOutputDevices",
        "groupActionTypes",
        "groupCustomNames",
        "groupOtherModes",
    } <= names


def test_row_details(model: _Model) -> None:
    one = _row(model, "parent:button:1")
    assert one["actionTypes"] == ["Map to vJoy", "Map to Xbox"]
    assert one["outputNotFound"] is False
    assert one["otherModes"] == ["Combat"]
    assert one["hasCondition"] is True
    assert one["customName"] is False
    two = _row(model, "parent:button:2")
    assert two["outputNotFound"] is True
    assert two["hasCondition"] is False
    assert two["customName"] is True
    assert two["otherModes"] == []
    axis = _row(model, "parent:axis:1")
    assert axis["bindingCount"] == 0
    assert axis["actionTypes"] == []
    assert axis["otherModes"] == ["Landing"]


def test_group_details(model: _Model) -> None:
    group = _row(model, "group:Stick")
    assert group["groupCounts"] == [
        {"type": "button", "controls": 3, "bindings": 3},
        {"type": "axis", "controls": 1, "bindings": 0},
    ]
    assert group["groupNoBindings"] == 2
    assert group["groupOutputNotFound"] == 1
    assert group["groupOutputDevices"] == ["vJoy 1", "Xbox 360 Controller", "vJoy 3"]
    assert group["groupActionTypes"] == [
        {"name": "Map to vJoy", "count": 2},
        {"name": "Map to Xbox", "count": 1},
    ]
    assert group["groupCustomNames"] == 1
    assert group["groupOtherModes"] == ["Combat", "Landing"]


def test_counts_follow_the_shown_mode(model: _Model) -> None:
    model.setMode("Combat")
    group = _row(model, "group:Stick")
    assert group["groupCounts"][0] == {"type": "button", "controls": 3, "bindings": 1}
    assert group["groupOutputNotFound"] == 0
    assert group["groupOutputDevices"] == ["vJoy 1"]
    one = _row(model, "parent:button:1")
    assert one["otherModes"] == ["Default"]
    assert one["hasCondition"] is False
    assert model._mode == "Combat"


def test_a_filter_counts_what_it_still_shows(model: _Model) -> None:
    model.setFilter("Fire", "all", False, False, False)
    group = _row(model, "group:Stick")
    assert group["groupCounts"] == [{"type": "button", "controls": 1, "bindings": 1}]
    assert group["groupCustomNames"] == 1
    assert group["groupOutputNotFound"] == 1


@pytest.fixture
def keyboard(
    profile: Profile, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[Any]:
    from gremlin.modules import store
    from gremlin.ui.keyboard_layout import KeyboardLayoutModel, keyboard_store

    folder = tmp_path / "modules"
    folder.mkdir()
    monkeypatch.setattr(store, "folder", lambda: folder)
    store.discard_pending("")
    keyboard_store().load()
    model = KeyboardLayoutModel()
    try:
        yield model
    finally:
        model.endPane()
        model.deleteLater()
        store.discard_pending("")
        keyboard_store().load()


def test_keyboard_page_reads_other_modes_through_its_own_items(
    profile: Profile,
    keyboard: Any,  # noqa: ANN401
) -> None:
    code = (30, False)
    for mode in ("Default", "Combat"):
        _bind(
            profile,
            InputType.Keyboard,
            code,
            mode,
            _vjoy(1, 1),
            guid=dill.UUID_Keyboard,
        )
    keyboard.setMode("Default")
    row = next(r for r in keyboard._rows if r["rowKind"] == "parent")
    assert row["otherModes"] == ["Combat"]
    assert row["actionTypes"] == ["Map to vJoy"]
    group = next(r for r in keyboard._rows if r["rowKind"] == "group")
    assert group["groupOtherModes"] == ["Combat"]
