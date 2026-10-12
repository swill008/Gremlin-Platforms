# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Search (to-do 9): gremlin.usages finds every use of an input, an output, a
mode or an action type in a profile, read back from its XML: Map to vJoy,
Xbox, Keyboard and Logical Device, macro steps, conditions, Change Mode
(Switch and Temporary), mode inheritance, and a binding whose output is not
found."""

from __future__ import annotations

import pathlib
import sys
import uuid
from collections.abc import Iterator
from xml.etree import ElementTree

sys.path.append(".")

import pytest

from gremlin import macro, shared_state
from gremlin.logical_device import LogicalDevice
from gremlin.modules import ids, output
from gremlin.types import InputType

B = InputType.JoystickButton
_STICK = uuid.UUID("{4DCB3090-97EC-11EB-8003-444553540000}")
_KEY_A = (0x1E, False)

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


@pytest.fixture
def made(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> Iterator[dict]:
    """A profile using every kind in every role, saved and read back."""
    from action_plugins.chain import ChainData
    from action_plugins.change_mode import ChangeModeData, ChangeType
    from action_plugins.condition import ConditionData
    from action_plugins.condition import condition as ca
    from action_plugins.description import DescriptionData
    from action_plugins.macro import MacroData
    from action_plugins.map_to_keyboard import MapToKeyboardData
    from action_plugins.map_to_logical_device import MapToLogicalDeviceData
    from action_plugins.map_to_vjoy import MapToVjoyData
    from action_plugins.map_to_xbox import MapToXboxData
    from action_plugins.root import RootData
    from gremlin import keyboard
    from gremlin.profile import InputItemBinding, Profile
    from vigem.xbox import XboxTarget

    # vJoy 9 is the one output that can't be sent; Xbox pads all can.
    monkeypatch.setattr(
        output,
        "cant_send_text",
        lambda v, k, c: "vJoy 9 is not Found." if int(v) == 9 else None,
    )
    monkeypatch.setattr(output, "xbox_cant_send_text", lambda pad: None)

    control = LogicalDevice().create(B)
    profile = Profile()
    monkeypatch.setattr(shared_state, "current_profile", profile)
    profile.modes.add_mode("Flight")
    profile.modes.set_parent("Flight", "Default")

    def bind(guid: uuid.UUID, input_id: object, mode: str, *actions: object) -> None:
        input_type = InputType.Keyboard if guid == ids.KEYBOARD else B
        item = profile.get_input_item(guid, input_type, input_id, mode, True)
        assert item is not None
        root = RootData(B)
        root.children = list(actions)
        binding = InputItemBinding(item)
        binding.root_action = root
        binding.behavior = B
        item.action_sequences.append(binding)
        for action in [root, *actions]:
            profile.library.add_action(action)

    def vjoy(vjoy_id: int, input_id: int) -> MapToVjoyData:
        action = MapToVjoyData(B)
        action.vjoy_device_id = vjoy_id
        action.vjoy_input_type = B
        action.vjoy_input_id = input_id
        return action

    def described(*actions: object) -> list:
        for action in actions:
            profile.library.add_action(action)
        return list(actions)

    bind(_STICK, 1, "Default", vjoy(2, 30))
    bind(_STICK, 1, "Flight", vjoy(3, 1))
    xbox = MapToXboxData(B)
    xbox.xbox_device_id = 1
    xbox.xbox_target = XboxTarget.A
    chain = ChainData(B)
    chain.chain_sequences = [described(xbox)]
    bind(_STICK, 2, "Default", chain)
    keys = MapToKeyboardData(B)
    keys.keys = [keyboard.key_from_code(*_KEY_A)]
    bind(_STICK, 3, "Default", keys)
    logical = MapToLogicalDeviceData(B)
    logical.logical_input_type = B
    logical.logical_input_id = control.id
    bind(_STICK, 4, "Default", logical)
    steps = MacroData()
    steps.actions = [
        macro.VJoyAction(2, B, 30, True),
        macro.KeyAction(keyboard.key_from_code(*_KEY_A), True),
        macro.JoystickAction(_STICK, B, 1, True),
        macro.LogicalDeviceAction(B, control.id, True),
    ]
    bind(_STICK, 5, "Default", steps)
    checks = ConditionData(B)
    vjoy_check = ca.VJoyCondition()
    vjoy_check.start_on(2, B, 30)
    keyboard_check = ca.KeyboardCondition()
    keyboard_check.from_xml(ElementTree.fromstring(_KEYBOARD_CONDITION))
    joystick_check = ca.JoystickCondition()
    joystick_check.from_xml(ElementTree.fromstring(_JOYSTICK_CONDITION))
    checks.conditions = [
        vjoy_check,
        keyboard_check,
        joystick_check,
        ca.LogicalDeviceCondition(),
    ]
    note = DescriptionData(B)
    checks.true_actions = described(note)
    bind(_STICK, 6, "Default", checks)
    switch = ChangeModeData(B)
    switch.change_type = ChangeType.Switch
    switch.target_modes = ["Flight"]
    bind(_STICK, 7, "Default", switch)
    temporary = ChangeModeData(B)
    temporary.change_type = ChangeType.Temporary
    temporary.target_modes = ["Flight"]
    bind(_STICK, 8, "Default", temporary)
    bind(ids.KEYBOARD, _KEY_A, "Default", vjoy(1, 1))
    bind(ids.LOGICAL_DEVICE, control.id, "Default", DescriptionData(B))
    bind(_STICK, 9, "Default", vjoy(9, 1))

    path = tmp_path / "usages.xml"
    profile.to_xml(path)
    loaded = Profile()
    monkeypatch.setattr(shared_state, "current_profile", loaded)
    loaded.from_xml(path)
    yield {"profile": loaded, "control": control}


def _find(profile: object, **query: object) -> list:
    from gremlin import usages

    return usages.find(profile, usages.Query(**query))  # type: ignore[arg-type]


def _where(found: list) -> list[tuple[str, object, str]]:
    return [(u.role, u.input_id, u.mode) for u in found]


def test_every_role_is_found(made: dict) -> None:
    from gremlin import usages

    roles = {ref.usage.role for ref in usages.iter_usages(made["profile"])}
    assert roles == set(usages.ROLES)
    assert set(usages.ROLE_TITLES) == set(usages.ROLES)


def test_vjoy_output_map_macro_step_and_condition(made: dict) -> None:
    found = _find(
        made["profile"],
        kind="output",
        output="vjoy",
        output_id=2,
        input_type=B.value,
        input_id=30,
    )
    assert _where(found) == [
        ("sends-output", 1, "Default"),
        ("sends-output", 5, "Default"),
        ("checks-output", 6, "Default"),
    ]
    step = found[1]
    assert step.text.startswith("In a macro")
    assert step.path[-1] == "Step 1"
    assert {u.device_guid for u in found} == {str(_STICK)}
    assert not any(u.not_found for u in found)
    # The whole vJoy device when no control is given.
    whole = _find(made["profile"], kind="output", output="vjoy", output_id=2)
    assert len(whole) == 3


def test_xbox_output_nested_in_a_chain(made: dict) -> None:
    found = _find(
        made["profile"], kind="output", output="xbox", output_id=1, input_id="a"
    )
    assert _where(found) == [("sends-output", 2, "Default")]
    assert found[0].path[0] == "Chain"
    assert _find(
        made["profile"], kind="output", output="xbox", output_id=1, input_id="b"
    ) == []


def test_joystick_input_read_sent_and_checked(made: dict) -> None:
    found = _find(
        made["profile"],
        kind="input",
        device_guid=str(_STICK),
        input_type=B.value,
        input_id=1,
    )
    roles = [u.role for u in found]
    assert roles == ["sends-output", "reads-input", "reads-input", "checks-input"]
    assert {u.mode for u in found if u.role == "reads-input"} == {
        "Default",
        "Flight",
    }
    # Braces and capitals don't matter.
    other = _find(
        made["profile"],
        kind="input",
        device_guid="{" + str(_STICK).upper() + "}",
        input_type=B.value,
        input_id=1,
    )
    assert len(other) == len(found)


def test_key_input_in_every_role(made: dict) -> None:
    found = _find(
        made["profile"],
        kind="input",
        device_guid=str(ids.KEYBOARD),
        input_type=InputType.Keyboard.value,
        input_id=list(_KEY_A),
    )
    assert [(u.role, u.input_id) for u in found] == [
        ("sends-output", 3),
        ("sends-output", 5),
        ("reads-input", _KEY_A),
        ("checks-input", 6),
    ]


def test_logical_device_control_in_every_role(made: dict) -> None:
    control = made["control"]
    found = _find(
        made["profile"],
        kind="input",
        device_guid=str(ids.LOGICAL_DEVICE),
        input_type=B.value,
        input_id=control.id,
    )
    assert [(u.role, u.input_id) for u in found] == [
        ("sends-output", 4),
        ("sends-output", 5),
        ("reads-input", control.id),
        ("checks-input", 6),
    ]


def test_mode_switch_runs_and_inherited(made: dict) -> None:
    found = _find(made["profile"], kind="mode", mode="Flight")
    switches = [u for u in found if u.role == "switches-mode"]
    assert [u.input_id for u in switches] == [7, 8]
    assert "Temporary" in switches[1].text
    runs = [u for u in found if u.role == "runs-in-mode"]
    assert [(u.input_id, u.mode) for u in runs] == [(1, "Flight")]
    inherited = [u for u in found if u.role == "inherited"]
    # Flight has its own button 1, so Default's isn't inherited there.
    assert 1 not in [u.input_id for u in inherited if u.device_guid == str(_STICK)]
    assert 2 in [u.input_id for u in inherited]
    assert all(u.mode == "Default" for u in inherited)
    assert all("Default" in u.text for u in inherited)
    # Grouped in role order.
    from gremlin import usages

    order = [usages.ROLES.index(u.role) for u in found]
    assert order == sorted(order)


def test_action_type(made: dict) -> None:
    found = _find(made["profile"], kind="action", action_tag="macro")
    assert _where(found) == [("uses-action", 5, "Default")]
    assert len(_find(made["profile"], kind="action", action_tag="change-mode")) == 2


def test_binding_output_not_found(made: dict) -> None:
    found = _find(made["profile"], kind="output", output="vjoy", output_id=9)
    assert [(u.role, u.input_id, u.not_found) for u in found] == [
        ("sends-output", 9, True)
    ]
    reads = _find(
        made["profile"],
        kind="input",
        device_guid=str(_STICK),
        input_type=B.value,
        input_id=9,
    )
    assert [(u.role, u.not_found) for u in reads] == [("reads-input", True)]
    assert not any(
        u.not_found
        for u in _find(made["profile"], kind="mode", mode="Default")
        if u.input_id != 9
    )


def test_unknown_kind_and_empty_profile() -> None:
    from gremlin import usages
    from gremlin.profile import Profile

    assert usages.find(Profile(), usages.Query(kind="mode", mode="Default")) == []
    assert usages.find(None, usages.Query(kind="input")) == []
    assert usages.find(Profile(), usages.Query(kind="nonsense")) == []
