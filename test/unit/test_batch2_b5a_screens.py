# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Batch 2, B5a: the Keyboard page's draft on screen (05 Q5, Q4; GL-106,
GL-164). Off-screen, in its own process (this file run as a script:
python test/unit/test_batch2_b5a_screens.py <out_dir>).

A key just added shows one empty binding with OK; an action put in it is
not in the profile until OK; Undo takes the OK back.
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


def test_the_keyboard_page_edits_a_draft(tmp_path: pathlib.Path) -> None:
    result = subprocess.run(
        [sys.executable, str(pathlib.Path(__file__)), str(tmp_path)],
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
    r = {
        line.split(" ", 2)[1]: line.split(" ", 2)[2]
        for line in lines
        if line.startswith("RESULT ")
    }
    errors = [line for line in lines if line.startswith("ERROR")]
    assert not errors, errors
    ours = [
        line for line in lines
        if line.startswith("WARN") and "InputConfiguration" in line
    ]
    assert not ours, ours
    # A new key: one empty binding, nothing written, OK shown.
    assert r["new-key"] == "1 0 true"
    # An action added in the draft is not in the profile until OK.
    assert r["before-ok"] == "true 0"
    assert r["after-ok"] == "false 1 true"
    assert r["undone"] == "0 true"


def _run(out: pathlib.Path) -> None:
    from PySide6 import QtCore

    s = _screens()
    app, engine, warnings = s._engine(out)  # noqa: F841
    import dill
    import gremlin.action_label  # noqa: F401
    import gremlin.ui.device  # noqa: F401
    import gremlin.ui.profile  # noqa: F401
    import gremlin.ui.util  # noqa: F401
    from gremlin import plugin_manager, shared_state
    from gremlin.event_handler import Event
    from gremlin.profile import Profile
    from gremlin.signal import signal
    from gremlin.types import InputType
    from gremlin.ui.backend import UIState

    plugin_manager.PluginManager()  # its QML module (Gremlin.ActionPlugins)
    profile = Profile()
    shared_state.current_profile = profile
    backend_cls, _ = s._fakes()
    backend = backend_cls()
    ui_state = UIState()
    ui_state.setCurrentDevice(str(dill.UUID_Keyboard))
    ui_state.setCurrentTab("keyboard")
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("uiState", ui_state)
    engine.rootContext().setContextProperty("signal", signal)
    engine.loadData(
        b"""
import QtQuick
import QtQuick.Window
Window {
    width: 1200; height: 700; visible: true
    QtObject { id: bsi; property var icons: ({ remove: "x" }) }
    KeyboardInputList { id: _page; width: 400; height: 700 }
    InputConfiguration { id: _editor; x: 400; width: 800; height: 700 }
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

    key = (30, False)
    events = [Event(InputType.Keyboard, key, dill.UUID_Keyboard, "Default")]
    from gremlin.ui.util import InputListenerModel

    add_key = win.findChildren(InputListenerModel)[0]
    add_key.listeningTerminated.emit(events)  # Add Key: A
    s._wait(400)

    def written() -> int:
        item = profile.get_input_item(
            dill.UUID_Keyboard, InputType.Keyboard, key, "Default"
        )
        return len(item.action_sequences) if item is not None else 0

    rows = js("_editor.shownModel ? _editor.shownModel.rowCount() : -1")
    ok = js("String(findName(_editor, 'keyboardOk').visible)")
    s._Out.result("new-key", f"{rows} {written()} {ok}")

    # An action into the draft's binding, as the editor's Add would.
    from gremlin.ui.binding_catalog import KeyboardPaneModel

    pane = win.findChildren(KeyboardPaneModel)[0]
    action = plugin_manager.PluginManager().create_instance(
        "Description", InputType.Keyboard
    )
    root = pane._pane_shadow.action_sequences[0].root_action
    root.insert_action(action, "children")
    s._Out.result("before-ok", f"{js('String(_editor.paneHasChanges())')} {written()}")
    js("findName(_editor, 'keyboardOk').clicked(); 1")
    s._wait(200)
    dirty = js("String(_editor.paneHasChanges())")
    undo = js("String(findName(_editor, 'keyboardUndo').enabled)")
    s._Out.result("after-ok", f"{dirty} {written()} {undo}")
    js("findName(_editor, 'keyboardUndo').clicked(); 1")
    s._wait(200)
    s._Out.result("undone", f"{written()} {js('String(!!_editor.shownModel)')}")
    s._report(warnings)


if __name__ == "__main__":
    _screens()._boot()
    sys.stdout.reconfigure(encoding="utf-8")
    _out_dir = pathlib.Path(sys.argv[1])
    _out_dir.mkdir(parents=True, exist_ok=True)
    try:
        _run(_out_dir)
    except Exception as failed:  # noqa: BLE001
        import traceback

        traceback.print_exc()
        print(f"ERROR keyboard-draft: {failed!r}", flush=True)
        os._exit(1)
