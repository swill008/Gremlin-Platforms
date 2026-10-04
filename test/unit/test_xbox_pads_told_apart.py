# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Real Xbox controllers versus Gremlin's own virtual Xbox pads.

Every device with the Xbox 360 hardware ID (045E:028E, also a genuine wired
360 pad) or a name with "xbox 360 ... windows" was taken for one of
Gremlin's pads and dropped from the device list, and any module whose name
held "xbox" was taken for Gremlin's Xbox output, so a real pad's inputs
were blocked. Now Gremlin's own pads are the ones it plugged in
(vigem.own_pads), and only Gremlin's own Xbox module names are outputs.
"""

from __future__ import annotations

import sys

sys.path.append(".")

from collections.abc import Iterator

import pytest

import dill
from gremlin import device_initialization
from gremlin.config import Configuration
from gremlin.modules import registry
from gremlin.modules.output import is_xbox_module
from vigem import own_pads


def _xbox_device(n: int, name: bytes) -> dill._DeviceSummary:
    guid = dill._GUID(
        Data1=0x5800 + n, Data2=1, Data3=2, Data4=(8, 7, 6, 5, 4, 3, 2, n)
    )
    return dill._DeviceSummary(
        device_guid=guid, vendor_id=0x045E, product_id=0x028E, joystick_id=10 + n,
        name=name, axis_count=6, button_count=10, hat_count=1,
        axis_map=(dill._AxisMap * 8)(),
    )


@pytest.fixture
def driver() -> Iterator[list]:
    """The fake driver's device list; anything added is taken away again."""
    devices = dill.DILL._dll.devices
    before = list(devices)
    own_pads.forget_all()
    stored = Configuration().value(*own_pads.SETTING)
    yield devices
    devices[:] = before
    own_pads.forget_all()
    Configuration().set(*own_pads.SETTING, stored)
    device_initialization.joystick_devices_initialization()


def _key(dev: dill._DeviceSummary) -> str:
    return own_pads._key(dill.GUID(dev.device_guid))


def test_real_xbox_pad_is_a_normal_device(driver: list) -> None:
    real = _xbox_device(1, b"Controller (XBOX 360 For Windows)")
    driver.append(real)
    device_initialization.joystick_devices_initialization()
    assert not own_pads.is_own_pad(dill.DeviceSummary(real))
    listed = [str(d.device_guid) for d in device_initialization.physical_devices()]
    assert str(dill.GUID(real.device_guid)) in listed  # it used to vanish


def test_the_pad_gremlin_plugs_in_is_its_own_and_remembered(driver: list) -> None:
    real = _xbox_device(1, b"Controller (XBOX 360 For Windows)")
    driver.append(real)
    own_pads.before_plug()  # what XboxPad does just before plugging
    mine = _xbox_device(2, b"Controller (XBOX 360 For Windows)")
    driver.append(mine)
    assert own_pads.note_device(dill.DeviceSummary(mine))  # the arrival
    assert not own_pads.is_own_pad(dill.DeviceSummary(real))
    assert _key(mine) in Configuration().value(*own_pads.SETTING)  # remembered

    own_pads._known = None  # a later session reads the settings
    own_pads._expect_until = 0.0
    assert own_pads.is_own_pad(dill.DeviceSummary(mine))
    device_initialization.joystick_devices_initialization()
    listed = [str(d.device_guid) for d in device_initialization.physical_devices()]
    assert str(dill.GUID(mine.device_guid)) not in listed
    assert str(dill.GUID(real.device_guid)) in listed


def test_a_device_arriving_later_is_not_taken(driver: list) -> None:
    own_pads.before_plug()
    own_pads._expect_until = 0.0  # the plug-in window has passed
    late = _xbox_device(3, b"Controller (XBOX 360 For Windows)")
    driver.append(late)
    assert not own_pads.note_device(dill.DeviceSummary(late))


@pytest.mark.parametrize(
    ("name", "output"),
    [
        ("Xbox 360 Controller", True),
        ("Xbox 360 2", True),
        ("Xbox pad 3", True),
        ("xbox", True),
        ("vJoy 1", True),
        ("Controller (XBOX 360 For Windows)", False),
        ("Controller (Xbox One For Windows)", False),
        ("Xbox Wireless Controller", False),
        ("Thrustmaster T.16000M", False),
    ],
)
def test_only_gremlins_xbox_names_are_outputs(name: str, output: bool) -> None:
    assert registry.is_output_name(name) is output
    assert (registry.module_direction({"device": name}) == "dest") is output
    if "vjoy" not in name.lower():
        assert is_xbox_module(name) is output
