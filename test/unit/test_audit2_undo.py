# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Undo that can't break the profile (audit 2, group B).

Snapshots never fail on unfinished actions; Logical Device Undo keeps copies
(not live actions the library can drop or hand out again); Reuse and the
pick lists offer only actions an input uses; a shared action stays shared
after Undo; Redo of "Delete row" takes the row's actions away again.
"""

from __future__ import annotations

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
from gremlin.profile import Profile
from gremlin.types import DataCreationMode, InputType

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
    shared_state.current_profile = p
    yield p
    shared_state.current_profile = None


def _create(name: str, kind: InputType = InputType.JoystickButton) -> Any:  # noqa: ANN401
    return plugin_manager.PluginManager().create_instance(name, kind)


def _vjoy(out: int) -> Any:  # noqa: ANN401
    action = _create("Map to vJoy")
    action.vjoy_device_id = 1
    action.vjoy_input_id = out
    action.vjoy_input_type = InputType.JoystickButton
    return action


def _axis_input(profile: Profile) -> Any:  # noqa: ANN401
    return profile.get_input_item(
        _STICK, InputType.JoystickAxis, 1, "Default", create_if_missing=True
    )


def test_a_snapshot_of_an_unfinished_merge_axis_works(profile: Profile) -> None:
    item = _axis_input(profile)
    root = item.add_item_binding().root_action
    root.insert_action(_create("Merge Axis", InputType.JoystickAxis), "children")
    root.insert_action(_create("Description", InputType.JoystickAxis), "children")
    snapshot = profile.input_snapshot(item)  # used to raise
    profile.put_input(_STICK, InputType.JoystickAxis, 1, "Default", snapshot)
    back = profile.get_input_item(_STICK, InputType.JoystickAxis, 1, "Default")
    kids = back.action_sequences[0].root_action.get_actions()[0]
    assert [a.tag for a in kids] == ["description"]


def test_a_snapshot_with_a_reference_placeholder_reads_back(profile: Profile) -> None:
    item = profile.get_input_item(
        _STICK, InputType.JoystickButton, 1, "Default", create_if_missing=True
    )
    root = item.add_item_binding().root_action
    root.insert_action(_vjoy(3), "children")
    root.insert_action(_create("Reference"), "children")
    snapshot = profile.input_snapshot(item)
    profile.put_input(_STICK, InputType.JoystickButton, 1, "Default", snapshot)
    back = profile.get_input_item(_STICK, InputType.JoystickButton, 1, "Default")
    kids = back.action_sequences[0].root_action.get_actions()[0]
    assert [a.tag for a in kids] == ["map-to-vjoy"]


def test_a_shared_action_stays_shared_after_undo(profile: Profile) -> None:
    merge = _create("Merge Axis", InputType.JoystickAxis)
    # A finished one (an unfinished one is left out of a copy).
    merge.axis_in1.device_guid = _STICK
    merge.axis_in1.input_id = 1
    merge.axis_in2.device_guid = _STICK
    merge.axis_in2.input_id = 2
    one = _axis_input(profile)
    two = profile.get_input_item(
        _STICK, InputType.JoystickAxis, 2, "Default", create_if_missing=True
    )
    one.add_item_binding().root_action.insert_action(merge, "children")
    two.add_item_binding().root_action.insert_action(merge, "children")
    snapshot = profile.input_snapshot(one)
    profile.put_input(_STICK, InputType.JoystickAxis, 1, "Default", snapshot)
    back = profile.get_input_item(_STICK, InputType.JoystickAxis, 1, "Default")
    assert back.action_sequences[0].root_action.get_actions()[0][0] is merge


def test_reuse_offers_only_merge_axes_an_input_uses(profile: Profile) -> None:
    from action_plugins.merge_axis import MergeAxisData

    old = MergeAxisData.create(DataCreationMode.Create, InputType.JoystickAxis)
    profile.library.add_action(old)  # deleted: nothing uses it any more
    fresh = MergeAxisData.create(DataCreationMode.Reuse, InputType.JoystickAxis)
    assert fresh is not old


def _logical_model() -> Any:  # noqa: ANN401
    from gremlin.ui.logical_layout import LogicalLayoutModel

    LogicalDevice().create(InputType.JoystickButton)
    return LogicalLayoutModel()


def _logical_input(profile: Profile) -> Any:  # noqa: ANN401
    return profile.get_input_item(
        LogicalDevice().device_guid, InputType.JoystickButton, 1, "Default"
    )


def test_redo_of_delete_row_takes_its_actions_away(profile: Profile) -> None:
    model = _logical_model()
    item = profile.get_input_item(
        LogicalDevice().device_guid, InputType.JoystickButton, 1, "Default",
        create_if_missing=True,
    )
    item.add_item_binding().root_action.insert_action(_vjoy(4), "children")
    model.deleteParents(["parent:button:1"])
    assert _logical_input(profile) is None
    model.undo()
    assert _logical_input(profile) is not None
    model.redo()
    # Gone again: a new Button 1 must not inherit it.
    assert _logical_input(profile) is None
    LogicalDevice().create(InputType.JoystickButton)
    assert _logical_input(profile) is None
    model.deleteLater()


def test_logical_undo_after_the_library_dropped_an_action_still_saves(
    profile: Profile, tmp_path: Path
) -> None:
    model = _logical_model()
    model.beginNewAction("parent:button:1")
    model._pane_shadow.action_sequences[0].root_action.insert_action(
        _vjoy(3), "children"
    )
    model.commitPane()
    model.endPane()
    assert model.deleteAction("parent:button:1", 0)
    # The delete took the action out of the library; Undo brings a copy.
    assert not profile.actions_in_use()
    model.undo()
    path = tmp_path / "p.xml"
    profile.to_xml(path)
    Profile().from_xml(str(path))  # loads
    assert _logical_input(profile).action_sequences
    model.deleteLater()


def test_configuration_undo_that_cant_be_played_keeps_its_step(
    profile: Profile,
) -> None:
    from gremlin.ui.binding_catalog import BindingCatalogModel

    model = BindingCatalogModel()
    key = (_STICK, InputType.JoystickButton, 1, "Default")
    model._undo.append({
        "hid": 0, "key": key,
        "before": {"input": "<not xml", "actions": []}, "after": None,
    })
    model.undo()
    assert model._undo and not model._redo
    model.endPane()
