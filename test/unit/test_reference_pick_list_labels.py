# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Reference's pick list (05 S60b): "[mode] device - input › action",
sorted with numbers by value, each action once, the pane's draft labelled;
one natural_key (gremlin.common) that keeps the Keyboard page's order; the
Share / Duplicate tooltips."""

from __future__ import annotations

import re
import sys
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

sys.path.append(".")

import pytest
from PySide6 import QtCore

from gremlin import plugin_manager, shared_state
from gremlin.logical_device import LogicalDevice
from gremlin.modules import ids
from gremlin.profile import Profile
from gremlin.types import InputType

_BUTTON = InputType.JoystickButton
_APPS: list[QtCore.QCoreApplication] = []


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


@pytest.fixture
def profile() -> Iterator[Profile]:
    LogicalDevice().reset()
    p = Profile()
    shared_state.current_profile = p
    yield p
    shared_state.current_profile = None
    LogicalDevice().reset()


def _create(name: str, kind: InputType = _BUTTON) -> Any:  # noqa: ANN401
    return plugin_manager.PluginManager().create_instance(name, kind)


def _vjoy(out: int, label: str) -> Any:  # noqa: ANN401
    action = _create("Map to vJoy")
    action.vjoy_device_id = 1
    action.vjoy_input_id = out
    action.vjoy_input_type = _BUTTON
    action.action_label = label
    return action


def _input(profile: Profile, device: uuid.UUID, kind: InputType, number: Any,  # noqa: ANN401
           mode: str = "Default") -> Any:  # noqa: ANN401
    return profile.get_input_item(device, kind, number, mode, create_if_missing=True)


def _bind(item: Any, action: Any) -> None:  # noqa: ANN401
    item.add_item_binding().root_action.insert_action(action, "children")


def _model_of(sequence: Any, data: Any, parent: Any = None) -> Any:  # noqa: ANN401
    from gremlin.ui.profile import InputItemBindingModel

    binding = InputItemBindingModel(sequence, parent)
    for action_model in binding._action_models.values():
        if action_model.action_data is data:
            return action_model
    raise AssertionError("no model for that action")


def test_labels_order_and_each_action_once(profile: Profile) -> None:
    profile.modes.add_mode("Second")
    logical = LogicalDevice().device_guid
    shared = _vjoy(1, "Shared")
    ten = _input(profile, logical, _BUTTON, 10)
    _bind(ten, _vjoy(2, "On ten"))
    _bind(ten, shared)
    _bind(_input(profile, logical, _BUTTON, 2), _vjoy(3, "On two"))
    _bind(_input(profile, logical, _BUTTON, 2, "Second"), shared)
    _bind(_input(profile, ids.KEYBOARD, InputType.Keyboard, (0x1E, False)),
          _vjoy(4, "On key"))
    placeholder = _create("Reference")
    holder = _input(profile, logical, _BUTTON, 30)
    _bind(holder, placeholder)

    labels = list(_model_of(holder.action_sequences[0], placeholder).actions._labels)
    assert labels == [
        "[Default] Keyboard - A › On key",
        "[Default] Logical Device - Button 2 › On two",
        "[Default] Logical Device - Button 10 › On ten",
        "[Default] Logical Device - Button 10 › Shared",
    ]


def test_a_pane_draft_action_gets_its_label(profile: Profile) -> None:
    from gremlin.ui.logical_layout import LogicalLayoutModel

    LogicalDevice().create(InputType.JoystickAxis)
    model = LogicalLayoutModel()
    item = _input(profile, LogicalDevice().device_guid, InputType.JoystickAxis, 1)
    root = item.add_item_binding().root_action
    vjoy = _create("Map to vJoy", InputType.JoystickAxis)
    vjoy.action_label = "Pane one"
    root.insert_action(vjoy, "children")
    root.insert_action(_create("Reference", InputType.JoystickAxis), "children")

    model.beginPane("parent:axis:1", 0)
    shadow = model._pane_shadow
    kids = shadow.action_sequences[0].root_action.get_actions()[0]
    actions = _model_of(shadow.action_sequences[0], kids[1], model._pane_model).actions
    assert list(actions._values) == [str(kids[0].id)]
    assert list(actions._labels) == ["[Default] Logical Device - X Axis › Pane one"]
    model.endPane()
    model.deleteLater()


def test_one_natural_key_and_the_keyboard_page_order_is_unchanged() -> None:
    import gremlin.logical_device as logical_device
    from gremlin import common
    from gremlin.ui import hardware_layout, keyboard_layout, osc_layout

    for module in (logical_device, hardware_layout, keyboard_layout, osc_layout):
        assert getattr(module, "natural_key", None) is common.natural_key
        assert not hasattr(module, "_natural_key")

    def old_keyboard_key(text: str) -> list:
        return [int(p) if p.isdigit() else p.casefold()
                for p in re.split(r"(\d+)", text)]

    names = ["F10", "F2", "f1", "Numpad 10", "Numpad 9", "A", "a", "Key 100",
             "Key 20", "Esc", "1", "10", "2", "Group B", "group a"]
    assert sorted(names, key=common.natural_key) == sorted(names, key=old_keyboard_key)
    assert sorted(["Button 10", "Button 2"], key=common.natural_key) == [
        "Button 2", "Button 10"]


def test_share_and_duplicate_tooltips() -> None:
    path = Path(__file__).parents[2] / "action_plugins/reference/ReferenceAction.qml"
    qml = path.read_text("utf-8")
    assert 'PointerTip { text: "Share this action" }' in qml
    assert 'PointerTip { text: "Duplicate this action" }' in qml
