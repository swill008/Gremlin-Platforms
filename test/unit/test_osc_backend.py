# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The screens' side of OSC's own file (D-09-OSC-FILE), as the Logical
Device's (test_ld_ui.py): read from its file at start and kept across
profile loads, its edits count for the "*" and the save-changes question,
Discard reads the file again; an older profile's OSC rows are not read, so
only the Logical Device's move is said (AD7)."""

from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import smoke_report  # pyright: ignore[reportMissingImports]  (test/)

sys.path.append(".")

import pytest
from PySide6 import QtCore

from gremlin import history_modules, shared_state
from gremlin import osc_device_file as odf
from gremlin.logical_device import LogicalDevice
from gremlin.modules import store
from gremlin.osc import OscDevice
from gremlin.osc_rows import OscRows
from gremlin.signal import signal
from gremlin.types import InputType
from gremlin.ui import backend

_APPS: list[QtCore.QCoreApplication] = []
_KEEP: list[Any] = []


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


def _clear() -> None:
    OscDevice().rows.reset()
    OscDevice().rows.mark_saved()
    LogicalDevice().reset()
    LogicalDevice().mark_saved()


@pytest.fixture
def modules(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Path]:
    folder = tmp_path / "modules"
    folder.mkdir()
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    monkeypatch.setattr(store, "folder", lambda: folder)
    monkeypatch.setattr(store, "_saved", lambda: None)
    monkeypatch.setattr(history_modules, "note_write", lambda *_a, **_k: None)
    _clear()
    yield folder
    _clear()
    shared_state.current_profile = None


def _file_with_gear() -> None:
    rows = OscRows()
    rows.create(InputType.JoystickButton, "/gear")
    odf.save(rows)
    OscDevice().rows.reset()
    OscDevice().rows.mark_saved()


def _labels() -> list[str]:
    return [row.label for row in OscDevice().rows.rows()]


def _backend() -> Any:  # noqa: ANN401
    # The class inside the singleton wrapper: a fresh one per test.
    made = backend.Backend.klass(None)
    _KEEP.append(made)
    return made


def test_start_reads_osc_from_its_file(modules: Path) -> None:
    _file_with_gear()
    _backend()
    assert _labels() == ["/gear"]
    assert not OscDevice().rows.dirty


def test_start_with_default_settings_makes_no_osc_file(modules: Path) -> None:
    # A fresh install gets no OSC file, so Home still selects the stick first.
    _backend()
    assert not odf.path().exists()


def test_another_profile_keeps_osc(modules: Path) -> None:
    _file_with_gear()
    made = _backend()
    made.newProfile()
    assert _labels() == ["/gear"]
    made.profileChanged.emit()
    assert _labels() == ["/gear"]


def test_an_osc_edit_is_an_unsaved_change(modules: Path) -> None:
    made = _backend()
    made.profile.mark_clean()
    assert not made.profileContainsUnsavedChanges
    seen: list[bool] = []
    made.unsavedChanged.connect(lambda: seen.append(True))
    OscDevice().rows.create(InputType.JoystickButton, "/flaps")
    signal.oscDeviceModified.emit()
    assert seen, "the window wasn't told to check the * again"
    assert made.profileLooksUnsaved
    assert made.profileContainsUnsavedChanges


def test_discard_reads_osc_file_again(modules: Path) -> None:
    _file_with_gear()
    made = _backend()
    OscDevice().rows.create(InputType.JoystickButton, "/flaps")
    assert made.profileContainsUnsavedChanges
    reloaded: list[bool] = []

    def heard() -> None:
        reloaded.append(True)

    signal.oscDeviceReloaded.connect(heard)
    try:
        made.discardOscDevice()
    finally:
        signal.oscDeviceReloaded.disconnect(heard)
    assert _labels() == ["/gear"]
    assert not OscDevice().rows.dirty
    assert reloaded, "the OSC page's Undo steps weren't told to go"


def test_main_window_discard_drops_the_osc_edits() -> None:
    main = (Path(__file__).resolve().parents[2] / "qml" / "Main.qml").read_text(
        encoding="utf-8"
    )
    dialog = main[main.index("id: _saveBeforeContinueDialog") :]
    discard = dialog[dialog.index("onDiscardChosen") : dialog.index("onCancelled")]
    assert "backend.discardOscDevice()" in discard


_SMOKE = Path(__file__).resolve().parent / "osc_module_setup_smoke.py"


def _plain(guid: str) -> str:
    return guid.upper().replace("{", "").replace("}", "").replace("-", "")


def test_options_osc_button_opens_osc_module_setup(tmp_path: Path) -> None:
    import json
    import os

    home = tmp_path / "home"
    home.mkdir()
    env = dict(
        os.environ,
        USERPROFILE=str(home),
        QT_QPA_PLATFORM="offscreen",
        GREMLIN_OFFLINE="1",
        PYTHONIOENCODING="utf-8",
    )
    result = proc_tree.run(
        [sys.executable, str(_SMOKE)],
        cwd=Path(__file__).resolve().parents[2],
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, smoke_report.explain(result)
    out = json.loads(lines[-1][len("RESULT ") :])
    assert out["signal"], "signal.openOscModuleSetup is missing"
    assert out["opened"], "OSC's Module Setup didn't open"
    assert _plain(out["guid"]) == _plain(str(backend.OSC_DEVICE_UUID))
    assert out["direction"] == "source"
    assert out["errors"] == []
