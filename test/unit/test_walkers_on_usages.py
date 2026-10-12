# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
"""The walkers built on gremlin.usages (batch Q): one input's uses
(item_usages), the depth-first action walk, the action's own sends versus its
macro steps and conditions (Usage.own), one broken action hiding nothing
else, and each action counted once per input."""

from __future__ import annotations

import logging
import sys
import uuid
from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

sys.path.append(".")

import pytest

from gremlin import macro, shared_state, usages
from gremlin.modules import output
from gremlin.profile import Profile
from gremlin.types import InputType

B = InputType.JoystickButton
_STICK = uuid.UUID("{4DCB3090-97EC-11EB-8003-444553540000}")


@pytest.fixture
def profile(monkeypatch: pytest.MonkeyPatch) -> Iterator[Profile]:

    # vJoy 9 is the one output that can't be sent.
    monkeypatch.setattr(
        output,
        "cant_send_text",
        lambda v, k, c: "vJoy 9 is not Found." if int(v) == 9 else None,
    )
    monkeypatch.setattr(output, "xbox_cant_send_text", lambda pad: None)
    made = Profile()
    made.modes.add_mode("Flight")
    made.modes.set_parent("Flight", "Default")
    monkeypatch.setattr(shared_state, "current_profile", made)
    yield made


def _vjoy(vjoy_id: int, control: int) -> Any:  # noqa: ANN401
    from action_plugins.map_to_vjoy import MapToVjoyData

    action = MapToVjoyData(B)
    action.vjoy_device_id = vjoy_id
    action.vjoy_input_type = B
    action.vjoy_input_id = control
    return action


def _bind(profile: Any, number: int, mode: str, *actions: Any) -> Any:  # noqa: ANN401
    """One binding holding these actions under its Root; the input item."""
    from action_plugins.root import RootData
    from gremlin.profile import InputItemBinding

    item = profile.get_input_item(_STICK, B, number, mode, True)
    root = RootData(B)
    root.children = list(actions)
    binding = InputItemBinding(item)
    binding.root_action = root
    binding.behavior = B
    item.action_sequences.append(binding)
    _add(profile, root)
    return item


def _add(profile: Any, root: Any) -> None:  # noqa: ANN401
    from gremlin.profile import reachable

    for action in reachable([root]):
        profile.library.add_action(action)


def _macro_with_vjoy_step(vjoy_id: int, control: int) -> Any:  # noqa: ANN401
    from action_plugins.macro import MacroData

    steps = MacroData()
    steps.actions = [macro.VJoyAction(vjoy_id, B, control, True)]
    return steps


def _sends(item: Any) -> list[tuple]:  # noqa: ANN401
    return [
        (ref.target, ref.usage.own)
        for ref in usages.item_usages(None, item)
        if ref.usage.role == "sends-output"
    ]


def test_macro_vjoy_steps_stay_out_of_vjoy_outputs_used(profile: Profile) -> None:
    from action_plugins.chain import ChainData

    chain = ChainData(B)
    chain.chain_sequences = [[_vjoy(1, 2)]]
    _bind(profile, 1, "Default", _vjoy(1, 1), _macro_with_vjoy_step(1, 3))
    _bind(profile, 2, "Default", chain)
    used = [(v.vjoy_id, v.input_id) for v in profile.vjoy_outputs_used("Default")]
    assert sorted(used) == [(1, 1), (1, 2)]


def test_own_send_versus_macro_step(profile: Profile) -> None:
    from gremlin.ui import input_pairing

    item = _bind(profile, 1, "Default", _vjoy(1, 1), _macro_with_vjoy_step(1, 3))
    assert _sends(item) == [
        (("vjoy", 1, B.value, 1), True),
        (("vjoy", 1, B.value, 3), False),
    ]
    mapped = input_pairing.map_refs(input_pairing.item_refs(item))
    assert [ref.target for ref in mapped] == [("vjoy", 1, B.value, 1)]


def test_condition_checks_are_not_the_actions_own(profile: Profile) -> None:
    from action_plugins.condition import ConditionData
    from action_plugins.condition import condition as ca

    checks = ConditionData(B)
    vjoy_check = ca.VJoyCondition()
    vjoy_check.start_on(2, B, 30)
    checks.conditions = [vjoy_check]
    checks.true_actions = [_vjoy(1, 1)]
    item = _bind(profile, 1, "Default", checks)
    found = {
        (ref.usage.role, ref.usage.own)
        for ref in usages.item_usages(None, item)
        if ref.target[0] == "vjoy"
    }
    assert found == {("checks-output", False), ("sends-output", True)}


def test_broken_references_hide_nothing_else(
    profile: Profile, caplog: pytest.LogCaptureFixture
) -> None:
    from action_plugins.description import DescriptionData

    class Broken(DescriptionData):
        def references(self) -> Any:  # noqa: ANN401
            raise RuntimeError("broken piece")

    usages._FAILED.discard("Broken")
    item = _bind(profile, 1, "Default", Broken(B), _vjoy(1, 1))
    with caplog.at_level(logging.ERROR, logger="system"):
        first = _sends(item)
        second = _sends(item)
    assert first == second == [(("vjoy", 1, B.value, 1), True)]
    logged = [r for r in caplog.records if "Broken.references()" in r.getMessage()]
    assert len(logged) == 1


def test_an_action_shared_by_two_bindings_is_one_use(profile: Profile) -> None:
    shared = _vjoy(9, 4)
    item = _bind(profile, 1, "Default", shared)
    from action_plugins.root import RootData
    from gremlin.profile import InputItemBinding

    root = RootData(B)
    root.children = [shared]
    binding = InputItemBinding(item)
    binding.root_action = root
    binding.behavior = B
    item.action_sequences.append(binding)
    _add(profile, root)
    assert _sends(item) == [(("vjoy", 9, B.value, 4), True)]
    # Each binding still reads the input.
    reads = [
        ref for ref in usages.item_usages(None, item) if ref.usage.role == "reads-input"
    ]
    assert len(reads) == 2


def test_input_scan_takes_cant_texts_from_the_uses(profile: Profile) -> None:
    from gremlin.ui.control_layout import input_scan

    item = _bind(profile, 1, "Default", _vjoy(9, 1), _macro_with_vjoy_step(9, 2))
    _bind(profile, 1, "Default", _vjoy(1, 1))
    scan = input_scan(item)
    assert scan.cant == {0: "vJoy 9 is not Found."}
    assert scan.not_found == 2
    assert scan.devices == ["vJoy 9", "vJoy 1"]


def test_item_usages_inherits_only_with_its_profile(profile: Profile) -> None:
    item = _bind(profile, 1, "Default", _vjoy(1, 1))
    with_profile = [r.usage.role for r in usages.item_usages(profile, item)]
    without = [r.usage.role for r in usages.item_usages(None, item)]
    assert "inherited" in with_profile
    assert "inherited" not in without
    _bind(profile, 1, "Flight", _vjoy(1, 2))
    again = [r.usage.role for r in usages.item_usages(profile, item)]
    assert "inherited" not in again
    assert list(usages.item_usages(profile, None)) == []


def test_walk_actions_depth_first_each_once() -> None:
    def node(name: str, *children: object) -> SimpleNamespace:
        return SimpleNamespace(name=name, get_actions=lambda: (list(children),))

    leaf = SimpleNamespace(name="leaf")  # no get_actions
    shared = node("shared")
    tree = node("root", node("a", node("a1"), shared), node("b", shared, leaf))
    names = [n.name for n in usages.walk_actions(tree)]
    assert names == ["root", "a", "a1", "shared", "b", "leaf"]
    assert usages.walk_actions(None) == []


def test_input_pairing_walk_actions_is_the_one_walk() -> None:
    from gremlin.ui import input_pairing

    assert input_pairing.walk_actions is usages.walk_actions


def test_xbox_maps_only_the_map_to_xbox_itself(profile: Profile) -> None:
    from action_plugins.map_to_xbox import MapToXboxData
    from gremlin.ui.xbox_maps import xbox_maps_for_item
    from vigem.xbox import XboxTarget

    xbox = MapToXboxData(B)
    xbox.xbox_device_id = 2
    xbox.xbox_target = XboxTarget.A
    item = _bind(profile, 1, "Default", xbox, _vjoy(1, 1))
    assert xbox_maps_for_item(item) == [(2, XboxTarget.A.value)]
