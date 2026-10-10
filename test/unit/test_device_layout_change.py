# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""A device that changes layout under the same id (an Xbox pad the reader
switches from XInput to DirectInput: 6 axes 1, 2, 4, 5, 7, 8 and 10 buttons
became 5 axes 1-5 and 16 buttons).

Before: the stored device copy (input cache) kept the old layout, because
only devices new to the list were re-read; the next profile start read
axis 3 of the new layout from the old copy, "Invalid axis 3", and the whole
start failed. Spec 02 S142 (gap D2G1), 02 S143 (D2G3), 06 S91 (D2G2),
02 S146 (TX1).
"""

from __future__ import annotations

import logging
import sys

sys.path.append(".")

from collections.abc import Iterator
from typing import Any

import pytest

import dill
from gremlin import (
    device_initialization,
    error,
    event_handler,
    input_cache,
    log_once,
    macro,
    trace,
)
from gremlin.input_refresh import RefreshPhysicalInputs
from gremlin.input_tester import devices as tester_devices
from gremlin.input_tester.model import InputTesterModel
from test import fake_hardware

_STICK = dill.GUID(fake_hardware.raw_guid(is_virtual=False)).uuid


def _relaid(axis_ids: list[int], buttons: int) -> dill._DeviceSummary:
    """The fake stick, same id, another layout."""
    dev = fake_hardware.raw_device(is_virtual=False)
    for i in range(8):
        aid = axis_ids[i] if i < len(axis_ids) else 0
        dev.axis_map[i] = dill._AxisMap(linear_index=i + 1, axis_index=aid)
    dev.axis_count = len(axis_ids)
    dev.button_count = buttons
    return dev


@pytest.fixture
def listed() -> Iterator[list]:
    """The fake driver's device list, put back (and re-read) afterwards."""
    devices = dill.DILL._dll.devices
    before = list(devices)
    device_initialization.joystick_devices_initialization()
    input_cache.Joystick()[_STICK]  # the cached copy exists, as in a Run
    yield devices
    devices[:] = before
    device_initialization.joystick_devices_initialization()
    input_cache.Joystick().reconnected(_STICK)


def _swap_stick(devices: list, new: dill._DeviceSummary) -> None:
    for i, dev in enumerate(devices):
        if bytes(dev.device_guid) == bytes(new.device_guid):
            devices[i] = new


def test_a_layout_change_on_re_read_rebuilds_the_cached_copy(
    listed: list,
    event_listener: event_handler.EventListener,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """02 S142 / D2G1: the user's log, step by step: the pad changes layout
    (no device added or gone), then another device is plugged in and the
    profile restarts; the start reads every axis of the new layout."""
    monkeypatch.setattr(event_listener, "device_change_event",
                        type("E", (), {"emit": staticmethod(lambda: None)})())
    _swap_stick(listed, _relaid([1, 2, 3, 4, 5], 16))
    event_listener._run_device_list_update()  # the layout change
    second = fake_hardware.raw_device(is_virtual=False)
    second.device_guid = dill._GUID(Data1=0x7711, Data2=3, Data3=4,
                                    Data4=(1, 2, 3, 4, 5, 6, 7, 8))
    second.name = b"Second pad"
    listed.append(second)
    event_listener._run_device_list_update()  # a second pad plugged in

    wrapper = input_cache.Joystick()[_STICK]
    assert wrapper.axis_count == 5 and wrapper.button_count == 16
    assert wrapper.axis(4) is not None  # was: "Invalid axis 4"
    assert wrapper.button(16) is not None

    queued: list[Any] = []
    monkeypatch.setattr(macro.MacroManager(), "queue_macro", queued.append)
    monkeypatch.setattr(log_once, "log_once", lambda *a: pytest.fail(a[3]))
    RefreshPhysicalInputs.refresh_axes()  # the start step that failed
    sent = sorted(
        a.input_id for m in queued for a in m.sequence
        if getattr(a, "device_guid", None) == _STICK
    )
    assert sent == [1, 2, 3, 4, 5]


def test_a_layout_change_is_logged_and_traced(
    listed: list, monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """02 S143 / D2G3: one system.log INFO line and one Trace EVENT line;
    the scan counts it as a change (unplug + plug-in)."""
    events: list[str] = []
    monkeypatch.setattr(trace, "event", events.append)
    _swap_stick(listed, _relaid([1, 2, 3, 4, 5], 16))
    with caplog.at_level(logging.INFO, logger="system"):
        device_initialization.joystick_devices_initialization()
    lines = [e for e in events if "changed layout" in e]
    assert lines == [
        "pJoy Pro changed layout: 6 axes, 64 buttons, 2 hats → "
        "5 axes, 16 buttons, 2 hats, axes 1, 2, 3, 6, 7, 8 → 1, 2, 3, 4, 5, "
        "buttons 64 → 16"
    ]
    infos = [r for r in caplog.records
             if r.levelno == logging.INFO and "changed layout" in r.getMessage()]
    assert [r.getMessage() for r in infos] == lines
    assert device_initialization.layout_changed() == {_STICK}
    stick = device_initialization.device_for_uuid(_STICK)
    assert stick.axis_count == 5  # the list follows too (was: kept the old one)
    # The same layout read again is no change.
    device_initialization.joystick_devices_initialization()
    assert device_initialization.layout_changed() == set()


def test_an_axis_that_cannot_be_read_does_not_stop_the_start(
    listed: list, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """06 S91 / D2G2: the control is skipped and logged once; the other
    axes are still sent."""
    listener = event_handler.EventListener()
    real = listener.axis_value

    def axis_value(guid: Any, axis_id: int) -> float:  # noqa: ANN401
        if guid == _STICK and axis_id == 3:
            raise error.GremlinError("Invalid axis 3")
        return real(guid, axis_id)

    monkeypatch.setattr(listener, "axis_value", axis_value)
    queued: list[Any] = []
    monkeypatch.setattr(macro.MacroManager(), "queue_macro", queued.append)
    logged: list[tuple] = []
    monkeypatch.setattr(log_once, "log_once", lambda *a: logged.append(a))
    RefreshPhysicalInputs.refresh_axes()  # was: raised, the start failed
    sent = sorted(
        a.input_id for m in queued for a in m.sequence
        if getattr(a, "device_guid", None) == _STICK
    )
    assert sent == [1, 2, 6, 7, 8]
    assert len(logged) == 1
    logger, _key, level, text = logged[0]
    assert logger == "system" and level == logging.WARNING
    assert "pJoy Pro" in text and "Axis 3" in text and "skipped" in text


def test_the_input_tester_follows_a_layout_change() -> None:
    """02 S146 / TX1: same device id, another layout: the tester's row and
    the axes it reads follow the new one (was: kept the old copy)."""
    guid = "{11111111-2222-3333-4444-555555555555}"

    def seen(axis_ids: list[int], buttons: int) -> tester_devices.SeenDevice:
        return tester_devices.SeenDevice(
            key=f"di:{guid}", kind="directinput", name="Pad", vid=0x045E,
            pid=0x02FF, guid=guid, axes=len(axis_ids), buttons=buttons,
            hats=1, axis_ids=axis_ids,
        )

    now = [seen([1, 2, 4, 5, 7, 8], 10)]
    polled: list[list[int]] = []

    def poll(device: tester_devices.SeenDevice) -> tester_devices.LiveValues:
        polled.append(list(device.axis_ids))
        return tester_devices.LiveValues([], [], [])

    model = InputTesterModel(
        None, snapshot=lambda: list(now), poll=poll, hid_list=lambda: [],
        steam_running=lambda: False, start_timers=False,
        hid_scan=lambda: ([], []),
    )
    model.refresh()
    now[:] = [seen([1, 2, 3, 4, 5], 16)]
    polled.clear()
    model.check_changes()
    row = next(r for r in model._rows if r["live"])
    assert (row["axisCount"], row["buttonCount"]) == (5, 16)
    assert polled and polled[-1] == [1, 2, 3, 4, 5]
