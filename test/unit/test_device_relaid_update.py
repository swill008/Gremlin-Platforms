# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""02 S143 (D2G3): a device that changes layout under the same id is an
unplug + plug-in for the device list update: what it held is let go, its
cached copy follows the new layout, and one device change is announced
(was: no device added or gone, so nothing happened)."""

from __future__ import annotations

import sys

sys.path.append(".")

from collections.abc import Iterator

import pytest

import dill
from gremlin import device_initialization, event_handler, input_cache
from test import fake_hardware

_STICK = dill.GUID(fake_hardware.raw_guid(is_virtual=False)).uuid


def _relaid(axis_ids: list[int], buttons: int) -> dill._DeviceSummary:
    dev = fake_hardware.raw_device(is_virtual=False)
    for i in range(8):
        aid = axis_ids[i] if i < len(axis_ids) else 0
        dev.axis_map[i] = dill._AxisMap(linear_index=i + 1, axis_index=aid)
    dev.axis_count = len(axis_ids)
    dev.button_count = buttons
    return dev


@pytest.fixture
def listed() -> Iterator[list]:
    devices = dill.DILL._dll.devices
    before = list(devices)
    device_initialization.joystick_devices_initialization()
    input_cache.Joystick()[_STICK]
    yield devices
    devices[:] = before
    device_initialization.joystick_devices_initialization()
    input_cache.Joystick().reconnected(_STICK)


def test_s143_a_layout_change_lets_go_and_announces_one_change(
    listed: list,
    event_listener: event_handler.EventListener,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    emitted: list[bool] = []
    monkeypatch.setattr(
        event_listener, "device_change_event",
        type("E", (), {"emit": staticmethod(lambda: emitted.append(True))})(),
    )
    let_go: list[object] = []
    monkeypatch.setattr(event_listener, "_let_go", let_go.append)
    for i, dev in enumerate(listed):
        if dill.GUID(dev.device_guid).uuid == _STICK:
            listed[i] = _relaid([1, 2, 3, 4, 5], 16)
    event_listener._run_device_list_update()
    assert emitted == [True]
    assert let_go == [_STICK]
    assert input_cache.Joystick()[_STICK].button_count == 16
    # Read again, same layout: no change.
    event_listener._run_device_list_update()
    assert emitted == [True]
