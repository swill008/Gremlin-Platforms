# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Action labels for Button Map chips: what each control does in a mode."""

from __future__ import annotations

import sys

sys.path.append(".")

import uuid
from types import SimpleNamespace

from gremlin.tree import TreeNode
from gremlin.types import InputType
from gremlin.ui import button_map_labels as labels

GUID = uuid.UUID("12345678-1234-1234-1234-123456789abc")


def _action(tag: str, children: list | None = None, **fields: object) -> object:
    action = SimpleNamespace(tag=tag, **fields)
    if children is not None:
        action.get_actions = lambda: ([*children],)
    return action


def _item(mode: str, kind: InputType, input_id: int, *actions: object) -> object:
    root = _action("root", list(actions))
    return SimpleNamespace(
        mode=mode,
        input_type=kind,
        input_id=input_id,
        action_sequences=[SimpleNamespace(root_action=root)],
    )


class _Modes:
    """Default, with Combat under it."""

    def __init__(self) -> None:
        self.top = TreeNode("")
        self.default = TreeNode("Default")
        self.top.add_child(self.default)
        self.combat = TreeNode("Combat")
        self.default.add_child(self.combat)

    def mode_list(self) -> list[TreeNode]:
        return [self.default, self.combat]

    def find_mode(self, name: str) -> TreeNode:
        return {"Default": self.default, "Combat": self.combat}[name]


def _key(name: str) -> object:
    return SimpleNamespace(name=name)


def _keys(*names: str) -> object:
    return _action("map-to-keyboard", keys=[_key(n) for n in names])


def _change(kind: str, targets: list[str]) -> object:
    return _action(
        "change-mode", change_type=SimpleNamespace(name=kind), target_modes=targets
    )


def _profile(*items: object) -> object:
    return SimpleNamespace(inputs={GUID: list(items)}, modes=_Modes())


BTN = InputType.JoystickButton


def test_texts_for_each_kind_of_action() -> None:
    profile = _profile(
        _item("Default", BTN, 1, _keys("Ctrl", "G")),
        _item("Default", BTN, 2, _action("description", description="Gear up")),
        _item("Default", BTN, 3, _change("Switch", ["Combat"])),
        _item("Default", BTN, 4, _change("Previous", [])),
        _item("Default", BTN, 5, _action("macro")),
        _item("Default", BTN, 6, _action("response-curve")),
        _item("Default", InputType.JoystickHat, 1, _action("map-to-mouse")),
    )
    got = labels.action_labels(profile, str(GUID), "Default")
    assert got == {
        "btn:1": "Ctrl+G",
        "btn:2": "Gear up",
        "btn:3": "→ Combat",
        "btn:4": "Previous mode",
        "btn:5": "Macro",
        "hat:1": "Mouse",
    }


def test_containers_give_the_text_of_what_they_hold() -> None:
    chain = _action("chain", [_action("map-to-keyboard", keys=[_key("F5")])])
    profile = _profile(_item("Default", BTN, 1, chain))
    assert labels.action_labels(profile, str(GUID), "Default") == {"btn:1": "F5"}


def test_description_first_or_with_the_rest() -> None:
    profile = _profile(
        _item(
            "Default", BTN, 1,
            _action("map-to-keyboard", keys=[_key("F5")]),
            _action("macro"),
            _action("description", description="Lights"),
        )
    )
    guid = str(GUID)
    assert labels.action_labels(profile, guid, "Default") == {"btn:1": "Lights"}
    assert labels.action_labels(profile, guid, "Default", False) == {"btn:1": "F5"}
    assert labels.action_labels(profile, guid, "Default", False, True) == {
        "btn:1": "F5 + Macro + Lights"
    }


def test_a_child_mode_inherits_unless_it_binds_the_control() -> None:
    profile = _profile(
        _item("Default", BTN, 1, _action("description", description="Gear")),
        _item("Default", BTN, 2, _action("description", description="Flaps")),
        _item("Combat", BTN, 2, _action("description", description="Fire")),
        # In Combat without actions: Default's binding still runs.
        _item("Combat", BTN, 1),
    )
    guid = str(GUID)
    default = labels.action_labels(profile, guid, "Default")
    assert default == {"btn:1": "Gear", "btn:2": "Flaps"}
    combat = labels.action_labels(profile, guid, "Combat")
    assert combat == {"btn:1": "Gear", "btn:2": "Fire"}


def test_other_devices_unknown_modes_and_no_profile() -> None:
    profile = _profile(_item("Default", BTN, 1, _action("macro")))
    assert labels.action_labels(profile, str(uuid.uuid4()), "Default") == {}
    assert labels.action_labels(profile, "not a guid", "Default") == {}
    assert labels.action_labels(profile, str(GUID), "Nowhere") == {}
    assert labels.action_labels(None, str(GUID), "Default") == {}


def test_mode_order_puts_parents_first() -> None:
    assert labels.mode_order(_profile()) == ["Default", "Combat"]
    assert labels.mode_order(None) == []
