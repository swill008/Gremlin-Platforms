# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import logging
from types import SimpleNamespace
from unittest import mock

import pytest

from gremlin.ui import output_modules


class _FakeVJoy:
    """A vJoy device with 126 buttons and axes 1-3, like the user's vJoy 3."""

    def __init__(self) -> None:
        self.asked: list[tuple[str, int]] = []
        self._buttons = {
            i: SimpleNamespace(_is_pressed=(i == 5)) for i in range(1, 127)
        }
        self._axes = {i: SimpleNamespace(_value=0.25 * i) for i in (1, 2, 3)}

    def is_axis_valid(
        self, axis_id: int | None = None, linear_index: int | None = None
    ) -> bool:
        return axis_id in self._axes

    def is_button_valid(self, index: int) -> bool:
        return index in self._buttons

    def axis(
        self, axis_id: int | None = None, linear_index: int | None = None
    ) -> SimpleNamespace:
        self.asked.append(("axis", axis_id))
        return self._axes[axis_id]

    def button(self, index: int) -> SimpleNamespace:
        self.asked.append(("button", index))
        return self._buttons[index]


@pytest.fixture
def device() -> _FakeVJoy:
    dev = _FakeVJoy()
    with mock.patch.object(output_modules, "_vjoy_device", return_value=dev):
        yield dev


def test_only_claimed_outputs_are_read(
    device: _FakeVJoy, caplog: pytest.LogCaptureFixture
) -> None:
    claim = {"axes": [1, 2, 3], "buttons": list(range(1, 57))}
    with caplog.at_level(logging.DEBUG):
        state = output_modules.vjoy_output_state(3, claim)

    axes = sorted(k for k in state if k[0] == "axis")
    assert axes == [("axis", 1), ("axis", 2), ("axis", 3)]
    assert len([k for k in state if k[0] == "button"]) == 56
    assert state[("button", 5)] == 1.0 and state[("button", 6)] == 0.0
    # The driver is never asked for an unclaimed output.
    assert not any(kind == "button" and index > 56 for kind, index in device.asked)
    assert not caplog.records


def test_claimed_outputs_the_device_lacks_are_skipped(device: _FakeVJoy) -> None:
    # Claimed beyond what the driver has: skipped quietly, never requested.
    claim = {"axes": [1, 7], "buttons": [126, 127, 128]}
    state = output_modules.vjoy_output_state(3, claim)
    assert set(state) == {("axis", 1), ("button", 126)}
    assert ("button", 127) not in device.asked and ("axis", 7) not in device.asked


def test_unopened_device_gives_nothing() -> None:
    with mock.patch.object(output_modules, "_vjoy_device", return_value=None):
        assert output_modules.vjoy_output_state(2, {"buttons": [1]}) == {}
