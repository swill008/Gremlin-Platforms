# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""What an OSC input's actions send is traced under it (D-09-OSC-TRACE,
09 S166 Inputs area): with the OSC Inputs area ticked, an OSC button's
Map to vJoy write shows as an OUTPUT line (BLOCKED when not claimed) in the
control column "OSC Button <n>", rate limited per output like axis lines;
unticked, nothing. Fake vJoy behind the output module, no real driver.

Spec: 09 S166 (D-09-OSC-TRACE).
"""

from __future__ import annotations

from collections.abc import Iterator
from types import SimpleNamespace
from unittest import mock

import pytest

from gremlin import event_handler, run_scope, trace
from gremlin.event_handler import Event
from gremlin.modules import ids, output
from gremlin.types import InputType

_CLAIM = {"buttons": [30], "axes": [], "hats": [], "keys": [], "friendly": {}}


class _FakeVJoy:
    def __init__(self) -> None:
        self._buttons = {i: SimpleNamespace(is_pressed=False) for i in range(1, 33)}

    def is_axis_valid(
        self, axis_id: int | None = None, linear_index: int | None = None
    ) -> bool:
        return False

    def is_button_valid(self, index: int) -> bool:
        return index in self._buttons

    def is_hat_valid(self, index: int) -> bool:
        return False

    def button(self, index: int) -> SimpleNamespace:
        return self._buttons[index]


@pytest.fixture
def traced() -> Iterator[None]:
    trace._reset_for_tests()
    run_scope.begin()
    with (
        mock.patch.object(trace, "_save"),
        mock.patch.object(trace, "_open_file"),
        mock.patch.object(trace, "_schedule_flush"),
        mock.patch.object(output, "_open_vjoy", return_value=_FakeVJoy()),
        mock.patch.object(output, "vjoy_claim", return_value=_CLAIM),
    ):
        output.clear_blocked_log()
        trace._ticks = {}
        trace.set_enabled(True)
        trace.set_osc("inputs", True)
        yield
        trace.set_osc_all(False)
        trace.set_enabled(False)
    output.clear_blocked_log()
    run_scope.stop()
    run_scope._reset_for_tests()
    trace._reset_for_tests()


def _press(button: int, *writes: int) -> None:
    """OSC Button <button> pressed while running; its action (Map to vJoy)
    writes vJoy 2 buttons writes."""
    handler = event_handler.EventHandler()

    def map_to_vjoy(_event: Event) -> None:
        for index in writes:
            output.write_vjoy(2, "button", index, True)

    event = Event(InputType.JoystickButton, button, ids.OSC, "Default", is_pressed=True)
    with mock.patch.object(handler, "_matching_callbacks", lambda e: [map_to_vjoy]):
        handler.process_event(event)


def _lines(control: str) -> list[tuple[str, str]]:
    return [(ln[2], ln[3]) for ln in trace.lines() if ln[1] == control]


def test_an_osc_buttons_vjoy_write_is_an_output_line(traced: None) -> None:
    _press(1, 30)
    assert (trace.OUTPUT, "vJoy 2 Button 30 = True · written") in _lines(
        "OSC Button 1"
    )


def test_an_unclaimed_vjoy_button_is_a_blocked_line(traced: None) -> None:
    _press(1, 31)
    lines = _lines("OSC Button 1")
    assert any(
        p == trace.BLOCKED and d.startswith("vJoy 2 Button 31 = True · blocked")
        for p, d in lines
    ), lines


def test_outputs_are_rate_limited_per_output(
    traced: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = [1000.0]
    fake = SimpleNamespace(**vars(trace.clock))
    fake.monotonic = lambda: now[0]
    monkeypatch.setattr(trace, "clock", fake)
    gap = 1.0 / trace.axis_rate()
    for _ in range(4):
        _press(1, 30)
        now[0] += gap / 10
    now[0] += gap
    _press(1, 30)
    lines = [d for _p, d in _lines("OSC Button 1")]
    assert lines == [
        "vJoy 2 Button 30 = True · written",
        "vJoy 2 Button 30 = True · written  (3 messages between)",
    ], lines


def test_inputs_area_unticked_writes_nothing(traced: None) -> None:
    trace.set_osc("inputs", False)
    _press(1, 30, 31)
    assert _lines("OSC Button 1") == []
