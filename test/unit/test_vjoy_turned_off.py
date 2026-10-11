# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""A vJoy device turned off in the vJoy configuration tool (the driver no
longer lists it) while its output module still claims controls: the Map to
vJoy picker (05 S118, S136), its refresh on a device change, and writes at
Run (06 S47, 01 S148)."""

from __future__ import annotations

import logging
from types import SimpleNamespace
from unittest import mock

import pytest

from gremlin import device_initialization, event_handler
from gremlin.modules import output
from gremlin.ui import output_modules

# vJoy 3 and vJoy 4 output modules; each claims buttons 1-32 and axes 1-8.
_CLAIM = {"axes": list(range(1, 9)), "buttons": list(range(1, 33)), "hats": []}


class _Driver:
    """The vJoy devices the driver lists; switch them off and on."""

    def __init__(self, on: set[int]) -> None:
        self.on = set(on)

    def devices(self) -> list[SimpleNamespace]:
        return [
            SimpleNamespace(vjoy_id=v, axis_map=[], button_count=32, hat_count=0)
            for v in sorted(self.on)
        ]

    def layout(self, vjoy_id: int) -> tuple[int, int, int]:
        return (8, 32, 0) if int(vjoy_id) in self.on else (0, 0, 0)

    def axes(self, vjoy_id: int) -> set[int]:
        return set(range(1, 9)) if int(vjoy_id) in self.on else set()


@pytest.fixture
def driver() -> _Driver:
    drv = _Driver({3, 4})
    modules = [
        (3, SimpleNamespace(name="vJoy 3", claim=_CLAIM)),
        (4, SimpleNamespace(name="vJoy 4", claim=_CLAIM)),
    ]
    with (
        mock.patch.object(output, "vjoy_modules", return_value=modules),
        mock.patch.object(device_initialization, "vjoy_devices", drv.devices),
        mock.patch.object(output, "vjoy_layout", drv.layout),
        mock.patch.object(output, "vjoy_axis_ids", drv.axes),
    ):
        yield drv


@pytest.fixture
def listener() -> mock.MagicMock:
    with mock.patch.object(event_handler, "EventListener") as el:
        yield el


def _picker(listener: mock.MagicMock) -> output_modules.OutputModuleDevices:
    devices = output_modules.OutputModuleDevices()
    devices.validTypes = ["button"]
    return devices


def _writes(devices: output_modules.OutputModuleDevices) -> list[tuple]:
    seen: list[tuple] = []
    devices.currentSelectionChanged.connect(lambda *args: seen.append(args))
    return seen


# --- (1) picking a vJoy that is off ------------------------------------------


def test_picking_a_vjoy_that_is_off_moves_to_the_same_control(
    driver: _Driver, listener: mock.MagicMock
) -> None:
    driver.on = {3}
    picker = _picker(listener)
    picker.setInitialState(3, "button", 5)
    writes = _writes(picker)
    # The device box changed to vJoy 4; the input box still says Button 5.
    picker.setState("vJoy 4", "Button 5")

    assert writes == [(4, "button", 5)]  # never id 0, never an invalid control
    assert picker.inputChoices[-1] == "⚠ Button 5"  # can't be sent while off
    assert picker.currentReason == "vJoy 4 is not Found."
    assert "vJoy 4" in picker.vjoyDevices


def test_picking_an_off_vjoy_falls_back_to_its_first_claimed_control(
    driver: _Driver, listener: mock.MagicMock
) -> None:
    driver.on = {3}
    picker = _picker(listener)
    # A saved wire to vJoy 3's Button 40 (claims 1-32): kept and flagged.
    picker.setInitialState(3, "button", 40)
    writes = _writes(picker)
    picker.setState("vJoy 4", "⚠ Button 40")

    assert writes == [(4, "button", 1)]


def test_saved_wire_to_an_off_vjoy_shows_cant_send(
    driver: _Driver, listener: mock.MagicMock
) -> None:
    driver.on = {3}
    picker = _picker(listener)
    writes = _writes(picker)
    picker.setInitialState(4, "button", 7)

    assert writes == []  # kept as saved (03 S30)
    assert picker.currentUnclaimed  # can't be sent (D-05-CANT-SEND)
    assert picker.currentReason == "vJoy 4 is not Found."
    assert "⚠ Button 7" in picker.inputChoices
    assert "Button 7" not in picker.inputChoices


# --- (2) turned off / on while the program runs --------------------------------


def test_picker_rereads_on_the_cant_send_notice(
    driver: _Driver, listener: mock.MagicMock
) -> None:
    """The picker follows the output layer's notice (D-05-CANT-SEND-LIVE),
    which a vJoy device-list change sends."""
    from gremlin.signal import signal

    picker = _picker(listener)
    picker.setInitialState(4, "button", 7)
    assert "Button 7" in picker.inputChoices

    driver.on = {3}  # vJoy 4 turned off in the vJoy configuration tool
    signal.cantSendChanged.emit()
    assert "⚠ Button 7" in picker.inputChoices
    assert "Button 7" not in picker.inputChoices

    driver.on = {3, 4}  # and on again
    signal.cantSendChanged.emit()
    assert "Button 7" in picker.inputChoices
    assert not any(label.startswith("⚠") for label in picker.inputChoices)


# --- (3) at Run --------------------------------------------------------------


@pytest.fixture
def in_a_run() -> object:
    from gremlin import run_scope

    run_scope.begin()
    output.clear_blocked_log()
    yield
    run_scope.stop()
    run_scope._reset_for_tests()


def test_write_to_an_off_vjoy_is_blocked_and_logged_once_per_run(
    in_a_run: object, caplog: pytest.LogCaptureFixture
) -> None:
    from vjoy import vjoy

    opened: list[int] = []

    class _Proxy:
        vjoy_devices: dict = {}

        def __getitem__(self, index: int) -> object:
            opened.append(index)
            raise RuntimeError("Requested vJoy device is not available")

    results: list[str] = []
    now = [100.0]
    with (
        mock.patch.object(output, "vjoy_claim", return_value=_CLAIM),
        mock.patch.object(output, "_vjoy_proxy", return_value=_Proxy),
        mock.patch.object(output, "vjoy_driver_found", return_value=True),
        mock.patch.object(vjoy, "device_exists", lambda vid: int(vid) != 4),
        mock.patch.object(output.clock, "monotonic", lambda: now[0]),
        mock.patch.object(output.trace, "enabled", return_value=True),
        mock.patch.object(output.trace, "output", lambda *a: results.append(a[-1])),
        caplog.at_level(logging.DEBUG),
    ):
        for _ in range(5):
            assert not output.write_vjoy(4, "button", 2, True)
            now[0] += 10.0  # past the open retry time
        warned = [r for r in caplog.records if "vJoy 4" in r.getMessage()]
        assert len(warned) == 1
        assert opened == []  # the driver is never asked to open an off vJoy
        # Trace: BLOCKED (01 S148: missing and blocked show as BLOCKED).
        assert results and all(r.startswith("missing") for r in results)

        output.clear_blocked_log()  # next Run
        caplog.clear()
        assert not output.write_vjoy(4, "button", 2, True)
        assert len([r for r in caplog.records if "vJoy 4" in r.getMessage()]) == 1
