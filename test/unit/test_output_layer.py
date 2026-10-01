# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import logging
from types import SimpleNamespace
from unittest import mock

import pytest

from gremlin.modules import output


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

    def is_hat_valid(self, index: int) -> bool:
        return index == 1

    def axis_id(self, linear_index: int) -> int:
        return linear_index

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
    with mock.patch.object(output, "_opened_vjoy", return_value=dev):
        yield dev


def test_only_claimed_outputs_are_read(
    device: _FakeVJoy, caplog: pytest.LogCaptureFixture
) -> None:
    claim = {"axes": [1, 2, 3], "buttons": list(range(1, 57))}
    with caplog.at_level(logging.DEBUG):
        state = output.vjoy_state(3, claim)

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
    state = output.vjoy_state(3, claim)
    assert set(state) == {("axis", 1), ("button", 126)}
    assert ("button", 127) not in device.asked and ("axis", 7) not in device.asked


def test_unopened_device_gives_nothing() -> None:
    with mock.patch.object(output, "_opened_vjoy", return_value=None):
        assert output.vjoy_state(2, {"buttons": [1]}) == {}


# --- writes go through the firewall -------------------------------------------

_CLAIM = {"buttons": [1, 2, 3], "axes": [1], "hats": [], "keys": [], "friendly": {}}


@pytest.fixture
def writable() -> _FakeVJoy:
    dev = _FakeVJoy()
    output.clear_blocked_log()
    with (
        mock.patch.object(output, "_open_vjoy", return_value=dev),
        mock.patch.object(output, "vjoy_claim", return_value=_CLAIM),
    ):
        yield dev
    output.clear_blocked_log()


def test_claimed_write_reaches_the_driver(writable: _FakeVJoy) -> None:
    assert output.write_vjoy(3, "button", 2, True)
    assert writable._buttons[2].is_pressed is True
    assert output.write_vjoy(3, "axis", 1, -0.5)
    assert writable._axes[1].value == -0.5


def test_unclaimed_write_is_blocked_and_logged_once(
    writable: _FakeVJoy, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING, logger="system"):
        for _ in range(5):
            assert not output.write_vjoy(3, "button", 57, True)
    assert not hasattr(writable._buttons[57], "is_pressed")
    blocked = [r for r in caplog.records if "vJoy 3 button 57" in r.getMessage()]
    assert len(blocked) == 1


def test_claimed_output_the_driver_lacks_is_refused(writable: _FakeVJoy) -> None:
    with mock.patch.object(
        output, "vjoy_claim", return_value={"buttons": [200], "axes": [], "hats": []}
    ):
        assert not output.write_vjoy(3, "button", 200, True)


def test_reads_of_unclaimed_outputs_are_neutral(writable: _FakeVJoy) -> None:
    assert output.vjoy_value(3, "button", 5) is False  # pressed, but unclaimed
    assert output.vjoy_value(3, "axis", 2) == 0.0
