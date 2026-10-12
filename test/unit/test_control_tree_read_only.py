# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
# ruff: noqa: E501 - the QML list rows below read best on one line each

"""The shared list's view-only switches (the Xbox Output View list, 05 S131):
ControlTree.readOnly hides the grips and opens no menu or pane on a click
(a left click only selects, carets still fold); ControlTree.showGroups false
draws no group row and doesn't indent rows for one; ControlFindBar.showUndo
false hides Undo / Redo and showCantSend false hides the "Can't be sent"
tick. The defaults keep the list pages as they are (grip shown, right-click
menu sent, group row drawn).

Runs off-screen in its own process (this file run as a script) on a small
stand-in ListModel, clicking with QTest.
"""

from __future__ import annotations

import os
import pathlib
import sys

sys.path.append(".")

_HERE = pathlib.Path(__file__).parent
_ROOT = _HERE.parents[1]


def _run(tmp_path: pathlib.Path) -> dict[str, str]:
    import proc_tree  # pyright: ignore[reportMissingImports]  (test/)

    result = proc_tree.run(
        [sys.executable, str(pathlib.Path(__file__)), "tree", str(tmp_path)],
        text=True,
        timeout=180,
        cwd=str(_ROOT),
        env={
            **os.environ,
            "QT_QPA_PLATFORM": "offscreen",
            "GREMLIN_OFFLINE": "1",
            "USERPROFILE": str(tmp_path),
        },
        encoding="utf-8",
    )
    lines = result.stdout.splitlines()
    assert "done" in lines, result.stdout[-3000:] + result.stderr[-3000:]
    errors = [line for line in lines if line.startswith("ERROR")]
    assert not errors, errors
    ours = [
        line
        for line in lines
        if line.startswith("WARN")
        and any(name in line for name in ("ControlTree", "ControlFindBar"))
    ]
    assert not ours, ours
    return {
        line.split(" ", 2)[1]: (line.split(" ", 2) + [""])[2]
        for line in lines
        if line.startswith("RESULT ")
    }


def test_read_only_tree_and_bar(tmp_path: pathlib.Path) -> None:
    r = _run(tmp_path)
    # Defaults: grip shown, a right-click sends the input's menu, the group
    # row is drawn and the input is indented under it; Undo and the tick show.
    assert r["defGrip"] == "true", r["defGrip"]
    assert r["defRight"] == "parentMenu", r["defRight"]
    assert r["defGroup"] == "true", r["defGroup"]
    assert r["defIndent"] == "true", r["defIndent"]
    assert r["defUndo"] == "true true", r["defUndo"]
    # readOnly: no grip, no menu on any row, no pane signal; a left click
    # on an input or its line selects the input.
    assert r["roGrip"] == "false", r["roGrip"]
    assert r["roRight"] == "", r["roRight"]
    assert r["roLeft"] == "parent:button:1", r["roLeft"]
    assert r["roChildLeft"] == "parent:button:2", r["roChildLeft"]
    assert r["roSignals"] == "", r["roSignals"]
    # The caret still folds the lines under an input.
    assert r["roCaret"] == "false true", r["roCaret"]
    # showGroups false: no group row, inputs start at the list's edge.
    assert r["roGroup"] == "false", r["roGroup"]
    assert r["roIndent"] == "0", r["roIndent"]
    # showUndo / showCantSend false, with the page's own type choices.
    assert r["roUndo"] == "false false", r["roUndo"]
    assert r["roTypes"] == "All|Sticks|Triggers", r["roTypes"]
    # ownScroll false: no scrollbar, no flicking; listHeight grows with rows.
    assert r["defScroll"] == "true true", r["defScroll"]
    assert r["roScroll"] == "false false", r["roScroll"]
    assert r["roGrows"] == "true", r["roGrows"]


def _tree(s, out: pathlib.Path) -> None:  # noqa: ANN001
    from PySide6 import QtCore, QtTest

    app, engine, warnings = s._engine(out)  # noqa: F841
    rows = """
        function keyAt(i) { return get(i).key }
        property var selected: []
        function setSelection(keys) { selected = keys }
        function setCantSendOnly(on) {}
        property int parentCount: 2
        property bool canUndo: false
        property bool canRedo: false
        property string undoTip: ""
        property string redoTip: ""
        property string lastChange: ""
        property string undone: ""
        ListElement { rowKind: "group"; key: "group:g"; title: "Sticks"; subtitle: ""; parentKey: ""; groupKey: "g"; groupName: "Sticks"; systemName: ""; userName: ""; sequenceIndex: -1; childCount: 2 }
        ListElement { rowKind: "parent"; key: "parent:button:1"; title: "Button 1"; subtitle: ""; parentKey: "parent:button:1"; groupKey: "g"; groupName: "Sticks"; systemName: "Button 1"; userName: ""; sequenceIndex: -1; childCount: 0 }
        ListElement { rowKind: "parent"; key: "parent:button:2"; title: "Button 2"; subtitle: ""; parentKey: "parent:button:2"; groupKey: "g"; groupName: "Sticks"; systemName: "Button 2"; userName: ""; sequenceIndex: -1; childCount: 1 }
        ListElement { rowKind: "child"; key: "child:button:2:0"; title: "Stick · Button 1"; subtitle: ""; parentKey: "parent:button:2"; groupKey: "g"; groupName: "Sticks"; systemName: "Button 2"; userName: ""; sequenceIndex: 0; childCount: 0 }
"""
    signals = """
        onParentMenu: _win.log("parentMenu")
        onGroupMenu: _win.log("groupMenu")
        onActionMenu: _win.log("actionMenu")
        onPageMenu: _win.log("pageMenu")
        onActionClicked: _win.log("actionClicked")
        onParentClicked: _win.log("parentClicked")
        onFeedbackMenu: _win.log("feedbackMenu")
        onFeedbackClicked: _win.log("feedbackClicked")
"""
    qml = (
        """
import QtQuick
import QtQuick.Window
import Gremlin.Style
Window {
    id: _win
    width: 1000; height: 700; visible: true
    property var said: []
    function log(name) { said = said.concat([name]) }
    ListModel { id: _defRows
ROWS
    }
    ListModel { id: _roRows
ROWS
    }
    ControlFindBar { id: _defFind; width: 480; layout: _defRows }
    ControlFindBar {
        id: _roFind
        x: 500; width: 480
        layout: _roRows
        showUndo: false
        showCantSend: false
        typeChoices: [{ label: "All", value: "all" }, { label: "Sticks", value: "stick" }, { label: "Triggers", value: "trigger" }]
    }
    ControlTree {
        id: _defTree
        y: 150; width: 480; height: 500
        layout: _defRows
SIGNALS
    }
    ControlTree {
        id: _roTree
        x: 500; y: 150; width: 480; height: 500
        layout: _roRows
        readOnly: true
        showGroups: false
        ownScroll: false
        Component.onCompleted: _roTree.opened = { "parent:button:2": true }
SIGNALS
    }
    function find(item, test) {
        if (test(item))
            return item
        for (var i = 0; i < item.children.length; i++) {
            var f = find(item.children[i], test)
            if (f) return f
        }
        return null
    }
    function row(tree, key) { return find(tree, function(i) { return i.rowKind !== undefined && i.key === key && i.shown !== undefined }) }
    function named(root, name) { return find(root, function(i) { return i.objectName === name }) }
    function grip(tree, key) { var g = named(row(tree, key), "rowGrip"); return g ? String(g.visible) : "missing" }
    // Window point in the middle of a row's title, as "x y".
    function spot(tree, key) {
        var r = row(tree, key)
        var p = r.mapToItem(null, r.width * 0.6, r.height / 2)
        return Math.round(p.x) + " " + Math.round(p.y)
    }
    function caretSpot(tree, key) {
        var r = row(tree, key)
        var c = find(r, function(i) { return i.text === "▸" || i.text === "▾" })
        var p = c.mapToItem(null, c.width / 2, c.height / 2)
        return Math.round(p.x) + " " + Math.round(p.y)
    }
    function scroll(tree) {
        var b = named(tree, tree.namePrefix + "ScrollBar")
        var l = find(tree, function(i) { return i.contentHeight !== undefined && i.interactive !== undefined })
        return String(!!b && b.visible) + " " + String(l.interactive)
    }
    function undoShown(bar) {
        var u = named(bar, bar.namePrefix + "UndoBar")
        return String(u.visible) + " " + String(named(bar, "cantSendTick").visible)
    }
}
"""
    ).replace("ROWS", rows).replace("SIGNALS", signals)
    engine.loadData(
        qml.encode("utf-8"),
        QtCore.QUrl.fromLocalFile(str(_ROOT / "qml" / "Root.qml")),
    )
    if not engine.rootObjects():
        for warning in warnings:
            print("ERROR load: " + warning, flush=True)
        os._exit(1)
    win = engine.rootObjects()[0]
    s._wait(300)
    js = lambda code: s._js(win, code)  # noqa: E731

    def click(where: str, button: QtCore.Qt.MouseButton) -> None:
        x, y = (int(v) for v in where.split())
        QtTest.QTest.mouseClick(
            win, button, QtCore.Qt.KeyboardModifier.NoModifier, QtCore.QPoint(x, y)
        )
        s._wait(80)

    def said() -> str:
        text = js("_win.said.join(',')")
        js("_win.said = []; 1")
        return text

    left = QtCore.Qt.MouseButton.LeftButton
    right = QtCore.Qt.MouseButton.RightButton

    # Defaults.
    s._Out.result("defGrip", js("grip(_defTree, 'parent:button:1')"))
    click(js("spot(_defTree, 'parent:button:1')"), right)
    s._Out.result("defRight", said())
    s._Out.result("defGroup", js("String(row(_defTree, 'group:g').shown)"))
    s._Out.result(
        "defIndent",
        js("String(row(_defTree, 'parent:button:1').boxX === Style.dp(_defTree.parentIndent))"),
    )
    s._Out.result("defUndo", js("undoShown(_defFind)"))

    # Read only, no groups.
    s._Out.result("roGrip", js("grip(_roTree, 'parent:button:1')"))
    for key in ("parent:button:1", "parent:button:2", "child:button:2:0"):
        click(js(f"spot(_roTree, '{key}')"), right)
    s._Out.result("roRight", said())
    click(js("spot(_roTree, 'parent:button:1')"), left)
    s._Out.result("roLeft", js("_roRows.selected.join(',')"))
    click(js("spot(_roTree, 'child:button:2:0')"), left)
    s._Out.result("roChildLeft", js("_roRows.selected.join(',')"))
    s._Out.result("roSignals", said())
    click(js("caretSpot(_roTree, 'parent:button:2')"), left)
    shut = js("String(!!_roTree.opened['parent:button:2'])")
    click(js("caretSpot(_roTree, 'parent:button:2')"), left)
    s._Out.result("roCaret", shut + " " + js("String(!!_roTree.opened['parent:button:2'])"))
    s._Out.result("roGroup", js("String(row(_roTree, 'group:g').shown)"))
    s._Out.result("roIndent", js("String(row(_roTree, 'parent:button:1').boxX)"))
    s._Out.result("roUndo", js("undoShown(_roFind)"))
    s._Out.result("defScroll", js("scroll(_defTree)"))
    s._Out.result("roScroll", js("scroll(_roTree)"))
    # Folding Button 2's line away shortens the list.
    tall = js("String(_roTree.listHeight)")
    click(js("caretSpot(_roTree, 'parent:button:2')"), left)
    s._wait(100)
    short = js("String(_roTree.listHeight)")
    s._Out.result("roGrows", str(float(tall) > float(short) > 0).lower())
    s._Out.result("roTypes", js("_roFind.typeChoices.map(function(c) { return c.label }).join('|')"))
    s._report(warnings)


if __name__ == "__main__":
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "_audit3_screens", _HERE / "test_audit3_screens.py"
    )
    assert spec is not None and spec.loader is not None
    _s = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_s)
    _s._boot()
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    _part, _out_dir = sys.argv[1], pathlib.Path(sys.argv[2])
    _out_dir.mkdir(parents=True, exist_ok=True)
    try:
        {"tree": _tree}[_part](_s, _out_dir)
    except Exception as failed:  # noqa: BLE001
        import traceback

        traceback.print_exc()
        print(f"ERROR {_part}: {failed!r}", flush=True)
        os._exit(1)
