# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""01 S140, S141, S143 on the Keyboard page, the Logical Device page and the
Options path settings (Phase B, B-config). Off-screen, each part in its own
process (this file run as a script: python <this> <part> <out_dir>).

- Keyboard page Delete asks the shared question (confirmDialog); Enter
  cancels (the key stays), a click on the red button deletes it.
- Logical Device page: Find is the shared SearchBox ("N found", Esc clears);
  Delete on a row asks the shared question; the Undo bar names the change.
- Options path setting: the shared FilePicker (folder mode, kind "log" for
  the Logs folder) starts in the setting's own folder while nothing is
  remembered, and in the remembered folder after a pick.
"""

from __future__ import annotations

import importlib.util
import os
import pathlib
import subprocess
import sys

sys.path.append(".")

_HERE = pathlib.Path(__file__).parent
_ROOT = _HERE.parents[1]


def _screens():  # noqa: ANN202
    spec = importlib.util.spec_from_file_location(
        "_audit3_screens", _HERE / "test_audit3_screens.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run(part: str, tmp_path: pathlib.Path) -> dict[str, str]:
    result = subprocess.run(
        [sys.executable, str(pathlib.Path(__file__)), part, str(tmp_path)],
        capture_output=True,
        text=True,
        timeout=180,
        cwd=str(_ROOT),
        env={
            **os.environ,
            "QT_QPA_PLATFORM": "offscreen",
            "GREMLIN_OFFLINE": "1",
            "USERPROFILE": str(tmp_path),
        },
    )
    lines = result.stdout.splitlines()
    assert "done" in lines, result.stdout[-3000:] + result.stderr[-3000:]
    errors = [line for line in lines if line.startswith("ERROR")]
    assert not errors, errors
    ours = [
        line for line in lines
        if line.startswith("WARN") and any(
            name in line for name in (
                "KeyboardInputList", "LogicalPage", "ConfigGroup", "FilePicker",
                "SearchBox", "UndoBar", "ConfirmDialog", "EmptyState",
            )
        )
    ]
    assert not ours, ours
    return {
        line.split(" ", 2)[1]: line.split(" ", 2)[2]
        for line in lines
        if line.startswith("RESULT ")
    }


def test_keyboard_delete_asks_the_shared_question(tmp_path: pathlib.Path) -> None:
    r = _run("keyboard", tmp_path)
    assert r["asked"] == "true Delete key A? | Delete Key | This can't be undone."
    assert r["enter"] == "False 1"  # Enter cancelled: the key stays
    assert r["click"] == "False 0"  # the red button deleted it


def test_logical_page_search_delete_and_undo_bar(tmp_path: pathlib.Path) -> None:
    r = _run("logical", tmp_path)
    assert r["search"] == "true 1 found"
    assert r["esc"] == "|false"
    assert r["asked"] == "true Delete Button 2? | Delete Row | 3"
    assert r["enter"] == "3"
    assert r["click"] == "2 Last change: Delete Button 2"
    assert r["undone"] == "3 Undone: Delete Button 2"


def test_option_folder_picker_remembers(tmp_path: pathlib.Path) -> None:
    r = _run("options", tmp_path)
    assert r["kind"] == "log folder"
    assert r["start"] == "setting"
    assert r["after"] == "remembered"


def _confirm(win: object):  # noqa: ANN202
    from PySide6 import QtCore

    found = [d for d in win.findChildren(QtCore.QObject, "confirmDialog")
             if d.property("visible")]
    return found[0] if found else None


def _confirm_text(win: object) -> str:

    dialog = _confirm(win)
    if dialog is None:
        return "false"
    title = dialog.property("titleText")
    action = dialog.property("actionText")
    last = dialog.property("lastLine")
    return f"true {title} | {action} | {last}" if dialog else "false"


def _key(win: object, key) -> None:  # noqa: ANN001
    from PySide6 import QtTest

    QtTest.QTest.keyClick(win, key)


def _click_red(win: object) -> None:
    from PySide6 import QtCore, QtTest

    dialog = _confirm(win)
    button = [b for b in dialog.findChildren(QtCore.QObject, "confirmAction")][0]
    point = button.mapToScene(
        QtCore.QPointF(button.property("width") / 2, button.property("height") / 2)
    ).toPoint()
    QtTest.QTest.mouseClick(win, QtCore.Qt.MouseButton.LeftButton,
                            QtCore.Qt.KeyboardModifier.NoModifier, point)


def _keyboard(s, out: pathlib.Path) -> None:  # noqa: ANN001
    from PySide6 import QtCore

    app, engine, warnings = s._engine(out)  # noqa: F841
    import dill
    import gremlin.action_label  # noqa: F401
    import gremlin.ui.device  # noqa: F401
    import gremlin.ui.util  # noqa: F401
    from gremlin import shared_state
    from gremlin.event_handler import Event
    from gremlin.profile import Profile
    from gremlin.signal import signal
    from gremlin.types import InputType
    from gremlin.ui.backend import UIState

    shared_state.current_profile = Profile()
    backend_cls, _ = s._fakes()
    backend = backend_cls()
    ui_state = UIState()
    ui_state.setCurrentDevice(str(dill.UUID_Keyboard))
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("uiState", ui_state)
    engine.rootContext().setContextProperty("signal", signal)
    engine.loadData(
        b"""
import QtQuick
import QtQuick.Window
Window {
    width: 600; height: 700; visible: true
    QtObject { id: bsi; property var icons: ({ remove: "x" }) }
    KeyboardInputList { id: _page; anchors.fill: parent }
    function list() {
        function find(item) {
            if (item.model !== undefined && item.currentIndex !== undefined
                    && item.count !== undefined)
                return item
            for (var i = 0; i < item.children.length; i++) {
                var f = find(item.children[i])
                if (f) return f
            }
            return null
        }
        return find(_page)
    }
}
""",
        QtCore.QUrl.fromLocalFile(str(_ROOT / "qml" / "Root.qml")),
    )
    win = engine.rootObjects()[0]
    s._wait(300)
    from PySide6 import QtQml

    context = QtQml.qmlContext(win)
    model = QtQml.QQmlExpression(context, win, "list().model").evaluate()[0]
    model.addKey(
        [Event(InputType.Keyboard, (30, False), dill.UUID_Keyboard, "Default")],
        "Default",
    )
    s._wait(200)
    s._js(win, "_page._confirmDelete(0, 'A'); 1")
    s._wait(200)
    s._Out.result("asked", _confirm_text(win))
    _key(win, QtCore.Qt.Key.Key_Return)
    s._wait(200)
    s._Out.result("enter", f"{_confirm(win) is not None} {model.rowCount()}")
    s._js(win, "_page._confirmDelete(0, 'A'); 1")
    s._wait(200)
    _click_red(win)
    s._wait(300)
    s._Out.result("click", f"{_confirm(win) is not None} {model.rowCount()}")
    s._report(warnings)


def _logical(s, out: pathlib.Path) -> None:  # noqa: ANN001
    from PySide6 import QtCore

    app, engine, warnings = s._engine(out)  # noqa: F841
    import gremlin.action_label  # noqa: F401
    import gremlin.ui.logical_layout  # noqa: F401
    import gremlin.ui.profile  # noqa: F401
    from gremlin import plugin_manager, shared_state
    from gremlin.common import InputType
    from gremlin.logical_device import LogicalDevice
    from gremlin.profile import Profile
    from gremlin.signal import signal
    from gremlin.ui import leave_text
    from gremlin.ui.backend import UIState

    _leave = leave_text.install(app)  # noqa: F841 (Esc leaves a text box, 01 S134)
    plugin_manager.PluginManager()  # its QML module (Gremlin.ActionPlugins)
    shared_state.current_profile = Profile()
    LogicalDevice().reset()
    LogicalDevice().create_many(InputType.JoystickButton, 2, "", "")
    LogicalDevice().create_many(InputType.JoystickAxis, 1, "", "")
    backend_cls, _ = s._fakes()
    backend = backend_cls()
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("uiState", UIState())
    engine.rootContext().setContextProperty("signal", signal)
    engine.loadData(
        b"""
import QtQuick
import QtQuick.Window
Window {
    width: 1200; height: 800; visible: true
    QtObject { id: bsi; property var icons: ({ remove: "x" }) }
    LogicalPage { id: _page; anchors.fill: parent }
    function findName(item, name) {
        if (item.objectName === name)
            return item
        for (var i = 0; i < item.children.length; i++) {
            var f = findName(item.children[i], name)
            if (f) return f
        }
        return null
    }
}
""",
        QtCore.QUrl.fromLocalFile(str(_ROOT / "qml" / "Root.qml")),
    )
    if not engine.rootObjects():
        for warning in warnings:
            print("ERROR load: " + warning, flush=True)
        os._exit(1)
    win = engine.rootObjects()[0]
    s._wait(400)
    js = lambda code: s._js(win, code)  # noqa: E731
    count = "String(findName(_page, 'searchCount').text)"
    # Ctrl+F goes to the search box; typing filters, the line counts.
    from PySide6 import QtTest

    ctrl = QtCore.Qt.KeyboardModifier.ControlModifier
    QtTest.QTest.keyClick(win, QtCore.Qt.Key.Key_F, ctrl)
    s._wait(100)
    box = "findName(findName(_page, 'logicalFind'), 'searchField')"
    focused = js(f"String({box}.activeFocus)")
    for char in "Axis":
        QtTest.QTest.keyClick(win, char)
    s._wait(200)
    s._Out.result("search", f"{focused} {js(count)}")
    _key(win, QtCore.Qt.Key.Key_Escape)
    s._wait(200)
    field = "findName(findName(_page, 'logicalFind'), 'searchField')"
    s._Out.result("esc", js(f"{field}.text + '|' + {field}.activeFocus"))

    from gremlin.ui.logical_layout import LogicalLayoutModel

    layout = win.findChildren(LogicalLayoutModel)[0]
    js("_page._askDeleteRows(['parent:button:2'], 'Button 2'); 1")
    s._wait(200)
    _restore = " | You can restore it from Tools › History."
    s._Out.result("asked", _confirm_text(win).replace(_restore, "")
                  + " | " + str(layout.parentCount))
    _key(win, QtCore.Qt.Key.Key_Return)
    s._wait(200)
    s._Out.result("enter", str(layout.parentCount))
    js("_page._askDeleteRows(['parent:button:2'], 'Button 2'); 1")
    s._wait(200)
    _click_red(win)
    s._wait(300)
    bar = "String(findName(_page, 'undoBarText').text)"
    s._Out.result("click", f"{layout.parentCount} {js(bar)}")
    js("findName(_page, 'undoBarUndo').clicked(); 1")
    s._wait(300)
    s._Out.result("undone", f"{layout.parentCount} {js(bar)}")
    s._report(warnings)


def _options(s, out: pathlib.Path) -> None:  # noqa: ANN001
    from PySide6 import QtCore

    app, engine, warnings = s._engine(out)  # noqa: F841
    from gremlin.ui import option

    setting = out / "my logs"
    setting.mkdir(parents=True, exist_ok=True)
    elsewhere = out / "elsewhere"
    elsewhere.mkdir(parents=True, exist_ok=True)
    import gremlin.config

    cfg = gremlin.config.Configuration()
    cfg.set("global", "files", "logs-folder", setting)
    model = option.ConfigEntryModel(
        "global", "files", keys=[("global", "files", "logs-folder")]
    )
    engine.rootContext().setContextProperty("logsModel", model)
    backend = s._fakes()[0]()
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty(
        "elsewhereUrl", QtCore.QUrl.fromLocalFile(str(elsewhere)).toString()
    )
    engine.rootContext().setContextProperty(
        "settingUrl", QtCore.QUrl.fromLocalFile(str(setting)).toString()
    )
    engine.loadData(
        b"""
import QtQuick
import QtQuick.Layouts
import QtQuick.Window
Window {
    width: 600; height: 400; visible: true
    ConfigGroup { id: _group; index: 0; groupName: "Folders"; entryModel: logsModel }
    function picker() {
        function find(item) {
            if (item.objectName === "optionPathPicker")
                return item
            for (var i = 0; i < item.children.length; i++) {
                var f = find(item.children[i])
                if (f) return f
            }
            return null
        }
        return find(_group)
    }
}
""",
        QtCore.QUrl.fromLocalFile(str(_ROOT / "qml" / "Root.qml")),
    )
    win = engine.rootObjects()[0]
    s._wait(300)
    js = lambda code: s._js(win, code)  # noqa: E731
    s._Out.result("kind", js("picker().kind + ' ' + picker().mode"))
    # The Select button sets the fallback folder; prepare() sets the dialog
    # up without showing it (no native dialog off-screen).
    def url(path: pathlib.Path) -> str:
        return QtCore.QUrl.fromLocalFile(str(path)).toString().lower().rstrip("/")

    js("picker().folder = settingUrl; 1")
    start = js("String(picker().prepare().currentFolder)").lower()
    s._Out.result("start", "setting" if start.rstrip("/") == url(setting) else start)
    js("picker()._accept(elsewhereUrl); 1")
    start = js("String(picker().prepare().currentFolder)").lower()
    s._Out.result(
        "after",
        "remembered" if start.rstrip("/") == url(elsewhere) else start,
    )
    s._report(warnings)


if __name__ == "__main__":
    _s = _screens()
    _s._boot()
    sys.stdout.reconfigure(encoding="utf-8")
    _part, _out_dir = sys.argv[1], pathlib.Path(sys.argv[2])
    _out_dir.mkdir(parents=True, exist_ok=True)
    try:
        parts = {"keyboard": _keyboard, "logical": _logical, "options": _options}
        parts[_part](_s, _out_dir)
    except Exception as failed:  # noqa: BLE001
        import traceback

        traceback.print_exc()
        print(f"ERROR {_part}: {failed!r}", flush=True)
        os._exit(1)
