# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Search window's model (D-01-SEARCH): query properties, setFrom*
slots, grouped rows and counts read through gremlin.usages, the pickers
(choices) and the rebuild on profile notices."""

from __future__ import annotations

import sys
import types
import uuid
from collections.abc import Iterator
from dataclasses import dataclass

import pytest
from PySide6 import QtCore, QtTest

import gremlin
from gremlin import shared_state
from gremlin.modules import output
from gremlin.signal import signal
from gremlin.types import InputType
from gremlin.ui.usages_model import UsagesModel
from vigem.xbox import XboxTarget

_STICK = uuid.UUID("{61111111-2222-3333-4444-555555555555}")


@dataclass(frozen=True)
class _Use:
    device_guid: str
    device_name: str
    mode: str
    input_type: int
    input_id: object
    input_label: str
    binding_index: int
    role: str
    text: str
    path: tuple
    not_found: bool


@dataclass(frozen=True)
class _Query:
    kind: str
    device_guid: str = ""
    input_type: int | None = None
    input_id: object = None
    output: str = ""
    output_id: int = 0
    mode: str = ""
    action_tag: str = ""


class _FakeUsages(types.ModuleType):
    """gremlin.usages stand-in: records each query, answers self.answer."""

    def __init__(self) -> None:
        super().__init__("gremlin.usages")
        self.Query = _Query
        self.ROLE_TITLES = {
            "sends-output": "Sends to this output",
            "checks-output": "Checks this output",
        }
        self.queries: list = []
        self.answer: list = []

    def find(self, profile: object, query: object) -> list:
        self.queries.append(query)
        return list(self.answer)


def _use(role: str, text: str, *, not_found: bool = False) -> _Use:
    return _Use(
        str(_STICK),
        "Stick",
        "Default",
        InputType.JoystickButton.value,
        3,
        "Button 3",
        0,
        role,
        text,
        ("Macro", "step 1"),
        not_found,
    )


@pytest.fixture
def profile(monkeypatch: pytest.MonkeyPatch) -> object:
    from gremlin.profile import Profile

    made = Profile()
    monkeypatch.setattr(shared_state, "current_profile", made)
    return made


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch) -> _FakeUsages:
    stub = _FakeUsages()
    monkeypatch.setitem(sys.modules, "gremlin.usages", stub)
    monkeypatch.setattr(gremlin, "usages", stub, raising=False)
    return stub


@pytest.fixture
def model(qapp: object, profile: object) -> Iterator[UsagesModel]:
    made = UsagesModel()
    yield made
    made.disconnect_notices()
    made.deleteLater()


def _rows(model: UsagesModel) -> list[dict]:
    names = {int(k): bytes(v).decode() for k, v in model.roleNames().items()}
    return [
        {name: model.data(model.index(r, 0), role) for role, name in names.items()}
        for r in range(model.rowCount())
    ]


def test_roles_are_the_contract(model: UsagesModel) -> None:
    names = {bytes(v).decode() for v in model.roleNames().values()}
    assert names == {
        "group",
        "groupTitle",
        "deviceGuid",
        "deviceName",
        "mode",
        "inputType",
        "inputId",
        "inputLabel",
        "bindingIndex",
        "text",
        "notFound",
        "path",
    }


def test_set_from_output_fills_query_and_groups_rows(
    model: UsagesModel, fake: _FakeUsages
) -> None:
    fake.answer = [
        _use("sends-output", "Map to vJoy · vJoy 2 Button 30"),
        _use("sends-output", "Macro · vJoy 2 Button 30", not_found=True),
        _use("checks-output", "Condition · vJoy 2 Button 30"),
    ]
    model.setFromOutput("vjoy", 2, InputType.JoystickButton.value, 30)
    assert fake.queries[-1] == _Query(
        kind="output",
        output="vjoy",
        output_id=2,
        input_type=InputType.JoystickButton.value,
        input_id=30,
    )
    assert (model.kind, model.output, model.outputId, model.inputId) == (
        "output",
        "vjoy",
        2,
        30,
    )
    assert model.count == 3
    assert model.groups == [
        {"role": "sends-output", "title": "Sends to this output", "count": 2},
        {"role": "checks-output", "title": "Checks this output", "count": 1},
    ]
    rows = _rows(model)
    assert rows[0]["groupTitle"] == "Sends to this output"
    assert rows[0]["deviceGuid"] == str(_STICK)
    assert rows[0]["inputLabel"] == "Button 3"
    assert rows[1]["notFound"] is True
    assert rows[0]["path"] == ["Macro", "step 1"]


def test_set_from_input_turns_a_key_list_back_into_a_tuple(
    model: UsagesModel, fake: _FakeUsages
) -> None:
    model.setFromInput("kb", InputType.Keyboard.value, [30, False])
    query = fake.queries[-1]
    assert query.kind == "input" and query.device_guid == "kb"
    assert query.input_id == (30, False)
    assert model.inputId == [30, False]


def test_mode_and_action_slots(model: UsagesModel, fake: _FakeUsages) -> None:
    model.setFromMode("Combat")
    assert fake.queries[-1] == _Query(kind="mode", mode="Combat")
    model.setFromAction("macro")
    assert fake.queries[-1] == _Query(kind="action", action_tag="macro")
    assert model.mode == "" and model.actionTag == "macro"


def test_incomplete_query_finds_nothing_without_asking(
    model: UsagesModel, fake: _FakeUsages
) -> None:
    model.kind = "input"
    model.search()
    assert fake.queries == [] and model.count == 0


def test_rebuilds_on_profile_notices_only_after_a_search(
    qapp: object, model: UsagesModel, fake: _FakeUsages
) -> None:
    signal.bindingsChanged.emit()
    QtTest.QTest.qWait(20)
    assert fake.queries == []
    model.setFromMode("Default")
    fake.answer = [_use("runs-in-mode", "Map to vJoy")]
    for notice in (
        signal.profileChanged,
        signal.bindingsChanged,
        signal.actionsChanged,
        signal.modesChanged,
    ):
        notice.emit()
    QtTest.QTest.qWait(20)
    assert len(fake.queries) == 2  # one search for the burst
    assert model.count == 1
    model.clear()
    assert model.count == 0 and model.kind == ""


def test_choices_modes_and_actions(model: UsagesModel, profile: object) -> None:
    profile.modes.add_mode("Combat")  # type: ignore[attr-defined]
    modes = model.choices("mode")
    assert [row["label"] for row in modes] == ["Combat", "Default"]
    actions = model.choices("action")
    by_tag = {row["value"]: row["label"] for row in actions}
    assert by_tag["map-to-vjoy"] == "Map to vJoy"
    assert by_tag["macro"] == "Macro"


def test_choices_devices_and_inputs_from_the_profile(
    model: UsagesModel, profile: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin.ui import input_pairing

    monkeypatch.setattr(input_pairing, "device_label", lambda guid: "Stick")
    item = profile.get_input_item(  # type: ignore[attr-defined]
        _STICK, InputType.JoystickButton, 7, "Default", True
    )
    item.add_item_binding()
    devices = model.choices("device")
    assert {"label": "Stick", "value": str(_STICK)} in devices
    model.deviceGuid = str(_STICK)
    inputs = model.choices("input")
    assert {
        "label": "Button 7",
        "value": {"inputType": InputType.JoystickButton.value, "inputId": 7},
    } in inputs


def test_choices_outputs_and_their_controls(
    model: UsagesModel, monkeypatch: pytest.MonkeyPatch
) -> None:
    claim = {"axes": [1, 2], "buttons": [1, 2, 3], "hats": []}
    monkeypatch.setattr(output, "vjoy_modules", lambda: [(1, object()), (2, object())])
    monkeypatch.setattr(output, "vjoy_claim", lambda vjoy_id: claim)
    monkeypatch.setattr(output, "xbox_pads_on", lambda: [1, 2])
    labels = [row["label"] for row in model.choices("output")]
    assert labels == ["vJoy 1", "vJoy 2", "Xbox 360 Controller", "Xbox 360 2"]
    model.output, model.outputId = "vjoy", 2
    controls = model.choices("outputInput")
    values = [row["value"] for row in controls]
    assert {"inputType": InputType.JoystickButton.value, "inputId": 3} in values
    assert {"inputType": InputType.JoystickAxis.value, "inputId": 2} in values
    model.output = "xbox"
    pad = model.choices("outputInput")
    assert len(pad) == len(XboxTarget)
    assert pad[0] == {
        "label": XboxTarget.LEFT_STICK_X.label,
        "value": {"inputType": -1, "inputId": "left_stick_x"},
    }


def test_real_find_on_a_real_profile(model: UsagesModel, profile: object) -> None:
    """The real gremlin.usages: a Map to vJoy on Button 1 is found from the
    output side and from the input side."""
    action = profile.library.create(  # type: ignore[attr-defined]
        "Map to vJoy", InputType.JoystickButton
    )
    action.vjoy_device_id = 2
    action.vjoy_input_type = InputType.JoystickButton
    action.vjoy_input_id = 30
    item = profile.get_input_item(  # type: ignore[attr-defined]
        _STICK, InputType.JoystickButton, 1, "Default", True
    )
    item.add_item_binding().root_action.insert_action(action, "children")
    model.setFromOutput("vjoy", 2, InputType.JoystickButton.value, 30)
    assert model.count >= 1
    first = _rows(model)[0]
    assert first["group"] == "sends-output"
    assert first["deviceGuid"] == str(_STICK) and first["mode"] == "Default"
    assert first["inputId"] == 1 and first["bindingIndex"] == 0
    model.setFromInput(str(_STICK), InputType.JoystickButton.value, 1)
    assert model.count >= 1
    assert {g["role"] for g in model.groups} == {"reads-input"}
    assert model.groups[0]["title"] == "Reads this input"
    # No control picked: every use of the vJoy device.
    model.setFromOutput("vjoy", 2, -1, None)
    assert model.count >= 1 and _rows(model)[0]["group"] == "sends-output"


def test_qml_makes_it_and_sets_the_query(qapp: object, profile: object) -> None:
    """Gremlin.Device's UsagesModel from QML: properties set, slots called."""
    from PySide6 import QtQml

    engine = QtQml.QQmlEngine()
    component = QtQml.QQmlComponent(engine)
    component.setData(
        b"import QtQml\nimport Gremlin.Device\n"
        b"UsagesModel { kind: 'mode'; mode: 'Default'"
        b"; property var picks: choices('mode') }",
        QtCore.QUrl(),
    )
    made = component.create()
    assert made is not None, component.errorString()
    try:
        assert made.property("kind") == "mode"
        assert made.property("mode") == "Default"
        assert {"label": "Default", "value": "Default"} in made.property("picks")
        made.setProperty("inputId", [30, False])
        assert made._input_id == (30, False)
    finally:
        made.disconnect_notices()
        made.deleteLater()


def test_listen_fills_an_input_search(monkeypatch: "pytest.MonkeyPatch") -> None:
    """Search's Listen (D-01-SEARCH): the first pressed input fills the query."""
    from types import SimpleNamespace

    from gremlin.types import InputType
    from gremlin.ui import usages_model

    model = usages_model.UsagesModel()
    seen = {}
    monkeypatch.setattr(
        model, "setFromInput", lambda g, t, i: seen.update(g=g, t=t, i=i)
    )
    event = SimpleNamespace(
        device_guid="{ABC}", event_type=InputType.JoystickButton, identifier=5
    )
    model.setFromListened([event, SimpleNamespace()])
    assert seen == {"g": "{ABC}", "t": InputType.JoystickButton.value, "i": 5}
    seen.clear()
    model.setFromListened([])
    assert seen == {}
