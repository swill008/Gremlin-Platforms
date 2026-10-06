# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""A mode renamed or deleted: what names a mode follows (audit 2, group C).

The Configuration page's open action and its Undo steps, the Logical
Device's, the running profile's mode list, Change Mode lists (in place: a
running Cycle holds them) and script mode settings.
"""

from __future__ import annotations

import sys
import uuid
from collections.abc import Iterator
from typing import Any

sys.path.append(".")

import pytest
from PySide6 import QtCore

from gremlin import error, plugin_manager, shared_state
from gremlin.logical_device import LogicalDevice
from gremlin.profile import Profile
from gremlin.signal import signal
from gremlin.types import InputType

_STICK = uuid.UUID("55555555-6666-7777-8888-999999999999")
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
    p.modes.add_mode("Combat")
    shared_state.current_profile = p
    yield p
    shared_state.current_profile = None


def _vjoy(out: int) -> Any:  # noqa: ANN401
    action = plugin_manager.PluginManager().create_instance(
        "Map to vJoy", InputType.JoystickButton
    )
    action.vjoy_device_id = 1
    action.vjoy_input_id = out
    action.vjoy_input_type = InputType.JoystickButton
    return action


def _catalog(profile: Profile, shown: dict) -> Any:  # noqa: ANN401
    from gremlin.ui.binding_catalog import BindingCatalogModel

    model = BindingCatalogModel()

    def spec(_index: int) -> tuple:
        mode = shown["mode"]
        real = profile.get_input_item(_STICK, InputType.JoystickButton, 1, mode)
        return profile, _STICK, InputType.JoystickButton, 1, mode, real

    model._control_spec = spec
    return model


def test_ok_after_the_panes_mode_is_renamed_writes_to_the_new_name(
    profile: Profile,
) -> None:
    shown = {"mode": "Combat"}
    model = _catalog(profile, shown)
    model.beginPane(0, -1)  # a new input in Combat
    model._pane_shadow.action_sequences[0].root_action.insert_action(
        _vjoy(5), "children"
    )
    profile.modes.rename_mode("Combat", "Air")
    signal.modeRenamed.emit("Combat", "Air")
    shown["mode"] = "Air"
    assert model.paneMode == "Air"
    model.commitPane()
    model.endPane()
    assert profile.get_input_item(_STICK, InputType.JoystickButton, 1, "Air")
    assert profile.get_input_item(_STICK, InputType.JoystickButton, 1, "Combat") is None
    model.undo()
    assert profile.get_input_item(_STICK, InputType.JoystickButton, 1, "Air") is None


def test_the_pane_of_a_deleted_mode_closes(profile: Profile) -> None:
    model = _catalog(profile, {"mode": "Combat"})
    lost: list[int] = []
    model.paneLost.connect(lambda: lost.append(1))
    model.beginPane(0, -1)
    profile.modes.delete_mode("Combat")
    signal.modeDeleted.emit("Combat")
    assert lost == [1] and model._pane_shadow is None
    assert model.commitPane() == -1  # nothing to write


def test_logical_ok_goes_to_the_panes_own_mode(profile: Profile) -> None:
    from gremlin.ui.logical_layout import LogicalLayoutModel

    LogicalDevice().create(InputType.JoystickButton)
    model = LogicalLayoutModel()
    model.beginNewAction("parent:button:1")  # in Default
    model._pane_shadow.action_sequences[0].root_action.insert_action(
        _vjoy(3), "children"
    )
    model.setMode("Combat")  # the toolbar's mode changed
    model.commitPane()
    model.endPane()
    guid = LogicalDevice().device_guid
    assert profile.get_input_item(guid, InputType.JoystickButton, 1, "Default")
    assert profile.get_input_item(guid, InputType.JoystickButton, 1, "Combat") is None
    assert model.canUndo
    signal.modeDeleted.emit("Combat")
    assert not model.canUndo
    model.deleteLater()


def test_change_mode_lists_are_renamed_in_place(profile: Profile) -> None:
    item = profile.get_input_item(
        _STICK, InputType.JoystickButton, 1, "Default", create_if_missing=True
    )
    change = plugin_manager.PluginManager().create_instance(
        "Change Mode", InputType.JoystickButton
    )
    change.target_modes = ["Combat"]
    held = change._target_modes  # a running Cycle holds this list
    item.add_item_binding().root_action.insert_action(change, "children")
    profile.modes.rename_mode("Combat", "Fight")
    assert held == ["Fight"]


def test_a_script_mode_setting_follows_a_rename(profile: Profile) -> None:
    from gremlin.user_script import ModeVariable

    script = type("S", (), {})()
    variable = ModeVariable("mode", "", False)
    variable.value = "Combat"
    script.variables = {"mode": variable}
    profile.scripts._scripts.append(script)
    profile.modes.rename_mode("Combat", "Fight")
    assert variable.value == "Fight"


def test_the_running_mode_list_follows(profile: Profile) -> None:
    from gremlin.event_handler import EventHandler

    handler = EventHandler()
    handler.known_modes = {"Default", "Combat", "Other"}
    handler.rename_mode("Combat", "Fight")
    handler.drop_mode("Other")
    assert handler.known_modes == {"Default", "Fight"}
    handler.known_modes = set()


def test_nothing_is_put_into_a_deleted_mode(profile: Profile) -> None:
    item = profile.get_input_item(
        _STICK, InputType.JoystickButton, 1, "Combat", create_if_missing=True
    )
    item.add_item_binding().root_action.insert_action(_vjoy(2), "children")
    snapshot = profile.input_snapshot(item)
    profile.modes.delete_mode("Combat")
    with pytest.raises(error.ProfileError):
        profile.put_input(_STICK, InputType.JoystickButton, 1, "Combat", snapshot)
