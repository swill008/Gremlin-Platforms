# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Configuration page has Undo and Redo for what OK and Delete change.

A step keeps the input's actions before and after (as XML, the same way
History keeps them: Profile.input_snapshot / put_input). Undo puts the
"before" back, Redo the "after". Not while an action is open in the pane;
another device or profile starts with no steps.
"""

from __future__ import annotations

import sys
import uuid
from collections.abc import Iterator

sys.path.append(".")

import pytest
from PySide6 import QtCore

from gremlin import plugin_manager, shared_state
from gremlin.profile import Profile
from gremlin.types import InputType

_STICK = uuid.UUID("55555555-6666-7777-8888-999999999999")
_APPS: list[QtCore.QCoreApplication] = []


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


def _map(item: object, out: int) -> None:
    action = plugin_manager.PluginManager().create_instance(
        "Map to vJoy", InputType.JoystickButton
    )
    action.vjoy_device_id = 1
    action.vjoy_input_id = out
    action.vjoy_input_type = InputType.JoystickButton
    item.add_item_binding().root_action.insert_action(action, "children")


def _targets(profile: Profile) -> list[int]:
    item = profile.get_input_item(_STICK, InputType.JoystickButton, 1, "Default")
    if item is None:
        return []
    return [
        b.root_action.get_actions()[0][0].vjoy_input_id for b in item.action_sequences
    ]


@pytest.fixture
def page() -> Iterator[tuple[object, Profile]]:
    from gremlin.ui.binding_catalog import BindingCatalogModel

    profile = Profile()
    shared_state.current_profile = profile
    item = profile.get_input_item(
        _STICK, InputType.JoystickButton, 1, "Default", create_if_missing=True
    )
    _map(item, 3)
    model = BindingCatalogModel()

    def spec(device_index: int) -> tuple:
        real = profile.get_input_item(_STICK, InputType.JoystickButton, 1, "Default")
        return profile, _STICK, InputType.JoystickButton, 1, "Default", real

    model._control_spec = spec
    yield model, profile
    model.endPane()
    shared_state.current_profile = None


def test_a_delete_undoes_and_redoes(page: tuple[object, Profile]) -> None:
    model, profile = page
    item = profile.get_input_item(_STICK, InputType.JoystickButton, 1, "Default")
    before = model._snapshot(0)
    item.remove_item_binding(item.action_sequences[0])
    model._step(0, before)
    assert _targets(profile) == [] and model.canUndo
    model.undo()
    assert _targets(profile) == [3]
    assert model.canRedo
    model.redo()
    assert _targets(profile) == []


def test_ok_undoes_and_redoes(page: tuple[object, Profile]) -> None:
    model, profile = page
    model.beginPane(0, -1)
    shadow = model._pane_shadow
    shadow.action_sequences[0].root_action.get_actions()[0][0].vjoy_input_id = 8
    model.commitPane()
    assert _targets(profile) == [8]
    assert not model.canUndo  # the pane is still open
    model.endPane()
    assert model.canUndo
    model.undo()
    assert _targets(profile) == [3]
    model.redo()
    assert _targets(profile) == [8]
    # What was put back is all the profile keeps.
    assert set(profile.library._actions) == profile.actions_in_use()


def test_another_profile_starts_without_steps(page: tuple[object, Profile]) -> None:
    from gremlin.signal import signal

    model, profile = page
    item = profile.get_input_item(_STICK, InputType.JoystickButton, 1, "Default")
    before = model._snapshot(0)
    item.remove_item_binding(item.action_sequences[0])
    model._step(0, before)
    signal.profileChanged.emit()
    assert not model.canUndo and not model.canRedo
