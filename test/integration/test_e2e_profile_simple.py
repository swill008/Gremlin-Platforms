# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""
Integration tests with a profile that does simple input forwarding.
"""

from __future__ import annotations

import itertools
import sys
import threading
import time
from collections.abc import Callable, Iterator
from unittest import mock

sys.path.append(".")

import pytest

import dill
import gremlin.input_cache
from action_plugins import map_to_vjoy
from gremlin import (
    clock,
    types,
    util,
)
from test.integration import app_tester
from vjoy import (
    vjoy,
    vjoy_interface,
)


@pytest.fixture
def patched_time() -> Iterator[threading.Semaphore]:
    """Runs the relative axis loops on a clock the test steps itself.

    Each sleep() waits for a release() on the yielded semaphore; now() is a
    counter that moves one step on each call.
    """
    time_stepper = threading.Semaphore(value=0)
    time_counter = itertools.count(
        step=map_to_vjoy.MapToVjoyFunctor.THREAD_SLEEP_DURATION_S
    )
    with (
        mock.patch.object(
            clock, "sleep", side_effect=lambda _: time_stepper.acquire(timeout=2)
        ),
        mock.patch.object(clock, "now", side_effect=lambda: next(time_counter)),
    ):
        yield time_stepper


def _settled(
    read: Callable[[], float], quiet: float = 0.2, limit: float = 3.0
) -> float:
    """read()'s value once it has stopped changing for quiet seconds."""
    deadline = time.monotonic() + limit
    last = read()
    since = time.monotonic()
    while time.monotonic() < deadline:
        time.sleep(0.02)
        value = read()
        if value != last:
            last, since = value, time.monotonic()
        elif time.monotonic() - since >= quiet:
            break
    return last


@pytest.fixture(scope="module")
def profile_name() -> str:
    return "e2e_profile_simple.xml"


class TestSimpleProfile:
    """Tests for a simple profile."""

    @pytest.mark.parametrize(
        "di_input",
        [
            32767,
            32766,
            32765,
            -2,
            -1,
            0,
            1,
            2,
            -32765,
            -32766,
            -32768,
        ],
    )
    def test_axis_sequential(
        self,
        subtests: pytest.Subtests,
        tester: app_tester.GremlinAppTester,
        vjoy_control_device: vjoy.VJoy,
        vjoy_di_device: dill.DeviceSummary,
        di_input: int,
    ) -> None:
        """Applies groups of sequential inputs."""
        self._test_axis(
            subtests,
            tester,
            vjoy_control_device,
            vjoy_di_device,
            di_input,
        )

    @pytest.mark.parametrize(
        "di_input",
        [
            32767,
            -2,
            32766,
            -1,
            32765,
            22937,
            16384,
            6554,
            0,
            -32766,
            1,
            -32767,
            2,
            -6554,
            -16384,
            -22940,
            0,
            -32768,
        ],
    )
    def test_axis_large_steps(
        self,
        subtests: pytest.Subtests,
        tester: app_tester.GremlinAppTester,
        vjoy_control_device: vjoy.VJoy,
        vjoy_di_device: dill.DeviceSummary,
        di_input: int,
    ) -> None:
        """Applies fixed sequence of inputs with large steps."""
        self._test_axis(
            subtests,
            tester,
            vjoy_control_device,
            vjoy_di_device,
            di_input,
        )

    def _test_axis(
        self,
        subtests: pytest.Subtests,
        tester: app_tester.GremlinAppTester,
        vjoy_control_device: vjoy.VJoy,
        vjoy_di_device: dill.DeviceSummary,
        di_input: int,
    ) -> None:
        input_axis_id = 1
        output_axis_id = 3
        calibrated_value = util.with_default_center_calibration(di_input)
        vjoy_control_device.axis(linear_index=input_axis_id).value = calibrated_value
        with subtests.test("input readback"):
            tester.assert_axis_eventually_equals(
                vjoy_di_device.device_guid, input_axis_id, di_input
            )
        with subtests.test("input axis cache"):
            tester.assert_cached_axis_eventually_equals(
                vjoy_di_device.device_guid.uuid, input_axis_id, calibrated_value
            )
        with subtests.test("output axis cache"):
            tester.assert_cached_axis_eventually_equals(
                vjoy_di_device.device_guid.uuid, output_axis_id, calibrated_value
            )
        tester.assert_axis_eventually_equals(
            vjoy_di_device.device_guid, output_axis_id, di_input
        )

    def test_axis_relative(
        self,
        subtests: pytest.Subtests,
        patched_time: threading.Semaphore,
        tester: app_tester.GremlinAppTester,
        vjoy_control_device: vjoy.VJoy,
        vjoy_di_device: dill.DeviceSummary,
    ) -> None:
        """Verifies relative axis changes over time."""
        input_axis_id = 2
        output_axis_id = 4
        sleep_calls_per_subtest = 10
        step_size = (
            map_to_vjoy.MapToVjoyFunctor.SCALING_MULTIPLIER
            * map_to_vjoy.MapToVjoyData.DEFAULT_SCALING
        )
        cache = gremlin.input_cache.Joystick()[vjoy_di_device.device_guid.uuid]
        for di_input, direction, subtest_count in [
            (tester.AXIS_MAX_INT, 1, 3),
            (-tester.AXIS_MAX_INT, -1, 6),
        ]:
            calibrated_value = util.with_default_center_calibration(di_input)
            vjoy_control_device.axis(
                linear_index=input_axis_id
            ).value = calibrated_value
            with subtests.test("input readback"):
                tester.assert_axis_eventually_equals(
                    vjoy_di_device.device_guid, input_axis_id, di_input
                )
            with subtests.test("input axis cache"):
                tester.assert_cached_axis_eventually_equals(
                    vjoy_di_device.device_guid.uuid, input_axis_id, calibrated_value
                )
            # The loop may step before the input has settled (with a value on
            # the way): count from where the output is once it is paused.
            start = _settled(lambda: cache.axis(output_axis_id).value)
            for n in range(1, subtest_count + 1):
                expected = start + direction * n * sleep_calls_per_subtest * step_size
                with subtests.test(
                    "output", di_input=di_input, steps=n * sleep_calls_per_subtest
                ):
                    patched_time.release(sleep_calls_per_subtest)
                    tester.assert_cached_axis_eventually_equals(
                        vjoy_di_device.device_guid.uuid, output_axis_id, expected
                    )
                    tester.assert_axis_eventually_equals(
                        vjoy_di_device.device_guid,
                        output_axis_id,
                        expected * tester.AXIS_MAX_INT,
                    )

        # Let go of the stick: the relative axis stops driving the output a
        # second (100 clock steps) later, and its thread ends.
        vjoy_control_device.axis(
            linear_index=input_axis_id
        ).value = util.with_default_center_calibration(0)
        tester.assert_cached_axis_eventually_equals(
            vjoy_di_device.device_guid.uuid,
            input_axis_id,
            util.with_default_center_calibration(0),
        )
        patched_time.release(200)
        axis_threads = [t for t in threading.enumerate() if "relative axis" in t.name]
        assert axis_threads, "no relative axis thread found"
        for thread in axis_threads:
            thread.join(timeout=5)
            assert not thread.is_alive(), "the relative axis kept running"

    @pytest.mark.parametrize(
        ("di_input", "vjoy_output", "cached_value"),
        [(False, 0, False), (True, 1, True), (False, 0, False), (True, 1, True)],
    )
    def test_button(
        self,
        tester: app_tester.GremlinAppTester,
        vjoy_control_device: vjoy.VJoy,
        vjoy_di_device: dill.DeviceSummary,
        di_input: bool,
        vjoy_output: int,
        cached_value: bool | None,
    ) -> None:
        input_button_id = 1
        output_button_id = 3
        vjoy_control_device.button(index=input_button_id).is_pressed = di_input
        tester.assert_button_eventually_equals(
            vjoy_di_device.device_guid, input_button_id, vjoy_output
        )
        tester.assert_cached_button_eventually_equals(
            vjoy_di_device.device_guid.uuid, input_button_id, cached_value
        )
        tester.assert_cached_button_eventually_equals(
            vjoy_di_device.device_guid.uuid, output_button_id, cached_value
        )
        tester.assert_button_eventually_equals(
            vjoy_di_device.device_guid, output_button_id, vjoy_output
        )

    @pytest.mark.parametrize(
        ("di_input", "vjoy_output", "cached_value"),
        [
            (types.HatDirection.Center, -1, types.HatDirection.Center),
            (types.HatDirection.North, 0, types.HatDirection.North),
            (types.HatDirection.NorthEast, 4500, types.HatDirection.NorthEast),
            (types.HatDirection.East, 9000, types.HatDirection.East),
            (types.HatDirection.SouthEast, 13500, types.HatDirection.SouthEast),
            (types.HatDirection.South, 18000, types.HatDirection.South),
            (types.HatDirection.SouthWest, 22500, types.HatDirection.SouthWest),
            (types.HatDirection.West, 27000, types.HatDirection.West),
            (types.HatDirection.NorthWest, 31500, types.HatDirection.NorthWest),
            (types.HatDirection.North, 0, types.HatDirection.North),
        ],
    )
    def test_hat(
        self,
        tester: app_tester.GremlinAppTester,
        vjoy_control_device: vjoy.VJoy,
        vjoy_di_device: dill.DeviceSummary,
        di_input: types.HatDirection,
        vjoy_output: int,
        cached_value: types.HatDirection | None,
    ) -> None:
        input_hat_id = 1
        output_hat_id = 3
        vjoy_control_device.hat(index=input_hat_id).direction = di_input
        tester.assert_hat_eventually_equals(
            vjoy_di_device.device_guid, input_hat_id, vjoy_output
        )
        tester.assert_cached_hat_eventually_equals(
            vjoy_di_device.device_guid.uuid, input_hat_id, cached_value
        )
        tester.assert_cached_hat_eventually_equals(
            vjoy_di_device.device_guid.uuid, output_hat_id, cached_value
        )
        tester.assert_hat_eventually_equals(
            vjoy_di_device.device_guid, output_hat_id, vjoy_output
        )

    @pytest.mark.parametrize(
        ("di_input", "vjoy_output", "cached_value"),
        [
            (678, -1, types.HatDirection.Center),
            (1234, -1, types.HatDirection.Center),
            (12340, -1, types.HatDirection.Center),
        ],
    )
    def test_hat_analog_values(
        self,
        tester: app_tester.GremlinAppTester,
        vjoy_control_device: vjoy.VJoy,
        vjoy_di_device: dill.DeviceSummary,
        di_input: int,
        vjoy_output: int,
        cached_value: types.HatDirection | None,
    ) -> None:
        """Tests the scenario where the input device has non-enum hat values."""
        input_hat_id = 1
        output_hat_id = 3
        if (
            vjoy_control_device.hat(index=input_hat_id).hat_type
            != vjoy.HatType.Continuous
        ):
            pytest.skip(
                "Skipping analog hat values test - vJoy device needs to be "
                "configured as such."
            )
        # Use the vJoy device directly to set a non-enum continuous value.
        vjoy_interface.VJoyInterface.SetContPov(
            di_input, vjoy_control_device.vjoy_id, input_hat_id
        )
        tester.assert_hat_eventually_equals(
            vjoy_di_device.device_guid, input_hat_id, di_input
        )
        tester.assert_cached_hat_eventually_equals(
            vjoy_di_device.device_guid.uuid, input_hat_id, cached_value
        )
        tester.assert_cached_hat_eventually_equals(
            vjoy_di_device.device_guid.uuid, output_hat_id, cached_value
        )
        tester.assert_hat_eventually_equals(
            vjoy_di_device.device_guid, output_hat_id, vjoy_output
        )
