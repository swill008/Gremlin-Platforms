# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""A mode renamed or deleted, followed everywhere (audit 3).

Every rename and delete goes through one path (gremlin.ui.profile
rename_mode / delete_mode): Manage Modes and Device Pack Undo Import alike.
A Cycle steps over a deleted mode, a script that could not be loaded keeps
a renamed mode's new name, and the Button Map's Labels mode follows.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
import types
import uuid
from collections.abc import Iterator
from pathlib import Path
from xml.etree import ElementTree

sys.path.append(".")

import pytest
from PySide6 import QtCore

from gremlin import mode_manager, plugin_manager, shared_state, util
from gremlin.event_handler import EventHandler
from gremlin.profile import Profile
from gremlin.signal import signal
from gremlin.types import InputType, PropertyType

_ROOT = Path(__file__).resolve().parents[2]
_APPS: list[QtCore.QCoreApplication] = []


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


@pytest.fixture
def profile() -> Iterator[Profile]:
    p = Profile()
    for name in ("A", "B", "C"):
        p.modes.add_mode(name)
    shared_state.current_profile = p
    yield p
    EventHandler().known_modes = set()
    mode_manager.ModeManager()._mode_stack = [mode_manager.Mode("Invalid", None)]
    shared_state.current_profile = None


@pytest.fixture
def ui_state(monkeypatch: pytest.MonkeyPatch) -> object:
    """The main window's state, as Backend holds it."""
    from gremlin.ui.backend import Backend, UIState

    state = UIState()
    monkeypatch.setattr(Backend, "instance", types.SimpleNamespace(ui_state=state))
    return state


def _running(profile: Profile, mode: str) -> mode_manager.ModeManager:
    """The profile as it runs: its modes known, the stack in the given mode."""
    EventHandler().known_modes = set(profile.modes.mode_names())
    mm = mode_manager.ModeManager()
    mm._mode_stack = [mode_manager.Mode(mode, None)]
    return mm


def test_cycle_steps_over_a_deleted_mode(profile: Profile, ui_state: object) -> None:
    from action_plugins.change_mode import ChangeModeFunctor, ChangeType
    from gremlin.ui.profile import ModeHierarchyModel

    action = plugin_manager.PluginManager().create_instance(
        "Change Mode", InputType.JoystickButton
    )
    action.change_type = ChangeType.Cycle
    action.target_modes = ["A", "B", "C"]
    functor = ChangeModeFunctor(action)
    mm = _running(profile, "A")
    model = ModeHierarchyModel()
    model.deleteMode("B")
    visited = []
    for _ in range(4):
        mm.cycle(functor._mode_sequence)
        visited.append(mm.current.name)
    # It stayed on A (B was refused at every press).
    assert visited == ["C", "A", "C", "A"]
    # The editor still says the mode is gone.
    assert any("no longer exists" in f.message for f in action.user_feedback())
    model.deleteLater()


@pytest.mark.parametrize(("modes", "deleted"), [(["A", "B"], "B"), (["A"], None)])
def test_cycle_with_only_the_current_mode_left_stays_put(
    profile: Profile, ui_state: object, modes: list[str], deleted: str | None
) -> None:
    from action_plugins.change_mode import ChangeModeFunctor, ChangeType
    from gremlin.ui.profile import ModeHierarchyModel

    action = plugin_manager.PluginManager().create_instance(
        "Change Mode", InputType.JoystickButton
    )
    action.change_type = ChangeType.Cycle
    action.target_modes = modes
    functor = ChangeModeFunctor(action)
    mm = _running(profile, "A")
    model = ModeHierarchyModel()
    if deleted:
        model.deleteMode(deleted)
    fired: list[str] = []
    mm.mode_changed.connect(fired.append)
    try:
        for _ in range(2):
            mm.cycle(functor._mode_sequence)
    finally:
        mm.mode_changed.disconnect(fired.append)
        model.deleteLater()
    # A was not stacked on itself, so Previous and Unwind have nothing to undo.
    assert [(m.name, m.previous) for m in mm._mode_stack] == [("A", None)]
    assert fired == []


def test_a_sequence_without_known_modes_is_unchanged() -> None:
    sequence = mode_manager.ModeSequence(["A", "B"])
    assert sequence.next("A") == "B"
    assert sequence.next("A", {"A"}) == "A"
    # None of them exists: the next one as before (switch_to refuses it).
    assert sequence.next("A", {"Z"}) == "B"


def test_undo_import_deletes_a_mode_everywhere(
    profile: Profile, ui_state: object
) -> None:
    from gremlin.ui import device_pack

    mm = _running(profile, "Default")
    mm.switch_to(mode_manager.Mode("C", "Default"))
    ui_state.setCurrentMode("C")
    deleted: list[str] = []
    signal.modeDeleted.connect(deleted.append)
    device_pack._last_import = {
        "files": [],
        "wires": {
            "profile": profile,
            "uid": uuid.uuid4(),
            "added": [],
            "removed": [],
            "modes": ["C"],
            "logical": [],
        },
    }
    try:
        assert device_pack.undo_import()["ok"]
    finally:
        signal.modeDeleted.disconnect(deleted.append)
        device_pack._last_import = None
    assert not profile.modes.mode_exists("C")
    # Manage Modes' steps: the pages, the main window, the running modes.
    assert deleted == ["C"]
    assert ui_state.currentMode == profile.modes.first_mode
    assert "C" not in [m.name for m in mm._mode_stack]
    assert "C" not in EventHandler().known_modes


def test_manage_modes_rename_moves_the_main_window(
    profile: Profile, ui_state: object
) -> None:
    from gremlin.ui.profile import ModeHierarchyModel

    mm = _running(profile, "A")
    ui_state.setCurrentMode("A")
    model = ModeHierarchyModel()
    model.renameMode("A", "Alpha")
    assert ui_state.currentMode == "Alpha"
    assert mm.current.name == "Alpha"
    assert "Alpha" in EventHandler().known_modes
    model.deleteLater()


def _script_node(mode: str) -> ElementTree.Element:
    node = ElementTree.Element("script")
    node.set("id", str(uuid.uuid4()))
    node.append(
        util.create_property_node(
            "path", Path("C:/no/such/folder/missing_script.py"), PropertyType.Path
        )
    )
    node.append(util.create_property_node("name", "Missing", PropertyType.String))
    variable = ElementTree.SubElement(node, "variable")
    variable.set("type", "mode")
    variable.append(util.create_property_node("name", "m", PropertyType.String))
    variable.append(util.create_property_node("value", mode, PropertyType.String))
    return node


def _saved_mode(script: object) -> str:
    variable = script.to_xml().find("variable")
    return util.read_property(variable, "value", PropertyType.String)


def test_a_script_that_failed_to_load_keeps_the_renamed_mode(
    profile: Profile, ui_state: object, tmp_path: Path
) -> None:
    from gremlin.ui.profile import ModeHierarchyModel
    from gremlin.user_script import Script

    script = Script()
    script.from_xml(_script_node("A"))
    assert script.load_error
    profile.scripts._scripts.append(script)
    model = ModeHierarchyModel()
    model.renameMode("A", "Alpha")
    model.deleteLater()
    assert _saved_mode(script) == "Alpha"
    path = tmp_path / "saved.xml"
    profile.to_xml(path)
    again = Profile()
    again.from_xml(path)
    shared_state.current_profile = again
    [loaded] = again.scripts.scripts
    assert loaded.load_error
    assert _saved_mode(loaded) == "Alpha"


_LABEL_MODE = textwrap.dedent(
    """
    import os, sys, tempfile, unittest.mock
    from pathlib import Path
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ.setdefault(
        "QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
    )
    ROOT = Path(sys.argv[1])
    sys.path.insert(0, str(ROOT))
    import gremlin.util
    gremlin.util.userprofile_path = unittest.mock.Mock(return_value=tempfile.mkdtemp())
    from PySide6 import QtCore, QtGui, QtQml, QtTest
    from gremlin import shared_state
    from gremlin.profile import Profile
    from gremlin.signal import signal

    class FakeBackend(QtCore.QObject):
        changed = QtCore.Signal()
        uiScale = QtCore.Property(int, fget=lambda self: 100, notify=changed)
        gremlinActive = QtCore.Property(bool, fget=lambda self: False, notify=changed)
        currentMode = QtCore.Property(str, fget=lambda self: "Default", notify=changed)

        @QtCore.Slot(str)
        def noteSave(self, text):
            pass

    class FakeUiState(QtCore.QObject):
        modeChanged = QtCore.Signal()
        currentMode = QtCore.Property(
            str, fget=lambda self: "Default", notify=modeChanged
        )

    app = QtGui.QGuiApplication(sys.argv[:1])
    QtQml.qmlRegisterSingletonType(
        QtCore.QUrl.fromLocalFile(str(ROOT / "qml" / "Style.qml")),
        "Gremlin.Style", 1, 0, "Style",
    )
    import gremlin.ui.backend
    import gremlin.ui.button_map_options
    import gremlin.ui.device_names
    import joystick_gremlin
    joystick_gremlin.register_config_options()
    from gremlin.ui.profile import ModeHierarchyModel
    from types import SimpleNamespace
    gremlin.ui.backend.Backend.instance = SimpleNamespace(
        ui_state=gremlin.ui.backend.UIState()
    )

    profile = Profile()
    profile.modes.add_mode("Combat")
    shared_state.current_profile = profile
    backend, ui_state = FakeBackend(), FakeUiState()
    engine = QtQml.QQmlApplicationEngine()
    engine.addImportPath(str(ROOT / "theme"))
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("uiState", ui_state)
    engine.rootContext().setContextProperty("signal", signal)
    engine.load(
        QtCore.QUrl.fromLocalFile(str(ROOT / "qml" / "DialogJoystickButtonMap.qml"))
    )
    win = engine.rootObjects()[0]
    QtTest.QTest.qWait(300)

    def run(code):
        expr = QtQml.QQmlExpression(QtQml.qmlContext(win), win, code)
        value = expr.evaluate()
        if expr.hasError():
            print("ERROR", expr.error().toString(), flush=True)
        return value[0]

    run("_buttonMap.labelMode = 'Combat'")
    model = ModeHierarchyModel()
    model.renameMode("Combat", "Fight")
    QtTest.QTest.qWait(100)
    print("RENAMED", run("_buttonMap.labelMode"), flush=True)
    model.deleteMode("Fight")
    QtTest.QTest.qWait(100)
    print("DELETED", repr(run("_buttonMap.labelMode")), flush=True)
    print("done", flush=True)
    os._exit(0)
    """
)


def test_button_map_labels_mode_follows_a_rename(tmp_path: Path) -> None:
    script = tmp_path / "label_mode.py"
    script.write_text(_LABEL_MODE, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(script), str(_ROOT)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=180,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        cwd=str(_ROOT),
    )
    lines = result.stdout.splitlines()
    assert "done" in lines, (result.stderr or "")[-2000:]
    assert not [line for line in lines if line.startswith("ERROR")], lines
    assert "RENAMED Fight" in lines
    assert "DELETED ''" in lines
