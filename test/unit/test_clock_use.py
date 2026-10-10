# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Caches, throttles and chart times read gremlin.clock, not the time
module, so a test can step them (thread rules; AUD-THREADS-10)."""

from __future__ import annotations

import ast
import pathlib
import uuid
from collections.abc import Iterator

import pytest

from gremlin import action_analysis, clock, input_monitor
from gremlin.base_classes import UserFeedback
from gremlin.event_handler import Event
from gremlin.types import InputType

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_FILES = [
    "gremlin/action_analysis.py",
    "gremlin/ui/profile.py",
    "gremlin/ui/device.py",
    "gremlin/input_monitor.py",
    "gremlin/osc_bulk.py",
]
_TIMING = {"time", "monotonic", "sleep", "perf_counter"}
# Wall-clock reads kept on purpose: (file, function) -> why.
_ALLOWED = {
    # The Input Monitor line's displayed time of day (milliseconds part).
    ("gremlin/input_monitor.py", "_entry"),
}


def _timing_calls(path: str) -> list[tuple[str, int]]:
    tree = ast.parse((_ROOT / path).read_text(encoding="utf-8"))
    found = []
    for func in ast.walk(tree):
        if not isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        name = func.name
        for node in ast.walk(func):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "time"
                and node.func.attr in _TIMING
                and (path, name) not in _ALLOWED
            ):
                found.append((name, node.lineno))
    return found


@pytest.mark.parametrize("path", _FILES)
def test_timing_goes_through_clock(path: str) -> None:
    assert _timing_calls(path) == []


class _FakeClock:
    def __init__(self) -> None:
        self.t = 1000.0

    def monotonic(self) -> float:
        return self.t


@pytest.fixture
def fake_clock(monkeypatch: pytest.MonkeyPatch) -> Iterator[_FakeClock]:
    fake = _FakeClock()
    monkeypatch.setattr(clock, "monotonic", fake.monotonic)
    yield fake


class _Binding:
    root_action = None
    behavior = InputType.JoystickButton


def test_feedback_cache_expires_on_the_clock(fake_clock: _FakeClock) -> None:
    action_analysis._feedback_cache.clear()
    first = action_analysis.action_sequence_feedback(_Binding())  # type: ignore[arg-type]
    marker: list[UserFeedback] = []
    key = uuid.UUID(int=0)
    action_analysis._feedback_cache[key] = (fake_clock.t, marker)
    fake_clock.t += action_analysis._CACHE_TTL / 2
    assert action_analysis.action_sequence_feedback(_Binding()) is marker  # type: ignore[arg-type]
    fake_clock.t += action_analysis._CACHE_TTL
    again = action_analysis.action_sequence_feedback(_Binding())  # type: ignore[arg-type]
    assert again is not marker and again == first
    action_analysis._feedback_cache.clear()


_DEV = uuid.UUID("11111111-2222-3333-4444-555555555555")


def _axis(value: float) -> Event:
    return Event(InputType.JoystickAxis, 1, _DEV, "Default", value=value)


def test_input_monitor_axis_throttle_steps_on_the_clock(
    fake_clock: _FakeClock,
) -> None:
    input_monitor.clear()
    try:
        input_monitor.record(_axis(0.1), [])
        input_monitor.record(_axis(0.2), [])  # within the interval: held
        assert len(input_monitor._entries) == 1
        assert len(input_monitor._axis_pending) == 1
        fake_clock.t += input_monitor.AXIS_INTERVAL * 2
        input_monitor.record(_axis(0.3), [])  # interval passed: recorded
        assert len(input_monitor._entries) == 2
        assert not input_monitor._axis_pending
    finally:
        input_monitor.clear()
