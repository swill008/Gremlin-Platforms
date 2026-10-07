# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The fake hardware answers which axes a vJoy device has (CI run
37697695524).

test/fake_hardware.py faked the vJoy axis, button and hat counts but not
vjoy.axis_ids, so the output module (and the Auto Mapper through it) asked the
real vJoy driver which axes exist. On this PC that is the user's vJoy, with
8 axes; on CI there is none, so every axis was "not on the vJoy device" and
test_automap_1to1_journey's axes were never mapped. A test run must not
reach the driver at all.
"""

from __future__ import annotations

import pathlib
from collections.abc import Iterator
from typing import Any

import pytest

from vjoy import vjoy

_ROOT = pathlib.Path(__file__).resolve().parents[2]


@pytest.fixture
def fake_hardware() -> Iterator[Any]:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "fake_hardware_ax", _ROOT / "test" / "fake_hardware.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    names = (
        "device_exists",
        "axis_ids",
        "axis_count",
        "button_count",
        "hat_count",
        "hat_configuration_valid",
    )
    import dill

    saved = {name: getattr(vjoy, name) for name in names}
    asked = vjoy.VJoyInterface.__dict__.get("GetVJDAxisExist")
    driver = (dill.DILL._dll, dill.DILL._dill_initialized)
    try:
        yield module
    finally:
        # install() is for a whole process: this one gets its own back.
        for name, value in saved.items():
            setattr(vjoy, name, value)
        dill.DILL._dll, dill.DILL._dill_initialized = driver
        if asked is None:
            if "GetVJDAxisExist" in vars(vjoy.VJoyInterface):
                delattr(vjoy.VJoyInterface, "GetVJDAxisExist")
        else:
            vjoy.VJoyInterface.GetVJDAxisExist = asked


def test_the_vjoy_axes_come_from_the_fake_not_the_driver(
    fake_hardware: Any,  # noqa: ANN401
) -> None:
    from gremlin.modules import output

    fake_hardware.install(vjoy_ids=(1,))
    # The fake answers where the driver is asked: the real vJoyInterface.dll
    # (here: this PC's vJoy; on CI: none) is not reached.
    assert vjoy.VJoyInterface.GetVJDAxisExist(1, vjoy.AxisCode.X.value) == 1
    axes = output.vjoy_axis_ids(1)
    # The fake vJoy Device's axes (X, Y, Z, then RZ and sliders: 1, 2, 3, 6,
    # 7, 8), and none for a vJoy device it doesn't have.
    assert axes == {1, 2, 3, 6, 7, 8}
    assert vjoy.axis_count(1) == len(axes)
    assert output.vjoy_axis_ids(2) == set()
