# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Input highlighting stays paused while Calibration is open (03 S114, 09 S33),
also across Run and Stop (hands-on 03 S114: Stop turned it back on)."""

from __future__ import annotations

import sys
from collections.abc import Iterator
from types import SimpleNamespace

sys.path.append(".")

import pytest
from PySide6 import QtCore

from gremlin import shared_state
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
        self._highlight_holders = set()


@pytest.fixture
def be() -> Iterator[_Backend]:
    shared_state.set_suspend_input_highlighting(False)
    yield _Backend()
    shared_state.set_suspend_input_highlighting(False)


def test_stop_keeps_highlighting_paused_while_calibration_is_open(
    be: _Backend,
) -> None:
    be.pauseInputHighlighting("calibration")
    be.activate_gremlin(True)
    be.activate_gremlin(False)
    assert shared_state.suspend_input_highlighting() is True
    be.resumeInputHighlighting("calibration")
    assert shared_state.suspend_input_highlighting() is False


def test_closing_calibration_while_running_keeps_the_run_pause(
    be: _Backend,
) -> None:
    be.activate_gremlin(True)
    be.pauseInputHighlighting("calibration")
    be.resumeInputHighlighting("calibration")
    assert shared_state.suspend_input_highlighting() is True
    be.activate_gremlin(False)
    assert shared_state.suspend_input_highlighting() is False


def test_run_pauses_and_stop_resumes_with_no_window_open(be: _Backend) -> None:
    be.activate_gremlin(True)
    assert shared_state.suspend_input_highlighting() is True
    be.activate_gremlin(False)
    assert shared_state.suspend_input_highlighting() is False


def test_osc_add_and_calibration_each_hold_their_own_pause(be: _Backend) -> None:
    be.pauseInputHighlighting("calibration")
    be.pauseInputHighlighting("osc-add")
    be.resumeInputHighlighting("osc-add")
    assert shared_state.suspend_input_highlighting() is True
    be.resumeInputHighlighting("calibration")
    assert shared_state.suspend_input_highlighting() is False
