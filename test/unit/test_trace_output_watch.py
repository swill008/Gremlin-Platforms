# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Control tracing: the OUTPUT tap in the vJoy output module and the
out-of-step watch (D-01-TRACE items 4 and 6). Fake driver, stand-in vJoy."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from types import SimpleNamespace
from unittest import mock

import pytest

import dill
from gremlin import device_initialization, trace, trace_watch
from gremlin.modules import output
from test import fake_hardware

STICK = uuid.UUID("11111111-2222-3333-4444-555555555555")
_CLAIM = {"buttons": [1, 2], "axes": [1], "hats": [], "keys": [], "friendly": {}}


class _FakeVJoy:
    """A held vJoy device with axis 1 and buttons 1-4."""

    def __init__(self) -> None:
        self._axes = {1: SimpleNamespace(value=0.0)}
        self._buttons = {i: SimpleNamespace(is_pressed=False) for i in range(1, 5)}

    def is_axis_valid(
        self, axis_id: int | None = None, linear_index: int | None = None
    ) -> bool:
        return axis_id in self._axes

    def is_button_valid(self, index: int) -> bool:
        return index in self._buttons

    def is_hat_valid(self, index: int) -> bool:
        return False

    def axis(self, axis_id: int) -> SimpleNamespace:
        return self._axes[axis_id]

    def button(self, index: int) -> SimpleNamespace:
        return self._buttons[index]


@pytest.fixture
def tracing() -> Iterator[None]:
    trace._reset_for_tests()
    with mock.patch.object(trace, "_save"), mock.patch.object(trace, "_open_file"):
        trace._ticks = {}
        trace.set_tick(STICK, "axis", 1, True)
        trace.set_oos(STICK, True)
        trace_watch.install()
        trace.set_enabled(True)
        yield
        trace.set_enabled(False)
        trace_watch.stop()
        trace._reset_for_tests()


@pytest.fixture
def vjoy() -> Iterator[_FakeVJoy]:
    dev = _FakeVJoy()
    output.clear_blocked_log()
    with (
        mock.patch.object(output, "_open_vjoy", return_value=dev),
        mock.patch.object(output, "vjoy_claim", return_value=_CLAIM),
    ):
        yield dev
    output.clear_blocked_log()


def _points() -> list[tuple[str, str]]:
    return [(point, detail) for _t, _c, point, detail, _w in trace.lines()]


def _warnings() -> list[str]:
    return [d for _t, _c, p, d, w in trace.lines() if w and p == trace.OUT_OF_STEP]


# --- OUTPUT tap ------------------------------------------------------------------


def test_writes_for_a_ticked_input_are_traced(tracing: None, vjoy: _FakeVJoy) -> None:
    trace.begin_input(STICK, "axis", 1)
    try:
        assert output.write_vjoy(3, "axis", 1, 0.5)
        assert not output.write_vjoy(3, "button", 9, True)  # not claimed
    finally:
        trace.end_input()
    lines = _points()
    assert any(
        p == trace.OUTPUT
        and d.startswith("vJoy 3 axis")
        and d.endswith("+0.500 · written")
        for p, d in lines
    )
    assert any(
        p == trace.BLOCKED and "blocked (not claimed by the vJoy 3 module)" in d
        for p, d in lines
    )
    assert trace.last_written(3, "axis", 1) is not None


def test_missing_output_is_traced(tracing: None, vjoy: _FakeVJoy) -> None:
    claim = dict(_CLAIM, buttons=[1, 2, 50])
    with mock.patch.object(output, "vjoy_claim", return_value=claim):
        trace.begin_input(STICK, "axis", 1)
        try:
            assert not output.write_vjoy(3, "button", 50, True)
        finally:
            trace.end_input()
    assert any(
        p == trace.BLOCKED and "missing (vJoy 3 has no button 50)" in d
        for p, d in _points()
    )


def test_unopened_vjoy_is_traced_as_failed(tracing: None) -> None:
    with (
        mock.patch.object(output, "_open_vjoy", return_value=None),
        mock.patch.object(output, "vjoy_claim", return_value=_CLAIM),
    ):
        trace.begin_input(STICK, "axis", 1)
        try:
            assert not output.write_vjoy(3, "axis", 1, 0.5)
        finally:
            trace.end_input()
    assert any(
        p == trace.OUTPUT and d.endswith("· failed: vJoy 3 not open")
        for p, d in _points()
    )


def test_unticked_input_writes_nothing(tracing: None, vjoy: _FakeVJoy) -> None:
    before = len(trace.lines())
    trace.begin_input(STICK, "button", 7)  # not ticked
    try:
        assert output.write_vjoy(3, "axis", 1, 0.25)
    finally:
        trace.end_input()
    assert len(trace.lines()) == before


# --- out-of-step watch -----------------------------------------------------------


@pytest.fixture
def stick(monkeypatch: pytest.MonkeyPatch) -> dict[str, int]:
    """The ticked stick on the fake driver; reading["raw"] is its axis 1."""
    fake = dill.DILL._dll  # the fake driver test/unit/conftest.py installed
    summary = dill.DeviceSummary(fake_hardware.raw_device(is_virtual=False))
    summary.device_guid = dill.GUID.from_uuid(STICK)
    reading = {"raw": 0}
    monkeypatch.setattr(fake, "get_axis", lambda guid, index: reading["raw"])
    monkeypatch.setattr(device_initialization, "physical_devices", lambda: [summary])
    monkeypatch.setattr(device_initialization, "vjoy_devices", lambda: [])
    return reading


def test_stick_that_moved_without_events_warns_once(
    tracing: None, stick: dict[str, int]
) -> None:
    trace.raw(STICK, "axis", 1, 0.0, raw_value=0)
    stick["raw"] = 32767  # moved; no RAW event came
    trace_watch.check(now=100.0)
    assert _warnings() == []  # apart, not yet for over a second
    trace_watch.check(now=101.5)
    trace_watch.check(now=103.0)
    warnings = _warnings()
    assert len(warnings) == 1
    assert "(polled)" in warnings[0]
    assert "isn't getting this stick's moves" in warnings[0]
    assert trace.notice()


def test_back_in_step_can_warn_again(tracing: None, stick: dict[str, int]) -> None:
    trace.raw(STICK, "axis", 1, 0.0, raw_value=0)
    stick["raw"] = 32767
    trace_watch.check(now=100.0)
    trace_watch.check(now=101.5)
    stick["raw"] = 0  # back in step
    trace_watch.check(now=102.0)
    stick["raw"] = 32767
    trace_watch.check(now=103.0)
    trace_watch.check(now=104.5)
    assert len(_warnings()) == 2


def test_vjoy_read_back_differs_warns(
    tracing: None, stick: dict[str, int], vjoy: _FakeVJoy
) -> None:
    trace.begin_input(STICK, "axis", 1)
    try:
        assert output.write_vjoy(3, "axis", 1, 0.5)
    finally:
        trace.end_input()
    # The driver's vJoy 3 still shows 0 (stuck).
    with mock.patch.object(trace_watch, "_vjoy_read_back", return_value=0.0):
        trace_watch.check(now=200.0)
        trace_watch.check(now=201.5)
    warnings = _warnings()
    assert any("vJoy 3 X shows 0.000, last written 0.500" in w for w in warnings)


def test_vjoy_read_back_through_the_driver_list(
    tracing: None, stick: dict[str, int], monkeypatch: pytest.MonkeyPatch
) -> None:
    vdev = dill.DeviceSummary(fake_hardware.raw_device(is_virtual=True))
    vdev.set_vjoy_id(3)
    monkeypatch.setattr(device_initialization, "vjoy_devices", lambda: [vdev])
    stick["raw"] = 32767
    assert trace_watch._vjoy_read_back(3, 1) == pytest.approx(1.0)


def test_tracing_off_stops_the_timer(tracing: None) -> None:
    assert trace_watch.running()
    trace.set_enabled(False)
    assert not trace_watch.running()
    assert trace_watch._timer is None
