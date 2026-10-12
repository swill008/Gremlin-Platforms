# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Device Bindings page has Undo and Redo for what OK and Delete change.

A step keeps the input's actions before and after (as XML, the same way
History keeps them: Profile.input_snapshot / put_input). Undo puts the
"before" back, Redo the "after". Not while an action is open in the pane;
another profile drops the action steps, another device starts with none
(05 S127). The page's own model (HardwareLayoutModel) is used.
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
    from test.unit.hardware_page_helper import close, page_on

    profile = Profile()
    shared_state.current_profile = profile
    item = profile.get_input_item(
        _STICK, InputType.JoystickButton, 1, "Default", create_if_missing=True
    )
    _map(item, 3)
    model = page_on(_STICK)
    yield model, profile
    close(model)
    shared_state.current_profile = None


_KEY = "parent:button:1"


def test_a_delete_undoes_and_redoes(page: tuple[object, Profile]) -> None:
    model, profile = page
    # The row's Delete (right-click menu, S126).
    assert model.deleteAction(_KEY, 0)
    assert _targets(profile) == [] and model.canUndo
    model.undo()
    assert _targets(profile) == [3]
    assert model.canRedo
    model.redo()
    assert _targets(profile) == []


def test_ok_undoes_and_redoes(page: tuple[object, Profile]) -> None:
    model, profile = page
    model.beginPane(_KEY, -1)
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


def test_undo_waits_while_the_pane_is_open() -> None:
    # S36: the page offers Undo and Redo (keys and menu) only with no action
    # open in the pane (the model's canUndo is the step list itself).
    from pathlib import Path

    qml = (
        Path(__file__).resolve().parents[2] / "qml/DeviceBindingsPage.qml"
    ).read_text(encoding="utf-8")
    assert "_undoKeys: visible && !editorLocked && !actionOpen" in qml
    assert "enabled: _root._undoKeys && _layout.canUndo" in qml
    assert "enabled: _root._undoKeys && _layout.canRedo" in qml


def test_another_profile_starts_without_steps(page: tuple[object, Profile]) -> None:
    # S127 (was S37): a profile load drops what a step did to the old
    # profile's actions; layout steps stay (test_hardware_layout covers those).
    from gremlin.signal import signal

    model, profile = page
    assert model.deleteAction(_KEY, 0)
    assert model.canUndo
    signal.profileChanged.emit()
    assert not model.canUndo and not model.canRedo


def test_another_device_starts_without_steps(page: tuple[object, Profile]) -> None:
    # S127: switching device clears every step.
    model, profile = page
    assert model.deleteAction(_KEY, 0)
    model.setDevice("{99999999-2222-3333-4444-555555555555}", "")
    assert not model.canUndo and not model.canRedo
