# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The screens' side of the stand-alone Logical Device (D-04-LD-FILE):
read from its file at start and kept across profile loads, its edits count
for the "*" and the save-changes question (04 S2), the one-time note after
a version 14 profile moved its rows (04 S25), and Logical page Undo steps
kept across profile loads (06 S83)."""

from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

sys.path.append(".")

import pytest
from PySide6 import QtCore

from gremlin import history_modules, shared_state
from gremlin import logical_device_file as ldf
from gremlin.logical_device import LogicalDevice, LogicalRows
from gremlin.modules import store
from gremlin.profile import Profile
from gremlin.signal import signal
from gremlin.types import InputType
from gremlin.ui import backend

_APPS: list[QtCore.QCoreApplication] = []
_KEEP: list[Any] = []

# A real version 14 profile with its own Logical Device rows.
_V14 = (
    Path(__file__).resolve().parents[1]
    / "action_interaction"
    / "profiles"
    / "axis_delta.xml"
)


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


@pytest.fixture
def modules(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Path]:
    folder = tmp_path / "modules"
    folder.mkdir()
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    monkeypatch.setattr(store, "folder", lambda: folder)
    monkeypatch.setattr(store, "_saved", lambda: None)
    monkeypatch.setattr(history_modules, "note_write", lambda *_a, **_k: None)
    LogicalDevice().reset()
    LogicalDevice().mark_saved()
    yield folder
    LogicalDevice().reset()
    LogicalDevice().mark_saved()
    shared_state.current_profile = None


def _file_with_gear() -> None:
    rows = LogicalRows()
    rows.create(InputType.JoystickButton, label="Gear")
    ldf.save(rows)


def _backend() -> Any:  # noqa: ANN401
    # The class inside the singleton wrapper: a fresh one per test.
    made = backend.Backend.klass(None)
    _KEEP.append(made)
    return made


def test_start_reads_the_logical_device_from_its_file(modules: Path) -> None:
    _file_with_gear()
    LogicalDevice().reset()
    _backend()
    assert [i.label for i in LogicalDevice().ordered()] == ["Gear"]
    assert not LogicalDevice().dirty


def test_another_profile_keeps_the_logical_device(modules: Path) -> None:
    _file_with_gear()
    LogicalDevice().reset()
    made = _backend()
    made.newProfile()
    assert [i.label for i in LogicalDevice().ordered()] == ["Gear"]


def test_a_logical_edit_is_an_unsaved_change(modules: Path) -> None:
    made = _backend()
    made.profile.mark_clean()
    LogicalDevice().mark_saved()
    assert not made.profileContainsUnsavedChanges
    seen: list[bool] = []
    made.unsavedChanged.connect(lambda: seen.append(True))
    LogicalDevice().create(InputType.JoystickButton, label="Flaps")
    signal.logicalDeviceModified.emit()
    assert seen, "the window wasn't told to check the * again"
    assert made.profileLooksUnsaved
    assert made.profileContainsUnsavedChanges


def test_discard_reads_the_logical_device_file_again(modules: Path) -> None:
    _file_with_gear()
    LogicalDevice().reset()
    made = _backend()
    LogicalDevice().create(InputType.JoystickButton, label="Flaps")
    assert made.profileContainsUnsavedChanges
    made.discardLogicalDevice()
    assert [i.label for i in LogicalDevice().ordered()] == ["Gear"]
    assert not LogicalDevice().dirty


def test_main_window_discard_drops_the_logical_device_edits() -> None:
    main = (Path(__file__).resolve().parents[2] / "qml" / "Main.qml").read_text(
        encoding="utf-8"
    )
    dialog = main[main.index("id: _saveBeforeContinueDialog") :]
    discard = dialog[dialog.index("onDiscardChosen") : dialog.index("onCancelled")]
    assert "backend.discardLogicalDevice()" in discard


def test_a_version_14_profile_says_once_what_moved(
    modules: Path, tmp_path: Path
) -> None:
    made = _backend()
    notes: list[tuple[str, str]] = []

    def note(title: str, message: str) -> None:
        notes.append((title, message))

    signal.showNotification.connect(note)
    old = tmp_path / "old.xml"
    old.write_text(_V14.read_text(encoding="utf-8"), encoding="utf-8")
    made._read_profile(str(old))
    moved = [m for t, m in notes if t == "Logical Device"]
    assert len(moved) == 1
    assert moved[0].startswith("Logical Device moved to its own file: added ")
    assert "Input Axis 1" in moved[0]
    notes.clear()
    made._read_profile(str(old))
    signal.showNotification.disconnect(note)
    assert not [m for t, m in notes if t == "Logical Device"]


def test_migration_note_text() -> None:
    assert backend.logical_migration_text([]) == ""
    assert backend.logical_migration_text(["Button 9 (Gear)", "Axis 3"]) == (
        "Logical Device moved to its own file: added Button 9 (Gear), Axis 3."
    )


@pytest.fixture
def layout() -> Iterator[Any]:
    from gremlin.ui.logical_layout import LogicalLayoutModel

    LogicalDevice().reset()
    shared_state.current_profile = Profile()
    LogicalDevice().create(InputType.JoystickButton)
    model = LogicalLayoutModel()
    yield model
    model.endPane()
    model.deleteLater()
    LogicalDevice().reset()
    shared_state.current_profile = None


def test_logical_steps_stay_when_another_profile_loads(
    layout: Any,  # noqa: ANN401
) -> None:
    key = "parent:button:1"
    layout.setUserName(key, "Trigger")
    assert layout.canUndo
    shared_state.current_profile = Profile()
    signal.profileChanged.emit()
    assert layout.canUndo
    layout.undo()
    assert LogicalDevice().ordered()[0].user_label == ""


def test_logical_steps_still_go_with_a_deleted_mode(
    layout: Any,  # noqa: ANN401
) -> None:
    layout.setUserName("parent:button:1", "Trigger")
    signal.modeDeleted.emit("Combat")
    assert not layout.canUndo


def test_discard_drops_the_logical_steps(
    modules: Path,
    layout: Any,  # noqa: ANN401
) -> None:
    made = _backend()  # reads the (empty) file: the page's row goes
    LogicalDevice().create(InputType.JoystickButton)
    signal.logicalDeviceModified.emit()
    layout.setUserName("parent:button:1", "Trigger")
    assert layout.canUndo
    made.discardLogicalDevice()
    assert not layout.canUndo
    assert not layout.canRedo


def test_a_restore_of_the_file_drops_the_logical_steps(
    modules: Path,
    layout: Any,  # noqa: ANN401
) -> None:
    # Restore / Import / History Restore replace the file through the store:
    # the page's Undo steps would replay edits that are gone (D-04-LD-FILE).
    _backend()
    LogicalDevice().create(InputType.JoystickButton)
    ldf.save()
    saved = ldf.path().read_bytes()
    signal.logicalDeviceModified.emit()
    layout.setUserName("parent:button:1", "Trigger")
    assert layout.canUndo
    store.replace(ldf.path(), saved, "test")
    assert not layout.canUndo
    assert not layout.canRedo
