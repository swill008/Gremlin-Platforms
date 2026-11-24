# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""DeviceLiveState.locked reads the Run state (shared_state.runtime_active),
so it tells QML when a Run starts or stops: lockedChanged follows
RunControl's runStarted / runStopped, and only when locked changed
(memory-qml-factory.md, stage 1).

Spec: none (no behaviour change).
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from PySide6 import QtCore

from gremlin import code_runner, shared_state


@pytest.fixture
def live(qapp: object) -> Iterator[object]:
    from gremlin.ui.live_input import DeviceLiveState

    before = shared_state.runtime_active()
    shared_state.set_runtime_active(False)
    state = DeviceLiveState()
    yield state
    shared_state.set_runtime_active(before)
    state.deleteLater()
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)


def _settle() -> None:
    QtCore.QCoreApplication.processEvents()


def test_locked_follows_run_start_and_stop(live: object) -> None:
    control = code_runner.run_control()
    seen: list[bool] = []
    live.lockedChanged.connect(lambda: seen.append(live.locked))
    assert live.locked is False

    shared_state.set_runtime_active(True)
    control.runStarted.emit(True, "")
    _settle()
    assert seen == [True]

    shared_state.set_runtime_active(False)
    control.runStopped.emit()
    _settle()
    assert seen == [True, False]


def test_no_emit_when_locked_did_not_change(live: object) -> None:
    control = code_runner.run_control()
    seen: list[bool] = []
    live.lockedChanged.connect(lambda: seen.append(live.locked))

    # A start that failed: runtime stays off, locked stays False.
    control.runStarted.emit(False, "boom")
    control.runStopped.emit()
    _settle()
    assert seen == []

    # Locked by hand already: a Run starting changes nothing it reports.
    live.locked = True
    seen.clear()
    shared_state.set_runtime_active(True)
    control.runStarted.emit(True, "")
    _settle()
    assert seen == []


def test_destroyed_state_is_disconnected(qapp: object) -> None:
    from gremlin.ui.live_input import DeviceLiveState

    control = code_runner.run_control()
    state = DeviceLiveState()
    state.deleteLater()
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
    # No dangling slot on a deleted object.
    control.runStarted.emit(True, "")
    control.runStopped.emit()
    _settle()
