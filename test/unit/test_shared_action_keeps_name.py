# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""05 S59: choosing an existing Merge Axis to share it keeps the shared
action's own name (the editor's list replaced the old "Reuse" mode, so the
word never appears on screen)."""

from __future__ import annotations

import sys

sys.path.append(".")

import uuid
from collections.abc import Iterator
from types import SimpleNamespace

import pytest
from PySide6 import QtCore

from gremlin.profile import Profile
from gremlin.types import InputType
from gremlin.ui.profile import InputItemBindingModel

_STICK = uuid.UUID("55555555-6666-7777-8888-999999999998")


class _Pane(QtCore.QObject):
    """The pane's parent model as the editors see it."""

    enumeration_index = 0


@pytest.fixture
def shared() -> Iterator[SimpleNamespace]:
    """Axis 1 uses a Merge Axis named "Throttle pair"; axis 4 is in a pane."""
    from gremlin import shared_state

    before = shared_state.current_profile
    profile = Profile()
    shared_state.current_profile = profile
    library = profile.library
    merge = library.create("Merge Axis", InputType.JoystickAxis, reuse=False)
    for axis, number in ((merge.axis_in1, 1), (merge.axis_in2, 2)):
        axis.device_guid = _STICK
        axis.input_id = number
        axis.input_type = InputType.JoystickAxis
    merge.label = "Throttle pair"
    first = profile.get_input_item(_STICK, InputType.JoystickAxis, 1, "Default", True)
    first.add_item_binding().root_action.insert_action(merge, "children")
    real = profile.get_input_item(_STICK, InputType.JoystickAxis, 4, "Default", True)
    real.add_item_binding()
    draft = library.draft(real, 0)
    pane = _Pane()  # held: the model is its child
    model = InputItemBindingModel(draft.item.action_sequences[0], pane)
    yield SimpleNamespace(
        library=library, merge=merge, real=real, draft=draft, model=model, pane=pane
    )
    library.discard(draft)
    shared_state.current_profile = before


def _merge_editor(model: InputItemBindingModel) -> object:
    return next(
        m for m in model._action_models.values() if m.action_data.tag == "merge-axis"
    )


def test_choosing_a_shared_merge_axis_keeps_its_own_name(
    shared: SimpleNamespace,
) -> None:
    root = next(
        m for m in shared.model._action_models.values() if m.action_data.tag == "root"
    )
    root.appendAction("Merge Axis", "children")
    shared.model.sync_data()
    editor = _merge_editor(shared.model)
    editor.newMergeAxis()  # "+": a new one, "Merge Axis N"
    shared.model.sync_data()
    editor = _merge_editor(shared.model)
    assert editor.label.startswith("Merge Axis ")
    editor.mergeAction = str(shared.merge.id)  # choose the shared one
    shared.model.sync_data()
    picked = _merge_editor(shared.model)
    assert picked.label == "Throttle pair"
    shared.library.commit(shared.draft, shared.real, 0)
    kids = shared.real.action_sequences[0].root_action.get_actions()[0]
    assert kids == [shared.merge]
    assert shared.merge.label == "Throttle pair"
