# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""08 S12b: Clear History empties every Device Library Undo/Redo, even when
an earlier Device Library model's Qt object is already deleted (its
stepsChanged raises "Signal source has been deleted"). The real model, the
real Steps and the real History, in temporary folders."""

from __future__ import annotations

import time
from collections.abc import Iterator
from pathlib import Path

import pytest
import shiboken6
from PySide6 import QtCore
from pytestqt.qtbot import QtBot

from gremlin import device_library as library
from gremlin import history, library_undo
from gremlin.modules import store
from gremlin.ui.device_library_model import DeviceLibraryModel


class _InOrder(list):
    """_ALL in a known order: the stale Steps is cleared first."""

    def add(self, item: object) -> None:
        self.append(item)


class _Source(QtCore.QObject):
    changed = QtCore.Signal()


@pytest.fixture
def folders(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    modules = tmp_path / "modules"
    modules.mkdir()
    monkeypatch.setattr(store, "folder", lambda: modules)
    monkeypatch.setattr(library, "folder", lambda: tmp_path / "device library")
    monkeypatch.setattr(library, "_connected", lambda: [])
    monkeypatch.setattr(history, "folder", lambda: tmp_path / "history")
    monkeypatch.setattr(history, "_pruned", True)
    monkeypatch.setattr(library_undo, "_ALL", _InOrder())
    yield tmp_path
    deadline = time.monotonic() + 5
    while history._writer is not None and time.monotonic() < deadline:
        time.sleep(0.02)


def _filled() -> library_undo.Steps:
    steps = library_undo.Steps()
    assert steps.note(0.0, "Remove Stick", undo=lambda: {"ok": True})
    return steps


def test_deleted_model_does_not_stop_clear(qtbot: QtBot, folders: Path) -> None:
    stale = DeviceLibraryModel(watch_devices=False)
    stale_steps = stale._steps
    assert stale_steps.note(0.0, "Rename Stick", undo=lambda: {"ok": True})
    shiboken6.delete(stale)
    live = _filled()
    assert live.undo_text()
    assert history.clear_all()["ok"]
    assert live.undo_text() == ""
    assert stale_steps.undo_text() == ""


def test_deleted_model_stops_listening(qtbot: QtBot, folders: Path) -> None:
    model = DeviceLibraryModel(watch_devices=False)
    steps = model._steps
    assert len(steps.on_cleared) == 1
    shiboken6.delete(model)
    assert steps.on_cleared == []


def test_dead_listener_dropped_and_rest_told(folders: Path) -> None:
    steps = _filled()
    source = _Source()
    dead = source.changed.emit
    shiboken6.delete(source)
    told: list[int] = []
    steps.on_cleared += [dead, lambda: told.append(1)]
    steps.clear()
    assert told == [1]
    assert len(steps.on_cleared) == 1 and dead not in steps.on_cleared
    steps.clear()
    assert told == [1, 1]
