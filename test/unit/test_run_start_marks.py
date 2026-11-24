# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""A Run start that takes 300 ms or more writes one line to system.log naming
its slow steps, largest first; a fast start writes nothing (01 S184). The
clock is a fake the slow step advances: no real waiting."""

from __future__ import annotations

import logging
import sys
from collections.abc import Iterator
from types import SimpleNamespace
from unittest import mock

sys.path.append(".")

import pytest
from PySide6 import QtCore

from gremlin import code_runner, shared_state, trace, trace_timing
from gremlin.error import VJoyBusyError
from gremlin.modules import output
from gremlin.profile import Profile

_CLAIM = {"axes": [1, 2], "buttons": [1, 2, 3], "hats": []}
_NO_CLAIM = {"axes": [], "buttons": [], "hats": []}
_APPS: list[QtCore.QCoreApplication] = []


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


class _Proxy:
    """Stand-in for VJoyProxy: opening is recorded, Stop's reset releases."""

    vjoy_devices: dict = {}
    opened: list[int] = []
    busy: set[int] = set()

    def __getitem__(self, index: int) -> object:
        _Proxy.opened.append(index)
        if index in _Proxy.busy:
            raise VJoyBusyError("held by another program")
        dev = SimpleNamespace()
        _Proxy.vjoy_devices = {**_Proxy.vjoy_devices, index: dev}
        return dev

    @classmethod
    def reset(cls) -> None:
        cls.vjoy_devices = {}


@pytest.fixture
def proxy() -> Iterator[type[_Proxy]]:
    _Proxy.vjoy_devices, _Proxy.opened, _Proxy.busy = {}, [], set()
    yield _Proxy
    _Proxy.vjoy_devices = {}


@pytest.fixture
def runner(
    monkeypatch: pytest.MonkeyPatch, proxy: type[_Proxy]
) -> Iterator[code_runner.CodeRunner]:
    """A real CodeRunner start/stop with the real output module; the vJoy
    driver, devices, sound and network are stand-ins."""
    for name in ("OscRuntime", "InputModuleRuntime", "audio_player", "tts"):
        monkeypatch.setattr(code_runner, name, mock.MagicMock())
    monkeypatch.setattr(output, "refresh", lambda: None)
    modules = [
        (1, SimpleNamespace(name="vJoy 1", claim=_CLAIM)),
        (2, SimpleNamespace(name="vJoy 2", claim=_NO_CLAIM)),
        (3, SimpleNamespace(name="vJoy 3", claim=_CLAIM)),
        (4, SimpleNamespace(name="vJoy 4", claim=_CLAIM)),
    ]
    monkeypatch.setattr(output, "vjoy_modules", lambda: modules)
    monkeypatch.setattr(output, "_vjoy_proxy", lambda: proxy)
    monkeypatch.setattr(output, "vjoy_driver_found", lambda: True)
    monkeypatch.setattr(output, "vjoy_exists", lambda vid: int(vid) != 4)
    monkeypatch.setattr(output, "held_vjoy_ids", lambda: sorted(proxy.vjoy_devices))
    # The can't-be-sent notice is made once per process and hooks
    # EventListener().device_change_event: made first inside start() it
    # would hook the stand-in below and later tests' device changes never
    # reach it. Make it now, on the real listener.
    output.watch_cant_send()
    listener = mock.MagicMock()
    fake_listener = mock.MagicMock(return_value=listener)
    fake_listener.instance = None
    monkeypatch.setattr(code_runner.event_handler, "EventListener", fake_listener)
    run = code_runner.CodeRunner()
    monkeypatch.setattr(run, "_refresh_axes", lambda: None)
    output.clear_blocked_log()
    yield run
    run.stop()
    shared_state.set_runtime_active(False)
    output.clear_blocked_log()


class _Clock:
    t = 100.0


@pytest.fixture
def fake_clock(monkeypatch: pytest.MonkeyPatch) -> type[_Clock]:
    _Clock.t = 100.0
    monkeypatch.setattr(code_runner.clock, "monotonic", lambda: _Clock.t)
    return _Clock


def _slow_open(monkeypatch: pytest.MonkeyPatch, clk: type[_Clock], secs: float) -> None:
    def slow() -> list:
        clk.t += secs
        return []

    monkeypatch.setattr(output, "open_claimed_vjoy", slow)


def _lines(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [
        r.getMessage() for r in caplog.records if "Run start took" in r.getMessage()
    ]


def test_a_slow_start_names_its_slow_step(
    runner: code_runner.CodeRunner,
    fake_clock: type[_Clock],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _slow_open(monkeypatch, fake_clock, 0.4)
    with caplog.at_level(logging.INFO, logger="system"):
        runner.start(Profile(), "Default")
    lines = _lines(caplog)
    assert len(lines) == 1
    assert lines[0].startswith("Run start took 400 ms: open vJoy 400 ms")


def test_a_fast_start_writes_nothing(
    runner: code_runner.CodeRunner,
    fake_clock: type[_Clock],
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger="system"):
        runner.start(Profile(), "Default")
    assert _lines(caplog) == []


def test_just_under_the_limit_writes_nothing(
    runner: code_runner.CodeRunner,
    fake_clock: type[_Clock],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _slow_open(monkeypatch, fake_clock, 0.29)
    with caplog.at_level(logging.INFO, logger="system"):
        runner.start(Profile(), "Default")
    assert _lines(caplog) == []


def test_the_line_is_also_a_timing_line_while_timing_is_on(
    runner: code_runner.CodeRunner,
    fake_clock: type[_Clock],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _slow_open(monkeypatch, fake_clock, 0.4)
    written: list[str] = []
    monkeypatch.setattr(trace_timing, "on", True)
    monkeypatch.setattr(
        trace, "timing", lambda text, warning=False: written.append(text)
    )
    runner.start(Profile(), "Default")
    assert any(t.startswith("Run start took 400 ms: open vJoy 400 ms") for t in written)


def test_a_clock_that_fails_never_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom() -> float:
        raise RuntimeError("no clock")

    monkeypatch.setattr(code_runner.clock, "monotonic", boom)
    marks = code_runner._Marks()
    marks.mark("x")
    marks.report("start")
