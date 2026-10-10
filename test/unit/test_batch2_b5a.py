# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Batch 2, B5a: the action panes and the edit lock.

- One edit lock (06 S13, S82, RB14; GL-171): binding_catalog.editing_locked()
  follows the Run; the pane models refuse edits with it, and every page
  reads it through EditLock instead of its own backend.gremlinActive rule.
- The catalog pane while running is read-only with no OK (05 Q11, GL-160);
  a Logical pane open when Run starts turns read-only too (06 Q6, GL-169).
- The panes answer Main.closeActionPanes(): paneHasChanges(),
  closeActionPane(), savePane() (05 Q8, GL-098; 06 Q6, GL-169).
- The Keyboard page edits a draft with OK, Undo and Redo (05 Q5, GL-106);
  a new key shows one empty binding to fill in (05 Q4, GL-164); its remove
  icon now removes from the draft only (GL-044).
- The Output filter shows with or without vJoy (05 S18, GL-166).
- A row's History shows the open profile's changes (08 Q16, GL-194).
"""

from __future__ import annotations

import re
import sys
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

sys.path.append(".")

import pytest
from PySide6 import QtCore

import dill
from gremlin import plugin_manager, run_scope, shared_state
from gremlin.logical_device import LogicalDevice
from gremlin.profile import Profile
from gremlin.types import InputType

_ROOT = Path(__file__).resolve().parents[2]
_QML = _ROOT / "qml"
_STICK = uuid.UUID("12121212-3434-5656-7878-909090909090")
_KEY = (30, False)
_APPS: list[QtCore.QCoreApplication] = []


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


@pytest.fixture
def profile() -> Iterator[Profile]:
    profile = Profile()
    shared_state.current_profile = profile
    yield profile
    shared_state.current_profile = None


@pytest.fixture
def running(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(run_scope, "_running", True)


def _vjoy(out: int) -> Any:  # noqa: ANN401
    action = plugin_manager.PluginManager().create_instance(
        "Map to vJoy", InputType.JoystickButton
    )
    action.vjoy_device_id = 1
    action.vjoy_input_id = out
    action.vjoy_input_type = InputType.JoystickButton
    return action


def _catalog(profile: Profile) -> Any:  # noqa: ANN401
    from gremlin.ui.binding_catalog import BindingCatalogModel

    item = profile.get_input_item(
        _STICK, InputType.JoystickButton, 1, "Default", create_if_missing=True
    )
    item.add_item_binding().root_action.insert_action(_vjoy(3), "children")
    model = BindingCatalogModel()

    def spec(device_index: int) -> tuple:
        real = profile.get_input_item(_STICK, InputType.JoystickButton, 1, "Default")
        return profile, _STICK, InputType.JoystickButton, 1, "Default", real

    model._control_spec = spec
    return model


def _targets(
    profile: Profile,
    guid: uuid.UUID = _STICK,
    kind: Any = InputType.JoystickButton,  # noqa: ANN401
    hw: Any = 1,  # noqa: ANN401
) -> list[int]:
    item = profile.get_input_item(guid, kind, hw, "Default")
    if item is None:
        return []
    return [
        b.root_action.get_actions()[0][0].vjoy_input_id
        for b in item.action_sequences
        if b.root_action.get_actions()[0]
    ]


# --- the edit lock (GL-171, GL-160, GL-169) ----------------------------------


def test_the_lock_follows_the_run(monkeypatch: pytest.MonkeyPatch) -> None:
    from gremlin.ui.binding_catalog import EditLock, editing_locked

    lock = EditLock()
    assert not editing_locked() and not lock.locked
    monkeypatch.setattr(run_scope, "_running", True)
    assert editing_locked() and lock.locked
    lock.deleteLater()


def test_catalog_ok_is_refused_while_running(profile: Profile, running: None) -> None:
    model = _catalog(profile)
    model.beginPane(0, -1)  # opens to look at (read-only)
    root = model._pane_shadow.action_sequences[0].root_action
    root.get_actions()[0][0].vjoy_input_id = 9
    assert model.paneDirty()
    assert model.commitPane() == -1
    assert _targets(profile) == [3]
    model.endPane()


def test_catalog_delete_and_undo_are_refused_while_running(
    profile: Profile, monkeypatch: pytest.MonkeyPatch
) -> None:
    model = _catalog(profile)
    before = model._snapshot(0)
    item = profile.get_input_item(_STICK, InputType.JoystickButton, 1, "Default")
    item.remove_item_binding(item.action_sequences[0])
    model._step(0, before)
    monkeypatch.setattr(run_scope, "_running", True)
    model.undo()
    assert _targets(profile) == []
    model._claimed.rowCount = lambda: 0
    assert not model.removeSequence(0, 0)


def test_logical_edits_are_refused_while_running(
    profile: Profile, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin.ui.logical_layout import LogicalLayoutModel

    LogicalDevice().reset()
    LogicalDevice().create(InputType.JoystickButton)
    model = LogicalLayoutModel()
    model.beginNewAction("parent:button:1")
    root = model._pane_shadow.action_sequences[0].root_action
    root.insert_action(_vjoy(4), "children")
    monkeypatch.setattr(run_scope, "_running", True)
    assert model.commitPane() == -1
    assert profile.get_input_item(
        LogicalDevice().device_guid, InputType.JoystickButton, 1, "Default"
    ) is None
    count = len(LogicalDevice().ordered())
    model.addMany("button", 2, "", "")
    assert len(LogicalDevice().ordered()) == count
    model.endPane()
    model.deleteLater()
    LogicalDevice().reset()


def _read(name: str) -> str:
    return (_QML / name).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "name",
    [
        "BindingCatalog.qml",
        "InputConfiguration.qml",
        "KeyboardInputList.qml",
        "LogicalPage.qml",
    ],
)
def test_every_page_reads_the_one_lock(name: str) -> None:
    text = _read(name)
    assert "EditLock" in text
    assert not re.search(r"editorLocked:\s*backend", text)


def test_the_catalog_pane_has_no_ok_while_running() -> None:
    text = _read("BindingCatalog.qml")
    pane = text[text.index("inputItemModel: _catalog.paneModel"):]
    pane = pane[: pane.index('text: "OK"')]
    assert 'text: "Profile running: stop it to edit"' in pane
    assert "visible: !_root.editorLocked" in pane


def test_a_logical_pane_has_no_ok_while_running() -> None:
    text = _read("ActionPane.qml")
    pane = text[text.index("inputItemModel: _pane.layout.paneModel"):]
    pane = pane[: pane.index('text: "OK"')]
    assert 'text: "Profile running: stop it to edit"' in pane
    assert "visible: !_pane.locked" in pane
    assert "locked: _root.editorLocked" in _read("LogicalPage.qml")


# --- Main.closeActionPanes() contract (GL-098, GL-169) -----------------------


@pytest.mark.parametrize(
    "name", ["BindingCatalog.qml", "InputConfiguration.qml", "LogicalPage.qml"]
)
def test_each_pane_answers_close_action_panes(name: str) -> None:
    text = _read(name)
    for fn in ("paneHasChanges", "closeActionPane", "savePane"):
        assert f"function {fn}()" in text, fn


# --- the Keyboard page's draft (GL-106, GL-164, GL-044) ----------------------


class _Key(QtCore.QObject):
    def __init__(self, key: tuple = _KEY) -> None:
        super().__init__()
        self.device_guid = dill.UUID_Keyboard
        self.input_type = InputType.Keyboard
        self.input_id = key
        self.isValid = True


def _keyboard_pane(profile: Profile) -> Any:  # noqa: ANN401
    from gremlin.ui.binding_catalog import KeyboardPaneModel

    model = KeyboardPaneModel()
    model.showInput(_Key(), 0, "Default")
    return model


def _first_action(model: Any) -> Any:  # noqa: ANN401
    return model._pane_shadow.action_sequences[0].root_action


def test_a_new_key_shows_one_empty_binding(profile: Profile) -> None:
    profile.get_input_item(
        dill.UUID_Keyboard, InputType.Keyboard, _KEY, "Default", True
    )  # Add Key
    model = _keyboard_pane(profile)
    assert model.paneModel is not None
    assert len(model._pane_shadow.action_sequences) == 1
    assert not model.paneDirty()
    model.endPane()


def test_keyboard_edits_wait_for_ok_and_undo(profile: Profile) -> None:
    model = _keyboard_pane(profile)
    _first_action(model).insert_action(_vjoy(5), "children")
    assert model.paneDirty()
    # The profile is not changed by the pane.
    assert _targets(profile, dill.UUID_Keyboard, InputType.Keyboard, _KEY) == []
    assert model.commitPane() >= 0
    assert _targets(profile, dill.UUID_Keyboard, InputType.Keyboard, _KEY) == [5]
    assert model.canUndo and not model.paneDirty()
    model.undo()
    assert _targets(profile, dill.UUID_Keyboard, InputType.Keyboard, _KEY) == []
    assert model.paneModel is not None  # the pane opens again
    assert model.canRedo
    model.redo()
    assert _targets(profile, dill.UUID_Keyboard, InputType.Keyboard, _KEY) == [5]
    model.endPane()


def test_keyboard_remove_and_cancel_change_nothing(profile: Profile) -> None:
    item = profile.get_input_item(
        dill.UUID_Keyboard, InputType.Keyboard, _KEY, "Default", True
    )
    item.add_item_binding().root_action.insert_action(_vjoy(6), "children")
    model = _keyboard_pane(profile)
    shadow = model._pane_shadow
    shadow.remove_item_binding(shadow.action_sequences[0])  # the remove icon
    assert model.paneDirty()
    assert _targets(profile, dill.UUID_Keyboard, InputType.Keyboard, _KEY) == [6]
    model.revert()  # Cancel
    assert not model.paneDirty()
    assert _targets(profile, dill.UUID_Keyboard, InputType.Keyboard, _KEY) == [6]
    model.endPane()


def test_keyboard_ok_is_refused_while_running(profile: Profile, running: None) -> None:
    model = _keyboard_pane(profile)
    _first_action(model).insert_action(_vjoy(5), "children")
    assert model.commitPane() == -1
    assert _targets(profile, dill.UUID_Keyboard, InputType.Keyboard, _KEY) == []
    model.endPane()


def test_the_keyboard_pane_takes_only_keys(profile: Profile) -> None:
    from gremlin.ui.binding_catalog import KeyboardPaneModel

    other = _Key()
    other.device_guid = _STICK
    model = KeyboardPaneModel()
    model.showInput(other, 0, "Default")
    assert model.paneModel is None


def test_the_keyboard_page_uses_the_draft() -> None:
    text = _read("InputConfiguration.qml")
    assert "KeyboardPaneModel" in text
    assert 'uiState.currentTab === "keyboard"' in text
    assert "model: _root.inlineMode ? null : _root.shownModel" in text
    assert 'objectName: "keyboardOk"' in text


# --- Output filter (GL-166) and History filter (GL-194) ----------------------


def test_the_output_filter_shows_without_vjoy() -> None:
    text = _read("BindingCatalog.qml")
    assert "hasValidVJoyDevices" not in text
    box = text[text.index("id: _destBox"):]
    box = box[: box.index("}")]
    assert "visible:" not in box


def test_a_rows_history_is_the_open_profiles() -> None:
    text = _read("BindingCatalog.qml")
    fn = text[text.index("function historyFilter(hid)"):]
    fn = fn[: fn.index("return JSON.stringify(w)")]
    assert "backend.profilePath()" in fn and "w.profile = path" in fn
    assert "filter: _root.historyFilter(deviceIndex)" in text


def test_the_history_filter_matches_by_profile() -> None:
    from gremlin.ui.history_model import _matches

    entry = {"area": "profile", "subject": {"profile": "C:/p/a.xml", "deviceId": "x"}}
    assert _matches(entry, {"profile": "C:/p/a.xml", "deviceId": "x"})
    assert not _matches(entry, {"profile": "C:/p/b.xml", "deviceId": "x"})
    # Show All keeps only the area.
    assert _matches(entry, {"area": "profile"})
