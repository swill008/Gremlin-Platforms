# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""New vJoy conditions and Map to vJoy actions start on a claimed output
(05 S113, S115), the output picker offers only ids the vJoy device has
(05 S118), and new button checks and macro steps start on Pressed (05 S116)."""

from __future__ import annotations

import sys
import uuid
from types import SimpleNamespace

sys.path.append(".")

import pytest
from PySide6 import QtCore

from gremlin import device_initialization, macro, shared_state
from gremlin.modules import output
from gremlin.profile import Profile
from gremlin.types import InputType
from gremlin.ui.profile import InputItemBindingModel

_GUID = uuid.UUID("{21111111-2222-3333-4444-555555555555}")
B = InputType.JoystickButton
A = InputType.JoystickAxis
_KEEP: list = []


@pytest.fixture(scope="session", autouse=True)
def terminate_event_listener(request: pytest.FixtureRequest) -> None:
    import gremlin.event_handler

    request.addfinalizer(lambda: gremlin.event_handler.EventListener().terminate())


def _device(vjoy_id: int, buttons: int = 8, axes: int = 2) -> SimpleNamespace:
    return SimpleNamespace(
        vjoy_id=vjoy_id,
        axis_map=[SimpleNamespace(axis_index=i) for i in range(1, axes + 1)],
        button_count=buttons,
        hat_count=0,
    )


@pytest.fixture
def vjoy(monkeypatch: pytest.MonkeyPatch):  # noqa: ANN201
    """vJoy 1 and 3 in the driver (8 buttons, axes 1-2); modules set per
    test through the returned dict {vjoy_id: claim}; `as_input` ids are
    read back as inputs."""
    state: dict = {"claims": {}, "as_input": set(), "devices": [_device(1), _device(3)]}
    monkeypatch.setattr(
        output,
        "vjoy_modules",
        lambda: sorted(
            (vid, SimpleNamespace(name=f"vJoy {vid}", claim=claim))
            for vid, claim in state["claims"].items()
        ),
    )
    monkeypatch.setattr(device_initialization, "vjoy_devices", lambda: state["devices"])
    monkeypatch.setattr(
        device_initialization,
        "output_vjoy_devices",
        lambda: [d for d in state["devices"] if d.vjoy_id not in state["as_input"]],
    )
    monkeypatch.setattr(output, "vjoy_layout", lambda vid: (2, 8, 0))
    monkeypatch.setattr(output, "vjoy_axis_ids", lambda vid: {1, 2})
    return state


# --- the shared helper (contract) ------------------------------------------


def test_first_claimed_output_walks_modules_kinds_ids(vjoy: dict) -> None:
    vjoy["claims"] = {3: {"buttons": [7, 5]}, 1: {"axes": [2]}}
    assert output.first_claimed_output([B]) == (3, B, 5)
    assert output.first_claimed_output([A, B]) == (1, A, 2)
    assert output.first_claimed_output([B], exclude={(3, B, 5)}) == (3, B, 7)
    assert output.first_claimed_output([B], exclude={(3, B, 5), (3, B, 7)}) is None


def test_first_claimed_output_skips_ids_the_driver_lacks(vjoy: dict) -> None:
    vjoy["claims"] = {3: {"buttons": [20, 21, 4]}}
    assert output.first_claimed_output([B]) == (3, B, 4)
    vjoy["claims"] = {3: {"buttons": [20]}}
    assert output.first_claimed_output([B]) is None


def test_first_claimed_output_never_a_vjoy_used_as_input(vjoy: dict) -> None:
    vjoy["claims"] = {1: {"buttons": [1]}, 3: {"buttons": [2]}}
    vjoy["as_input"] = {1}
    assert output.first_claimed_output([B]) == (3, B, 2)


def test_first_claimed_output_none_claimed(vjoy: dict) -> None:
    assert output.first_claimed_output([B, A]) is None


# --- R6: a new vJoy condition (05 S113) -------------------------------------


def _add_condition(kind: int) -> tuple[list, list]:
    from action_plugins.condition import ConditionModel
    from gremlin.signal import signal

    shown: list = []

    def note(_title: str, text: str) -> None:
        shown.append(text)

    data = SimpleNamespace(conditions=[], behavior_type=B)
    fake = QtCore.QObject()  # the condition's Qt parent, as the model is
    fake._data = data  # type: ignore[attr-defined]
    fake.conditionsChanged = SimpleNamespace(emit=lambda: None)  # type: ignore[attr-defined]
    signal.showNotification.connect(note)
    try:
        ConditionModel.addCondition(fake, kind)  # type: ignore[arg-type]
    finally:
        signal.showNotification.disconnect(note)
    _KEEP.append(fake)  # the Qt parent outlives the test's checks
    return data.conditions, shown


def test_new_vjoy_condition_starts_on_the_claimed_output(
    vjoy: dict, qtbot: object
) -> None:
    from action_plugins.condition.comparator import PressedComparator
    from gremlin.types import ConditionType

    vjoy["claims"] = {3: {"buttons": [5]}}
    conditions, shown = _add_condition(ConditionType.VJoy.value)
    assert shown == []
    (cond,) = conditions
    assert (cond.vjoyDeviceId, cond.vjoyInputType, cond.vjoyInputId) == (3, "button", 5)
    assert isinstance(cond._comparator, PressedComparator)
    assert cond._comparator.is_pressed is True  # 05 S116


def test_new_vjoy_condition_axis_only_claim_gets_a_range(
    vjoy: dict, qtbot: object
) -> None:
    from action_plugins.condition.comparator import RangeComparator
    from gremlin.types import ConditionType

    vjoy["claims"] = {1: {"axes": [2]}}
    (cond,), _shown = _add_condition(ConditionType.VJoy.value)
    assert (cond.vjoyDeviceId, cond.vjoyInputType, cond.vjoyInputId) == (1, "axis", 2)
    assert isinstance(cond._comparator, RangeComparator)


def test_new_vjoy_condition_with_none_claimed_is_refused(vjoy: dict) -> None:
    from gremlin.types import ConditionType

    conditions, shown = _add_condition(ConditionType.VJoy.value)
    assert conditions == []
    assert shown == ["Claim an output on a vJoy output module first."]


def test_new_button_comparator_is_pressed_and_loaded_keeps_its_state() -> None:
    from xml.etree import ElementTree

    from action_plugins.condition.comparator import PressedComparator

    assert PressedComparator().is_pressed is True
    loaded = PressedComparator()
    loaded.from_xml(PressedComparator(is_pressed=False).to_xml())
    assert loaded.is_pressed is False
    assert isinstance(ElementTree.tostring(loaded.to_xml()), bytes)


# --- R8: a new Map to vJoy (05 S115) ----------------------------------------


class _Item(QtCore.QObject):
    def __init__(self) -> None:
        super().__init__()
        self.enumeration_index = 0


@pytest.fixture
def profile(monkeypatch: pytest.MonkeyPatch) -> Profile:
    p = Profile()
    p.modes.add_mode("B")
    monkeypatch.setattr(shared_state, "current_profile", p)
    return p


def _wire(profile: Profile, button: int, mode: str, vjoy_button: int) -> None:
    item = profile.get_input_item(_GUID, B, button, mode, create_if_missing=True)
    action = profile.library.create("Map to vJoy", B, item=item)
    action.vjoy_device_id = 3
    action.vjoy_input_type = B
    action.vjoy_input_id = vjoy_button
    item.add_item_binding().root_action.insert_action(action, "children")


def _add_map_to_vjoy(profile: Profile, button: int, mode: str = "Default"):  # noqa: ANN202
    item = profile.get_input_item(_GUID, B, button, mode, create_if_missing=True)
    binding = item.add_item_binding()
    owner = _Item()
    _KEEP.append(owner)  # the Qt parent outlives the test's checks
    model = InputItemBindingModel(binding, owner)
    model.rootAction.appendAction("Map to vJoy", "children")
    return binding.root_action.get_actions()[0][-1]


def test_new_map_to_vjoy_starts_on_the_claimed_output(
    vjoy: dict, profile: Profile, qtbot: object
) -> None:
    vjoy["claims"] = {3: {"buttons": [5]}}
    action = _add_map_to_vjoy(profile, 10)
    assert (action.vjoy_device_id, action.vjoy_input_type, action.vjoy_input_id) == (
        3,
        B,
        5,
    )


def test_new_map_to_vjoy_skips_outputs_used_in_this_mode(
    vjoy: dict, profile: Profile, qtbot: object
) -> None:
    vjoy["claims"] = {3: {"buttons": [1, 2, 3, 4, 5]}}
    for n in (1, 2, 3):
        _wire(profile, n, "Default", n)
    assert _add_map_to_vjoy(profile, 10).vjoy_input_id == 4


def test_new_map_to_vjoy_ignores_outputs_used_in_another_mode(
    vjoy: dict, profile: Profile, qtbot: object
) -> None:
    vjoy["claims"] = {3: {"buttons": [2, 3, 4, 5]}}
    for n in (2, 3):
        _wire(profile, n, "B", n)
    assert _add_map_to_vjoy(profile, 10).vjoy_input_id == 2


def test_new_map_to_vjoy_all_used_takes_the_first_claimed(
    vjoy: dict, profile: Profile, qtbot: object
) -> None:
    vjoy["claims"] = {3: {"buttons": [6, 7]}}
    _wire(profile, 1, "Default", 6)
    _wire(profile, 2, "Default", 7)
    assert _add_map_to_vjoy(profile, 10).vjoy_input_id == 6


def test_new_map_to_vjoy_none_claimed_is_unchanged(
    vjoy: dict, profile: Profile, qtbot: object
) -> None:
    action = _add_map_to_vjoy(profile, 10)
    assert (action.vjoy_device_id, action.vjoy_input_id) == (1, 1)


def test_used_rule_has_one_owner(vjoy: dict, profile: Profile) -> None:
    from gremlin.auto_mapper import AutoMapper

    _wire(profile, 1, "Default", 4)
    assert profile.vjoy_outputs_used("Default") == [(3, B, 4)]
    assert AutoMapper(profile)._get_used_vjoy_inputs("Default") == [(3, B, 4)]
    assert profile.vjoy_outputs_used("B") == []


def test_map_to_vjoy_and_vjoy_condition_load_with_no_vjoy(
    monkeypatch: pytest.MonkeyPatch, qtbot: object
) -> None:
    """05 S104: made from a file on a PC with no vJoy and no modules."""
    from action_plugins.condition import condition as ca
    from action_plugins.map_to_vjoy import MapToVjoyData

    monkeypatch.setattr(device_initialization, "vjoy_devices", lambda: [])
    monkeypatch.setattr(device_initialization, "output_vjoy_devices", lambda: [])
    monkeypatch.setattr(output, "vjoy_modules", lambda: [])
    data = MapToVjoyData(B)
    assert (data.vjoy_device_id, data.vjoy_input_id) == (1, 1)
    cond = ca.VJoyCondition()
    loaded = ca.VJoyCondition()
    cond.start_on(4, B, 9)
    loaded.from_xml(cond.to_xml())
    assert (loaded.vjoyDeviceId, loaded.vjoyInputId) == (4, 9)


# --- G-a: the output picker (05 S118) ---------------------------------------


def test_picker_drops_ids_the_driver_lacks(vjoy: dict) -> None:
    from gremlin.ui import output_modules

    vjoy["claims"] = {3: {"buttons": [1, 2, 9, 10], "axes": [1, 5]}}
    (module,) = output_modules._dest_modules()
    assert module["claim"]["buttons"] == [1, 2]
    assert module["claim"]["axes"] == [1]


# --- R11b: new macro steps press (05 S116) ----------------------------------


def test_new_macro_steps_start_on_pressed() -> None:
    from gremlin.logical_device import LogicalDevice

    LogicalDevice().reset()
    assert macro.JoystickAction.create().value is True
    assert macro.KeyAction.create().is_pressed is True
    assert macro.LogicalDeviceAction.create().value is True
    assert macro.MouseButtonAction.create().is_pressed is True
    assert macro.VJoyAction.create().value is True


def test_loaded_macro_steps_keep_released() -> None:
    from gremlin.types import MouseButton

    step = macro.MouseButtonAction(MouseButton.Left, False)
    loaded = macro.MouseButtonAction.create()
    loaded.from_xml(step.to_xml())
    assert loaded.is_pressed is False
