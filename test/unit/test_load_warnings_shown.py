# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Unreadable rows in the Logical Device's and OSC's files (AD1): the user is
told at start, once the main window is up (not during Backend's start, when
nothing listens yet); OSC keeps its unreadable rows in osc.json at Save, in
their places; a failed library change's rollback keeps the Logical Device's
and OSC's unreadable rows."""

from __future__ import annotations

import json
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

sys.path.append(".")

import pytest
from PySide6 import QtCore

from gremlin import history_modules, shared_state
from gremlin import logical_device_file as ldf
from gremlin import osc_device_file as odf
from gremlin.logical_device import LogicalDevice
from gremlin.modules import store
from gremlin.osc import OscDevice
from gremlin.profile import Profile
from gremlin.signal import signal
from gremlin.types import InputType
from gremlin.ui import backend

_KEEP: list[Any] = []

LD_GOOD = {"uid": "a" * 32, "type": "button", "id": 1, "label": "Fire"}
LD_BAD = {"uid": "d" * 32, "type": "button", "id": "abc", "label": "Broken"}
OSC_GOOD_1 = {"uid": "1" * 32, "type": "button", "id": 1, "label": "/gear"}
OSC_BAD = {"uid": "9" * 32, "type": "button", "id": "abc", "label": "/broken"}
OSC_GOOD_2 = {"uid": "2" * 32, "type": "button", "id": 2, "label": "/flaps"}


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _KEEP.append(app)
    yield app


def _clear() -> None:
    OscDevice().rows.reset()
    OscDevice().rows.unreadable = []
    OscDevice().rows.mark_saved()
    LogicalDevice().reset()
    LogicalDevice().load_dict({})
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


def _write_ld(controls: list) -> None:
    doc = {"device": "Logical Device", ldf.KEY: {"controls": controls, "groups": []}}
    ldf.path().write_text(json.dumps(doc), encoding="utf-8")


def _write_osc(inputs: list) -> None:
    odf.path().write_text(json.dumps({odf.KEY: inputs}), encoding="utf-8")


def _osc_on_file() -> list:
    return json.loads(odf.path().read_text(encoding="utf-8"))[odf.KEY]


def _ld_on_file() -> list:
    return json.loads(ldf.path().read_text(encoding="utf-8"))[ldf.KEY]["controls"]


def _drain() -> None:
    for _ in range(5):
        QtCore.QCoreApplication.processEvents()


def test_start_tells_user_about_both_files_once_window_is_up(modules: Path) -> None:
    _write_ld([LD_GOOD, LD_BAD])
    _write_osc([OSC_GOOD_1, OSC_BAD])
    notes: list[tuple[str, str]] = []

    def heard(title: str, text: str) -> None:
        notes.append((title, text))

    signal.showNotification.connect(heard)
    try:
        made = backend.Backend.klass(None)
        _KEEP.append(made)
        # Nothing is said while Backend starts: QML isn't connected yet.
        assert notes == []
        _drain()
    finally:
        signal.showNotification.disconnect(heard)
    titles = [title for title, _ in notes]
    assert "Logical Device" in titles
    assert "OSC" in titles
    text = "\n".join(text for _, text in notes)
    assert "Logical Device control 2 skipped" in text
    assert "OSC input 2 skipped" in text
    # Said once.
    assert len(notes) == 2
    # The good rows still loaded.
    assert [r.label for r in OscDevice().rows.rows()] == ["/gear"]


def test_osc_edit_and_save_keeps_the_unreadable_row_in_place(modules: Path) -> None:
    _write_osc([OSC_GOOD_1, OSC_BAD, OSC_GOOD_2, 42])
    rows = OscDevice().rows
    odf.load()
    assert len(rows.load_warnings) == 2
    assert [r.label for r in rows.rows()] == ["/gear", "/flaps"]
    rows.create(InputType.JoystickButton, "/hook")
    assert odf.save()
    saved = _osc_on_file()
    assert saved[1] == OSC_BAD
    assert saved[3] == 42
    assert [r["label"] for r in saved if isinstance(r, dict)] == [
        "/gear",
        "/broken",
        "/flaps",
        "/hook",
    ]
    # Read again: the same rows are skipped, the same are kept.
    odf.load()
    assert len(rows.load_warnings) == 2
    assert odf.save()
    assert _osc_on_file() == saved


def test_library_rollback_keeps_unreadable_rows(modules: Path) -> None:
    _write_ld([LD_GOOD, LD_BAD])
    _write_osc([OSC_GOOD_1, OSC_BAD])
    ldf.load()
    odf.load()
    profile = Profile()
    with pytest.raises(RuntimeError), profile.library.change():
        LogicalDevice().create(InputType.JoystickButton)
        OscDevice().rows.create(InputType.JoystickButton, "/hook")
        raise RuntimeError("undo")
    assert ldf.save(LogicalDevice())
    assert LD_BAD in _ld_on_file()
    assert odf.save()
    assert OSC_BAD in _osc_on_file()
