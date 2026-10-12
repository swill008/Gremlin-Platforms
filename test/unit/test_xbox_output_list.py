# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Xbox Output View's list model (03 S115-S139, 05 S121-S135): parents
in pad order, a child line per source from a real profile's Map to Xbox
actions, Find text, type and "sending" filters, selection, live values from
output.xbox_state, and no undo."""

from __future__ import annotations

import uuid
import warnings
from collections.abc import Iterator

import pytest

from gremlin import shared_state
from gremlin.modules import output
from gremlin.signal import signal
from gremlin.types import InputType
from gremlin.ui import xbox_device_model, xbox_output_list
from gremlin.ui.xbox_output_list import XboxOutputListModel
from vigem.xbox import XboxTarget

_STICK = uuid.UUID("{51111111-2222-3333-4444-555555555555}")
_NAME = "VKBsim Gladiator EVO R"


def _bind(profile: object, button: int, pad: int, target: XboxTarget) -> None:
    action = profile.library.create(  # type: ignore[attr-defined]
        "Map to Xbox", InputType.JoystickButton
    )
    action.xbox_device_id = pad
    action.xbox_target = target
    item = profile.get_input_item(  # type: ignore[attr-defined]
        _STICK, InputType.JoystickButton, button, "Default", True
    )
    item.add_item_binding().root_action.insert_action(action, "children")


@pytest.fixture
def model(
    qapp: object, monkeypatch: pytest.MonkeyPatch
) -> Iterator[XboxOutputListModel]:
    from gremlin.profile import Profile

    profile = Profile()
    _bind(profile, 1, 1, XboxTarget.A)
    _bind(profile, 2, 1, XboxTarget.A)
    _bind(profile, 3, 1, XboxTarget.LEFT_TRIGGER)
    _bind(profile, 4, 2, XboxTarget.B)
    monkeypatch.setattr(shared_state, "current_profile", profile)
    monkeypatch.setattr(xbox_device_model, "device_label", lambda guid: _NAME)
    made = XboxOutputListModel()
    yield made
    made.liveActive = False
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        for notice in (
            signal.bindingsChanged,
            signal.deviceNamesChanged,
            signal.logicalDeviceModified,
        ):
            try:
                notice.disconnect(made._reload_soon)
            except (RuntimeError, TypeError):
                pass
    made.deleteLater()


def _rows(model: XboxOutputListModel) -> list[dict]:
    names = {int(k): bytes(v).decode() for k, v in model.roleNames().items()}
    return [
        {name: model.data(model.index(r, 0), role) for role, name in names.items()}
        for r in range(model.rowCount())
    ]


def _parents(model: XboxOutputListModel) -> list[str]:
    return [r["title"] for r in _rows(model) if r["rowKind"] == "parent"]


def test_parents_in_pad_order_with_tree_roles(model: XboxOutputListModel) -> None:
    rows = _rows(model)
    assert _parents(model) == [t.label for t in XboxTarget]
    assert model.parentCount == len(XboxTarget)
    for need in (
        "rowKind", "key", "title", "subtitle", "parentKey", "groupKey",
        "groupName", "systemName", "userName", "sequenceIndex", "childCount",
        "fixedGroup", "liveIndex", "sending",
    ):
        assert need in rows[0]
    first = rows[0]
    assert first["key"] == "parent:axis:left_stick_x"
    assert first["groupKey"] == "" and first["fixedGroup"] is True
    keys = [r["key"] for r in rows if r["rowKind"] == "parent"]
    assert "parent:axis:left_trigger" in keys
    assert "parent:button:a" in keys
    assert "parent:hat:dpad_up" in keys and "parent:hat:dpad" in keys


def test_child_line_per_source(model: XboxOutputListModel) -> None:
    rows = _rows(model)
    at = next(i for i, r in enumerate(rows) if r["key"] == "parent:button:a")
    parent = rows[at]
    assert parent["childCount"] == 2 and parent["sending"] is True
    children = rows[at + 1 : at + 3]
    assert [c["title"] for c in children] == [
        f"{_NAME} · Button 1",
        f"{_NAME} · Button 2",
    ]
    assert [c["key"] for c in children] == ["child:a:0", "child:a:1"]
    assert all(c["parentKey"] == "parent:button:a" for c in children)
    assert all(c["rowKind"] == "child" and c["liveIndex"] == -1 for c in children)
    # Pad 2's binding is not this pad's.
    b = next(r for r in rows if r["key"] == "parent:button:b")
    assert b["childCount"] == 0 and b["sending"] is False


def test_pad_id_switches_sources(model: XboxOutputListModel) -> None:
    model.padId = 2
    rows = _rows(model)
    b = next(r for r in rows if r["key"] == "parent:button:b")
    assert b["childCount"] == 1
    assert next(r for r in rows if r["key"] == "parent:button:a")["childCount"] == 0


def test_find_text_matches_label_and_source(model: XboxOutputListModel) -> None:
    model.setFilter("left trig", "all", False)
    assert _parents(model) == ["Left Trigger"]
    model.setFilter("button 2", "all", False)
    assert _parents(model) == ["A"]
    assert model.parentCount == 1


def test_type_filter(model: XboxOutputListModel) -> None:
    model.setFilter("", "trigger", False)
    assert _parents(model) == ["Left Trigger", "Right Trigger"]
    model.setFilter("", "dpad", False)
    assert _parents(model) == [
        "DPad Up", "DPad Down", "DPad Left", "DPad Right", "DPad"
    ]
    model.setFilter("", "stick", False)
    assert len(_parents(model)) == 4
    model.setFilter("", "button", False)
    assert "A" in _parents(model) and "DPad Up" not in _parents(model)
    assert [c["value"] for c in model.typeChoices] == [
        "all", "stick", "trigger", "button", "dpad"
    ]


def test_sending_filter(model: XboxOutputListModel) -> None:
    model.setFilter("", "all", True)
    assert _parents(model) == ["Left Trigger", "A"]
    assert model.filters == [
        {"label": "Only controls with something sending", "name": "sending"}
    ]


def test_selection_and_key_at(model: XboxOutputListModel) -> None:
    model.setSelection(["parent:button:a", "child:a:0"])
    assert model.selected() == ["parent:button:a"]
    assert model.keyAt(0) == "parent:axis:left_stick_x"
    assert model.keyAt(9999) == ""


def test_no_undo(model: XboxOutputListModel) -> None:
    assert model.canUndo is False and model.canRedo is False
    assert model.undoTip == model.redoTip == model.lastChange == model.undone == ""
    model.undo()
    model.redo()
    model.setCantSendOnly(True)
    assert model.parentCount == len(XboxTarget)


def test_bindings_changed_refreshes(model: XboxOutputListModel) -> None:
    from PySide6 import QtCore

    _bind(shared_state.current_profile, 5, 1, XboxTarget.Y)
    signal.bindingsChanged.emit()
    QtCore.QCoreApplication.processEvents()
    y = next(r for r in _rows(model) if r["key"] == "parent:button:y")
    assert y["childCount"] == 1


def test_live_reads_xbox_state_only_while_active(
    model: XboxOutputListModel, monkeypatch: pytest.MonkeyPatch
) -> None:
    reads: list[int] = []
    state = {"left_stick_x": 0.5, "left_trigger": 1.0, "a": 1.0, "dpad_up": 1.0}

    def fake(pad: int) -> dict:
        reads.append(pad)
        return dict(state)

    monkeypatch.setattr(output, "xbox_state", fake)
    targets = list(XboxTarget)
    ix = {t: i for i, t in enumerate(targets)}
    rows = {r["key"]: r for r in _rows(model)}
    assert rows["parent:button:a"]["liveIndex"] == ix[XboxTarget.A]

    assert model.kindAt(ix[XboxTarget.LEFT_STICK_X]) == "axis"
    assert model.kindAt(ix[XboxTarget.LEFT_TRIGGER]) == "axis"
    assert model.kindAt(ix[XboxTarget.A]) == "button"
    assert model.kindAt(ix[XboxTarget.DPAD_UP]) == "hat"
    assert model.valueAt(ix[XboxTarget.A]) == 0.0
    assert not reads  # nothing read until the page turns live on

    before = model.stamp
    model.liveActive = True
    assert reads == [1]
    assert model.stamp > before
    assert model.valueAt(ix[XboxTarget.LEFT_STICK_X]) == 0.5
    assert model.valueAt(ix[XboxTarget.LEFT_TRIGGER]) == 1.0  # 0..1 to -1..1
    assert model.valueAt(ix[XboxTarget.A]) == 1.0
    assert model.valueAt(ix[XboxTarget.DPAD_UP]) == 1.0
    assert model._poll.isActive()
    assert model._poll.interval() == xbox_output_list.POLL_MS

    model.liveActive = False
    assert not model._poll.isActive()
    assert model.valueAt(ix[XboxTarget.A]) == 0.0
