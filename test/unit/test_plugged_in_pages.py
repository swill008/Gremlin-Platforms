# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Plugged in is decided by the Windows id, never by the name (03 S90a), on
the pages that ask: the Button Map's cover (07 S5-S8), Module Setup's Save
(03 S46) and the Home card's status (03 S73)."""

from __future__ import annotations

import uuid

import dill
from gremlin import device_initialization
from gremlin.ui import module_model
from gremlin.ui.viewer_devices import ViewerDeviceModel
from test import fake_hardware

_S46 = "Plug in pJoy Pro to change its setup. Nothing was saved."


def _pjoy_guid() -> str:
    return str(dill.GUID(fake_hardware.raw_guid(is_virtual=False)).uuid)


def _twin() -> dill._DeviceSummary:
    """A second "pJoy Pro" (the same name) with its own id."""
    raw = fake_hardware.raw_device(is_virtual=False)
    raw.device_guid = dill._GUID(
        Data1=777, Data2=1, Data3=2, Data4=(1, 2, 3, 4, 5, 6, 7, 8)
    )
    return raw


def _twin_guid() -> str:
    return str(dill.GUID(_twin().device_guid).uuid)


# Button Map cover (07 S5-S8) -------------------------------------------------


def test_button_map_of_a_stick_with_no_id_is_covered_though_its_name_is_in() -> None:
    # "pJoy Pro" is plugged in; a card with no id isn't it.
    assert ViewerDeviceModel().available("", "pJoy Pro") is False


def test_button_map_of_the_unplugged_one_of_two_identical_sticks_is_covered() -> None:
    model = ViewerDeviceModel()
    assert model.available(_pjoy_guid(), "pJoy Pro") is True
    assert model.available(_twin_guid(), "pJoy Pro") is False
    assert model.available("", "pJoy  Pro") is False


def test_button_map_shows_as_soon_as_the_stick_is_in_the_live_list() -> None:
    # Windows lists the twin before the program's own device list is rebuilt
    # (before it moves): its Button Map loads now, not when it moves.
    fake = dill.DILL._dll
    twin = _twin()
    fake.devices.append(twin)
    try:
        assert ViewerDeviceModel().available(_twin_guid(), "pJoy Pro") is True
    finally:
        fake.devices.remove(twin)


def test_button_map_built_ins_always_show() -> None:
    model = ViewerDeviceModel()
    assert model.available("", "vJoy Device 1") is True
    assert model.available(str(dill.UUID_Keyboard), "Keyboard") is True
    assert model.available(str(dill.UUID_LogicalDevice), "Logical Device") is True
    assert model.available(str(uuid.uuid4()), "Nowhere Stick") is False


# Module Setup (03 S46) -------------------------------------------------------


def test_module_setup_with_no_id_refuses_save() -> None:
    model = module_model.DriverInputModel()
    model.loadDevice("", "pJoy Pro")
    assert model.saveBlockedReason() == _S46


def test_module_setup_of_the_unplugged_twin_refuses_save() -> None:
    model = module_model.DriverInputModel()
    model.loadDevice(_twin_guid(), "pJoy Pro")
    assert model.saveBlockedReason() == _S46
    model.loadDevice(_pjoy_guid(), "pJoy Pro")
    assert model.saveBlockedReason() == ""


# Home card (03 S73) ----------------------------------------------------------


def test_home_cards_come_from_the_live_list_by_id() -> None:
    # A card says Connected only for a device in the live list; it carries
    # that device's id, so a same-named stick never lends it its status.
    ids = {
        str(d.device_guid) for d in device_initialization.joystick_devices()
    }
    model = module_model.ModuleListModel()
    sticks = [row for row in model._rows if row.tab == "physical"]
    assert sticks
    for row in sticks:
        assert row.guid in ids
        if row.status == "Connected":
            assert row.guid in ids
            assert module_model._device_connected(row.guid)
