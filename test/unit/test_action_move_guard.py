# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Moving actions in the tree (05 S144, D-05-UPSTREAM-B2, upstream 86ea050c).

- An action can't be moved into its own child: the old move removed it
  first, then put it inside the part of the tree it had just cut off, so
  the action and its children vanished.
- A move to a container that doesn't exist leaves the action where it was:
  the old move removed it before the insert failed.
"""

from __future__ import annotations

import sys

sys.path.append(".")

from collections.abc import Iterator

import pytest
from PySide6 import QtCore

from action_plugins.chain import ChainData
from action_plugins.description import DescriptionData
from action_plugins.root import RootData
from gremlin.base_classes import AbstractActionData
from gremlin.profile import InputItem, InputItemBinding, Profile
from gremlin.signal import signal
from gremlin.types import InputType
from gremlin.ui.profile import InputItemBindingModel

_app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
_made: list[InputItemBindingModel] = []


@pytest.fixture(autouse=True)
def _drop_models() -> Iterator[None]:
    yield
    while _made:
        model = _made.pop()
        for action_model in model._action_models.values():
            action_model.dispose()
        signal.inputItemChanged.disconnect(model._check_user_feedback)


def _tree() -> tuple[InputItemBindingModel, RootData, ChainData, ChainData]:
    """Root > Chain A > Chain B, plus a Description beside Chain A."""
    profile = Profile()
    item = InputItem(profile.library)
    binding = InputItemBinding(item)
    binding.root_action = RootData(InputType.JoystickButton)
    binding.behavior = InputType.JoystickButton
    root = binding.root_action
    chain_a = ChainData(InputType.JoystickButton)
    chain_b = ChainData(InputType.JoystickButton)
    other = DescriptionData(InputType.JoystickButton)
    for action in (root, chain_a, chain_b, other):
        profile.library.add_action(action)
    root.insert_action(chain_a, "children")
    root.insert_action(other, "children")
    chain_a.insert_action(chain_b, "0")
    model = InputItemBindingModel(binding)
    _made.append(model)
    return model, root, chain_a, chain_b


def _sidx(model: InputItemBindingModel, action: object) -> int:
    return next(
        m.sequence_index.index
        for m in model._action_models.values()
        if m.action_data is action
    )


def _shape(root: RootData) -> list[tuple[int, str, list]]:
    def walk(action: AbstractActionData) -> list[tuple[int, str, list]]:
        actions, containers = action.get_actions()
        return [(id(a), c, walk(a)) for a, c in zip(actions, containers)]

    return walk(root)


def test_moving_a_chain_into_its_own_child_is_refused() -> None:
    model, root, chain_a, chain_b = _tree()
    before = _shape(root)
    assert not model.can_move_action(_sidx(model, chain_a), _sidx(model, chain_b), "0")
    model.move_action(_sidx(model, chain_a), _sidx(model, chain_b), "0")
    assert _shape(root) == before
    assert chain_a in root.get_actions("children")[0]


def test_moving_a_chain_after_its_own_child_is_refused() -> None:
    model, root, chain_a, chain_b = _tree()
    before = _shape(root)
    model.move_action(_sidx(model, chain_a), _sidx(model, chain_b))
    assert _shape(root) == before


def test_moving_into_itself_is_refused() -> None:
    model, root, chain_a, _ = _tree()
    before = _shape(root)
    model.move_action(_sidx(model, chain_a), _sidx(model, chain_a), "0")
    assert _shape(root) == before


def test_drop_into_own_child_keeps_the_tree() -> None:
    model, root, chain_a, chain_b = _tree()
    before = _shape(root)
    action_model = model.get_action_model_by_sidx(_sidx(model, chain_a))
    # The part of dropAction that moves (the rest needs an input's model).
    action_model._append_drop_action(_sidx(model, chain_a), _sidx(model, chain_b), "0")
    assert _shape(root) == before


def test_move_to_a_missing_container_keeps_the_action() -> None:
    model, root, chain_a, chain_b = _tree()
    before = _shape(root)
    assert not model.can_move_action(_sidx(model, chain_b), _sidx(model, chain_a), "7")
    model.move_action(_sidx(model, chain_b), _sidx(model, chain_a), "7")
    assert _shape(root) == before
    assert chain_b in chain_a.get_actions("0")[0]


def test_a_valid_move_into_a_container_still_works() -> None:
    model, root, chain_a, chain_b = _tree()
    other = root.get_actions("children")[0][1]
    assert model.can_move_action(_sidx(model, other), _sidx(model, chain_b), "0")
    model.move_action(_sidx(model, other), _sidx(model, chain_b), "0")
    assert other in chain_b.get_actions("0")[0]
    assert other not in root.get_actions("children")[0]


def test_moving_a_child_out_of_its_parent_still_works() -> None:
    model, root, chain_a, chain_b = _tree()
    model.move_action(_sidx(model, chain_b), _sidx(model, chain_a))
    assert chain_b in root.get_actions("children")[0]
    assert chain_b not in chain_a.get_actions("0")[0]
