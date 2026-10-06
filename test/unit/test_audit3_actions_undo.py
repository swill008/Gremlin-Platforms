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


def test_ok_on_a_shared_action_changes_it_for_both(profile: Profile) -> None:
    # 05 S62, decision A1: OK writes the edit into the one shared action.
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
    assert _kids(row)[0] is merge and _kids(other)[0] is merge  # still shared
    assert merge.label == "edited"

    values = _values(_live_editor(row, merge).mergeActionList)
    assert values.count(str(merge.id)) == 1
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

    # The pane lists its copy, not the original; OK writes the edit into
    # the original, which axis 4 still shares (decision A1).
    model.beginPane(0, 0)
    draft = _kids(model._pane_shadow)[2]
    values = _values(_action_model(model, draft).mergeActionList)
    assert str(draft.id) in values and str(merge.id) not in values
    draft.label = "edited"
    model.commitPane()
    model.endPane()
    assert _kids(item)[2] is merge and _kids(other)[0] is merge
    assert merge.label == "edited"
    values = _values(_live_editor(item, merge).mergeActionList)
    assert values.count(str(merge.id)) == 1
    back = _reload(profile, tmp_path)  # loadable, the placeholder left out
    again = _get(back, _STICK, InputType.JoystickAxis, 1, "Default")
    assert [a.tag for a in _kids(again)] == ["map-to-vjoy", "merge-axis"]
    four = _get(back, _STICK, InputType.JoystickAxis, 4, "Default")
    assert _kids(four)[0] is _kids(again)[1]  # one action after reload too
    model.deleteLater()


# --- Map 2: the profile's Library owns every action object -------------------


def _shared_merge(profile: Profile) -> tuple[Any, Any, Any]:  # noqa: ANN401
    """A Merge Axis shared by stick axes 1 and 4: (merge, axis 1, axis 4)."""
    merge = _merge()
    merge.label = "before"
    one = _get(profile,
        _STICK, InputType.JoystickAxis, 1, "Default", create_if_missing=True
    )
    one.add_item_binding().root_action.insert_action(merge, "children")
    four = _get(profile,
        _STICK, InputType.JoystickAxis, 4, "Default", create_if_missing=True
    )
    four.add_item_binding().root_action.insert_action(merge, "children")
    return merge, one, four


def test_undo_of_ok_on_a_shared_action_puts_both_back(profile: Profile) -> None:
    # 08 S40, decision A2: Undo restores the shared action for every input.
    merge, one, four = _shared_merge(profile)
    model = _catalog(profile)
    model.beginPane(0, 0)
    _kids(model._pane_shadow)[0].label = "after"
    model.commitPane()
    model.endPane()
    assert merge.label == "after" and _kids(four)[0] is merge

    model.undo()
    assert merge.label == "before"
    one = _get(profile, _STICK, InputType.JoystickAxis, 1, "Default")
    assert _kids(one)[0] is merge and _kids(four)[0] is merge
    model.redo()
    assert merge.label == "after"
    model.deleteLater()


def test_restore_puts_a_shared_actions_settings_back(profile: Profile) -> None:
    # History Restore of one input brings the shared action back for both.
    merge, one, four = _shared_merge(profile)
    key = (_STICK, InputType.JoystickAxis, 1, "Default")
    kept = profile.library.snapshot(one)
    merge.label = "changed since"
    profile.library.restore(key, kept)
    assert merge.label == "before"
    again = _get(profile, _STICK, InputType.JoystickAxis, 1, "Default")
    assert _kids(again)[0] is merge and _kids(four)[0] is merge


def test_a_picked_shared_action_is_a_copy_until_ok(profile: Profile) -> None:
    # 05 S63, decision A4: Cancel leaves the shared action as it was.
    merge, one, four = _shared_merge(profile)
    five = _get(profile,
        _STICK, InputType.JoystickAxis, 5, "Default", create_if_missing=True
    )
    five.add_item_binding()
    model = _catalog(profile, 5)
    model.beginPane(0, 0)
    pane = model._pane_shadow
    picked = profile.library.adopt(pane, merge)
    assert picked is not merge
    pane.action_sequences[0].root_action.insert_action(picked, "children")
    picked.label = "edited in the pane"
    model.discardPane()
    model.endPane()
    assert merge.label == "before"
    assert not profile.library.has_action(picked.id)

    model.beginPane(0, 0)
    pane = model._pane_shadow
    picked = profile.library.adopt(pane, merge)
    pane.action_sequences[0].root_action.insert_action(picked, "children")
    picked.label = "edited in the pane"
    model.commitPane()
    model.endPane()
    five = _get(profile, _STICK, InputType.JoystickAxis, 5, "Default")
    assert _kids(five)[0] is merge and merge.label == "edited in the pane"
    assert _kids(one)[0] is merge and _kids(four)[0] is merge
    model.deleteLater()


def test_reuse_in_a_pane_makes_a_copy(profile: Profile) -> None:
    # Add Action > Merge Axis reuses the shared one, as a copy until OK.
    merge, _one, _four = _shared_merge(profile)
    model = _catalog(profile, 5)
    model.beginPane(0, -1)
    reused = profile.library.create(
        "Merge Axis", InputType.JoystickAxis, item=model._pane_shadow
    )
    assert reused is not merge and reused is not None
    assert reused.label == "before"
    assert profile.library.create("Merge Axis", InputType.JoystickAxis) is merge
    model.endPane()
    assert not profile.library.has_action(reused.id)
    model.deleteLater()


def test_ok_after_the_input_changed_under_the_pane_writes_nothing(
    profile: Profile,
) -> None:
    # 05 Q8: History Restore changed the input after the pane opened; OK
    # must not write over it.
    item = _get(profile,
        _STICK, InputType.JoystickAxis, 1, "Default", create_if_missing=True
    )
    item.add_item_binding().root_action.insert_action(_vjoy(1), "children")
    kept = profile.library.snapshot(item)
    _kids(item)[0].vjoy_input_id = 2
    model = _catalog(profile)
    model.beginPane(0, 0)
    profile.library.restore((_STICK, InputType.JoystickAxis, 1, "Default"), kept)
    _kids(model._pane_shadow)[0].vjoy_input_id = 3
    assert model.commitPane() == -1
    item = _get(profile, _STICK, InputType.JoystickAxis, 1, "Default")
    assert _kids(item)[0].vjoy_input_id == 1
    model.endPane()
    model.deleteLater()


def test_a_library_works_out_in_use_from_its_own_profile(profile: Profile) -> None:
    # 04 R2: a library that isn't the open profile's kept nothing in use.
    other = Profile()
    item = other.get_input_item(
        _STICK, InputType.JoystickButton, 1, "Default", create_if_missing=True
    )
    root = item.add_item_binding().root_action
    assert other.library.has_action(root.id)  # 05 RB1: its own library
    assert not profile.library.has_action(root.id)
    other.library.release([root])
    assert other.library.has_action(root.id)  # an input uses it
    assert other.library.in_use() == {root.id}
    assert other.library.users(root) == [item]


def test_one_removal_rule_frees_what_only_a_dead_action_held(
    profile: Profile,
) -> None:
    # 04 R4: an action held only by a removed (unused) action goes too; one
    # an input uses stays, with what is inside it.
    dead = profile.library.create("Root", InputType.JoystickButton)
    child = _vjoy(1, InputType.JoystickButton)
    dead.insert_action(child, "children")
    profile.library.release([child])
    assert not profile.library.has_action(child.id)
    dead.remove_action(0, "children")
    profile.library.release([dead])

    item = _get(profile,
        _STICK, InputType.JoystickButton, 1, "Default", create_if_missing=True
    )
    root = item.add_item_binding().root_action
    kept = _vjoy(2, InputType.JoystickButton)
    root.insert_action(kept, "children")
    profile.library.release([root])
    assert profile.library.has_action(root.id)
    assert profile.library.has_action(kept.id)


def test_run_leaves_out_unfinished_actions_with_a_line_each(
    profile: Profile, caplog: pytest.LogCaptureFixture
) -> None:
    # 05 S99, Q3: an OK'd Reference placeholder or an unfinished Merge Axis
    # doesn't run; the log names the action and the input.
    from gremlin import base_classes

    item = _get(profile,
        _STICK, InputType.JoystickAxis, 1, "Default", create_if_missing=True
    )
    root = item.add_item_binding().root_action
    root.insert_action(_create("Reference"), "children")
    root.insert_action(_create("Merge Axis"), "children")
    vjoy = _vjoy(1)
    root.insert_action(vjoy, "children")
    with base_classes.building_for("Stick Axis 1 (Default)"):
        functor = root.functor(root)
    built = [type(f).__name__ for f in functor.functors["children"]]
    assert built == [vjoy.functor.__name__]
    lines = [r.getMessage() for r in caplog.records if "not finished" in r.getMessage()]
    assert len(lines) == 2
    assert all("on Stick Axis 1 (Default)" in line for line in lines)
