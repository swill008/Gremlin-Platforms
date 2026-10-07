# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Hands-on fixes F2: Map to vJoy Relative on a vJoy nothing else writes
(05 S83) and the idle vJoy keep-alive after 60 s (06 S54).

Both run on the fake vJoy driver behind the output module
(test/journeys/_harness.py FakeVJoy), never the real device, and on a
stepped gremlin.clock.
"""

from __future__ import annotations

import importlib.util
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from gremlin import clock, run_scope
from gremlin.modules import output

_ROOT = Path(__file__).resolve().parents[2]
_STICK = uuid.UUID("0000000a-0000-0000-0000-000000000000")


def _harness() -> Any:  # noqa: ANN401
    spec = importlib.util.spec_from_file_location(
        "_f2_harness", _ROOT / "test" / "journeys" / "_harness.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def fake_vjoy(monkeypatch: pytest.MonkeyPatch) -> Iterator[Any]:
    """The output module on the fake vJoy driver, every output claimed,
    nothing opened yet."""
    proxy = _harness().FakeVJoy
    proxy.vjoy_devices = {}
    proxy.opened = {}
    monkeypatch.setattr(output, "_vjoy_proxy", lambda: proxy)
    monkeypatch.setattr(output, "vjoy_allows", lambda *_a: True)
    monkeypatch.setattr(output, "_keep_alive", {})
    output.clear_blocked_log()
    yield proxy
    proxy.vjoy_devices = {}
    proxy.opened = {}


# --- 05 S83: Map to vJoy Relative opens the vJoy device itself ----------------------


def _relative_functor(monkeypatch: pytest.MonkeyPatch, steps: int) -> Any:  # noqa: ANN401
    """A Map to vJoy Relative on vJoy 1 X whose loop runs here, on a stepped
    clock, for at most steps steps."""
    from action_plugins.map_to_vjoy import MapToVjoyData, MapToVjoyFunctor
    from gremlin.types import AxisMode, InputType

    data = MapToVjoyData(InputType.JoystickAxis)
    data.axis_mode = AxisMode.Relative
    data.vjoy_device_id = 1
    data.vjoy_input_id = 1
    data.axis_scaling = 1.0
    functor = MapToVjoyFunctor(data)

    now = [1000.0]
    taken = [0]

    def sleep(seconds: float) -> None:
        now[0] += seconds
        taken[0] += 1
        if taken[0] >= steps:  # bound: end the loop here
            functor._ask_to_stop()

    monkeypatch.setattr(clock, "now", lambda: now[0])
    monkeypatch.setattr(clock, "sleep", sleep)
    monkeypatch.setattr(run_scope, "alive", lambda _run: True)
    monkeypatch.setattr(run_scope, "loop", lambda *_a, **_k: None)  # run below
    return functor


def _deflect(functor: Any, value: float) -> None:  # noqa: ANN401
    from gremlin.base_classes import Value
    from gremlin.event_handler import Event
    from gremlin.types import InputType

    event = Event(InputType.JoystickAxis, 1, _STICK, "Default", value=value)
    functor(event, Value(value))


def test_s83_vjoy_relative_moves_an_axis_nothing_else_writes(
    fake_vjoy: Any, monkeypatch: pytest.MonkeyPatch  # noqa: ANN401
) -> None:
    functor = _relative_functor(monkeypatch, steps=50)
    _deflect(functor, 0.5)  # held off-centre
    assert functor.thread_running
    functor.relative_axis_thread(1, functor._loop_token)

    # The loop's own write opened vJoy 1 and moved X at Speed 1.0
    # (0.5 * 1/1000 per step); it used to end before its first write.
    assert 1 in fake_vjoy.opened
    axis = [v for kind, i, v in fake_vjoy.all_writes(1) if (kind, i) == ("axis", 1)]
    assert len(axis) == 50
    assert axis[-1] == pytest.approx(50 * 0.0005)
    assert output.vjoy_value(1, "axis", 1) == pytest.approx(50 * 0.0005)


def test_s83_vjoy_relative_ends_when_the_held_vjoy_is_lost(
    fake_vjoy: Any, monkeypatch: pytest.MonkeyPatch  # noqa: ANN401
) -> None:
    output.write_vjoy(1, "axis", 1, 0.0)  # Gremlin holds vJoy 1
    fake_vjoy.vjoy_devices[1].valid = False  # another program took it
    writes = len(fake_vjoy.all_writes(1))
    functor = _relative_functor(monkeypatch, steps=50)
    _deflect(functor, 0.5)
    functor.relative_axis_thread(1, functor._loop_token)

    assert not functor.thread_running
    assert len(fake_vjoy.all_writes(1)) == writes


# --- 06 S54: an idle held vJoy is re-sent 60 s after its last write ----------------


class _Device:
    """The fake vJoy device with the driver's last-write time and reset."""

    def __init__(self, base: Any, now: list[float]) -> None:  # noqa: ANN401
        self._base = base
        self._now = now
        self.last_active = now[0]
        self.resets: list[float] = []

    def __getattr__(self, name: str) -> Any:  # noqa: ANN401
        return getattr(self._base, name)

    def write(self) -> None:
        self.last_active = self._now[0]

    def reset(self) -> None:
        self.resets.append(self._now[0])
        self.last_active = self._now[0]


@pytest.fixture
def stepped_keep_alive(
    fake_vjoy: Any, monkeypatch: pytest.MonkeyPatch  # noqa: ANN401
) -> Iterator[tuple[list[float], list[list[Any]], Any]]:
    """A stepped gremlin.clock; the keep-alive's timers are kept here (due
    time, function, args) and fired by the test, nothing else is stepped."""

    now = [500.0]
    timers: list[list[Any]] = []

    class Timer:
        def __init__(self, entry: list[Any]) -> None:
            self.entry = entry

        def is_alive(self) -> bool:
            return self.entry in timers

        def cancel(self) -> None:
            if self.entry in timers:
                timers.remove(self.entry)

    def timer(_name: str, seconds: float, fn: Any, *args: object) -> Timer:  # noqa: ANN401
        entry = [now[0] + seconds, fn, args]
        timers.append(entry)
        return Timer(entry)

    monkeypatch.setattr(clock, "monotonic", lambda: now[0])
    monkeypatch.setattr(output.run_scope, "timer", timer)

    class Proxy(fake_vjoy):
        def __getitem__(self, vjoy_id: int) -> Any:  # noqa: ANN401
            if vjoy_id not in Proxy.vjoy_devices:
                Proxy.vjoy_devices[vjoy_id] = _Device(
                    fake_vjoy.__getitem__(self, vjoy_id), now
                )
            return Proxy.vjoy_devices[vjoy_id]

    Proxy.vjoy_devices = {}
    monkeypatch.setattr(output, "_vjoy_proxy", lambda: Proxy)
    yield now, timers, Proxy
    Proxy.vjoy_devices = {}


def _run_until(now: list[float], timers: list[list[Any]], end: float) -> None:
    """Fires the keep-alive's timers in time order up to end."""
    for _ in range(100):
        due = [t for t in timers if t[0] <= end]
        if not due:
            break
        entry = min(due, key=lambda t: t[0])
        timers.remove(entry)
        now[0] = entry[0]
        entry[1](*entry[2])
    now[0] = end


def test_s54_an_idle_vjoy_is_re_sent_60_s_after_its_last_write(
    stepped_keep_alive: tuple[list[float], list[list[Any]], Any],
) -> None:
    now, timers, proxy = stepped_keep_alive
    opened_at = now[0]
    assert output.write_vjoy(2, "button", 1, True)  # opens vJoy 2, held
    device = proxy.vjoy_devices[2]
    now[0] += 1.0
    device.write()  # written again a second after it opened
    last = now[0]

    _run_until(now, timers, opened_at + 200.0)
    # The first re-send is 60 s after the last write (it was ~120 s: the
    # check ran 60 s after the open, found 59 s idle and waited 60 s more).
    assert device.resets[0] == pytest.approx(last + 60.0)
    # Still idle: again every 60 s, one timer per device.
    assert device.resets[1] == pytest.approx(last + 120.0)
    assert len(timers) == 1


def test_s54_a_vjoy_written_meanwhile_is_not_re_sent(
    stepped_keep_alive: tuple[list[float], list[list[Any]], Any],
) -> None:
    now, timers, proxy = stepped_keep_alive
    assert output.write_vjoy(2, "button", 1, True)
    device = proxy.vjoy_devices[2]
    start = now[0]
    # Written every 30 s for three minutes: never idle for 60 s.
    for n in range(1, 7):
        _run_until(now, timers, start + 30.0 * n)
        device.write()
    assert device.resets == []
    _run_until(now, timers, start + 180.0 + 61.0)
    assert device.resets == [pytest.approx(start + 240.0)]


def test_s54_a_released_vjoy_arms_no_keep_alive(
    stepped_keep_alive: tuple[list[float], list[list[Any]], Any],
) -> None:
    now, timers, proxy = stepped_keep_alive
    assert output.write_vjoy(2, "button", 1, True)
    device = proxy.vjoy_devices[2]
    proxy.vjoy_devices = {}  # released
    _run_until(now, timers, now[0] + 300.0)
    assert device.resets == []
    assert timers == []
