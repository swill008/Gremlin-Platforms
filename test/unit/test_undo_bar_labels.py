# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""01 S143: the Configuration page (binding catalog) and the Logical Device
page show the shared Undo / Redo bar with the last change beside it. Each
model names its Undo steps: lastChange is "Last change: X", undone is
"Undone: X" right after an Undo, and the tips say what Undo / Redo do.
A step with nothing to name leaves the text empty.
"""

from __future__ import annotations

import sys
import uuid
from collections.abc import Iterator

sys.path.append(".")

import pytest
from PySide6 import QtCore

from gremlin import plugin_manager, shared_state
from gremlin.logical_device import LogicalDevice
from gremlin.profile import Profile
from gremlin.types import InputType

_STICK = uuid.UUID("55555555-6666-7777-8888-999999999998")


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    yield app


def _map(item: object, out: int) -> None:
    action = plugin_manager.PluginManager().create_instance(
        "Map to vJoy", InputType.JoystickButton
    )
    action.vjoy_device_id = 1
    action.vjoy_input_id = out
    action.vjoy_input_type = InputType.JoystickButton
    item.add_item_binding().root_action.insert_action(action, "children")


@pytest.fixture
def catalog() -> Iterator[tuple[object, Profile]]:
    from gremlin.ui.binding_catalog import BindingCatalogModel

    profile = Profile()
    old = shared_state.current_profile
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
    # The page's name for the input (the claimed rows need a real device).
    model._step_name = lambda device_index: "Button 1"
    yield model, profile
    model.endPane()
    shared_state.current_profile = old


def test_catalog_ok_names_its_step(catalog: tuple[object, Profile]) -> None:
    model, _profile = catalog
    assert model.lastChange == "" and model.undone == ""
    model.beginPane(0, -1)
    shadow = model._pane_shadow
    shadow.action_sequences[0].root_action.get_actions()[0][0].vjoy_input_id = 8
    model.commitPane()
    model.endPane()
    assert model.lastChange == "Last change: Edit actions of Button 1"
    assert model.undoTip == "Undo Edit actions of Button 1"
    model.undo()
    assert model.undone == "Undone: Edit actions of Button 1"
    assert model.redoTip == "Redo Edit actions of Button 1"
    model.redo()
    assert model.undone == ""
    assert model.lastChange == "Last change: Edit actions of Button 1"


def test_catalog_delete_names_its_step(catalog: tuple[object, Profile]) -> None:
    model, profile = catalog
    item = profile.get_input_item(_STICK, InputType.JoystickButton, 1, "Default")
    before = model._snapshot(0)
    binding = item.action_sequences[0]
    item.remove_item_binding(binding)
    profile.library.release([binding.root_action])
    model._step(0, before, label="Delete action from Button 1")
    assert model.lastChange == "Last change: Delete action from Button 1"
    # A step with no name: no text.
    _map(item, 4)
    before = model._snapshot(0)
    binding = item.action_sequences[0]
    item.remove_item_binding(binding)
    profile.library.release([binding.root_action])
    model._step(0, before)
    assert model.lastChange == "" and model.undoTip == ""


@pytest.fixture
def logical() -> Iterator[object]:
    from gremlin.ui.logical_layout import LogicalLayoutModel

    LogicalDevice().reset()
    profile = Profile()
    old = shared_state.current_profile
    shared_state.current_profile = profile
    model = LogicalLayoutModel()
    yield model
    model.deleteLater()
    shared_state.current_profile = old
    LogicalDevice().reset()


def test_logical_steps_are_named(logical: object) -> None:
    model = logical
    assert model.lastChange == ""
    model.addMany("button", 3, "", "")
    assert model.lastChange == "Last change: Add 3 Buttons"
    model.deleteParents(["parent:button:2"])
    assert model.lastChange == "Last change: Delete Button 2"
    assert model.undoTip == "Undo Delete Button 2"
    model.undo()
    assert model.undone == "Undone: Delete Button 2"
    assert model.redoTip == "Redo Delete Button 2"
    assert model.lastChange == "Last change: Add 3 Buttons"
    model.redo()
    assert model.undone == ""
    model.deleteParents(["parent:button:1", "parent:button:3"])
    assert model.lastChange == "Last change: Delete 2 rows"
    model.addGroup("Throttle")
    assert model.lastChange == "Last change: New Group Throttle"
    model.removeGroup("Throttle")
    assert model.lastChange == "Last change: Delete Group Throttle"


def test_logical_parent_count_is_the_search_count(logical: object) -> None:
    model = logical
    model.addMany("button", 2, "", "")
    model.addMany("axis", 1, "", "")
    assert model.parentCount == 3
    model.setFilter("Axis", "all", False, False, False)
    assert model.parentCount == 1
