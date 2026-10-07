# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Listen and macro Record hold input highlighting off like Run, Calibration
and OSC Add: ending one doesn't turn it back on while another still holds it
(03 S114, 09 S33, 02 S65)."""

from __future__ import annotations

import sys
from collections.abc import Callable, Iterator
from types import SimpleNamespace
from typing import Any

sys.path.append(".")

import pytest
from PySide6 import QtCore

from gremlin import shared_state, threads
from gremlin.types import InputType
from gremlin.ui import backend


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    yield QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])


class _Runner:
    def __init__(self) -> None:
        self.running = False

    def start(self, _profile: object, _mode: str) -> None:
        self.running = True

    def stop(self) -> None:
        self.running = False

    def is_running(self) -> bool:
        return self.running


class _Backend(backend.Backend.klass):  # type: ignore[name-defined, misc]
    """The real Backend's Run/Stop and highlight pause, without the
    program's start-up (drivers, profile, process monitor)."""

    def __init__(self) -> None:
        QtCore.QObject.__init__(self)
        self.runner = _Runner()
        self.profile = object()
        self.ui_state = SimpleNamespace(currentMode="Default")
        self.config = SimpleNamespace(value=lambda *_a: True)
        self._highlight_holders = set()  # F1's holders (old code)


class _FakeTimer:
    """Stands in for the delayed release's timer: fired by the test."""

    def __init__(self, function: Callable[..., Any], args: tuple) -> None:
        self.function = function
        self.args = args
        self.cancelled = False

    def cancel(self) -> None:
        self.cancelled = True

    def is_alive(self) -> bool:
        return not self.cancelled

    def fire(self) -> None:
        if not self.cancelled:
            self.cancelled = True
            self.function(*self.args)


@pytest.fixture
def timers(monkeypatch: pytest.MonkeyPatch) -> list[_FakeTimer]:
    made: list[_FakeTimer] = []

    def timer(
        _name: str, _seconds: float, function: Callable[..., Any], *args: object
    ) -> _FakeTimer:
        made.append(_FakeTimer(function, args))
        return made[-1]

    monkeypatch.setattr(threads, "timer", timer)
    return made


def _fire_all(timers: list[_FakeTimer]) -> None:
    for t in list(timers):
        t.fire()


@pytest.fixture
def be() -> Iterator[_Backend]:
    shared_state.set_suspend_input_highlighting(False)
    yield _Backend()
    shared_state.set_suspend_input_highlighting(False)


_KEEP: list[Any] = []


def _listen() -> Any:  # noqa: ANN401
    from gremlin.ui.util import InputListenerModel

    model = InputListenerModel()
    _KEEP.append(model)
    model.setProperty("eventTypes", [InputType.to_string(InputType.JoystickButton)])
    model.setProperty("enabled", True)
    return model


def _recorder() -> Any:  # noqa: ANN401
    from gremlin.ui.util import MacroRecorder

    return MacroRecorder(lambda action: None)


def test_ending_listen_while_calibration_is_open_keeps_highlighting_paused(
    be: _Backend, timers: list[_FakeTimer]
) -> None:
    be.pauseInputHighlighting("calibration")
    model = _listen()
    model.setProperty("enabled", False)
    _fire_all(timers)  # Listen's delayed release has run
    assert shared_state.suspend_input_highlighting() is True
    be.resumeInputHighlighting("calibration")
    assert shared_state.suspend_input_highlighting() is False


@pytest.mark.filterwarnings("ignore:libpyside. Failed to disconnect:RuntimeWarning")
def test_ending_record_while_calibration_is_open_keeps_highlighting_paused(
    be: _Backend, timers: list[_FakeTimer]
) -> None:
    be.pauseInputHighlighting("calibration")
    recorder = _recorder()
    recorder.start([InputType.JoystickButton], False)
    assert shared_state.suspend_input_highlighting() is True
    recorder.stop()
    _fire_all(timers)
    assert shared_state.suspend_input_highlighting() is True
    be.resumeInputHighlighting("calibration")
    assert shared_state.suspend_input_highlighting() is False


@pytest.mark.filterwarnings("ignore:libpyside. Failed to disconnect:RuntimeWarning")
def test_record_alone_turns_highlighting_back_on_when_it_stops(
    be: _Backend, timers: list[_FakeTimer]
) -> None:
    recorder = _recorder()
    recorder.start([InputType.JoystickButton], False)
    recorder.stop()
    assert shared_state.suspend_input_highlighting() is False


def test_listen_alone_turns_highlighting_back_on_after_its_delay(
    be: _Backend, timers: list[_FakeTimer]
) -> None:
    model = _listen()
    assert shared_state.suspend_input_highlighting() is True
    model.setProperty("enabled", False)
    # Still held until the delay is over (the press that ended Listen).
    assert shared_state.suspend_input_highlighting() is True
    assert len(timers) == 1
    timers[0].fire()
    assert shared_state.suspend_input_highlighting() is False


def test_listen_again_before_the_delay_keeps_it_held(
    be: _Backend, timers: list[_FakeTimer]
) -> None:
    model = _listen()
    model.setProperty("enabled", False)
    model.setProperty("enabled", True)
    _fire_all(timers)  # the first delayed release was cancelled
    assert shared_state.suspend_input_highlighting() is True
    model.setProperty("enabled", False)
    _fire_all(timers)
    assert shared_state.suspend_input_highlighting() is False


def test_listen_ending_while_running_keeps_highlighting_paused(
    be: _Backend, timers: list[_FakeTimer]
) -> None:
    be.activate_gremlin(True)
    model = _listen()
    model.setProperty("enabled", False)
    _fire_all(timers)
    assert shared_state.suspend_input_highlighting() is True
    be.activate_gremlin(False)
    assert shared_state.suspend_input_highlighting() is False


def test_stop_while_listening_keeps_listens_hold(
    be: _Backend, timers: list[_FakeTimer]
) -> None:
    be.activate_gremlin(True)
    model = _listen()
    be.activate_gremlin(False)
    assert shared_state.suspend_input_highlighting() is True
    model.setProperty("enabled", False)
    _fire_all(timers)
    assert shared_state.suspend_input_highlighting() is False
