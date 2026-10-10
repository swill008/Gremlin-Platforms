# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Out-of-step watch after Stop (06 S86-S87, 01 S150; 06 S17 rest on release).

Stop releases every vJoy device at rest (output.reset_drivers ->
reset_vjoy -> VJoyProxy.reset -> VJoy.invalidate -> rest). That rest is
a write (S86: each written value is kept for the check), so the watch must
compare the read-back with the rest value, not with the last value the
profile wrote. A real mismatch while running still warns.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from types import SimpleNamespace
from unittest import mock

import pytest

from gremlin import trace, trace_watch
from gremlin.modules import output
from vjoy import vjoy

STICK = uuid.UUID("11111111-2222-3333-4444-555555555556")
_CLAIM = {"buttons": [1], "axes": [1, 3], "hats": [], "keys": [], "friendly": {}}


class _HeldVJoy:
    """A held vJoy device: axes 1 and 3; invalidate() rests it like VJoy."""

    def __init__(self) -> None:
        self._axes = {1: SimpleNamespace(value=0.0), 3: SimpleNamespace(value=0.0)}
        self._buttons = {1: SimpleNamespace(is_pressed=False)}
        self.vjoy_id: int | None = 2

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

    def invalidate(self) -> None:
        # VJoy.invalidate: rest (axes centred, buttons up), then released.
        for a in self._axes.values():
            a.value = 0.0
        for b in self._buttons.values():
            b.is_pressed = False
        self.vjoy_id = None


@pytest.fixture
def held(monkeypatch: pytest.MonkeyPatch) -> Iterator[_HeldVJoy]:
    trace._reset_for_tests()
    dev = _HeldVJoy()
    output.clear_blocked_log()
    monkeypatch.setattr(vjoy.VJoyProxy, "vjoy_devices", {2: dev})
    with (
        mock.patch.object(trace, "_save"),
        mock.patch.object(trace, "_open_file"),
        mock.patch.object(output, "_open_vjoy", return_value=dev),
        mock.patch.object(output, "vjoy_claim", return_value=_CLAIM),
        # Read-back: what the device holds (as Windows would see it).
        mock.patch.object(
            trace_watch,
            "_vjoy_read_back",
            side_effect=lambda vid, aid: dev._axes[aid].value,
        ),
        # The watch only reads vJoy back when a device is ticked for it;
        # the stick itself has no RAW value, so (a) checks nothing.
        mock.patch.object(trace_watch, "_check_stick"),
    ):
        trace._ticks = {}
        trace.set_tick(STICK, "axis", 1, True)
        trace.set_oos(STICK, True)
        trace_watch.install()
        trace.set_enabled(True)
        try:
            yield dev
        finally:
            trace.set_enabled(False)
            trace_watch.stop()
            trace._reset_for_tests()
            output.clear_blocked_log()


def _warnings() -> list[str]:
    return [d for _t, _c, p, d, w in trace.lines() if w and p == trace.OUT_OF_STEP]


def _write(vjoy_id: int, axis_id: int, value: float) -> None:
    trace.begin_input(STICK, "axis", 1)
    try:
        assert output.write_vjoy(vjoy_id, "axis", axis_id, value)
    finally:
        trace.end_input()


def test_stop_rest_is_not_out_of_step(held: _HeldVJoy) -> None:
    """S86/S150: the rest on Stop counts as written; no OUT OF STEP after."""
    _write(2, 1, 0.913)
    _write(2, 3, -0.4)
    trace_watch.check(now=10.0)
    trace_watch.check(now=11.5)
    assert _warnings() == []  # in step while running
    output.reset_vjoy()  # what Stop's DRIVERS stage does (reset_drivers)
    assert held._axes[1].value == 0.0
    for t in (12.0, 13.5, 15.0, 20.0):
        trace_watch.check(now=t)
    assert _warnings() == []
    assert trace.last_written(2, "axis", 1)[0] == 0.0
    assert trace.last_written(2, "axis", 3)[0] == 0.0


def test_real_mismatch_while_running_still_warns(held: _HeldVJoy) -> None:
    """S87: a vJoy axis that doesn't show what was written still warns."""
    _write(2, 1, 0.913)
    held._axes[1].value = 0.0  # something else moved it (stuck/other feeder)
    trace_watch.check(now=10.0)
    trace_watch.check(now=11.5)
    warnings = _warnings()
    assert len(warnings) == 1
    assert "vJoy 2 X shows 0.000, last written 0.913" in warnings[0]


def test_rest_only_touches_released_devices(held: _HeldVJoy) -> None:
    """A vJoy Gremlin didn't hold isn't rested, so its last value stays."""
    _write(2, 1, 0.5)
    with trace._LOCK:
        trace._last_written[(5, "axis", 1)] = (0.7, 0.0)
    output.reset_vjoy()
    assert trace.last_written(2, "axis", 1)[0] == 0.0
    assert trace.last_written(5, "axis", 1)[0] == 0.7
