# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The Keyboard page on the shared control layout (05 S128, CF-Q7).

Rows are the profile's keys (each listed once, the shown mode's actions as
children, S72); Add Key and Delete are page Undo steps (S73, S75, S127);
groups, order and Rename are held for File > Save in the Keyboard's input
module file (S122, S129: Rename is the friendly name, CS1); the pane edits a
draft that OK writes (05 Q5).

Spec: 05 S72-S77, S121-S131 (CF-Q7, CF-Q8).
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any, cast

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest
import smoke_report  # pyright: ignore[reportMissingImports]  (test/)

import dill
from gremlin import shared_state
from gremlin.event_handler import Event
from gremlin.profile import InputItem, Profile
from gremlin.types import InputType
from gremlin.ui.keyboard_layout import KeyboardLayoutModel, key_row, keyboard_store
from test.unit._device_folders import put_module

A = (30, False)
S = (31, False)


@pytest.fixture
def modules(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    from gremlin.modules import store

    folder = tmp_path / "modules"
    folder.mkdir()
    monkeypatch.setattr(store, "folder", lambda: folder)
    return folder


@pytest.fixture
def page(qapp: object, modules: Path) -> Iterator[KeyboardLayoutModel]:
    from gremlin.modules import store

    profile = Profile()
    profile.modes.add_mode("Combat")
    old = shared_state.current_profile
    shared_state.current_profile = profile
    store.discard_pending("")
    keyboard_store().load()
    model = KeyboardLayoutModel()
    try:
        yield model
    finally:
        model.endPane()
        model.deleteLater()
        store.discard_pending("")
        keyboard_store().load()
        shared_state.current_profile = old


def _must(item: InputItem | None) -> InputItem:
    assert item is not None
    return item


def _profile() -> Profile:
    profile = shared_state.current_profile
    assert profile is not None
    return profile


def _keys(model: KeyboardLayoutModel) -> list[str]:
    return [
        model.keyAt(i)
        for i in range(model.rowCount())
        if model.keyAt(i).startswith("parent:")
    ]


def _rows(model: KeyboardLayoutModel, kind: str) -> list[dict]:
    return [row for row in model._rows if row["rowKind"] == kind]


def _add(model: KeyboardLayoutModel, code: tuple, mode: str = "Default") -> str:
    event = Event(InputType.Keyboard, code, dill.UUID_Keyboard, mode)
    return model.addKey([event], mode)


def _items(code: tuple) -> list:
    return [
        item
        for item in _profile().inputs.get(dill.UUID_Keyboard, [])
        if tuple(cast(Any, item.input_id)) == code
    ]


def test_rows_are_the_profiles_keys_once_with_the_shown_modes_actions(
    page: KeyboardLayoutModel,
) -> None:
    profile = _profile()
    for mode in ("Default", "Combat"):
        profile.get_input_item(dill.UUID_Keyboard, InputType.Keyboard, A, mode, True)
    _must(
        profile.get_input_item(
            dill.UUID_Keyboard, InputType.Keyboard, A, "Combat", True
        )
    ).add_item_binding()
    page.setMode("Default")
    assert _keys(page) == [key_row(A)]
    assert _rows(page, "parent")[0]["childCount"] == 0
    page.setMode("Combat")
    assert _rows(page, "parent")[0]["childCount"] == 1
    assert _rows(page, "parent")[0]["title"] == "A"


def test_add_key_is_an_undo_step_in_the_mode_shown(page: KeyboardLayoutModel) -> None:
    page.setMode("Combat")
    assert _add(page, A, "Combat") == key_row(A)
    assert [(tuple(i.input_id), i.mode) for i in _items(A)] == [(A, "Combat")]
    assert _keys(page) == [key_row(A)]
    assert page.canUndo
    page.undo()
    assert _items(A) == []
    assert _keys(page) == []
    page.redo()
    assert [(tuple(i.input_id), i.mode) for i in _items(A)] == [(A, "Combat")]
    # The same key again: nothing new, no step.
    page.undo()
    page.redo()
    steps = len(page._undo)
    assert _add(page, A, "Combat") == key_row(A)
    assert len(page._undo) == steps
    assert _add(page, A, "Combat") == key_row(A)
    assert page.addKey([], "Combat") == ""


def test_delete_takes_only_this_modes_actions_and_undo_puts_them_back(
    page: KeyboardLayoutModel,
) -> None:
    profile = _profile()
    for mode in ("Default", "Combat"):
        _must(
            profile.get_input_item(
                dill.UUID_Keyboard, InputType.Keyboard, A, mode, True
            )
        ).add_item_binding()
    page.setMode("Default")
    page.deleteParents([key_row(A)])
    assert [i.mode for i in _items(A)] == ["Combat"]
    # Still listed: another mode has it (S75).
    assert _keys(page) == [key_row(A)]
    page.undo()
    assert sorted(i.mode for i in _items(A)) == ["Combat", "Default"]
    default = next(i for i in _items(A) if i.mode == "Default")
    assert len(default.action_sequences) == 1


def test_delete_shows_only_where_it_does_something(page: KeyboardLayoutModel) -> None:
    profile = _profile()
    _must(
        profile.get_input_item(
            dill.UUID_Keyboard, InputType.Keyboard, A, "Combat", True
        )
    ).add_item_binding()
    page.setMode("Default")
    assert not page.canDelete(key_row(A))
    page.deleteParents([key_row(A)])
    assert [i.mode for i in _items(A)] == ["Combat"]
    _add(page, S, "Default")
    assert page.canDelete(key_row(S))
    page.deleteParents([key_row(S)])
    assert _items(S) == []
    page.undo()
    assert [i.mode for i in _items(S)] == ["Default"]


def test_groups_and_order_are_held_for_save_and_undo_drops_them(
    page: KeyboardLayoutModel, modules: Path
) -> None:
    from gremlin.modules import store

    _add(page, A)
    _add(page, S)
    page.addGroup("Flight")
    page.setSelection([key_row(S)])
    page.moveSelected("Flight")
    held = store.pending_layout(str(dill.UUID_Keyboard))
    assert held is not None
    assert held["layout"]["groups"] == ["Flight"]
    assert held["layout"]["group_of"] == {"key:31": "Flight"}
    parents = _rows(page, "parent")
    assert [(r["key"], r["groupName"]) for r in parents] == [
        (key_row(A), ""),
        (key_row(S), "Flight"),
    ]
    page.moveRow(key_row(A), key_row(S))
    assert [r["key"] for r in _rows(page, "parent")] == [key_row(A), key_row(S)]
    assert _rows(page, "parent")[0]["groupName"] == "Flight"
    # Nothing written to a file until Save.
    assert not any(modules.iterdir())
    while page.canUndo:
        page.undo()
    held = store.pending_layout(str(dill.UUID_Keyboard))
    assert held is None or (
        held["layout"] in (None, store.empty_layout()) and not held["names"]
    )


def test_rename_is_the_friendly_name_held_until_save(
    page: KeyboardLayoutModel, modules: Path
) -> None:
    from gremlin.modules import store

    path = put_module(modules, "Keyboard", {"name": "Keyboard"})
    _add(page, A)
    page.setUserName(key_row(A), "Fire")
    row = _rows(page, "parent")[0]
    assert row["userName"] == "Fire"
    assert "Fire" in row["title"]
    held = store.pending_layout(str(dill.UUID_Keyboard))
    assert held is not None and held["names"] == {"key:30": "Fire"}
    # Not in the profile any more (was 05 S77) and not written yet.
    assert all(not getattr(i, "action_name", "") for i in _items(A))
    assert "Fire" not in path.read_text(encoding="utf-8")
    page.undo()
    assert _rows(page, "parent")[0]["userName"] == ""


def test_the_pane_edits_a_draft_that_ok_writes_as_one_step(
    page: KeyboardLayoutModel,
) -> None:
    _add(page, A)
    page.beginNewAction(key_row(A))
    assert page.paneModel is not None
    assert _items(A)[0].action_sequences == []
    _must(page._pane_shadow).add_item_binding()
    assert page.paneDirty()
    assert page.commitPane() >= 0
    assert len(_items(A)[0].action_sequences) == 1
    assert _rows(page, "parent")[0]["childCount"] == 1
    page.endPane()
    page.undo()
    assert not any(i.action_sequences for i in _items(A))


def test_steps_and_rows_follow_another_profile(page: KeyboardLayoutModel) -> None:
    from gremlin.signal import signal

    _add(page, A)
    page.addGroup("Flight")
    shared_state.current_profile = Profile()
    signal.profileChanged.emit()
    # The key list is the Keyboard module file's (AD4), shared by every
    # profile: the key stays listed, and the add's list part stays as a
    # layout step (S127); its profile part went with the old profile.
    assert _keys(page) == [key_row(A)]
    assert [e["label"] for e in page._undo] == ["Add Key A", "New Group Flight"]
    assert all(not e["links"] for e in page._undo)


_QML_BUILD = """
from PySide6 import QtCore, QtGui, QtQml
app = QtGui.QGuiApplication([])
import gremlin.ui.keyboard_layout  # registers KeyboardLayoutModel
engine = QtQml.QQmlEngine()
component = QtQml.QQmlComponent(engine)
component.setData(
    b"import QtQml; import Gremlin.Device; KeyboardLayoutModel {"
    b" property var g: groups; property bool u: canUndo }",
    QtCore.QUrl(),
)
built = component.create()
print("BUILT" if built is not None else "NULL " + component.errorString())
"""


def test_qml_builds_the_model() -> None:
    # A property notified by a base-class signal crashes QML building the
    # type (as HardwareLayoutModel did); a child process so a crash fails
    # this test instead of the run.
    import os
    import pathlib
    import sys

    done = proc_tree.run(
        [sys.executable, "-c", _QML_BUILD],
        cwd=str(pathlib.Path(__file__).resolve().parents[2]),
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        text=True,
        timeout=60,
    )
    assert done.returncode == 0, smoke_report.explain(done)
    assert "BUILT" in done.stdout, smoke_report.explain(done)


def test_key_names_do_not_depend_on_which_lookup_ran_first(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A letter looked up by its character first ("a") still shows by its
    key name ("A"), as a lookup by code gives it (seed 707209 order bug)."""
    from gremlin import keyboard

    monkeypatch.setattr(
        keyboard, "g_scan_code_to_key", dict(keyboard.g_scan_code_to_key)
    )
    monkeypatch.setattr(keyboard, "g_name_to_key", dict(keyboard.g_name_to_key))
    for code in (A, S):
        keyboard.g_scan_code_to_key.pop(code, None)
    for name in ("a", "s"):
        keyboard.g_name_to_key.pop(name, None)

    assert keyboard.key_from_name("a").name == "A"
    assert keyboard.key_from_code(*A).name == "A"
    assert keyboard.key_from_code(*S).name == "S"
    assert keyboard.key_from_name("s") is keyboard.key_from_code(*S)


# -- AD4 (SHAKE-JOURNEYS SJ-01): a key with no actions is kept --------------


def _save_and_reopen(path: Path) -> KeyboardLayoutModel:
    """File > Save (the profile, then the held layouts), then the profile
    opened again on a fresh page."""
    from gremlin.modules import store

    _profile().to_xml(path)
    store.save_pending()
    reopened = Profile()
    reopened.from_xml(path)
    shared_state.current_profile = reopened
    keyboard_store().load()
    return KeyboardLayoutModel()


def _keyboard_file(modules: Path) -> Path:
    path = put_module(modules, "Keyboard", {"name": "Keyboard"})
    return path


def test_a_key_with_no_actions_is_kept_at_save_and_reopen(
    page: KeyboardLayoutModel, modules: Path, tmp_path: Path
) -> None:
    _keyboard_file(modules)
    _add(page, A)
    assert _items(A)[0].action_sequences == []
    again = _save_and_reopen(tmp_path / "p.xml")
    try:
        assert _keys(again) == [key_row(A)]
        assert again.canDelete(key_row(A))
        # Delete takes it off the list; Save and reopen: gone.
        again.deleteParents([key_row(A)])
        assert _keys(again) == []
        again.undo()
        assert _keys(again) == [key_row(A)]
        again.redo()
        assert _keys(again) == []
        third = _save_and_reopen(tmp_path / "p.xml")
        try:
            assert _keys(third) == []
        finally:
            third.deleteLater()
    finally:
        again.deleteLater()


def test_discard_drops_an_unsaved_added_key(
    page: KeyboardLayoutModel, modules: Path, tmp_path: Path
) -> None:
    from gremlin.modules import store

    _keyboard_file(modules)
    path = tmp_path / "p.xml"
    _profile().to_xml(path)
    _add(page, A)
    assert store.has_pending()
    # Discard on the save-changes question: the held layout and the
    # profile's edits both go (the saved profile is opened again).
    store.discard_pending("")
    reopened = Profile()
    reopened.from_xml(path)
    shared_state.current_profile = reopened
    again = KeyboardLayoutModel()
    try:
        assert _keys(again) == []
    finally:
        again.deleteLater()


# -- GL-254 (05 G13, RB18): viewing a key creates nothing --------------------


def test_viewing_a_key_with_no_actions_creates_no_input(
    page: KeyboardLayoutModel, modules: Path, tmp_path: Path
) -> None:
    """Selecting a key row with no actions and opening its pane (input or
    Add Action) leaves the profile alone: no input, not unsaved, and Save
    writes no empty input for it. OK on an action then creates the input,
    one Undo step."""
    _keyboard_file(modules)
    profile = _profile()
    _add(page, A)  # A is listed (Default); Combat has no input for it.
    path = tmp_path / "p.xml"
    profile.to_xml(path)
    from gremlin.modules import store

    store.save_pending()
    profile.mark_clean()
    page.setMode("Combat")
    steps = len(page._undo)
    page.setSelection([key_row(A)])
    for open_pane in (
        lambda: page.beginPane(key_row(A), -1),
        lambda: page.beginNewAction(key_row(A)),
    ):
        open_pane()
        assert page.paneModel is not None
        assert not page.paneDirty()
        assert page.commitPane() == -1  # OK on nothing writes nothing
        page.discardPane()
        page.endPane()
        assert [i.mode for i in _items(A)] == ["Default"]
    assert not profile.has_unsaved_changes()
    assert len(page._undo) == steps
    profile.to_xml(path)
    assert path.read_text(encoding="utf-8").count('mode="Combat"') == 0

    page.beginNewAction(key_row(A))
    _must(page._pane_shadow).add_item_binding()
    assert page.commitPane() >= 0
    page.endPane()
    combat = [i for i in _items(A) if i.mode == "Combat"]
    assert len(combat) == 1 and combat[0].action_sequences
    assert len(page._undo) == steps + 1
    assert profile.has_unsaved_changes()
    page.undo()
    assert not any(i.action_sequences for i in _items(A) if i.mode == "Combat")
