# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Each action declares what it points at (batch Q, references()): Map to
vJoy, Xbox, Keyboard, Logical Device and Mouse send to an output, Send OSC to
an OSC target, Load Profile loads a file, Change Mode switches modes, a
macro passes on its steps' references and a Condition its conditions'. The
not-found flag comes from the output module's own can't-send rules."""

from __future__ import annotations

import pathlib
import sys
import uuid

sys.path.append(".")

import pytest

from gremlin import references, shared_state
from gremlin.modules import ids, output
from gremlin.references import Reference
from gremlin.types import InputType, MouseButton

B = InputType.JoystickButton


@pytest.fixture
def profile(monkeypatch: pytest.MonkeyPatch) -> object:
    from gremlin.profile import Profile

    made = Profile()
    monkeypatch.setattr(shared_state, "current_profile", made)
    return made


def _vjoy(vjoy_id: int, input_id: int) -> object:
    from action_plugins.map_to_vjoy import MapToVjoyData

    action = MapToVjoyData(B)
    action.vjoy_device_id = vjoy_id
    action.vjoy_input_type = B
    action.vjoy_input_id = input_id
    return action


def test_map_to_vjoy(monkeypatch: pytest.MonkeyPatch) -> None:
    asked = []

    def cant(v: int, kind: object, c: int) -> str | None:
        asked.append((int(v), kind, int(c)))
        return "vJoy 9 is not Found." if int(v) == 9 else None

    monkeypatch.setattr(output, "cant_send_text", cant)
    assert list(_vjoy(2, 30).references()) == [
        Reference("sends-output", ("vjoy", 2, B.value, 30))
    ]
    assert list(_vjoy(9, 1).references()) == [
        Reference(
            "sends-output",
            ("vjoy", 9, B.value, 1),
            not_found=True,
            why="vJoy 9 is not Found.",
        )
    ]
    assert asked[0] == (2, output.kind_of(B), 30)


def test_map_to_xbox(monkeypatch: pytest.MonkeyPatch) -> None:
    from action_plugins.map_to_xbox import MapToXboxData
    from vigem.xbox import XboxTarget

    monkeypatch.setattr(
        output, "xbox_cant_send_text", lambda pad: "off" if pad == 3 else None
    )
    action = MapToXboxData(B)
    action.xbox_device_id = 1
    action.xbox_target = XboxTarget.A
    assert list(action.references()) == [
        Reference("sends-output", references.xbox(1, XboxTarget.A))
    ]
    action.xbox_device_id = 3
    assert [r.not_found for r in action.references()] == [True]


def test_map_to_keyboard_one_per_key() -> None:
    from action_plugins.map_to_keyboard import MapToKeyboardData
    from gremlin import keyboard

    action = MapToKeyboardData(B)
    action.keys = [
        keyboard.key_from_code(0x1E, False),
        keyboard.key_from_code(0x1F, False),
    ]
    assert list(action.references()) == [
        Reference("sends-output", references.keyboard((0x1E, False))),
        Reference("sends-output", references.keyboard((0x1F, False))),
    ]
    action.keys = []
    assert list(action.references()) == []


def test_map_to_logical_device(monkeypatch: pytest.MonkeyPatch) -> None:
    from action_plugins.map_to_logical_device import MapToLogicalDeviceData
    from gremlin.logical_device import LogicalDevice

    control = LogicalDevice().create(B)
    action = MapToLogicalDeviceData(B)
    action.logical_input_type = B
    action.logical_input_id = control.id
    target = references.input_ref(ids.LOGICAL_DEVICE, B, control.id)
    assert list(action.references()) == [Reference("sends-output", target)]
    monkeypatch.setattr(output, "logical_cant_send_text", lambda a: "gone")
    assert [(r.not_found, r.why) for r in action.references()] == [(True, "gone")]


def test_map_to_mouse_button_and_motion() -> None:
    from action_plugins.map_to_mouse import MapToMouseData, MapToMouseMode

    action = MapToMouseData(B)
    action.mode = MapToMouseMode.Button
    action.button = MouseButton.WheelUp
    assert list(action.references()) == [
        Reference("sends-output", ("mouse", "WheelUp"))
    ]
    action.mode = MapToMouseMode.Motion
    assert list(action.references()) == [Reference("sends-output", ("mouse", "Motion"))]


def test_send_osc_target_and_cant_send(monkeypatch: pytest.MonkeyPatch) -> None:
    from action_plugins.send_osc import SendOscData

    asked = []

    def cant(target: str, settings: object, name: str) -> str | None:
        asked.append((target, settings, name))
        return "OSC output is Off." if target == "t2" else None

    monkeypatch.setattr(output, "osc_cant_send_text", cant)
    action = SendOscData(B)
    action._target = "t1"
    action.target_name = "Sim"
    action.address = "/gear"
    assert list(action.references()) == [
        Reference("sends-output", ("osc-out", "t1", "/gear"))
    ]
    assert asked == [("t1", None, "Sim")]
    action._target = "t2"
    assert [(r.not_found, r.why) for r in action.references()] == [
        (True, "OSC output is Off.")
    ]


def test_load_profile(tmp_path: pathlib.Path) -> None:
    from action_plugins.load_profile import LoadProfileData

    action = LoadProfileData(B)
    assert list(action.references()) == []
    there = tmp_path / "other.xml"
    there.write_text("<profile/>", encoding="utf-8")
    action.profile_filename = str(there)
    assert list(action.references()) == [
        Reference("loads-profile", references.profile(there))
    ]
    action.profile_filename = str(tmp_path / "gone.xml")
    assert [r.not_found for r in action.references()] == [True]


def test_change_mode_one_per_mode(profile: object) -> None:
    from action_plugins.change_mode import ChangeModeData, ChangeType

    action = ChangeModeData(B)
    action.change_type = ChangeType.Cycle
    action.target_modes = ["Flight", "Landing"]
    assert list(action.references()) == [
        Reference("switches-mode", ("mode", "Flight"), "Change Mode (Cycle): Flight"),
        Reference("switches-mode", ("mode", "Landing"), "Change Mode (Cycle): Landing"),
    ]


class _Piece:
    """A step or condition declaring fixed references."""

    def __init__(self, *refs: Reference) -> None:
        self._refs = refs

    def references(self) -> tuple[Reference, ...]:
        return self._refs


def test_macro_numbers_its_steps() -> None:
    from action_plugins.macro import MacroData

    one = Reference("sends-output", ("vjoy", 1, B.value, 2), "vJoy 1 Button 2")
    two = Reference("sends-output", ("mouse", "Left"), "Left", not_found=True)
    action = MacroData()
    action.actions = [_Piece(one), _Piece(), _Piece(two)]
    assert list(action.references()) == [
        Reference(
            "sends-output",
            one.target,
            "In a macro: vJoy 1 Button 2",
            False,
            ("Step 1",),
        ),
        Reference("sends-output", two.target, "In a macro: Left", True, ("Step 3",)),
    ]


def test_condition_numbers_its_conditions_not_its_actions() -> None:
    from action_plugins.condition import ConditionData

    stick = uuid.UUID("{4DCB3090-97EC-11EB-8003-444553540000}")
    check = Reference(
        "checks-input", references.input_ref(stick, B, 1), "Stick Button 1"
    )
    action = ConditionData(B)
    action.conditions = [_Piece(), _Piece(check)]
    action.true_actions = [_vjoy(2, 3)]
    assert list(action.references()) == [
        Reference(
            "checks-input",
            check.target,
            "Condition: Stick Button 1",
            False,
            ("Condition 2",),
        )
    ]


def test_macro_with_real_steps(monkeypatch: pytest.MonkeyPatch) -> None:
    from action_plugins.macro import MacroData
    from gremlin import macro

    monkeypatch.setattr(output, "cant_send_text", lambda v, k, c: None)
    action = MacroData()
    action.actions = [macro.VJoyAction(2, B, 30, True), macro.PauseAction(0.1)]
    found = list(action.references())
    assert [(r.target, r.where) for r in found] == [
        (("vjoy", 2, B.value, 30), ("Step 1",))
    ]


_STICK = uuid.UUID("{4DCB3090-97EC-11EB-8003-444553540000}")
_A = InputType.JoystickAxis


def _axes_read(action: object, first: str, second: str) -> list:
    from action_plugins.axis_pair import AxisRef

    setattr(action, first, AxisRef(_STICK, _A, 1))
    setattr(action, second, AxisRef())  # not chosen yet: points at nothing
    return list(action.references())  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    "module, cls, first, second",
    [
        ("merge_axis", "MergeAxisData", "axis_in1", "axis_in2"),
        ("dual_axis_deadzone", "DualAxisDeadzoneData", "axis1", "axis2"),
    ],
)
def test_axis_pair_reads_its_axes(
    module: str, cls: str, first: str, second: str
) -> None:
    import importlib

    data = getattr(importlib.import_module(f"action_plugins.{module}"), cls)
    action = data(_A)
    found = _axes_read(action, first, second)
    assert [(r.role, r.target, r.not_found) for r in found] == [
        ("reads-input", references.input_ref(_STICK, _A, 1), False)
    ]
    assert found[0].text.startswith(f"{data.name}: ")
    assert references.input_label(_A, 1) in found[0].text
    setattr(action, second, getattr(action, first))
    assert len(list(action.references())) == 2
