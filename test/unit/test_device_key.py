# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""How a remembered device is recognised (12 S43), on real Windows ids."""

from __future__ import annotations

import pytest

from gremlin.device_key import device_key, device_numbers

STEAM_3 = r"HID\VID_28DE&PID_1302&COL03\A&E40AA7B&0&0002"
STEAM_1 = r"HID\VID_28DE&PID_1302&COL01\A&E40AA7B&0&0000"
MIC = r"HID\VID_352F&PID_0104&MI_03\B&12148D1&0&0000"
VKB = r"HID\VID_231D&PID_0200\A&6B6F223&0&0000"


@pytest.mark.parametrize(
    ("instance_id", "numbers"),
    [
        (STEAM_3, ("28DE", "1302", "", "03")),
        (MIC, ("352F", "0104", "03", "")),
        (r"HID\VID_231D&PID_2234\8&2FE8E01B&0&0000", ("231D", "2234", "", "")),
        (VKB, ("231D", "0200", "", "")),
        (r"HID\VID_231D&PID_3201\A&39CB7826&0&0000", ("231D", "3201", "", "")),
        (r"HID\{1812}_DEV_VID&0228DE_PID&1303&COL02\9&1", ("28DE", "1303", "", "02")),
        (r"HID\CUSTOM\1&VID_1111&PID_2222", ("", "", "", "")),
        ("", ("", "", "", "")),
    ],
)
def test_numbers(instance_id: str, numbers: tuple) -> None:
    assert device_numbers(instance_id) == numbers
    assert device_numbers(instance_id.lower()) == numbers


def test_same_device_in_another_port_has_the_same_key() -> None:
    other = r"HID\VID_231D&PID_0200\7&1111111&0&0000"
    assert device_key("VKB", VKB) == device_key("VKB", other)
    assert device_key("VKB", VKB) == device_key("VKB", VKB.lower())
    # Listed by its id when it has no name: still the same device.
    assert device_key(VKB, VKB) == device_key(other, other)


def test_name_model_and_part_keep_devices_apart() -> None:
    keys = {
        device_key("Steam Controller", STEAM_1),
        device_key("Steam Controller", STEAM_3),
        device_key("Steam Controller", STEAM_3.replace("1302", "1303")),
        device_key("Other", STEAM_3),
        device_key("Steam Controller", MIC),
    }
    assert len(keys) == 5


def test_without_maker_and_model_the_full_id() -> None:
    assert device_key("A", r"HID\Custom\1") == r"HID\CUSTOM\1"
    assert device_key("A", r"HID\Custom\1") != device_key("A", r"HID\Custom\2")
    assert device_key("A", r"HID\VID_231D\1") == r"HID\VID_231D\1"
