# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Opening another input in the action pane with unsaved edits asks Save /
Discard / Cancel first (05 S26). Every list page (Device Bindings, Keyboard,
Logical Device, OSC) opens the pane through ActionPane.openAt / openNew:
a row click, an action row, the menu's Open and Add Action. Cancel keeps
the edit, the pane on the first input and the selection; Discard drops the
edit and opens the second; Save writes it, then opens the second.

The test runs the real program off-screen (stand-in hardware) in its own
process with a fresh user folder: this file run as a script creates an
ActionPane on a stand-in layout and tree inside the main window.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
    import smoke_report  # pyright: ignore[reportMissingImports]  (test/)
    home = tmp_path_factory.mktemp("home")
    (home / "Gremlin Platforms").mkdir(parents=True)
    env = dict(
        os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen",
        GREMLIN_OFFLINE="1", PYTHONIOENCODING="utf-8",
        TEMP=str(home), TMP=str(home),
    )
    result = proc_tree.run(
        [sys.executable, str(pathlib.Path(__file__).resolve())],
        cwd=_ROOT, env=env, text=True,
        encoding="utf-8", errors="replace", timeout=180,
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, smoke_report.explain(result)
    out = json.loads(lines[-1][len("RESULT "):])
    assert "error" not in out, out
    return out


def test_clean_pane_opens_the_other_input_at_once(run: dict) -> None:
    assert run["clean"] == {"asked": False, "key": "b", "begun": ["a:-1", "b:-1"]}


def test_row_click_with_edits_asks_first(run: dict) -> None:
    assert run["dirty"] == {"asked": True, "key": "a", "begun": ["a:-1"],
                            "discarded": 0, "committed": 0}


def test_cancel_keeps_edit_input_and_selection(run: dict) -> None:
    assert run["cancel"] == {"open": True, "key": "a", "dirty": True,
                             "begun": ["a:-1"], "picked": ["a"]}


def test_discard_drops_edit_then_opens_other(run: dict) -> None:
    assert run["discard"] == {"open": True, "key": "b", "discarded": 1,
                              "committed": 0, "begun": ["a:-1", "b:-1"]}


def test_save_commits_then_opens_other(run: dict) -> None:
    assert run["save"] == {"open": True, "key": "b", "discarded": 0,
                           "committed": 1, "begun": ["a:-1", "b:-1"]}


def test_action_row_and_add_action_ask_too(run: dict) -> None:
    assert run["action_row"] == {"asked": True, "key": "a", "begun": ["a:-1"]}
    assert run["add_action"] == {"asked": True, "key": "a", "begun": ["a:-1"]}


def test_same_row_again_keeps_editing(run: dict) -> None:
    assert run["same_row"] == {"asked": False, "key": "a", "dirty": True,
                               "begun": ["a:-1"]}


def _smoke() -> None:  # noqa: C901
    import importlib.util

    sys.path.insert(0, str(_ROOT))
    spec = importlib.util.spec_from_file_location(
        "fake_hardware", _ROOT / "test" / "fake_hardware.py"
    )
    assert spec is not None and spec.loader is not None
    fake_hardware = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fake_hardware)
    fake_hardware.install()

    import gremlin.ui.update_model as um

    um.UpdateModel.startup = lambda self, *a, **k: None

    from PySide6 import QtCore, QtQml

    import joystick_gremlin
    from gremlin import clock

    def wait_until(cond, limit_ms: int = 10000) -> bool:  # noqa: ANN001
        end = clock.monotonic() + limit_ms / 1000.0
        qapp = QtCore.QCoreApplication.instance()
        while True:
            if cond():
                return True
            if clock.monotonic() > end:
                return False
            qapp.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 20)
            clock.sleep(0.005)

    def ev(obj: QtCore.QObject, code: str) -> object:
        expr = QtQml.QQmlExpression(QtQml.qmlContext(obj), obj, code)
        value = expr.evaluate()
        if expr.hasError():
            raise RuntimeError(expr.error().toString() + " :: " + code[:200])
        value = value[0] if isinstance(value, tuple) else value
        return value.toVariant() if hasattr(value, "toVariant") else value

    out: dict = {}
    app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
    win = app.main_window
    win.setProperty("visible", True)
    wait_until(lambda: win.isVisible())
    try:
        res = ev(win, """(function() {
            var c = Qt.createComponent("ActionPane.qml")
            if (c.status !== Component.Ready)
                throw new Error(c.errorString())
            var lay = {
                paneModel: null, dirty: false, committed: 0, discarded: 0,
                begun: [],
                paneDirty: function() { return lay.dirty },
                commitPane: function() { lay.committed++; lay.dirty = false; return 0 },
                discardPane: function() { lay.discarded++; lay.dirty = false },
                endPane: function() { lay.dirty = false },
                beginPane: function(k, s) { lay.begun.push(k + ":" + s) },
                beginNewAction: function(k) { lay.begun.push(k + ":new") }
            }
            // ControlTree's row click: select, then open (S126).
            var tree = Qt.createQmlObject(
                "import QtQuick; QtObject { property var picked: []; "
                + "function select(k, shift) { picked = [k] } }",
                _root.contentItem, "stand_in_tree")
            var p = c.createObject(_root.contentItem, { layout: lay, tree: tree })
            var dlg = null
            for (var i = 0; i < p.data.length; ++i) {
                var o = p.data[i]
                if (o && typeof o.saveChosen === "function"
                        && typeof o.ask === "function")
                    dlg = o
            }
            if (!dlg)
                throw new Error("no unsaved-changes dialog in ActionPane")
            function click(k) {
                tree.select(k, false); p.openAt(k, -1, k.toUpperCase())
            }
            function start(edit) {
                dlg.visible = false
                lay.committed = 0; lay.discarded = 0; lay.begun = []
                p.closeNow()
                click("a")
                lay.dirty = edit
            }
            var r = {}

            start(false)
            click("b")
            r.clean = { asked: dlg.visible, key: p.paneKey, begun: lay.begun.slice() }

            start(true)
            click("b")
            r.dirty = { asked: dlg.visible, key: p.paneKey, begun: lay.begun.slice(),
                        discarded: lay.discarded, committed: lay.committed }
            dlg.cancelled()
            r.cancel = { open: p.open, key: p.paneKey, dirty: lay.dirty,
                         begun: lay.begun.slice(), picked: tree.picked.slice() }

            start(true)
            click("b"); dlg.discardChosen()
            r.discard = { open: p.open, key: p.paneKey, discarded: lay.discarded,
                          committed: lay.committed, begun: lay.begun.slice() }

            start(true)
            click("b"); dlg.saveChosen()
            r.save = { open: p.open, key: p.paneKey, discarded: lay.discarded,
                       committed: lay.committed, begun: lay.begun.slice() }

            start(true)
            p.openAt("b", 0, "B action")
            r.action_row = { asked: dlg.visible, key: p.paneKey,
                          begun: lay.begun.slice() }
            dlg.cancelled()

            start(true)
            p.openNew("b", "B")
            r.add_action = { asked: dlg.visible, key: p.paneKey,
                          begun: lay.begun.slice() }
            dlg.cancelled()

            start(true)
            click("a")
            r.same_row = { asked: dlg.visible, key: p.paneKey, dirty: lay.dirty,
                           begun: lay.begun.slice() }
            dlg.visible = false
            return JSON.stringify(r)
        })()""")
        out.update(json.loads(res))
    except Exception as exc:  # noqa: BLE001
        out["error"] = repr(exc)
    print("RESULT " + json.dumps(out), flush=True)
    os._exit(0)


if __name__ == "__main__":
    _smoke()
