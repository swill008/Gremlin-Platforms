# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Fake joystick driver (dill.dll) and vJoy queries for tests.

test/unit and test/action_interaction install these before anything starts,
so a test run never reads the real joysticks or vJoy: it gives the same
results on every PC and cannot get in the way of a Gremlin-Platforms that
is open on the same PC. test/integration keeps the real ones on purpose
(it drives a real vJoy device as a loopback).
"""

from __future__ import annotations

from collections.abc import Callable

import dill
from vjoy import vjoy


def raw_guid(is_virtual: bool) -> dill._GUID:
    """The "raw" _GUID of a fake device."""
    return dill._GUID(
        Data1=501018480 + int(is_virtual),
        Data2=264,
        Data3=4592,
        Data4=(128, 4, 68, 69, 83, 84, 0, 0),
    )


def raw_device(is_virtual: bool) -> dill._DeviceSummary:
    """A repeatable fake device, as dill.dll describes one (data from a vJoy device)."""
    axis_map_array = (dill._AxisMap * 8)()
    for i, (linear_i, axis_i) in enumerate(
        [(1, 1), (2, 2), (3, 3), (4, 6), (5, 7), (6, 8), (7, 0), (8, 0)]
    ):
        axis_map_array[i] = dill._AxisMap(linear_index=linear_i, axis_index=axis_i)
    return dill._DeviceSummary(
        device_guid=raw_guid(is_virtual),
        vendor_id=0x1234 if is_virtual else 0x5678,
        product_id=0xBEAD if is_virtual else 0xFACE,
        joystick_id=0 if is_virtual else 1,
        name=b"vJoy Device" if is_virtual else b"pJoy Pro",
        axis_count=6,
        button_count=64,
        hat_count=2,
        axis_map=axis_map_array,
    )


def _same_guid(a: dill._GUID, b: dill._GUID) -> bool:
    return bytes(a) == bytes(b)


class FakeDill:
    """Stands in for dill.dll: the same functions, no DirectInput, no thread."""

    def __init__(self, devices: list[dill._DeviceSummary]) -> None:
        self.devices = list(devices)
        self.input_event_callback: Callable | None = None
        self.device_change_callback: Callable | None = None

    def init(self) -> None:
        pass

    def set_input_event_callback(self, callback: Callable) -> None:
        self.input_event_callback = callback

    def set_device_change_callback(self, callback: Callable) -> None:
        self.device_change_callback = callback

    def get_device_count(self) -> int:
        return len(self.devices)

    def get_device_information_by_index(self, index: int) -> dill._DeviceSummary:
        if 0 <= index < len(self.devices):
            return self.devices[index]
        return dill._DeviceSummary()

    def get_device_information_by_guid(self, guid: dill._GUID) -> dill._DeviceSummary:
        for device in self.devices:
            if _same_guid(device.device_guid, guid):
                return device
        return dill._DeviceSummary()

    def device_exists(self, guid: dill._GUID) -> bool:
        return any(_same_guid(d.device_guid, guid) for d in self.devices)

    def get_axis(self, guid: dill._GUID, index: int) -> int:
        return 0

    def get_button(self, guid: dill._GUID, index: int) -> bool:
        return False

    def get_hat(self, guid: dill._GUID, index: int) -> int:
        return -1


def install(vjoy_ids: tuple[int, ...] = (1,)) -> FakeDill:
    """Uses the fake driver and fake vJoy queries from now on.

    Two fake joysticks (a "pJoy Pro" and a "vJoy Device"), and the vJoy
    devices in vjoy_ids, each with 6 axes (1, 2, 3, 6, 7, 8), 64 buttons and
    2 hats.
    """
    fake = FakeDill([raw_device(is_virtual=False), raw_device(is_virtual=True)])
    dill.DILL._dll = fake  # type: ignore[assignment]
    dill.DILL._dill_initialized = False
    ids = set(vjoy_ids)
    vjoy.device_exists = lambda vjoy_id: vjoy_id in ids  # type: ignore[assignment]
    # The fake vJoy Device's axes (raw_device's axis map: X, Y, Z, RZ, SL0,
    # SL1), answered where the driver is asked, so vjoy.axis_ids and the
    # output module see them; never the real driver, which CI doesn't have
    # and this PC answers for its own vJoy. A test may still set its own.
    axis_codes = {0x30, 0x31, 0x32, 0x35, 0x36, 0x37}
    vjoy.VJoyInterface.GetVJDAxisExist = staticmethod(  # type: ignore[attr-defined]
        lambda vjoy_id, code: int(vjoy_id in ids and code in axis_codes)
    )
    vjoy.axis_count = lambda vjoy_id: 6  # type: ignore[assignment]
    vjoy.button_count = lambda vjoy_id: 64  # type: ignore[assignment]
    vjoy.hat_count = lambda vjoy_id: 2  # type: ignore[assignment]
    vjoy.hat_configuration_valid = lambda vjoy_id: True  # type: ignore[assignment]
    return fake

