# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Every macro step and every condition declares what it uses
(references()); a new step or condition type without it fails."""

from __future__ import annotations

import sys
import uuid
from xml.etree import ElementTree

sys.path.append(".")

import pytest

from gremlin import error, keyboard, macro
from gremlin import references as refs
from gremlin.logical_device import LogicalDevice
from gremlin.modules import ids, output
from gremlin.types import InputType, MouseButton

B = InputType.JoystickButton
_STICK = uuid.UUID("{4DCB3090-97EC-11EB-8003-444553540000}")

_KEYBOARD_CONDITION = """<condition>
<property type="string"><name>condition-type</name><value>keyboard</value></property>
<input>
<property type="int"><name>scan-code</name><value>30</value></property>
<property type="bool"><name>is-extended</name><value>false</value></property>
</input>
<comparator>
<property type="string"><name>comparator-type</name><value>pressed</value></property>
<property type="bool"><name>is-pressed</name><value>true</value></property>
</comparator>
</condition>"""

_JOYSTICK_CONDITION = f"""<condition>
<property type="string"><name>condition-type</name><value>joystick</value></property>
<input>
<property type="uuid"><name>device-guid</name><value>{_STICK}</value></property>
<property type="string"><name>device-name</name><value>Stick</value></property>
<property type="input_type"><name>input-type</name><value>button</value></property>
<property type="int"><name>input-id</name><value>1</value></property>
</input>
<comparator>
<property type="string"><name>comparator-type</name><value>pressed</value></property>
<property type="bool"><name>is-pressed</name><value>true</value></property>
</comparator>
</condition>"""


def _one(piece: object) -> refs.Reference:
    found = list(piece.references())  # type: ignore[attr-defined]
    assert len(found) == 1, found
    return found[0]


def test_every_step_type_declares_its_own_references() -> None:
    for step_type in macro.STEP_TYPES.values():
        assert "references" in vars(step_type), step_type.__name__


def test_a_step_type_without_references_cannot_be_made() -> None:
    class NoReferences(macro.AbstractAction):
        tag = "no-references"

        def __call__(self) -> None:
            pass

        @classmethod
        def create(cls) -> NoReferences:
            return cls()

        def to_xml(self) -> ElementTree.Element:
            return ElementTree.Element("macro-action")

        def from_xml(self, node: ElementTree.Element) -> None:
            pass

        def is_valid(self) -> bool:
            return True

    with pytest.raises(TypeError, match="references"):
        NoReferences()


def test_vjoy_step_sends_output_and_is_not_found_by_the_cant_send_rule(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        output,
        "cant_send_text",
        lambda v, k, c: "vJoy 9 is not Found." if int(v) == 9 else None,
    )
    sent = _one(macro.VJoyAction(2, B, 30, True))
    assert sent.role == "sends-output"
    assert sent.target == ("vjoy", 2, B.value, 30)
    assert sent.text.startswith("vJoy 2 ")
    assert not sent.not_found
    assert _one(macro.VJoyAction(9, B, 1, True)).not_found


def test_key_step_sends_the_key_and_an_empty_one_points_at_nothing() -> None:
    sent = _one(macro.KeyAction(keyboard.key_from_code(0x1E, False), True))
    assert sent.role == "sends-output"
    assert sent.target == ("input", ids.guid_key(ids.KEYBOARD),
                           InputType.Keyboard.value, (0x1E, False))
    assert list(macro.KeyAction(None, True).references()) == []


def test_joystick_step_sends_the_device_input() -> None:
    sent = _one(macro.JoystickAction(_STICK, B, 3, True))
    assert sent.role == "sends-output"
    assert sent.target == refs.input_ref(_STICK, B, 3)


def test_logical_device_step_and_its_missing_control() -> None:
    control = LogicalDevice().create(B)
    sent = _one(macro.LogicalDeviceAction(B, control.id, True))
    assert sent.target == refs.input_ref(ids.LOGICAL_DEVICE, B, control.id)
    assert sent.text.startswith("Logical Device ")
    assert not sent.not_found

    gone = macro.LogicalDeviceAction(B, control.id, True)
    LogicalDevice().delete(control.identifier)
    assert _one(gone).not_found
    assert list(macro.LogicalDeviceAction(B, None, True).references()) == []


def test_mouse_steps_point_at_the_mouse() -> None:
    button = _one(macro.MouseButtonAction(MouseButton.Right, True))
    assert button.role == "sends-output"
    assert button.target == ("mouse", "Right")
    assert button.text == "Mouse Right"
    wheel = _one(macro.MouseButtonAction(MouseButton.WheelUp, True))
    assert wheel.target == ("mouse", "WheelUp")
    motion = _one(macro.MouseMotionAction(5, 0))
    assert motion.target == ("mouse", "Motion")


def test_pause_and_unchosen_osc_steps_point_at_nothing() -> None:
    assert list(macro.PauseAction(0.5).references()) == []
    assert list(macro.OscAction(None, B, True).references()) == []


def test_conditions_check_what_they_name() -> None:
    from action_plugins.condition import condition as ca

    vjoy_check = ca.VJoyCondition()
    vjoy_check.start_on(2, B, 30)
    checked = _one(vjoy_check)
    assert checked.role == "checks-output"
    assert checked.target == ("vjoy", 2, B.value, 30)

    key_check = ca.KeyboardCondition()
    key_check.from_xml(ElementTree.fromstring(_KEYBOARD_CONDITION))
    checked = _one(key_check)
    assert checked.role == "checks-input"
    assert checked.target == refs.keyboard((0x1E, False))

    stick_check = ca.JoystickCondition()
    stick_check.from_xml(ElementTree.fromstring(_JOYSTICK_CONDITION))
    checked = _one(stick_check)
    assert checked.role == "checks-input"
    assert checked.target == refs.input_ref(_STICK, B, 1)

    assert list(ca.CurrentInputCondition().references()) == []


def test_logical_device_condition_and_its_missing_control() -> None:
    from action_plugins.condition import condition as ca

    control = LogicalDevice().create(B)
    check = ca.LogicalDeviceCondition()
    check._states = [ca.LogicalDeviceCondition.State(B, control.id)]
    checked = _one(check)
    assert checked.role == "checks-input"
    assert checked.target == refs.input_ref(ids.LOGICAL_DEVICE, B, control.id)
    assert not checked.not_found

    LogicalDevice().delete(control.identifier)
    check._states = [ca.LogicalDeviceCondition.State(B, control.id, "gone")]
    assert _one(check).not_found


def test_every_condition_type_declares_its_own_references() -> None:
    from action_plugins.condition import condition as ca

    for kind in (
        ca.VJoyCondition,
        ca.KeyboardCondition,
        ca.JoystickCondition,
        ca.CurrentInputCondition,
        ca.LogicalDeviceCondition,
    ):
        assert "references" in vars(kind), kind.__name__

    class NoReferences(ca.AbstractCondition):
        pass

    with pytest.raises(error.MissingImplementationError):
        NoReferences().references()


def test_not_found_steps_and_conditions_say_why(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from action_plugins.condition import condition as ca

    monkeypatch.setattr(
        output,
        "cant_send_text",
        lambda v, k, c: "vJoy 9 is not Found." if int(v) == 9 else None,
    )
    assert _one(macro.VJoyAction(9, B, 1, True)).why == "vJoy 9 is not Found."
    assert _one(macro.VJoyAction(2, B, 1, True)).why == ""

    control = LogicalDevice().create(B)
    step = macro.LogicalDeviceAction(B, control.id, True)
    check = ca.LogicalDeviceCondition()
    check._states = [ca.LogicalDeviceCondition.State(B, control.id)]
    assert _one(step).why == "" and _one(check).why == ""
    LogicalDevice().delete(control.identifier)
    check._states = [ca.LogicalDeviceCondition.State(B, control.id, "gone")]
    assert _one(step).why.endswith("is not Found.")
    assert _one(check).why.endswith("is not Found.")
