# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Undo Delete Mode (04 S46a, D-04-UNDO-DELETE-MODE).

While the same profile is open, Manage Modes' Undo Delete Mode brings back
the mode deleted last (then the one before) with its bindings, its place in
the tree, the child modes that moved up and Startup Mode if it named it; if
it can't, a notice says why. The tests go through the Manage Modes model
(the slots the window's buttons call); the last one clicks the real button
in the real window, off-screen in its own process.
"""

from __future__ import annotations

import sys

sys.path.append(".")

import json
import os
import pathlib
import subprocess
import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from PySide6 import QtCore

from gremlin import plugin_manager, shared_state
from gremlin.logical_device import LogicalDevice
from gremlin.profile import Profile
from gremlin.signal import signal
from gremlin.types import InputType
from gremlin.ui.profile import ModeHierarchyModel

_ROOT = pathlib.Path(__file__).parents[2]
_STICK = uuid.UUID("55555555-6666-7777-8888-999999999999")
_APP = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])


@pytest.fixture
def profile() -> Iterator[Profile]:
    before = shared_state.current_profile
    p = Profile()
    shared_state.current_profile = p
    yield p
    shared_state.current_profile = before
    LogicalDevice().reset()


@pytest.fixture
def model(profile: Profile) -> Iterator[ModeHierarchyModel]:
    m = ModeHierarchyModel()
    yield m
    m.deleteLater()
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)


def _bind(profile: Profile, mode: str, note: str, hw: int = 1) -> None:
    item = profile.get_input_item(
        _STICK, InputType.JoystickButton, hw, mode, create_if_missing=True
    )
    assert item is not None
    desc: Any = plugin_manager.PluginManager().create_instance(
        "Description", InputType.JoystickButton
    )
    desc.description = note
    item.add_item_binding().root_action.insert_action(desc, "children")


def _notes(profile: Profile, mode: str, hw: int = 1) -> list[str]:
    item = profile.get_input_item(_STICK, InputType.JoystickButton, hw, mode)
    if item is None:
        return []
    return [
        a.description
        for binding in item.action_sequences
        for a in binding.root_action.get_actions()[0]
    ]


def _parent(profile: Profile, mode: str) -> str:
    return profile.modes._parent_name(profile.modes.find_mode(mode))


def _tree(profile: Profile, *names: str, under: str = "") -> None:
    for name in names:
        profile.modes.add_mode(name)
        if under:
            profile.modes.set_parent(name, under)


def test_bindings_come_back(profile: Profile, model: ModeHierarchyModel) -> None:
    _tree(profile, "Flight")
    _bind(profile, "Flight", "gear", hw=1)
    _bind(profile, "Flight", "flaps", hw=2)
    model.deleteMode("Flight")
    assert _notes(profile, "Flight") == []

    assert model.undoDelete() == ""
    assert _notes(profile, "Flight", 1) == ["gear"]
    assert _notes(profile, "Flight", 2) == ["flaps"]
    assert model.bindingCount("Flight") == 2


def test_place_in_tree_and_moved_children_come_back(
    profile: Profile, model: ModeHierarchyModel
) -> None:
    _tree(profile, "Top")
    _tree(profile, "Mid", under="Top")
    _tree(profile, "KidA", "KidB", under="Mid")
    _tree(profile, "Grandkid", under="KidA")
    model.deleteMode("Mid")
    assert _parent(profile, "KidA") == "Top" and _parent(profile, "KidB") == "Top"

    assert model.undoDelete() == ""
    assert _parent(profile, "Mid") == "Top"
    assert _parent(profile, "KidA") == "Mid" and _parent(profile, "KidB") == "Mid"
    assert _parent(profile, "Grandkid") == "KidA"


def test_startup_mode_comes_back_if_it_named_the_mode(
    profile: Profile, model: ModeHierarchyModel
) -> None:
    _tree(profile, "Flight", "Taxi")
    profile.settings.startup_mode = "Flight"
    model.deleteMode("Flight")
    assert profile.settings.startup_mode == "Last Active"
    model.undoDelete()
    assert profile.settings.startup_mode == "Flight"

    # A mode Startup Mode didn't name leaves it as it is.
    model.deleteMode("Taxi")
    model.undoDelete()
    assert profile.settings.startup_mode == "Flight"


def test_several_deletes_come_back_newest_first(
    profile: Profile, model: ModeHierarchyModel
) -> None:
    _tree(profile, "Parent")
    _tree(profile, "Child", under="Parent")
    _bind(profile, "Child", "child note")
    _bind(profile, "Parent", "parent note")
    model.deleteMode("Child")
    model.deleteMode("Parent")
    assert model.undoDeleteName == "Parent"

    assert model.undoDelete() == ""
    assert profile.modes.mode_exists("Parent")
    assert not profile.modes.mode_exists("Child")
    assert model.canUndoDelete and model.undoDeleteName == "Child"

    assert model.undoDelete() == ""
    assert _parent(profile, "Child") == "Parent"
    assert _notes(profile, "Child") == ["child note"]
    assert _notes(profile, "Parent") == ["parent note"]
    assert not model.canUndoDelete and model.undoDeleteName == ""


def test_another_profile_opened_leaves_nothing_to_undo(
    profile: Profile, model: ModeHierarchyModel
) -> None:
    _tree(profile, "Flight")
    model.deleteMode("Flight")
    assert model.canUndoDelete

    other = Profile()
    shared_state.current_profile = other
    assert not model.canUndoDelete and model.undoDeleteName == ""
    assert model.undoDelete() == ""
    assert not other.modes.mode_exists("Flight")
    # Back to the first profile: its deletes went when the other opened.
    shared_state.current_profile = profile
    assert not model.canUndoDelete


def test_a_failed_undo_shows_a_notice_saying_why(
    profile: Profile, model: ModeHierarchyModel
) -> None:
    notes: list[tuple[str, str]] = []

    def note(title: str, text: str) -> None:
        notes.append((title, text))

    signal.showNotification.connect(note)
    try:
        _tree(profile, "Flight")
        model.deleteMode("Flight")
        model.newMode("FLIGHT")
        why = model.undoDelete()
    finally:
        signal.showNotification.disconnect(note)
    assert notes == [("Undo Delete Mode", why)]
    assert "a mode with that name is in the profile now" in why
    assert profile.modes.mode_names() == ["Default", "FLIGHT"]


def test_place_in_tree_follows_a_renamed_parent(
    profile: Profile, model: ModeHierarchyModel
) -> None:
    # The parent renamed after the delete is still the mode's place.
    _tree(profile, "Mid")
    _tree(profile, "Kid", under="Mid")
    model.deleteMode("Kid")
    model.renameMode("Mid", "Middle")
    assert model.undoDelete() == ""
    assert _parent(profile, "Kid") == "Middle"


def test_moved_children_follow_a_rename(
    profile: Profile, model: ModeHierarchyModel
) -> None:
    # A child mode that moved up and was renamed since still goes back.
    _tree(profile, "Top")
    _tree(profile, "Mid", under="Top")
    _tree(profile, "Kid", under="Mid")
    model.deleteMode("Mid")
    model.renameMode("Kid", "Kiddo")
    assert model.undoDelete() == ""
    assert _parent(profile, "Mid") == "Top"
    assert _parent(profile, "Kiddo") == "Mid"


_WINDOW = """
import json, os, sys, uuid
sys.path.insert(0, '.')
import importlib.util
spec = importlib.util.spec_from_file_location('fake_hardware', 'test/fake_hardware.py')
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake_hardware.install()
import gremlin.ui.update_model as um
um.UpdateModel.startup = lambda self, *a, **k: None
import joystick_gremlin
from PySide6 import QtCore, QtQml, QtQuick, QtTest
from gremlin import shared_state
app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
win = app.main_window
modes = shared_state.current_profile.modes
modes.add_mode('Flight')
modes.add_mode('Kid')
modes.set_parent('Kid', 'Flight')

expr = QtQml.QQmlExpression(
    QtQml.qmlContext(win), win, 'Helpers.createComponent("DialogManageModes.qml")')
expr.evaluate()
assert not expr.hasError(), expr.error().toString()
QtTest.QTest.qWait(400)
dialog = [w for w in app.topLevelWindows() if w is not win and w.isVisible()
          and isinstance(w, QtQuick.QQuickWindow) and w.title() == 'Manage Modes'][0]
def items(item):
    yield item
    for child in item.childItems():
        yield from items(child)
# Undo Delete Mode is the shared Undo / Redo pair's Undo (01 S143).
button = [b for b in items(dialog.contentItem())
          if b.objectName() == 'undoBarUndo'][0]
out = {'before': button.property('enabled')}
delete = QtQml.QQmlExpression(QtQml.qmlContext(dialog), dialog,
                              'modeHierarchy.deleteMode("Flight")')
delete.evaluate()
assert not delete.hasError(), delete.error().toString()
QtTest.QTest.qWait(100)
out['after_delete'] = button.property('enabled')
out['deleted'] = not modes.mode_exists('Flight')
point = button.mapToScene(QtCore.QPointF(button.width() / 2, button.height() / 2))
QtTest.QTest.mouseClick(dialog, QtCore.Qt.MouseButton.LeftButton,
                        QtCore.Qt.KeyboardModifier.NoModifier, point.toPoint())
QtTest.QTest.qWait(200)
out['back'] = modes.mode_exists('Flight')
out['kid_parent'] = modes._parent_name(modes.find_mode('Kid'))
out['after_undo'] = button.property('enabled')
print('RESULT ' + json.dumps(out), flush=True)
os._exit(0)  # threads started by the app would keep it alive
"""


def test_the_button_in_manage_modes_brings_the_mode_back(
    tmp_path: pathlib.Path,
) -> None:
    home = tmp_path / "home"
    (home / "Gremlin Platforms").mkdir(parents=True)
    script = home / "undo_delete.py"
    script.write_text(_WINDOW, encoding="utf-8")
    env = dict(os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen")
    result = subprocess.run(
        [sys.executable, str(script)], cwd=_ROOT, env=env,
        capture_output=True, text=True, timeout=120,
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, result.stdout[-1500:] + result.stderr[-1500:]
    out = json.loads(lines[0][len("RESULT "):])
    assert out == {
        "before": False, "after_delete": True, "deleted": True,
        "back": True, "kid_parent": "Flight", "after_undo": False,
    }
