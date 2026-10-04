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
from types import SimpleNamespace
from unittest import mock

import pytest

from action_plugins.description import DescriptionData
from action_plugins.root import RootData
from gremlin.profile import InputItem, InputItemBinding, Profile
from gremlin.types import DataCreationMode, InputType
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
    other = RootData(InputType.JoystickButton)
    library.add_action(other)
    other.insert_action(first, "children")  # shared, as Merge Axis is
    model.remove_action(_sidx(model, first))
    assert library.has_action(first.id)


def test_the_broken_profile_remove_action_is_gone() -> None:
    assert not hasattr(Profile, "remove_action")


# ACT18 --------------------------------------------------------------------


def test_reuse_keeps_the_shared_actions_name() -> None:
    from action_plugins.merge_axis import MergeAxisData

    shared = MergeAxisData(InputType.JoystickAxis)
    shared.action_label = "Throttle pair"
    with mock.patch.object(MergeAxisData, "_do_create", return_value=shared):
        got = MergeAxisData.create(DataCreationMode.Reuse, InputType.JoystickAxis)
    assert got is shared and got.action_label == "Throttle pair"
    fresh = MergeAxisData(InputType.JoystickAxis)
    with mock.patch.object(MergeAxisData, "_do_create", return_value=fresh):
        got = MergeAxisData.create(DataCreationMode.Reuse, InputType.JoystickAxis)
    assert got.action_label == MergeAxisData.name  # a new one gets the default


# ACT22 --------------------------------------------------------------------


def test_merge_axis_error_names_the_value() -> None:
    from action_plugins.merge_axis import MergeOperation
    from gremlin.error import GremlinError

    with pytest.raises(GremlinError, match="'nonsense'"):
        MergeOperation.to_enum("nonsense")


def test_merge_operations_read_as_words() -> None:
    from action_plugins.merge_axis import MergeAxisModel

    with mock.patch("action_plugins.merge_axis.LabelValueSelectionModel") as made:
        MergeAxisModel.operationList.fget(SimpleNamespace())
    labels, values = made.call_args.args[:2]
    assert "Prefer Center" in labels and "Prefercenter" not in labels
    assert "Prefercenter" in values  # what profiles store


def test_a_new_merge_axis_gets_the_next_free_name() -> None:
    from action_plugins.merge_axis import MergeAxisData, MergeAxisModel

    existing = [SimpleNamespace(label=f"Merge Axis {n}") for n in (1, 2)]
    added: list = []
    fake = SimpleNamespace(
        library=SimpleNamespace(
            actions_by_type=lambda kind: existing, add_action=added.append
        ),
        _binding_model=SimpleNamespace(behavior_type=InputType.JoystickAxis),
        modelChanged=SimpleNamespace(emit=lambda: None),
    )
    with mock.patch.object(
        MergeAxisData, "create",
        return_value=SimpleNamespace(label=""),
    ):
        MergeAxisModel.newMergeAxis(fake)
    assert added[0].label == "Merge Axis 3"


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
