# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""To-do 81: File/Exit releases the Windows speech engine, which otherwise
holds the process for about 5 s after it ends (no behaviour change).

A fake engine stands in for QTextToSpeech: the real one needs Windows speech
and, left alive, is the very 5 s exit delay this guards against."""

from __future__ import annotations

import sys

sys.path.append(".")

import pytest
from PySide6 import QtCore

import joystick_gremlin
from gremlin import event_handler, tts
from gremlin.modules import output
from gremlin.ui import backend


class _FakeEngine(QtCore.QObject):
    stateChanged = QtCore.Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self.stopped = 0

    def stop(self) -> None:
        self.stopped += 1


@pytest.fixture
def manager(
    qapp: QtCore.QCoreApplication, monkeypatch: pytest.MonkeyPatch
) -> tts.TTSManager:
    m = tts.TTSManager()
    monkeypatch.setattr(m, "_engine", None)
    monkeypatch.setattr(m, "_running", False)
    return m


def _with_engine(manager: tts.TTSManager) -> tuple[_FakeEngine, list[bool]]:
    engine = _FakeEngine()
    engine.stateChanged.connect(manager._on_state_changed)
    destroyed: list[bool] = []
    engine.destroyed.connect(lambda *_: destroyed.append(True))
    manager._engine = engine  # type: ignore[assignment]
    manager._running = True
    return engine, destroyed


def test_shutdown_cleanup_releases_the_speech_engine(
    manager: tts.TTSManager, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine, destroyed = _with_engine(manager)
    monkeypatch.setattr(output, "reset_drivers", lambda: None)
    monkeypatch.setattr(joystick_gremlin, "_shutdown_done", False)
    monkeypatch.setattr(event_handler.EventListener, "instance", None)
    monkeypatch.setattr(backend.Backend, "instance", None)

    joystick_gremlin.shutdown_cleanup()

    assert engine.stopped >= 1
    assert manager._engine is None
    # Deleted now, not left for an event loop that has already ended.
    assert destroyed == [True]


def test_close_twice_or_with_no_engine_is_harmless(manager: tts.TTSManager) -> None:
    manager.close()  # never made
    _with_engine(manager)
    manager.close()
    manager.close()
    assert manager._engine is None
    assert manager._running is False
