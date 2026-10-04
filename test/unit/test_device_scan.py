# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The device scan (device_initialization) when devices change.

Before: an error during a scan (vJoy checks) left its lock held, so every
later device update (hot-plug) blocked for good, with the error lost on a
timer thread; and every scan found every device "removed" (objects were
compared, not ids), so every device event released all vJoy devices, even
in the middle of play.
"""

from __future__ import annotations

import sys

sys.path.append(".")

from collections.abc import Iterator
from unittest import mock

import pytest

import dill
from gremlin import device_initialization, error, event_handler
from gremlin.modules import output
from gremlin.signal import signal
from test import fake_hardware
from vjoy import vjoy


@pytest.fixture
def devices() -> Iterator[list]:
    listed = dill.DILL._dll.devices
    before = list(listed)
    device_initialization.joystick_devices_initialization()
    yield listed
    listed[:] = before
    device_initialization._joystick_devices.clear()
    device_initialization.joystick_devices_initialization()


def _stick(n: int) -> dill._DeviceSummary:
    dev = fake_hardware.raw_device(is_virtual=False)
    dev.device_guid = dill._GUID(
        Data1=0x7700 + n, Data2=3, Data3=4, Data4=(1, 2, 3, 4, 5, 6, 7, n)
    )
    dev.name = f"Stick {n}".encode()
    return dev


def test_a_scan_error_does_not_leave_the_lock_held(devices: list) -> None:
    devices.append(_stick(1))  # a change, so the vJoy checks run
    with (
        mock.patch.object(vjoy, "hat_configuration_valid", return_value=False),
        pytest.raises(error.GremlinError),
    ):
        device_initialization.joystick_devices_initialization()
    lock = device_initialization._joystick_init_lock
    assert lock.acquire(blocking=False), "lock still held: hot-plug would block"
    lock.release()


def test_nothing_changed_resets_nothing(devices: list) -> None:
    with mock.patch.object(output, "reset_vjoy") as reset:
        device_initialization.joystick_devices_initialization()
    reset.assert_not_called()  # was: every scan released all vJoy devices


def test_plugging_in_a_stick_does_not_reset_vjoy(devices: list) -> None:
    devices.append(_stick(2))
    with mock.patch.object(output, "reset_vjoy") as reset:
        device_initialization.joystick_devices_initialization()
    reset.assert_not_called()
    names = [d.name for d in device_initialization.physical_devices()]
    assert "Stick 2" in names


def test_a_vjoy_change_still_resets_vjoy(devices: list) -> None:
    device_initialization._joystick_devices.clear()  # as at start
    with mock.patch.object(output, "reset_vjoy") as reset:
        device_initialization.joystick_devices_initialization()
    reset.assert_called_once()


def test_hot_plug_error_is_shown_not_lost(
    event_listener: event_handler.EventListener,
) -> None:
    shown: list[tuple[str, str]] = []

    def record(message: str, details: str) -> None:
        shown.append((message, details))

    signal.showError.connect(record)
    try:
        with mock.patch.object(
            device_initialization,
            "joystick_devices_initialization",
            side_effect=error.GremlinError("vJoy id 2: Hats are set to discrete"),
        ):
            event_listener._run_device_list_update()
    finally:
        signal.showError.disconnect(record)
    assert shown and "discrete" in shown[0][1]
