# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Actions and their editors (3 Oct review, ACT16, ACT18, ACT22, ACT23, E2,
E3, E4, N21).

- A deleted action stayed in the profile's library, so Merge Axis 'Reuse'
  could offer it; Profile.remove_action was never called and could not
  work (ACT16).
- 'Reuse' renamed the shared Merge Axis back to its default name (ACT18).
- Merge Axis errors didn't show the value, a new one was called 'New Merge
  Axis 123' and 'Prefercenter' was shown as one word (ACT22).
- The editors' units, labels and ranges (ACT23, E2, E3, E4, N21).
"""

from __future__ import annotations

import sys

sys.path.append(".")

import pathlib
import uuid
from collections.abc import Iterator
from types import SimpleNamespace
from unittest import mock

import pytest
from PySide6 import QtCore

from action_plugins.description import DescriptionData
from action_plugins.merge_axis import MergeOperation
from action_plugins.root import RootData
from gremlin.profile import InputItem, InputItemBinding, Profile
from gremlin.types import InputType
from gremlin.ui.profile import InputItemBindingModel

_ROOT = pathlib.Path(__file__).parents[2]


def _binding_model() -> tuple[InputItemBindingModel, list]:
    profile = Profile()
    item = InputItem(profile.library)
    binding = InputItemBinding(item)
    binding.root_action = RootData(InputType.JoystickButton)
    binding.behavior = InputType.JoystickButton
    profile.library.add_action(binding.root_action)
    children = [DescriptionData(InputType.JoystickButton) for _ in range(2)]
    for child in children:
        profile.library.add_action(child)
        binding.root_action.insert_action(child, "children")
    return InputItemBindingModel(binding), children


def _sidx(model: InputItemBindingModel, action: object) -> int:
    return next(
        m.sequence_index.index for m in model._action_models.values()
        if m.action_data is action
    )


# ACT16 --------------------------------------------------------------------


def test_a_deleted_action_leaves_the_library() -> None:
    model, (first, second) = _binding_model()
    library = model.input_item_binding.library
    model.remove_action(_sidx(model, first))
    assert not library.has_action(first.id)
    assert library.has_action(second.id)


def test_a_moved_action_stays_in_the_library() -> None:
    model, (first, second) = _binding_model()
    library = model.input_item_binding.library
    model.move_action(_sidx(model, first), _sidx(model, second))
    assert library.has_action(first.id) and library.has_action(second.id)
    assert model.input_item_binding.root_action.get_actions()[0] == [second, first]


def test_an_action_used_elsewhere_stays_when_deleted_here() -> None:
    model, (first, _second) = _binding_model()
    library = model.input_item_binding.library
    profile = library._profile
    other = profile.get_input_item(
        uuid.uuid4(), InputType.JoystickButton, 2, "Default", True
    )
    other.add_item_binding().root_action.insert_action(first, "children")
    model.remove_action(_sidx(model, first))  # shared, as Merge Axis is
    assert library.has_action(first.id)


def test_an_action_only_a_dead_one_holds_leaves_the_library() -> None:
    # One removal rule (map 2): an action no input uses goes, even when a
    # deleted action (kept for Undo) still holds it.
    model, (first, _second) = _binding_model()
    library = model.input_item_binding.library
    dead = RootData(InputType.JoystickButton)
    library.add_action(dead)
    dead.insert_action(first, "children")
    model.remove_action(_sidx(model, first))
    assert not library.has_action(first.id)


def test_the_broken_profile_remove_action_is_gone() -> None:
    assert not hasattr(Profile, "remove_action")


# ACT22 --------------------------------------------------------------------


def test_merge_axis_error_names_the_value() -> None:
    from action_plugins.merge_axis import MergeOperation
    from gremlin.error import GremlinError

    with pytest.raises(GremlinError, match="'nonsense'"):
        MergeOperation.to_enum("nonsense")


def _operation_list() -> tuple[list[str], list[str]]:
    from action_plugins.merge_axis import MergeAxisModel

    with mock.patch("action_plugins.merge_axis.LabelValueSelectionModel") as made:
        MergeAxisModel.operationList.fget(SimpleNamespace())
    labels, values = made.call_args.args[:2]
    return list(labels), list(values)


def test_merge_operations_read_as_words() -> None:
    """05 S114: shown as words; the drop-down values are the stored names."""

    labels, values = _operation_list()
    assert "Prefer Center" in labels and "Maximum Deflection" in labels
    assert sorted(values) == sorted(MergeOperation.to_string(o) for o in MergeOperation)
    assert labels[values.index("prefercenter")] == "Prefer Center"
    assert labels[values.index("maximum-deflection")] == "Maximum Deflection"


@pytest.mark.parametrize("name", [o.name for o in MergeOperation])
def test_the_current_operation_is_one_of_the_list(name: str) -> None:
    """05 S114: the editor's current value matches a drop-down value, and
    picking that value sets the operation back (else the selection vanishes)."""
    from action_plugins.merge_axis import MergeAxisModel

    _, values = _operation_list()
    fake = SimpleNamespace(
        _data=SimpleNamespace(operation=MergeOperation[name]),
        modelChanged=SimpleNamespace(emit=lambda: None),
    )
    current = MergeAxisModel._get_operation(fake)
    assert current in values
    other = MergeOperation.Sum if name == "Average" else MergeOperation.Average
    fake._data.operation = other
    MergeAxisModel._set_operation(fake, current)
    assert fake._data.operation == MergeOperation[name]


def test_a_new_merge_axis_gets_the_next_free_name() -> None:
    from action_plugins.merge_axis import MergeAxisData, MergeAxisModel

    existing = [SimpleNamespace(label=f"Merge Axis {n}") for n in (1, 2)]
    made = SimpleNamespace(label="", id="new")
    asked: list = []

    def create(name: str, behavior: InputType, reuse: bool = True) -> object:
        asked.append((name, reuse))
        return made

    fake = SimpleNamespace(
        library=SimpleNamespace(
            actions_by_type=lambda kind: existing + [made], create=create
        ),
        _binding_model=SimpleNamespace(behavior_type=InputType.JoystickAxis),
        modelChanged=SimpleNamespace(emit=lambda: None),
        _set_merge_action=lambda value: None,  # "+" selects the new one
    )
    MergeAxisModel.newMergeAxis(fake)
    assert made.label == "Merge Axis 3"
    # Always a new one, added by the library (map 2 create).
    assert asked == [(MergeAxisData.name, False)]


# ACT23 / E2 / E3 / E4 / N21 ------------------------------------------------


def _qml(rel: str) -> str:
    return (_ROOT / "action_plugins" / rel).read_text(encoding="utf-8")


def test_editors_say_their_units_and_count_from_one() -> None:
    chain = _qml("chain/ChainAction.qml")
    assert '"Timeout (sec, 0 = never)"' in chain
    assert '"Sequence " + (index + 1)' in chain
    toggle = _qml("smart_toggle/SmartToggleAction.qml")
    assert '"Hold time (sec)"' in toggle
    assert "maxValue: 10\n" in toggle.replace("\r", "")
    macro = _qml("macro/MacroAction.qml")
    assert '"Delay (sec)"' in macro and '"Times"' in macro
    mouse = _qml("map_to_mouse/MapToMouseAction.qml")
    for label in ("(px/s)", "Time to maximum speed (sec)", "Direction (degrees)"):
        assert label in mouse
    tts = _qml("text_to_speech/TextToSpeechAction.qml")
    assert '"Volume (%)"' in tts and "playbackVolume = val / 100" in tts
    assert "Invert activation" in _qml("map_to_xbox/MapToXboxAction.qml")
    assert '"Speed"' in _qml("map_to_vjoy/MapToVjoyAction.qml")
    assert "Reversed: full at the lower end" in _qml("split_axis/SplitAxisAction.qml")
    assert "Lower half: outer end" in _qml("response_curve/ResponseCurveAction.qml")


# GL-108 (06 Q15): Condition on an empty Logical Device ----------------------


def test_a_logical_device_condition_on_an_empty_device_asks_for_a_control() -> None:
    from action_plugins.condition import ConditionModel
    from action_plugins.condition import condition as ca
    from gremlin.logical_device import LogicalDevice
    from gremlin.signal import signal
    from gremlin.types import ConditionType

    LogicalDevice().reset()
    shown: list = []

    def note(title: str, text: str) -> None:
        shown.append(text)

    data = SimpleNamespace(conditions=[], behavior_type=InputType.JoystickButton)
    fake = SimpleNamespace(
        _data=data, conditionsChanged=SimpleNamespace(emit=lambda: None)
    )
    signal.showNotification.connect(note)
    try:
        ConditionModel.addCondition(fake, ConditionType.LogicalDevice.value)
    finally:
        signal.showNotification.disconnect(note)
    assert data.conditions == []  # nothing added, no error
    assert shown == ["Add a Logical Device control first."]
    assert LogicalDevice().inputs_of_type() == []  # no hidden Button 1
    # Loading one still works on an empty device (from_xml sets its control).
    assert ca.LogicalDeviceCondition().is_valid() is False


# GL-055 (05 Q3): a Reference placeholder can't make Run fail -----------------


def test_a_reference_placeholder_does_nothing_at_run() -> None:
    from action_plugins.reference import ReferenceData

    placeholder = ReferenceData(InputType.JoystickButton)
    assert not placeholder.is_valid()  # unfinished: Run and Save skip it
    functor = placeholder.functor(placeholder)  # building it no longer fails
    functor(SimpleNamespace(), SimpleNamespace(current=True))


# GL-097 (05 S63, S21, S27; decisions A1, A4): a shared action picked in the
# pane is edited as a copy until OK -------------------------------------------

_STICK = uuid.UUID("55555555-6666-7777-8888-999999999999")


class _Pane(QtCore.QObject):
    """The pane's parent model as the editors see it."""

    enumeration_index = 0


@pytest.fixture
def shared_merge() -> Iterator[SimpleNamespace]:
    """Axis 1 uses a finished Merge Axis; axis 4 is open in a pane (draft)."""
    from gremlin import plugin_manager, shared_state

    before = shared_state.current_profile
    profile = Profile()
    shared_state.current_profile = profile
    library = profile.library
    merge = library.create("Merge Axis", InputType.JoystickAxis, reuse=False)
    for axis, number in ((merge.axis_in1, 1), (merge.axis_in2, 2)):
        axis.device_guid = _STICK
        axis.input_id = number
        axis.input_type = InputType.JoystickAxis
    merge.label = "live"
    first = profile.get_input_item(_STICK, InputType.JoystickAxis, 1, "Default", True)
    first.add_item_binding().root_action.insert_action(merge, "children")
    real = profile.get_input_item(_STICK, InputType.JoystickAxis, 4, "Default", True)
    real.add_item_binding()
    draft = library.draft(real, 0)
    pane = _Pane()
    model = InputItemBindingModel(draft.item.action_sequences[0], pane)
    assert plugin_manager.PluginManager().get_class("Merge Axis")
    yield SimpleNamespace(
        profile=profile, library=library, merge=merge, first=first, real=real,
        draft=draft, model=model, pane=pane,
    )
    library.discard(draft)
    shared_state.current_profile = before


def _models(model: InputItemBindingModel, tag: str) -> list:
    return [m for m in model._action_models.values() if m.action_data.tag == tag]


def _editor(pane: SimpleNamespace, name: str, tag: str) -> object:
    _models(pane.model, "root")[0].appendAction(name, "children")
    pane.model.sync_data()
    return _models(pane.model, tag)[0]


def test_reusing_a_shared_merge_axis_then_cancel_changes_nothing(
    shared_merge: SimpleNamespace,
) -> None:
    editor = _editor(shared_merge, "Merge Axis", "merge-axis")
    assert editor.action_data is not shared_merge.merge  # a copy until OK
    editor.label = "edited in the pane"
    shared_merge.library.discard(shared_merge.draft)
    assert shared_merge.merge.label == "live"


def test_picking_a_shared_merge_axis_then_cancel_changes_nothing(
    shared_merge: SimpleNamespace,
) -> None:
    editor = _editor(shared_merge, "Merge Axis", "merge-axis")
    editor.newMergeAxis()  # "+": a new one in the pane
    shared_merge.model.sync_data()
    editor = _models(shared_merge.model, "merge-axis")[0]
    editor.mergeAction = str(shared_merge.merge.id)  # pick the shared one
    shared_merge.model.sync_data()
    picked = _models(shared_merge.model, "merge-axis")[0]
    assert picked.action_data is not shared_merge.merge
    picked.operation = "maximum"
    shared_merge.library.discard(shared_merge.draft)
    from action_plugins.merge_axis import MergeOperation

    assert shared_merge.merge.operation == MergeOperation.Average


def test_picking_a_shared_merge_axis_then_ok_keeps_it_shared(
    shared_merge: SimpleNamespace,
) -> None:
    editor = _editor(shared_merge, "Merge Axis", "merge-axis")
    editor.label = "edited in the pane"
    shared_merge.library.commit(shared_merge.draft, shared_merge.real, 0)
    # Both inputs use the one action, with the edit (decision A1).
    kids = shared_merge.real.action_sequences[0].root_action.get_actions()[0]
    assert kids == [shared_merge.merge]
    assert shared_merge.merge.label == "edited in the pane"
    assert shared_merge.first.action_sequences[0].root_action.get_actions()[0] == [
        shared_merge.merge
    ]


def test_referencing_a_shared_action_then_cancel_changes_nothing(
    shared_merge: SimpleNamespace,
) -> None:
    # A Reference placeholder on an axis input points at the shared one.
    reference = _editor(shared_merge, "Reference", "reference")
    reference.referenceAction(str(shared_merge.merge.id))
    shared_merge.model.sync_data()
    picked = _models(shared_merge.model, "merge-axis")[0]
    assert picked.action_data is not shared_merge.merge
    picked.label = "edited in the pane"
    shared_merge.library.discard(shared_merge.draft)
    assert shared_merge.merge.label == "live"


def test_a_new_deadzone_is_added_by_the_library() -> None:
    from action_plugins.dual_axis_deadzone import (
        DualAxisDeadzoneData,
        DualAxisDeadzoneModel,
    )

    made = SimpleNamespace(label="", id="new")
    asked: list = []

    def create(name: str, behavior: InputType, reuse: bool = True) -> object:
        asked.append((name, reuse))
        return made

    picked: list = []
    fake = SimpleNamespace(
        library=SimpleNamespace(create=create, actions_by_type=lambda _t: [made]),
        _binding_model=SimpleNamespace(behavior_type=InputType.JoystickAxis),
        _set_deadzone=picked.append,
    )
    DualAxisDeadzoneModel.newDeadzone(fake)
    assert asked == [(DualAxisDeadzoneData.name, False)]
    assert picked == ["new"]


def test_a_logical_device_macro_step_on_an_empty_device_asks_for_a_control() -> None:
    from action_plugins.macro import LogicalDeviceActionModel, MacroModel
    from gremlin.logical_device import LogicalDevice
    from gremlin.signal import signal

    LogicalDevice().reset()
    steps: list = []
    shown: list = []

    def note(title: str, text: str) -> None:
        shown.append(text)

    fake = SimpleNamespace(
        action_lookup=MacroModel.action_lookup,
        _action_list_model=SimpleNamespace(append=steps.append),
        changed=SimpleNamespace(emit=lambda: None),
    )
    signal.showNotification.connect(note)
    try:
        MacroModel.addAction(fake, "logical-device")
    finally:
        signal.showNotification.disconnect(note)
    assert shown == ["Add a Logical Device control first."]
    assert LogicalDevice().inputs_of_type() == []  # no hidden Button 1
    step = steps[0]
    assert step.input_id is None
    assert LogicalDeviceActionModel.needsControl.fget(SimpleNamespace(_action=step))
    qml = _qml("macro/MacroAction.qml")
    assert "modelData.needsControl" in qml
    assert '"Add a Logical Device control first."' in qml


# GL-096 (05 S62, Q1; decision A1): the pane says when an action is shared ---


def test_a_shared_action_says_who_else_uses_it(
    shared_merge: SimpleNamespace,
) -> None:
    from gremlin.common import input_to_ui_string

    editor = _editor(shared_merge, "Merge Axis", "merge-axis")
    note = editor.sharedWith
    first = input_to_ui_string(InputType.JoystickAxis, 1)
    assert note.startswith("Shared with ") and f"{first} (Default)" in note
    assert "OK changes it for every input that uses it." in note
    root = _models(shared_merge.model, "root")[0]
    assert root.sharedWith == ""  # only this input uses it
    qml = (_ROOT / "qml" / "ActionNode.qml").read_text(encoding="utf-8")
    assert "_root.action.sharedWith" in qml
