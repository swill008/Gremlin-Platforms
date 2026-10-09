# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Macro steps and script variables point at Logical Device controls by
their permanent id (D-04-LD-FILE, "Reference XML"); the profile check
reads the one Logical Device and flags an id it doesn't know (decision 4).

A saved reference writes `uid` beside its type and number. On load the uid
wins (the control may have a new number); an unknown uid is missing:
nothing runs, it is kept on save and never re-targeted by number. Data
saved before ids falls back to the v14 load map, then type+number.
"""

from __future__ import annotations

import sys
import types
import uuid
from collections.abc import Iterator
from typing import Any
from xml.etree import ElementTree

sys.path.append(".")

import pytest
from PySide6 import QtCore

from gremlin import logical_device_file, macro, user_script, validate
from gremlin.logical_device import LogicalDevice
from gremlin.types import InputType

pytestmark = pytest.mark.validate_off

_APPS: list[QtCore.QCoreApplication] = []
_UNKNOWN = "f" * 32


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


@pytest.fixture
def ld() -> Iterator[LogicalDevice]:
    """The Logical Device emptied for the test and put back afterwards."""
    device = LogicalDevice()
    saved = device.to_dict()
    device.load_dict({"controls": [], "groups": []})
    yield device
    logical_device_file.current_uid_map = None
    device.load_dict(saved)


def _ident(input_type: InputType, input_id: int) -> LogicalDevice.Input.Identifier:
    return LogicalDevice.Input.Identifier(input_type, input_id)


def _renumber(device: LogicalDevice, uid: str, new_id: int) -> None:
    """Gives the control `uid` the number `new_id`, keeping its uid (as the
    file would after the user renumbered it)."""
    data = device.to_dict()
    for row in data["controls"]:
        if row["uid"] == uid:
            row["id"] = new_id
    device.load_dict(data)


# --- macro steps --------------------------------------------------------------


def _step_xml(
    input_id: int, uid: str | None, input_type: InputType = InputType.JoystickButton
) -> ElementTree.Element:
    step = macro.LogicalDeviceAction(input_type, input_id, True)
    node = step.to_xml()
    node.attrib.pop("uid", None)
    if uid is not None:
        node.set("uid", uid)
    return node


def _load_step(node: ElementTree.Element) -> macro.LogicalDeviceAction:
    step = macro.LogicalDeviceAction(InputType.JoystickButton, None, False)
    step.from_xml(node)
    return step


def test_a_macro_step_saves_the_uid(ld: LogicalDevice) -> None:
    made = ld.create(InputType.JoystickButton)
    step = macro.LogicalDeviceAction(InputType.JoystickButton, made.id, True)
    node = step.to_xml()
    assert node.get("uid") == made.uid
    assert node.find("./property[name='input-id']") is not None


def test_a_macro_step_follows_its_uid_to_the_new_number(ld: LogicalDevice) -> None:
    made = ld.create(InputType.JoystickButton)
    node = _step_xml(made.id, made.uid)
    _renumber(ld, made.uid, 7)
    step = _load_step(node)
    assert (step.input_type, step.input_id) == (InputType.JoystickButton, 7)
    assert step.is_valid()
    assert step.to_xml().get("uid") == made.uid


def test_an_unknown_uid_is_missing_and_never_retargeted(ld: LogicalDevice) -> None:
    other = ld.create(InputType.JoystickButton, 1)
    other.update(False)
    step = _load_step(_step_xml(1, _UNKNOWN))
    assert step.is_missing()
    assert not step.is_valid()
    step()  # does nothing at runtime
    assert not other.is_pressed
    # Kept on save: the saved uid, not the uid of control 1.
    assert step.to_xml().get("uid") == _UNKNOWN


def test_old_macro_data_uses_the_v14_map_then_the_number(ld: LogicalDevice) -> None:
    first = ld.create(InputType.JoystickButton, 1)
    moved = ld.create(InputType.JoystickButton, 4)
    # v14 load: the profile's button 2 was added to the file as button 4.
    logical_device_file.current_uid_map = {("button", 2): moved.uid}
    step = _load_step(_step_xml(2, None))
    assert step.input_id == 4
    assert step.to_xml().get("uid") == moved.uid
    logical_device_file.current_uid_map = None
    step = _load_step(_step_xml(1, None))
    assert step.input_id == 1
    assert step.to_xml().get("uid") == first.uid


# --- script variables ---------------------------------------------------------


def _variable() -> user_script.LogicalDeviceVariable:
    return user_script.LogicalDeviceVariable(
        "target", "", False, [InputType.JoystickButton]
    )


def _variable_xml(input_id: int, uid: str | None) -> ElementTree.Element:
    node = ElementTree.fromstring(
        '<variable type="logical-device">'
        '<property type="string"><name>name</name><value>target</value></property>'
        '<property type="input_type"><name>input-type</name><value>button</value>'
        "</property>"
        f'<property type="int"><name>input-id</name><value>{input_id}</value>'
        "</property></variable>"
    )
    if uid is not None:
        node.set("uid", uid)
    return node


def test_a_script_variable_saves_and_follows_its_uid(ld: LogicalDevice) -> None:
    made = ld.create(InputType.JoystickButton)
    var = _variable()
    var.from_xml(_variable_xml(made.id, None))
    saved = var.to_xml()
    assert saved is not None and saved.get("uid") == made.uid
    _renumber(ld, made.uid, 5)
    again = _variable()
    again.from_xml(saved)
    assert again.value.identifier == _ident(InputType.JoystickButton, 5)
    assert again.is_valid()


def test_a_script_variable_with_an_unknown_uid_is_kept(ld: LogicalDevice) -> None:
    ld.create(InputType.JoystickButton, 1)
    var = _variable()
    var.from_xml(_variable_xml(1, _UNKNOWN))
    assert var.is_missing()
    assert not var.is_valid()
    saved = var.to_xml()
    assert saved is not None and saved.get("uid") == _UNKNOWN


# --- profile check ------------------------------------------------------------


def _check(actions: list[Any], rows: Any = None) -> list[str]:  # noqa: ANN401
    out: list[str] = []
    stub = types.SimpleNamespace(logical_device=rows)
    validate._check_logical(stub, out, {uuid.uuid4(): a for a in actions})  # type: ignore[arg-type]
    return out


def _map_action(input_id: int, uid: str | None) -> types.SimpleNamespace:
    return types.SimpleNamespace(
        logical_input_type=InputType.JoystickButton,
        logical_input_id=input_id,
        logical_input_uid=uid,
        name="Map to Logical Device",
    )


def test_the_check_flags_an_unknown_uid_even_when_the_number_exists(
    ld: LogicalDevice,
) -> None:
    made = ld.create(InputType.JoystickButton, 1)
    assert _check([_map_action(1, made.uid)]) == []
    problems = _check([_map_action(1, _UNKNOWN)])
    assert [validate.code_of(p) for p in problems] == ["PROFILE-LOGICAL-MISSING"]


def test_the_check_reads_the_one_logical_device_not_profile_rows(
    ld: LogicalDevice,
) -> None:
    # Stale per-profile rows holding the control don't hide it missing.
    from gremlin.logical_device import LogicalRows

    stale = LogicalRows()
    stale.create(InputType.JoystickButton, 3)
    problems = _check([_map_action(3, None)], rows=stale)
    assert [validate.code_of(p) for p in problems] == ["PROFILE-LOGICAL-MISSING"]


def test_the_check_flags_a_map_action_that_reports_itself_missing(
    ld: LogicalDevice,
) -> None:
    from gremlin import plugin_manager, shared_state
    from gremlin.profile import Profile

    before = shared_state.current_profile
    shared_state.current_profile = Profile()
    try:
        _map_action_reports_missing(ld, plugin_manager)
    finally:
        shared_state.current_profile = before


def _map_action_reports_missing(ld: LogicalDevice, plugin_manager: Any) -> None:  # noqa: ANN401
    ld.create(InputType.JoystickButton, 1)
    action: Any = plugin_manager.PluginManager().create_instance(
        "Map to Logical Device", InputType.JoystickButton
    )
    action.logical_input_id = 1
    assert not action.logical_missing
    assert _check([action]) == []
    action._logical_input_uid = _UNKNOWN  # saved id the file doesn't have
    assert action.logical_missing
    problems = _check([action])
    assert [validate.code_of(p) for p in problems] == ["PROFILE-LOGICAL-MISSING"]


# --- stored uid: delete + recreate under the same number ---------------------


def _delete_and_recreate(device: LogicalDevice, input_id: int) -> Any:  # noqa: ANN401
    device.delete(_ident(InputType.JoystickButton, input_id))
    return device.create(InputType.JoystickButton, input_id)


def test_a_loaded_macro_step_is_not_retargeted_by_a_recreated_number(
    ld: LogicalDevice,
) -> None:
    made = ld.create(InputType.JoystickButton, 1)
    step = _load_step(_step_xml(1, made.uid))
    assert not step.is_missing()
    again = _delete_and_recreate(ld, 1)
    again.update(False)
    assert step.is_missing()
    assert not step.is_valid()
    step()
    assert not again.is_pressed
    assert step.to_xml().get("uid") == made.uid


def test_a_loaded_script_variable_is_not_retargeted_by_a_recreated_number(
    ld: LogicalDevice,
) -> None:
    made = ld.create(InputType.JoystickButton, 1)
    var = _variable()
    var.from_xml(_variable_xml(1, made.uid))
    assert var.is_valid()
    _delete_and_recreate(ld, 1)
    assert var.is_missing()
    assert not var.is_valid()
    saved = var.to_xml()
    assert saved is not None and saved.get("uid") == made.uid


def test_setting_the_number_points_the_stored_uid_at_that_control(
    ld: LogicalDevice,
) -> None:
    ld.create(InputType.JoystickButton, 1)
    second = ld.create(InputType.JoystickButton, 2)
    step = macro.LogicalDeviceAction(InputType.JoystickButton, 1, True)
    step.input_id = 2
    assert step.uid == second.uid
    step.uid = _UNKNOWN
    assert step.is_missing()


def test_one_resolver_for_every_reference() -> None:
    import action_plugins.map_to_logical_device as mapping
    from gremlin import logical_device

    assert mapping.resolve_logical_reference is logical_device.resolve_logical_reference
    assert macro.resolve_logical_reference is logical_device.resolve_logical_reference
    assert user_script.resolve_logical_reference is (
        logical_device.resolve_logical_reference
    )


def test_the_v14_map_accepts_the_enum_name(ld: LogicalDevice) -> None:
    from gremlin.logical_device import resolve_logical_reference

    made = ld.create(InputType.JoystickButton, 6)
    logical_device_file.current_uid_map = {("JoystickButton", 2): made.uid}
    assert resolve_logical_reference(None, InputType.JoystickButton, 2) == (
        _ident(InputType.JoystickButton, 6),
        made.uid,
    )


# --- reading an action never adds a control ----------------------------------


def test_reading_a_map_action_leaves_an_empty_logical_device_empty_and_clean(
    ld: LogicalDevice, tmp_path: Any  # noqa: ANN401
) -> None:
    from action_plugins.map_to_logical_device import MapToLogicalDeviceData
    from gremlin import shared_state
    from gremlin.profile import Profile

    before = shared_state.current_profile
    try:
        made = Profile()
        shared_state.current_profile = made
        item = made.get_input_item(
            uuid.UUID("5a1d0000-1111-2222-3333-444444444444"),
            InputType.JoystickButton,
            1,
            "Default",
            create_if_missing=True,
        )
        assert item is not None
        binding = item.add_item_binding()
        assert binding.root_action is not None
        # A new action made in the editor still gets a control to drive.
        action = made.library.create("Map to Logical Device", InputType.JoystickButton)
        assert isinstance(action, MapToLogicalDeviceData)
        binding.root_action.insert_action(action, "children")
        assert len(ld.inputs_of_type()) == 1
        path = tmp_path / "with_map.xml"
        made.to_xml(path)

        # The Logical Device file has no controls; reading the profile
        # (and copying the action) adds none and changes nothing.
        ld.load_dict({"controls": [], "groups": []})
        ld.mark_saved()
        loaded = Profile()
        shared_state.current_profile = loaded
        loaded.from_xml(path)
        read = [
            a
            for a in loaded.library._actions.values()
            if isinstance(a, MapToLogicalDeviceData)
        ]
        assert len(read) == 1
        assert read[0].logical_missing
        assert ld.inputs_of_type() == []
        assert ld.dirty is False
    finally:
        shared_state.current_profile = before
