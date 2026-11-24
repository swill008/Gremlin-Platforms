# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Models handed to QML are kept, not made again on every read (upstream
9602a510, 66bb2477; plan claude/plans/memory-qml-factory.md, answer 8a).

- A pick list (Merge Axis, Reference, Dual Axis Deadzone) made a new
  LabelValueSelectionModel, held by the action's model, on every read.
- The vJoy initial values list made a new child model, held by the list,
  for every row read.
"""

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
from gremlin.ui import profile as ui_profile
from gremlin.ui.profile import (
    InputItemBindingModel,
    LabelValueSelectionModel,
    reuse_or_replace_selection_model,
)


@pytest.fixture
def scheduled_deletions(
    monkeypatch: pytest.MonkeyPatch,
) -> list[LabelValueSelectionModel]:
    scheduled: list[LabelValueSelectionModel] = []
    monkeypatch.setattr(
        LabelValueSelectionModel, "deleteLater", lambda self: scheduled.append(self)
    )
    return scheduled


# The helper -----------------------------------------------------------------


def test_reuse_returns_matching_model(
    scheduled_deletions: list[LabelValueSelectionModel],
) -> None:
    owner = QtCore.QObject()
    current = LabelValueSelectionModel(["A", "B"], ["1", "2"], parent=owner)

    result = reuse_or_replace_selection_model(current, ["A", "B"], ["1", "2"], owner)

    assert result is current
    assert scheduled_deletions == []


@pytest.mark.parametrize(
    ("labels", "values", "bootstrap"),
    [
        (["A", "C"], ["1", "2"], []),
        (["A", "B"], ["1", "3"], []),
        (["A", "B"], ["1", "2"], ["x", "y"]),
    ],
)
def test_replace_creates_owned_model_and_deletes_current(
    scheduled_deletions: list[LabelValueSelectionModel],
    labels: list[str],
    values: list[str],
    bootstrap: list[str],
) -> None:
    owner = QtCore.QObject()
    current = LabelValueSelectionModel(["A", "B"], ["1", "2"], parent=owner)

    result = reuse_or_replace_selection_model(
        current, labels, values, owner, bootstrap=bootstrap
    )

    assert result is not current
    assert result.parent() is owner
    assert scheduled_deletions == [current]


def test_replace_without_current_creates_owned_model() -> None:
    owner = QtCore.QObject()

    result = reuse_or_replace_selection_model(None, ["A"], ["1"], owner)

    assert result.rowCount() == 1
    assert result.parent() is owner


def test_replace_keeps_selected_value(
    scheduled_deletions: list[LabelValueSelectionModel],
) -> None:
    owner = QtCore.QObject()
    current = LabelValueSelectionModel(["A", "B"], ["1", "2"], parent=owner)
    current.currentValue = "2"

    result = reuse_or_replace_selection_model(
        current, ["Z", "A", "B"], ["0", "1", "2"], owner
    )

    assert result.currentValue == "2"


def test_replace_without_selected_value_starts_at_first_entry(
    scheduled_deletions: list[LabelValueSelectionModel],
) -> None:
    owner = QtCore.QObject()
    current = LabelValueSelectionModel(["A", "B"], ["1", "2"], parent=owner)
    current.currentValue = "2"

    result = reuse_or_replace_selection_model(current, ["A", "C"], ["1", "3"], owner)

    assert result.currentValue == "1"


# The real editors -----------------------------------------------------------

_STICK = uuid.UUID("55555555-6666-7777-8888-999999999998")


class _Pane(QtCore.QObject):
    enumeration_index = 0


@pytest.fixture
def axis_pane() -> Iterator[SimpleNamespace]:
    """An axis input open in a pane, with a finished Merge Axis elsewhere."""
    from gremlin import plugin_manager, shared_state

    before = shared_state.current_profile
    profile = Profile()
    shared_state.current_profile = profile
    library = profile.library
    merge = library.create("Merge Axis", InputType.JoystickAxis, reuse=False)
    first = profile.get_input_item(_STICK, InputType.JoystickAxis, 1, "Default", True)
    first.add_item_binding().root_action.insert_action(merge, "children")
    real = profile.get_input_item(_STICK, InputType.JoystickAxis, 4, "Default", True)
    real.add_item_binding()
    draft = library.draft(real, 0)
    pane = _Pane()
    model = InputItemBindingModel(draft.item.action_sequences[0], pane)
    assert plugin_manager.PluginManager().get_class("Merge Axis")
    yield SimpleNamespace(model=model, library=library, draft=draft, pane=pane)
    library.discard(draft)
    shared_state.current_profile = before


def _editor(pane: SimpleNamespace, name: str, tag: str) -> QtCore.QObject:
    def of(tag: str) -> list:
        return [m for m in pane.model._action_models.values()
                if m.action_data.tag == tag]

    of("root")[0].appendAction(name, "children")
    pane.model.sync_data()
    return of(tag)[0]


def _selection_children(owner: QtCore.QObject) -> int:
    return len(owner.findChildren(LabelValueSelectionModel))


@pytest.mark.parametrize(
    ("name", "tag", "prop"),
    [
        ("Merge Axis", "merge-axis", "operationList"),
        ("Merge Axis", "merge-axis", "mergeActionList"),
        ("Reference", "reference", "actions"),
        ("Dual Axis Deadzone", "dual-axis-deadzone", "deadzoneActionList"),
    ],
)
def test_a_pick_list_read_twice_is_the_same_model(
    axis_pane: SimpleNamespace, name: str, tag: str, prop: str
) -> None:
    editor = _editor(axis_pane, name, tag)
    first = getattr(editor, prop)
    count = _selection_children(editor)
    for _ in range(5):
        assert getattr(editor, prop) is first
    assert _selection_children(editor) == count


# The vJoy initial values ----------------------------------------------------


def test_a_vjoy_rows_initial_values_model_is_made_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gremlin import shared_state

    monkeypatch.setattr(shared_state, "current_profile", Profile())
    monkeypatch.setattr(
        ui_profile,
        "_vjoy_devices",
        lambda: [ui_profile._VJoyDevice(1, [1, 2]), ui_profile._VJoyDevice(2, [1])],
    )
    owner = QtCore.QObject()
    model = ui_profile.OutputVJoyListModel(owner)
    role = next(
        r for r, n in model.roleNames().items() if bytes(n) == b"initialValuesModel"
    )
    first = [model.data(model.index(row, 0), role) for row in range(2)]
    for _ in range(5):
        again = [model.data(model.index(row, 0), role) for row in range(2)]
        assert again[0] is first[0]
        assert again[1] is first[1]
    assert len(model.findChildren(ui_profile.OutputVJoyInitialValuesModel)) == 2
    assert first[0]._device.vjoy_id == 1
    assert first[1]._device.vjoy_id == 2
