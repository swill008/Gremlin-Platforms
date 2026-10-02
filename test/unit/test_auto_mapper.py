# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import pathlib

import pytest

import dill
from gremlin import (
    auto_mapper,
    device_initialization,
    profile,
    shared_state,
    types,
)

_PROFILE_DEVICE_AXIS_COUNT = 4
_PROFILE_DEVICE_BUTTON_COUNT = 6
_PROFILE_DEVICE_HAT_COUNT = 1


@pytest.fixture
def register_profile_device() -> dill.DeviceSummary:
    """Registers the device in the test profile, and returns its DeviceSummary."""
    axis_map_array = (dill._AxisMap * 8)()
    for i, (linear_i, axis_i) in enumerate(
        [(1, 1), (2, 2), (3, 3), (4, 4), (5, 5), (6, 6), (7, 7), (8, 8)]
    ):
        axis_map_array[i] = dill._AxisMap(linear_index=linear_i, axis_index=axis_i)
    dev = dill.DeviceSummary(
        dill._DeviceSummary(
            device_guid=dill.GUID.from_str(
                "97b77b40-07d8-11f0-8028-444553540000"
            ).ctypes,
            vendor_id=0x5678,
            product_id=0xFACE,
            joystick_id=1,
            name=b"pJoy Pro",
            axis_count=_PROFILE_DEVICE_AXIS_COUNT,
            button_count=_PROFILE_DEVICE_BUTTON_COUNT,
            hat_count=_PROFILE_DEVICE_HAT_COUNT,
            axis_map=axis_map_array,
        )
    )

    for mocked_dev in device_initialization._joystick_devices.values():
        if mocked_dev.device_guid == dev.device_guid:
            yield dev
    else:
        device_initialization._joystick_devices[dev.device_guid.uuid] = dev
        yield dev
    for mocked_dev in list(device_initialization._joystick_devices.values()):
        if mocked_dev.device_guid == dev.device_guid:
            device_initialization._joystick_devices.pop(mocked_dev.device_guid.uuid)
            break


def test_get_used_vjoy_inputs_from_profile(
    subtests: pytest.Subtests,
    xml_dir: pathlib.Path,
    register_profile_device: dill.DeviceSummary,
) -> None:
    p = profile.Profile()
    p.from_xml(str(xml_dir / "profile_auto_mapper.xml"))
    shared_state.current_profile = p

    mapper = auto_mapper.AutoMapper(p)
    used_vjoy_inputs = mapper._get_used_vjoy_inputs("Default")

    assert len(used_vjoy_inputs) == 14

    with subtests.test("axis single mapping"):
        assert types.VjoyInput(1, types.InputType.JoystickAxis, 1) in used_vjoy_inputs

    with subtests.test("axis double mapping"):
        assert types.VjoyInput(2, types.InputType.JoystickAxis, 4) in used_vjoy_inputs
        assert types.VjoyInput(2, types.InputType.JoystickAxis, 5) in used_vjoy_inputs
        assert types.VjoyInput(1, types.InputType.JoystickAxis, 4) in used_vjoy_inputs
        assert types.VjoyInput(1, types.InputType.JoystickAxis, 5) in used_vjoy_inputs

    with subtests.test("button single mapping"):
        assert types.VjoyInput(1, types.InputType.JoystickButton, 1) in used_vjoy_inputs

    with subtests.test("button double mapping"):
        assert types.VjoyInput(2, types.InputType.JoystickButton, 5) in used_vjoy_inputs
        assert types.VjoyInput(2, types.InputType.JoystickButton, 6) in used_vjoy_inputs
        assert types.VjoyInput(1, types.InputType.JoystickButton, 5) in used_vjoy_inputs
        assert types.VjoyInput(1, types.InputType.JoystickButton, 6) in used_vjoy_inputs

    with subtests.test("hat mappings"):
        assert types.VjoyInput(1, types.InputType.JoystickHat, 1) in used_vjoy_inputs
        assert types.VjoyInput(1, types.InputType.JoystickHat, 2) in used_vjoy_inputs
        assert types.VjoyInput(2, types.InputType.JoystickHat, 1) in used_vjoy_inputs
        assert types.VjoyInput(2, types.InputType.JoystickHat, 2) in used_vjoy_inputs


def test_get_used_vjoy_inputs_from_empty_mode(
    xml_dir: pathlib.Path, register_profile_device: dill.DeviceSummary
) -> None:
    p = profile.Profile()
    p.from_xml(str(xml_dir / "profile_auto_mapper.xml"))
    shared_state.current_profile = p

    mapper = auto_mapper.AutoMapper(p)
    used_vjoy_inputs = mapper._get_used_vjoy_inputs("EmptyMode")

    assert len(used_vjoy_inputs) == 0


# Intentionally not using the register_profile_device fixture in this test.
def test_get_used_vjoy_inputs_for_disconnected_device_in_profile(
    xml_dir: pathlib.Path,
) -> None:
    p = profile.Profile()
    p.from_xml(str(xml_dir / "profile_auto_mapper.xml"))
    shared_state.current_profile = p

    mapper = auto_mapper.AutoMapper(p)
    used_vjoy_inputs = mapper._get_used_vjoy_inputs("Default")

    assert not len(used_vjoy_inputs)

