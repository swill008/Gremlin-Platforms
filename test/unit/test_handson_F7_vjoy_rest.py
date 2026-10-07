# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""A vJoy device the program lets go of is put at rest first (06 S17,
decision D-06-VJOY-REST): every button up, every hat centred, every axis
centred, and the next Run starts from rest.

Hands-on finding (claude/hands-on-results/02-06-devices-runtime.md): the
release ran ResetVJD and then wrote every cached value back, so a held
button stayed pressed after Stop or quit and was pressed again at the next
Run. The driver here is a stand-in for vjoyinterface.dll (no real vJoy).
"""

from __future__ import annotations

import ctypes
import os
from collections.abc import Iterator
from unittest import mock

import pytest

from gremlin.types import HatDirection
from vjoy import vjoy

_VID = 9  # not one the other unit tests use
_AXIS_MAX = 32767
_CENTRE = 16384  # what Axis writes for 0.0 with this range


class _FakeDriver:
    """vjoyinterface.dll for one vJoy device: 3 axes, 8 buttons, 1 hat."""

    def __init__(self) -> None:
        self.owned = False
        self.buttons: dict[int, bool] = {}
        self.axes: dict[int, int] = {}
        self.povs: dict[int, int] = {}

    def functions(self) -> dict[str, object]:
        axis_codes = [a.value for a in vjoy.AxisCode][:3]

        def axis_range(value: int):  # noqa: ANN202
            def fn(vid: int, axis: int, out: object) -> bool:
                ctypes.cast(out, ctypes.POINTER(ctypes.c_ulong))[0] = value
                return True

            return fn

        def status(vid: int) -> int:
            state = vjoy.VJoyState.Owned if self.owned else vjoy.VJoyState.Free
            return state.value

        def acquire(vid: int) -> bool:
            self.owned = True
            return True

        def relinquish(vid: int) -> None:
            self.owned = False

        def reset(vid: int) -> bool:
            self.buttons = {}
            self.povs = {}
            self.axes = {}
            return True

        def set_btn(pressed: bool, vid: int, index: int) -> bool:
            self.buttons[index] = bool(pressed)
            return True

        def set_axis(value: int, vid: int, axis: int) -> bool:
            self.axes[axis] = value
            return True

        def set_pov(value: int, vid: int, index: int) -> bool:
            self.povs[index] = value
            return True

        return {
            "vJoyEnabled": lambda: True,
            "GetvJoyVersion": lambda: 0x219,
            "GetVJDStatus": status,
            "GetOwnerPid": lambda vid: os.getpid() if self.owned else 0,
            "AcquireVJD": acquire,
            "RelinquishVJD": relinquish,
            "GetVJDAxisExist": lambda vid, code: 1 if code in axis_codes else 0,
            "GetVJDAxisMin": axis_range(0),
            "GetVJDAxisMax": axis_range(_AXIS_MAX),
            "GetVJDButtonNumber": lambda vid: 8,
            "GetVJDDiscPovNumber": lambda vid: 0,
            "GetVJDContPovNumber": lambda vid: 1,
            "ResetVJD": reset,
            "SetBtn": set_btn,
            "SetAxis": set_axis,
            "SetContPov": set_pov,
        }

    def pressed(self) -> list[int]:
        return sorted(i for i, down in self.buttons.items() if down)

    def at_rest(self) -> bool:
        return (
            not self.pressed()
            and all(v == -1 for v in self.povs.values())
            and all(v == _CENTRE for v in self.axes.values())
        )


@pytest.fixture
def driver() -> Iterator[_FakeDriver]:
    from gremlin.modules import output

    fake = _FakeDriver()
    cache = vjoy.VJoyStateCache()
    cache._cache.pop(_VID, None)
    with mock.patch.multiple(vjoy.VJoyInterface, create=True, **fake.functions()):
        kept = vjoy.VJoyProxy.vjoy_devices
        vjoy.VJoyProxy.vjoy_devices = {}
        try:
            yield fake
        finally:
            output._stop_keep_alive()
            for dev in vjoy.VJoyProxy.vjoy_devices.values():
                dev.vjoy_id = None
            vjoy.VJoyProxy.vjoy_devices = kept
            cache._cache.pop(_VID, None)


def _hold_everything() -> vjoy.VJoy:
    dev = vjoy.VJoyProxy()[_VID]
    dev.button(3).is_pressed = True
    dev.button(8).is_pressed = True
    dev.hat(1).direction = HatDirection.North
    dev.axis(1).value = 0.7
    dev.axis(3).value = -1.0
    return dev


def _release(how: str) -> None:
    from gremlin.modules import output

    # Stop's DRIVERS stage and quit both call reset_drivers; a vJoy device
    # change calls reset_vjoy. Every one ends in VJoy.invalidate.
    getattr(output, how)()


@pytest.mark.parametrize("how", ["reset_drivers", "reset_vjoy"])
def test_a_released_vjoy_is_left_at_rest(driver: _FakeDriver, how: str) -> None:
    _hold_everything()
    assert driver.pressed() == [3, 8]

    _release(how)

    assert not driver.owned
    assert driver.pressed() == []
    assert driver.povs == {1: -1}
    assert all(v == _CENTRE for v in driver.axes.values()), driver.axes


def test_the_next_run_starts_from_rest(driver: _FakeDriver) -> None:
    _hold_everything()
    _release("reset_drivers")

    dev = vjoy.VJoyProxy()[_VID]  # the next Run opens the device again

    assert driver.owned
    assert driver.pressed() == []
    assert driver.at_rest(), (driver.buttons, driver.povs, driver.axes)
    assert not dev.button(3).is_pressed
    assert dev.hat(1).direction == HatDirection.Center
    assert dev.axis(1).value == 0.0


def test_keep_alive_reset_keeps_what_is_held(driver: _FakeDriver) -> None:
    """The keep-alive's reset (06 S54) is not a release: what a Run holds
    stays held."""
    dev = _hold_everything()

    dev.reset()

    assert driver.pressed() == [3, 8]
    assert driver.povs == {1: 0}
