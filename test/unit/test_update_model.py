# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import sys

sys.path.append(".")

import pathlib
from collections.abc import Iterator

import pytest
from PySide6 import QtCore

from gremlin import updater
from gremlin.config import Configuration
from gremlin.signal import signal
from gremlin.ui import update_model

_app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])


@pytest.fixture
def updates(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> pathlib.Path:
    monkeypatch.setattr(updater, "updates_dir", lambda: tmp_path)
    return tmp_path


@pytest.fixture
def notices() -> Iterator[list[tuple[str, str]]]:
    shown: list[tuple[str, str]] = []

    def note(title: str, text: str) -> None:
        shown.append((title, text))

    signal.showNotification.connect(note)
    yield shown
    signal.showNotification.disconnect(note)


def test_nothing_installs_without_a_verified_download() -> None:
    model = update_model.UpdateModel()
    model.setInstallOnExit(True)
    assert model.start_pending_install() is False


def test_cancelled_quit_clears_the_install(
    monkeypatch: pytest.MonkeyPatch, updates: pathlib.Path
) -> None:
    started = []
    monkeypatch.setattr(
        QtCore.QProcess, "startDetached", lambda *args: started.append(args) or True
    )
    setup = updates / "Gremlin-Platforms-R1-9.9.9-Setup.exe"
    setup.write_bytes(b"x")
    model = update_model.UpdateModel()
    model._ready_path = setup
    model.setInstallOnExit(True)
    model.setInstallOnExit(False)
    assert model.start_pending_install() is False
    model.setInstallOnExit(True)
    assert model.start_pending_install() is True
    assert started[0][0] == str(setup)
    assert "/LAUNCH=1" in started[0][1]


def test_says_so_once_after_an_update(
    updates: pathlib.Path, notices: list[tuple[str, str]]
) -> None:
    (updates / "old-Setup.exe").write_bytes(b"x")
    cfg = Configuration()
    cfg.set("global", "internal", "last-run-version", "0.0.1")
    shown = notices
    model = update_model.UpdateModel()
    model._note_finished_update()
    model._note_finished_update()
    assert len(shown) == 1
    assert model.currentVersion in shown[0][1]
    assert not (updates / "old-Setup.exe").exists()
    assert cfg.value("global", "internal", "last-run-version") == model.currentVersion


def test_first_run_is_not_an_update(
    updates: pathlib.Path, notices: list[tuple[str, str]]
) -> None:
    Configuration().set("global", "internal", "last-run-version", "")
    update_model.UpdateModel()._note_finished_update()
    assert notices == []
