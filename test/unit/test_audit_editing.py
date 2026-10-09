# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Configuration page and Logical Device fixes from the code audit (AU-10,
11, 12, 13, 28, 29, 30, 33)."""

from __future__ import annotations

import sys
import uuid
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

sys.path.append(".")

import pytest
from PySide6 import QtCore

from gremlin import plugin_manager, shared_state
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


def _vjoy(out: int) -> Any:  # noqa: ANN401
    action = plugin_manager.PluginManager().create_instance(
        "Map to vJoy", InputType.JoystickButton
    )
    action.vjoy_device_id = 1
    action.vjoy_input_id = out
    action.vjoy_input_type = InputType.JoystickButton
    return action


def _draft_root(model: Any) -> Any:  # noqa: ANN401
    return model._pane_shadow.action_sequences[0].root_action


def _first(model: Any) -> Any:  # noqa: ANN401
    return _draft_root(model).get_actions()[0][0]


def _outs(item: Any) -> list[int]:  # noqa: ANN401
    if item is None:
        return []
    return [
        b.root_action.get_actions()[0][0].vjoy_input_id for b in item.action_sequences
    ]


@pytest.fixture
def catalog() -> Iterator[tuple[Any, Profile, dict]]:
    from gremlin.ui.binding_catalog import BindingCatalogModel

    profile = Profile()
    shared_state.current_profile = profile
    profile.modes.add_mode("Combat")
    item = profile.get_input_item(
        _STICK, InputType.JoystickButton, 1, "Default", create_if_missing=True
    )
    for out in (1, 2):
        item.add_item_binding().root_action.insert_action(_vjoy(out), "children")
    model = BindingCatalogModel()
    shown = {"mode": "Default"}

    def spec(_index: int) -> tuple:
        mode = shown["mode"]
        real = profile.get_input_item(_STICK, InputType.JoystickButton, 1, mode)
        return profile, _STICK, InputType.JoystickButton, 1, mode, real

    model._control_spec = spec
    yield model, profile, shown
    model.endPane()
    shared_state.current_profile = None


def _input(profile: Profile, mode: str = "Default") -> Any:  # noqa: ANN401
    return profile.get_input_item(_STICK, InputType.JoystickButton, 1, mode)


def test_ok_after_a_mode_change_stays_on_its_input_and_undoes(
    catalog: tuple[Any, Profile, dict],
) -> None:
    model, profile, shown = catalog
    model.beginPane(0, -1)
    _first(model).vjoy_input_id = 7
    shown["mode"] = "Combat"  # the toolbar's mode changed with the pane open
    model.commitPane()
    model.endPane()
    assert _outs(_input(profile)) == [7, 2]
    assert _input(profile, "Combat") is None
    model.undo()
    assert _outs(_input(profile)) == [1, 2]


def test_steps_follow_a_mode_rename_and_go_with_a_deleted_mode(
    catalog: tuple[Any, Profile, dict],
) -> None:
    model, profile, _shown = catalog
    before = model._snapshot(0)
    _input(profile).remove_item_binding(_input(profile).action_sequences[0])
    model._step(0, before)
    assert model.canUndo
    signal.modesChanged.emit()  # a mode added: the steps stay
    assert model.canUndo
    signal.modeRenamed.emit("Default", "Main")
    assert model._undo[0]["key"][3] == "Main"
    signal.modeDeleted.emit("Main")
    assert not model.canUndo


def test_the_list_delete_waits_while_the_pane_edits_that_input(
    catalog: tuple[Any, Profile, dict],
) -> None:
    model, profile, _shown = catalog
    # A claimed device with button 1 on row 0, so removeSequence reaches the
    # delete (without one it returns False whatever the pane does).
    model._claimed._device = SimpleNamespace(device_guid=SimpleNamespace(uuid=_STICK))
    model._claimed._rows = [
        {"kind": "button", "hwId": 1, "deviceIndex": 0, "name": "Button 1"}
    ]
    model.beginPane(0, 1)
    assert model.removeSequence(0, 0) is False
    assert _outs(_input(profile)) == [1, 2]
    model.endPane()
    assert model.removeSequence(0, 0) is True  # the pane closed: it deletes
    assert _outs(_input(profile)) == [2]


def test_removing_every_action_in_the_pane_then_ok_clears_the_input(
    catalog: tuple[Any, Profile, dict],
) -> None:
    model, profile, _shown = catalog
    model.beginPane(0, -1)
    shadow = model._pane_shadow
    for binding in list(shadow.action_sequences):
        shadow.remove_item_binding(binding)
    assert model.paneDirty()
    model.commitPane()
    model.endPane()
    assert _outs(_input(profile)) == []
    model.undo()
    assert _outs(_input(profile)) == [1, 2]


@pytest.fixture
def logical() -> Iterator[tuple[Any, Profile]]:
    from gremlin.ui.logical_layout import LogicalLayoutModel

    LogicalDevice().load_dict({"controls": [], "groups": []})
    profile = Profile()
    shared_state.current_profile = profile
    LogicalDevice().create(InputType.JoystickButton)
    model = LogicalLayoutModel()
    yield model, profile
    model.endPane()
    model.deleteLater()
    shared_state.current_profile = None


def _logical_input(profile: Profile) -> Any:  # noqa: ANN401
    return profile.get_input_item(
        LogicalDevice().device_guid, InputType.JoystickButton, 1, "Default"
    )


def test_logical_edit_undoes_and_the_profile_still_loads(
    logical: tuple[Any, Profile], tmp_path: Path
) -> None:
    model, profile = logical
    model.beginNewAction("parent:button:1")
    _draft_root(model).insert_action(_vjoy(3), "children")
    model.commitPane()
    model.endPane()
    model.beginPane("parent:button:1", 0)
    _first(model).vjoy_input_id = 5
    model.commitPane()
    model.endPane()
    assert _outs(_logical_input(profile)) == [5]
    model.undo()
    assert _outs(_logical_input(profile)) == [3]
    model.redo()
    assert _outs(_logical_input(profile)) == [5]
    path = tmp_path / "l.xml"
    profile.to_xml(path)
    Profile().from_xml(str(path))  # loads


def test_logical_layout_steps_stay_when_another_profile_loads(
    logical: tuple[Any, Profile],
) -> None:
    """06 S83 (D-04-LD-FILE): the Logical Device is shared by every profile,
    so its page's steps stay when another profile loads; a step that only
    changed the old profile's actions goes."""
    model, _profile = logical
    key = "parent:button:1"
    model.setUserName(key, "Trigger")
    model.beginNewAction(key)
    _draft_root(model).insert_action(_vjoy(3), "children")
    model.commitPane()
    model.endPane()
    assert len(model._undo) == 2
    shared_state.current_profile = Profile()
    signal.profileChanged.emit()
    # The rename stays; the action step (old profile only) is dropped.
    assert model.canUndo
    assert len(model._undo) == 1
    model.undo()
    assert LogicalDevice().button(1).second_name == ""
    assert not model.canUndo


def test_a_logical_change_to_nothing_is_no_step(logical: tuple[Any, Profile]) -> None:
    model, _profile = logical
    key = "parent:button:1"
    model.setUserName(key, "Trigger")
    steps = len(model._undo)
    model.setUserName(key, "Trigger")
    assert len(model._undo) == steps
