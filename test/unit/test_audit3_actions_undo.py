# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Reference, Merge Axis and Dual Axis Deadzone in the action pane, and
Logical Device Undo (audit 3).

The pane edits copies, unfinished actions too, so Cancel changes nothing; a
Reference placeholder picked in the pane can't leave the profile unloadable;
the pick lists show the action being edited; a Logical Device Undo step
plays whole or not at all, and puts a Map to Logical Device link back where
it was.
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
from gremlin.profile import Profile, VirtualAxisButton
from gremlin.types import InputType

_STICK = uuid.UUID("55555555-6666-7777-8888-999999999999")
_APPS: list[QtCore.QCoreApplication] = []
_KEEP: list[QtCore.QObject] = []


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


def _create(name: str, kind: InputType = InputType.JoystickAxis) -> Any:  # noqa: ANN401
    return plugin_manager.PluginManager().create_instance(name, kind)


def _vjoy(out: int, kind: InputType = InputType.JoystickAxis) -> Any:  # noqa: ANN401
    action = _create("Map to vJoy", kind)
    action.vjoy_device_id = 1
    action.vjoy_input_id = out
    action.vjoy_input_type = kind
    return action


def _merge(first: int = 1, second: int = 2) -> Any:  # noqa: ANN401
    merge = _create("Merge Axis")
    for axis, number in ((merge.axis_in1, first), (merge.axis_in2, second)):
        axis.device_guid = _STICK
        axis.input_id = number
        axis.input_type = InputType.JoystickAxis
    return merge


def _get(profile: Profile, *args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
    """An input of the profile (Any: tests know it is there)."""
    return profile.get_input_item(*args, **kwargs)


def _reload(profile: Profile, tmp_path: Path) -> Profile:
    path = tmp_path / "profile.xml"
    profile.to_xml(path)
    back = Profile()
    back.from_xml(path)
    return back


def _logical_model(kind: InputType = InputType.JoystickAxis) -> Any:  # noqa: ANN401
    from gremlin.ui.logical_layout import LogicalLayoutModel

    LogicalDevice().create(kind)
    return LogicalLayoutModel()


def _row(profile: Profile, kind: InputType = InputType.JoystickAxis) -> Any:  # noqa: ANN401
    return _get(profile,
        LogicalDevice().device_guid, kind, 1, "Default", create_if_missing=True
    )


def _logical_item(profile: Profile) -> Any:  # noqa: ANN401
    return _get(profile,
        LogicalDevice().device_guid, InputType.JoystickAxis, 1, "Default"
    )


def _kids(item: Any) -> list:  # noqa: ANN401
    return item.action_sequences[0].root_action.get_actions()[0]


def _action_model(model: Any, data: Any) -> Any:  # noqa: ANN401
    """The pane's model for this draft action (as the pane's QML gets it)."""
    from gremlin.ui.profile import InputItemBindingModel

    binding = InputItemBindingModel(
        model._pane_shadow.action_sequences[0], model._pane_model
    )
    for action_model in binding._action_models.values():
        if action_model.action_data is data:
            return action_model
    raise AssertionError("no model for that action")


def _values(selection: Any) -> list[str]:  # noqa: ANN401
    return list(selection._values)


# --- Item 1: Reference placeholder, then Cancel


def test_reference_picked_in_the_pane_then_cancel_keeps_the_profile_loadable(
    profile: Profile, tmp_path: Path
) -> None:
    model = _logical_model()
    row = _row(profile)
    root = row.add_item_binding().root_action
    vjoy = _vjoy(1)
    root.insert_action(vjoy, "children")
    placeholder = _create("Reference")
    root.insert_action(placeholder, "children")

    model.beginPane("parent:axis:1", 0)
    draft = _kids(model._pane_shadow)[1]
    assert draft is not placeholder  # the pane edits a copy
    reference = _action_model(model, draft)
    reference.referenceAction(_values(reference.actions)[0])
    model.discardPane()
    model.endPane()  # Cancel

    assert _kids(row)[1] is placeholder
    assert profile.library.has_action(placeholder.id)  # was deleted
    assert model.beginPane("parent:axis:1", 0) >= 0  # used to raise
    model.endPane()
    back = _reload(profile, tmp_path)  # used to write an unloadable file
    item = _logical_item(back)
    assert [a.tag for a in _kids(item)] == ["map-to-vjoy"]
    model.deleteLater()


def test_reference_picked_in_the_pane_then_ok_replaces_the_placeholder(
    profile: Profile, tmp_path: Path
) -> None:
    model = _logical_model()
    row = _row(profile)
    root = row.add_item_binding().root_action
    root.insert_action(_vjoy(1), "children")
    placeholder = _create("Reference")
    root.insert_action(placeholder, "children")
    merge = _merge()
    other = _get(profile,
        _STICK, InputType.JoystickAxis, 4, "Default", create_if_missing=True
    )
    other.add_item_binding().root_action.insert_action(merge, "children")

    model.beginPane("parent:axis:1", 0)
    reference = _action_model(model, _kids(model._pane_shadow)[1])
    reference.referenceAction(str(merge.id))
    model.commitPane()
    model.endPane()

    assert _kids(row)[1] is merge
    assert not profile.library.has_action(placeholder.id)
    back = _reload(profile, tmp_path)
    item = _logical_item(back)
    assert [a.tag for a in _kids(item)] == ["map-to-vjoy", "merge-axis"]
    model.deleteLater()


def test_a_save_drops_a_child_missing_from_the_library(
    profile: Profile, tmp_path: Path
) -> None:
    item = _get(profile,
        _STICK, InputType.JoystickAxis, 1, "Default", create_if_missing=True
    )
    root = item.add_item_binding().root_action
    root.insert_action(_vjoy(1), "children")
    gone = _vjoy(2)
    root.insert_action(gone, "children")
    profile.library.delete_action(gone.id)
    back = _reload(profile, tmp_path)  # used to fail: root listed it
    again = _get(back, _STICK, InputType.JoystickAxis, 1, "Default")
    assert len(_kids(again)) == 1


def test_cancel_leaves_an_unfinished_merge_axis_as_it_was(profile: Profile) -> None:
    model = _logical_model()
    merge = _create("Merge Axis")
    _row(profile).add_item_binding().root_action.insert_action(merge, "children")

    model.beginPane("parent:axis:1", 0)
    draft = _kids(model._pane_shadow)[0]
    assert draft is not merge  # was shared
    draft.axis_in1.device_guid = _STICK
    draft.axis_in1.input_id = 3
    draft.axis_in1.input_type = InputType.JoystickAxis
    model.discardPane()
    model.endPane()

    assert merge.axis_in1.input_id is None
    model.deleteLater()


def test_ok_writes_an_edit_to_an_unfinished_merge_axis(
    profile: Profile, tmp_path: Path
) -> None:
    model = _logical_model()
    merge = _create("Merge Axis")
    row = _row(profile)
    row.add_item_binding().root_action.insert_action(merge, "children")

    model.beginPane("parent:axis:1", 0)
    draft = _kids(model._pane_shadow)[0]
    draft.axis_in1.device_guid = _STICK
    draft.axis_in1.input_id = 3
    draft.axis_in1.input_type = InputType.JoystickAxis
    assert model.paneDirty()  # still unfinished, but changed
    model.commitPane()
    model.endPane()

    assert _kids(row)[0].axis_in1.input_id == 3
    model.deleteLater()


# --- Item 2: pick lists


def test_merge_axis_list_shows_the_one_being_edited(profile: Profile) -> None:
    model = _logical_model()
    merge = _merge()
    _row(profile).add_item_binding().root_action.insert_action(merge, "children")

    model.beginPane("parent:axis:1", 0)
    draft = _kids(model._pane_shadow)[0]
    editor = _action_model(model, draft)
    values = _values(editor.mergeActionList)
    assert str(draft.id) in values  # was missing: the combo showed another
    assert str(merge.id) not in values  # the copy stands in for it
    assert editor.mergeAction == str(draft.id)
    model.endPane()
    model.deleteLater()


def test_new_merge_axis_is_selected_and_listed(profile: Profile) -> None:
    model = _logical_model()
    _row(profile).add_item_binding().root_action.insert_action(_merge(), "children")

    model.beginPane("parent:axis:1", 0)
    editor = _action_model(model, _kids(model._pane_shadow)[0])
    editor.newMergeAxis()
    fresh = _kids(model._pane_shadow)[0]
    assert fresh.label == "Merge Axis 2" or fresh.label.startswith("Merge Axis")
    assert fresh.axis_in1.input_id is None  # the new one, not the old copy
    editor = _action_model(model, fresh)
    assert str(fresh.id) in _values(editor.mergeActionList)
    model.endPane()
    model.deleteLater()


def test_deadzone_list_shows_the_one_being_edited_and_new_is_selected(
    profile: Profile,
) -> None:
    model = _logical_model()
    deadzone = _create("Dual Axis Deadzone")
    _row(profile).add_item_binding().root_action.insert_action(deadzone, "children")

    model.beginPane("parent:axis:1", 0)
    draft = _kids(model._pane_shadow)[0]
    assert draft is not deadzone
    editor = _action_model(model, draft)
    assert str(draft.id) in _values(editor.deadzoneActionList)
    editor.newDeadzone()
    fresh = _kids(model._pane_shadow)[0]
    assert fresh is not draft
    assert str(fresh.id) in _values(_action_model(model, fresh).deadzoneActionList)
    model.endPane()
    model.deleteLater()


def test_reference_list_offers_the_pane_copy_not_the_original(
    profile: Profile,
) -> None:
    model = _logical_model()
    root = _row(profile).add_item_binding().root_action
    vjoy = _vjoy(1)
    root.insert_action(vjoy, "children")
    root.insert_action(_create("Reference"), "children")

    model.beginPane("parent:axis:1", 0)
    kids = _kids(model._pane_shadow)
    values = _values(_action_model(model, kids[1]).actions)
    assert str(kids[0].id) in values
    assert str(vjoy.id) not in values
    model.endPane()
    model.deleteLater()


# --- Item 32: Reference "duplicate"


def test_reference_duplicate_copies_every_nested_action(
    profile: Profile, tmp_path: Path
) -> None:
    model = _logical_model()
    merge = _merge()
    inner = _vjoy(5)
    merge.insert_action(inner, "children")
    other = _get(profile,
        _STICK, InputType.JoystickAxis, 4, "Default", create_if_missing=True
    )
    other.add_item_binding().root_action.insert_action(merge, "children")
    row = _row(profile)
    row.add_item_binding().root_action.insert_action(_create("Reference"), "children")

    model.beginPane("parent:axis:1", 0)
    reference = _action_model(model, _kids(model._pane_shadow)[0])
    reference.duplicateAction(str(merge.id))  # used to raise (deep copy)
    model.commitPane()
    model.endPane()

    copy = _kids(row)[0]
    assert copy is not merge and copy.id != merge.id
    copy_inner = copy.get_actions()[0][0]
    assert copy_inner.id != inner.id
    assert profile.library.has_action(copy.id)
    assert profile.library.has_action(copy_inner.id)
    back = _reload(profile, tmp_path)
    item = _logical_item(back)
    first = _get(back, _STICK, InputType.JoystickAxis, 4, "Default")
    assert _kids(item)[0].get_actions()[0][0] is not _kids(first)[0].get_actions()[0][0]
    model.deleteLater()


# --- Item 30: a Logical Device step plays whole or not at all


def test_logical_undo_with_a_damaged_input_copy_changes_nothing(
    profile: Profile,
) -> None:
    model = _logical_model()
    _row(profile).add_item_binding().root_action.insert_action(_vjoy(1), "children")
    model.deleteParents(["parent:axis:1"])
    assert LogicalDevice().axis_count == 0
    entry = model._undo[-1]
    entry["links"].append({
        "op": "input",
        "key": (_STICK, InputType.JoystickAxis, 9, "Default"),
        "before": {"input": "<input/>", "actions": []},
        "after": None,
    })
    model.undo()
    assert LogicalDevice().axis_count == 0  # was put back half way
    assert model._undo[-1] is entry and not model._redo
    model.deleteLater()


# --- Item 31: Undo puts a Map to Logical Device link back where it was


def _button_binding_on_axis(profile: Profile, number: int) -> Any:  # noqa: ANN401
    item = _get(profile,
        _STICK, InputType.JoystickAxis, number, "Default", create_if_missing=True
    )
    plain = item.add_item_binding()
    plain.root_action.insert_action(_vjoy(1), "children")
    binding = item.add_item_binding()
    binding.behavior = InputType.JoystickButton
    binding.virtual_button = VirtualAxisButton(0.25, 0.75)
    return item, binding


def _link(binding: Any, label: str) -> Any:  # noqa: ANN401
    link = _create("Map to Logical Device", InputType.JoystickButton)
    link.logical_input_type = InputType.JoystickButton
    link.logical_input_id = 1
    link.action_label = label
    binding.root_action.insert_action(link, "children")
    return link


def test_logical_undo_puts_a_link_back_into_its_button_binding(
    profile: Profile, tmp_path: Path
) -> None:
    model = _logical_model(InputType.JoystickButton)
    item, binding = _button_binding_on_axis(profile, 3)
    binding.root_action.insert_action(_vjoy(2, InputType.JoystickButton), "children")
    _link(binding, "Fire")
    model.deleteParents(["parent:button:1"])
    assert len(binding.root_action.get_actions()[0]) == 1
    model.undo()

    assert len(item.action_sequences) == 2  # was a third, axis binding
    kids = binding.root_action.get_actions()[0]
    assert [k.tag for k in kids] == ["map-to-vjoy", "map-to-logical-device"]
    assert kids[1].action_label == "Fire"
    _reload(profile, tmp_path)
    model.deleteLater()


def test_logical_undo_brings_back_a_removed_button_binding(
    profile: Profile, tmp_path: Path
) -> None:
    model = _logical_model(InputType.JoystickButton)
    item, binding = _button_binding_on_axis(profile, 3)
    _link(binding, "Fire")
    model.deleteParents(["parent:button:1"])
    assert len(item.action_sequences) == 1  # the binding went with its link
    model.undo()

    assert len(item.action_sequences) == 2
    back = item.action_sequences[1]
    assert back.behavior == InputType.JoystickButton  # was the axis behaviour
    assert back.virtual_button.lower_limit == 0.25
    assert back.virtual_button.upper_limit == 0.75
    kids = back.root_action.get_actions()[0]
    assert [k.tag for k in kids] == ["map-to-logical-device"]
    assert kids[0].behavior_type == InputType.JoystickButton
    model.redo()
    assert len(item.action_sequences) == 1
    model.undo()
    reloaded = _reload(profile, tmp_path)
    again = _get(reloaded, _STICK, InputType.JoystickAxis, 3, "Default")
    assert again.action_sequences[1].behavior == InputType.JoystickButton
    model.deleteLater()


# --- Round 2: a shared original after OK, "+" on a shared action, and the
# Configuration page pane


def _live_editor(item: Any, data: Any) -> Any:  # noqa: ANN401
    """The editor's model for an action on a real input (no pane draft)."""
    from gremlin.ui.profile import InputItemBindingModel, InputItemModel

    owner = InputItemModel(item, 0, None)
    binding = InputItemBindingModel(item.action_sequences[0], owner)
    _KEEP.extend([owner, binding])  # alive while the test uses them
    for action_model in binding._action_models.values():
        if action_model.action_data is data:
            return action_model
    raise AssertionError("no model for that action")


def _catalog(profile: Profile, hw: int = 1) -> Any:  # noqa: ANN401
    """The Configuration page model, its pane opened on stick axis hw."""
    from gremlin.ui.binding_catalog import BindingCatalogModel

    model = BindingCatalogModel()

    def spec(device_index: int) -> tuple:
        real = _get(profile, _STICK, InputType.JoystickAxis, hw, "Default")
        return profile, _STICK, InputType.JoystickAxis, hw, "Default", real

    model._control_spec = spec
    return model


def test_after_ok_the_pick_list_shows_a_shared_original(profile: Profile) -> None:
    model = _logical_model()
    merge = _merge()
    row = _row(profile)
    row.add_item_binding().root_action.insert_action(merge, "children")
    other = _get(profile,
        _STICK, InputType.JoystickAxis, 4, "Default", create_if_missing=True
    )
    other.add_item_binding().root_action.insert_action(merge, "children")

    model.beginPane("parent:axis:1", 0)
    _kids(model._pane_shadow)[0].label = "edited"
    model.commitPane()
    model.endPane()
    now = _kids(row)[0]
    assert now is not merge and _kids(other)[0] is merge

    values = _values(_live_editor(row, now).mergeActionList)
    assert str(now.id) in values
    assert str(merge.id) in values  # was hidden: axis 4 still uses it
    model.deleteLater()


def test_new_merge_axis_leaves_a_shared_one_finished(
    profile: Profile, tmp_path: Path
) -> None:
    merge = _merge(1, 2)
    item = _get(profile,
        _STICK, InputType.JoystickAxis, 1, "Default", create_if_missing=True
    )
    item.add_item_binding().root_action.insert_action(merge, "children")
    other = _get(profile,
        _STICK, InputType.JoystickAxis, 4, "Default", create_if_missing=True
    )
    other.add_item_binding().root_action.insert_action(merge, "children")

    _live_editor(item, merge).newMergeAxis()
    assert _kids(item)[0] is not merge
    assert merge.axis_in1.input_id == 1  # was cleared: axis 4 still uses it
    back = _reload(profile, tmp_path)
    again = _get(back, _STICK, InputType.JoystickAxis, 4, "Default")
    assert [a.tag for a in _kids(again)] == ["merge-axis"]  # was dropped


def test_new_merge_axis_still_clears_an_unshared_one(profile: Profile) -> None:
    merge = _merge(1, 2)
    item = _get(profile,
        _STICK, InputType.JoystickAxis, 1, "Default", create_if_missing=True
    )
    item.add_item_binding().root_action.insert_action(merge, "children")

    _live_editor(item, merge).newMergeAxis()
    assert merge.axis_in1.input_id is None


def test_new_deadzone_leaves_a_shared_one_as_it_was(profile: Profile) -> None:
    deadzone = _create("Dual Axis Deadzone")
    deadzone.axis1.device_guid = _STICK
    deadzone.axis1.input_id = 1
    deadzone.axis1.input_type = InputType.JoystickAxis
    item = _get(profile,
        _STICK, InputType.JoystickAxis, 1, "Default", create_if_missing=True
    )
    item.add_item_binding().root_action.insert_action(deadzone, "children")
    other = _get(profile,
        _STICK, InputType.JoystickAxis, 4, "Default", create_if_missing=True
    )
    other.add_item_binding().root_action.insert_action(deadzone, "children")

    _live_editor(item, deadzone).newDeadzone()
    assert _kids(item)[0] is not deadzone
    assert deadzone.axis1.input_id == 1  # was cleared


def test_configuration_pane_reference_cancel_and_pick_list(
    profile: Profile, tmp_path: Path
) -> None:
    item = _get(profile,
        _STICK, InputType.JoystickAxis, 1, "Default", create_if_missing=True
    )
    root = item.add_item_binding().root_action
    root.insert_action(_vjoy(1), "children")
    placeholder = _create("Reference")
    root.insert_action(placeholder, "children")
    merge = _merge()
    root.insert_action(merge, "children")
    other = _get(profile,
        _STICK, InputType.JoystickAxis, 4, "Default", create_if_missing=True
    )
    other.add_item_binding().root_action.insert_action(merge, "children")
    model = _catalog(profile)

    # Reference picked in the pane, then Cancel: nothing changes.
    model.beginPane(0, 0)
    reference = _action_model(model, _kids(model._pane_shadow)[1])
    reference.referenceAction(_values(reference.actions)[0])
    model.discardPane()
    model.endPane()
    assert _kids(item)[1] is placeholder
    assert profile.library.has_action(placeholder.id)

    # The pane lists its copy, not the original; after OK the original
    # (still used by axis 4) is listed again.
    model.beginPane(0, 0)
    draft = _kids(model._pane_shadow)[2]
    values = _values(_action_model(model, draft).mergeActionList)
    assert str(draft.id) in values and str(merge.id) not in values
    draft.label = "edited"
    model.commitPane()
    model.endPane()
    now = _kids(item)[2]
    assert now is not merge
    values = _values(_live_editor(item, now).mergeActionList)
    assert str(now.id) in values and str(merge.id) in values
    back = _reload(profile, tmp_path)  # loadable, the placeholder left out
    again = _get(back, _STICK, InputType.JoystickAxis, 1, "Default")
    assert [a.tag for a in _kids(again)] == ["map-to-vjoy", "merge-axis"]
    model.deleteLater()
