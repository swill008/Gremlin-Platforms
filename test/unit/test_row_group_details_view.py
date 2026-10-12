# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
# ruff: noqa: E501 - the QML below reads best on one line per function

"""Group details and Row details in ControlTree (batch L contract, 05).

The group line under a group's name is built from the group roles
(groupCounts, groupNoBindings, ...) in a fixed order with " · " between the
details; each detail has its own switch, "Hide empty" leaves out the 0
details (the type itself stays), "Wrap details" wraps the line or cuts it
with "…" and lists every detail on hover. Bindable rows add their details
after the bindings strip. Every detail uses the Bindings number style;
Binding output not found uses the theme warning colour.

The QML runs off-screen in its own process (this file run as a script) on
a stub model carrying the roles.

Spec: 05 Group details, Row details (batch L contract).
"""

from __future__ import annotations

import os
import pathlib
import sys
from typing import Any

sys.path.append(".")

_HERE = pathlib.Path(__file__).parent
_ROOT = _HERE.parents[1]

ALL_ON = (
    "29 buttons [30 bindings] · 6 axes [6 bindings] · 1 hat [0 bindings]"
    " · [1 with no bindings] · [1 binding output not found]"
    " · [outputs: vJoy 1, Xbox 360 1] · [30 Map to vJoy, 2 Macro]"
    " · [5 custom names] · [also in mode Combat]"
)


def _run(part: str, tmp_path: pathlib.Path) -> dict[str, str]:
    import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
    import smoke_report  # pyright: ignore[reportMissingImports]  (test/)

    result = proc_tree.run(
        [sys.executable, str(pathlib.Path(__file__)), part, str(tmp_path)],
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
    assert "done" in lines, smoke_report.explain(result)
    errors = [line for line in lines if line.startswith("ERROR")]
    assert not errors, errors
    ours = [line for line in lines if line.startswith("WARN") and "ControlTree" in line]
    assert not ours, ours
    return {
        line.split(" ", 2)[1]: (line.split(" ", 2) + [""])[2]
        for line in lines
        if line.startswith("RESULT ")
    }


def test_group_and_row_details(tmp_path: pathlib.Path) -> None:
    r = _run("tree", tmp_path)
    # Defaults: controls and bindings by type, nothing else; no row details.
    assert r["groupDefault"] == (
        "29 buttons [30 bindings] · 6 axes [6 bindings] · 1 hat [0 bindings]"
    ), r["groupDefault"]
    assert r["rowDefault"] == "false", r["rowDefault"]
    # Everything on: the contract's order and wording, number style.
    assert r["groupAll"] == ALL_ON, r["groupAll"]
    assert r["groupStyle"] == "mono|number|warn", r["groupStyle"]
    # Singular and plural.
    assert r["groupOther"] == (
        "1 button [1 binding] · [2 with no bindings] · [2 binding outputs not found]"
        " · [1 custom name] · [also in modes Combat, Landing]"
    ), r["groupOther"]
    # Hide empty: "[0 bindings]" goes, "1 hat" stays; 0 counts go.
    assert r["groupHide"] == (
        "29 buttons [30 bindings] · 6 axes [6 bindings] · 1 hat"
        " · [1 with no bindings] · [1 binding output not found]"
        " · [outputs: vJoy 1, Xbox 360 1] · [30 Map to vJoy, 2 Macro]"
        " · [5 custom names] · [also in mode Combat]"
    ), r["groupHide"]
    assert r["groupHideZero"] == "4 buttons", r["groupHideZero"]
    # Brackets off: the bare details.
    assert r["groupBare"] == (
        "29 buttons 30 bindings · 6 axes 6 bindings · 1 hat 0 bindings"
    ), r["groupBare"]
    # Every switch off: no group line (and not the old plain line).
    assert r["groupOff"] == "false", r["groupOff"]
    # Wrap off: one line ending "…", every detail on hover.
    assert r["wrapOff"] == "1|…", r["wrapOff"]
    assert r["wrapTip"] == ALL_ON.replace(" · ", "\\n"), r["wrapTip"]
    # Wrap on: more than one line, no "…".
    assert r["wrapOn"].split("|")[1] == "none", r["wrapOn"]
    assert int(r["wrapOn"].split("|")[0]) > 1, r["wrapOn"]
    # Row details after the bindings strip, in order, custom name only.
    assert r["rowAll"] == (
        "[Map to vJoy, Map to Xbox] · [binding output not found] · [also in mode Combat]"
        " · [system name: Button 5] · [has a condition]"
    ), r["rowAll"]
    assert r["rowAfterStrip"] == "after", r["rowAfterStrip"]
    assert r["rowWarn"] == "warn", r["rowWarn"]
    assert r["rowPlain"] == "[also in modes Combat, Landing]", r["rowPlain"]
    assert r["rowNone"] == "[no bindings]", r["rowNone"]
    # The bindings column still lines up with details on.
    assert r["column"] == "same", r["column"]
    # Row wrap on: a long row wraps.
    assert int(r["rowWrap"]) > 1, r["rowWrap"]


_QML = """
import QtQuick
import QtQuick.Window
import Gremlin.Style
Window {
    width: 700; height: 600; visible: true
    ControlTree {
        id: _tree
        width: 700; height: 560
        layout: rowsModel
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
    function all(item, test, out) {
        if (test(item)) out.push(item)
        for (var i = 0; i < item.children.length; i++) all(item.children[i], test, out)
        return out
    }
    function row(key) { return find(_tree, function(i) { return i.rowKind !== undefined && i.key === key && i.shown !== undefined }) }
    function part(key, name) {
        var r = row(key)
        return r ? find(r, function(i) { return i.objectName === name }) : null
    }
    function pieces(key, name) {
        var r = row(key)
        return all(r, function(i) { return i.objectName === name && i.visible }, [])
    }
    function line(key, holder, name) {
        var h = part(key, holder)
        if (!h || !h.visible || h.height <= 0) return "false"
        return pieces(key, name).map(function(p) { return p.text }).join(" · ")
    }
    function group(key) { return line(key, "groupDetails", "groupDetail") }
    function rowLine(key) { return line(key, "rowDetails", "rowDetail") }
    function lines(key, holder, name) {
        var ys = {}
        pieces(key, name).forEach(function(p) { ys[Math.round(p.mapToItem(null, 0, 0).y)] = 1 })
        return Object.keys(ys).length
    }
    function wrap(key) {
        var h = part(key, "groupDetails")
        var dots = part(key, "groupDetailsMore")
        return lines(key, "groupDetails", "groupDetail") + "|" + (dots && dots.visible ? dots.text : "none")
    }
    function style(key) {
        var ps = pieces(key, "groupDetail")
        var first = ps[0]
        var lost = ps.filter(function(p) { return p.text.indexOf("not found") >= 0 })[0]
        return (first.font.family === Style.monoFont ? "mono" : first.font.family)
            + "|" + (Qt.colorEqual(first.color, _tree.bindingsNumberColor) ? "number" : String(first.color))
            + "|" + (Qt.colorEqual(lost.color, Style.warn) ? "warn" : String(lost.color))
    }
    function rowWarn(key) {
        var lost = pieces(key, "rowDetail").filter(function(p) { return p.text.indexOf("not found") >= 0 })[0]
        return lost && Qt.colorEqual(lost.color, Style.warn) ? "warn" : "plain"
    }
    function afterStrip(key) {
        var s = part(key, "bindingsStrip")
        var d = part(key, "rowDetails")
        var dx = d.mapToItem(null, 0, 0).x, sx = s.mapToItem(null, 0, 0).x
        return dx >= sx + s.width - 1 && s.width > 0 ? "after" : "before " + dx + "," + sx + "," + s.width + "," + d.width
    }
    function stripX(key) { var s = part(key, "bindingsWord"); return s ? Math.round(s.mapToItem(null, 0, 0).x) : -1 }
    function column() {
        var a = stripX("parent:button:5"), b = stripX("parent:button:2")
        return Math.abs(a - b) <= 1 ? "same" : a + "," + b
    }
}
"""

# Every role the tree reads; the stub model carries them all.
_EXTRA = {
    "customName": False,
    "actionTypes": [],
    "outputNotFound": False,
    "otherModes": [],
    "hasCondition": False,
    "groupCounts": [],
    "groupNoBindings": 0,
    "groupOutputNotFound": 0,
    "groupOutputDevices": [],
    "groupActionTypes": [],
    "groupCustomNames": 0,
    "groupOtherModes": [],
}


def _rows_model(rows: list[dict]) -> Any:  # noqa: ANN401
    from PySide6 import QtCore

    from gremlin.ui.control_layout import ROW_DEFAULTS

    defaults = {**ROW_DEFAULTS, **_EXTRA}
    names = list(defaults)
    full = [{**defaults, **row} for row in rows]

    class Model(QtCore.QAbstractListModel):
        changed = QtCore.Signal()

        def rowCount(self, parent: Any = None) -> int:  # noqa: ANN401
            return len(full)

        def roleNames(self) -> dict:
            base = QtCore.Qt.ItemDataRole.UserRole + 1
            return {
                base + i: QtCore.QByteArray(n.encode()) for i, n in enumerate(names)
            }

        def data(self, index: Any, role: int = 0) -> Any:  # noqa: ANN401
            i = role - QtCore.Qt.ItemDataRole.UserRole - 1
            if not (0 <= i < len(names)):
                return None
            return full[index.row()][names[i]]

        @QtCore.Slot(int, result=str)
        def keyAt(self, i: int) -> str:
            return full[i]["key"]

        @QtCore.Slot(list)
        def setSelection(self, keys: list) -> None:
            pass

        def _titles(self) -> list:
            return [r["title"] for r in full if r["rowKind"] == "parent"]

        parentTitles = QtCore.Property(list, _titles, notify=changed)

    return Model()


def _parent(n: int, title: str, group: str, targets: list[str], **more: Any) -> dict:  # noqa: ANN401
    key = f"parent:button:{n}"
    return {
        "rowKind": "parent",
        "key": key,
        "title": title,
        "parentKey": key,
        "groupKey": group,
        "systemName": f"Button {n}",
        "childCount": 0,
        "bindingCount": len(targets),
        "bindingTargets": targets,
        **more,
    }


def _rows() -> list[dict]:
    two = ["vJoy 1 · Button 1", "Xbox 360 Controller · A"]
    return [
        {
            "rowKind": "group",
            "key": "group:a",
            "title": "Stick",
            "groupKey": "a",
            "subtitle": "29 buttons · 6 axes · 1 hat",
            "childCount": 3,
            "groupCounts": [
                {"type": "button", "controls": 29, "bindings": 30},
                {"type": "axis", "controls": 6, "bindings": 6},
                {"type": "hat", "controls": 1, "bindings": 0},
            ],
            "groupNoBindings": 1,
            "groupOutputNotFound": 1,
            "groupOutputDevices": ["vJoy 1", "Xbox 360 1"],
            "groupActionTypes": [
                {"name": "Map to vJoy", "count": 30},
                {"name": "Macro", "count": 2},
            ],
            "groupCustomNames": 5,
            "groupOtherModes": ["Combat"],
        },
        _parent(
            5,
            "Trigger",
            "a",
            two,
            userName="Trigger",
            customName=True,
            actionTypes=["Map to vJoy", "Map to Xbox"],
            outputNotFound=True,
            otherModes=["Combat"],
            hasCondition=True,
        ),
        _parent(2, "Button 2", "a", two, otherModes=["Combat", "Landing"]),
        _parent(3, "Button 3", "a", []),
        {
            "rowKind": "group",
            "key": "group:b",
            "title": "Other",
            "groupKey": "b",
            "childCount": 0,
            "groupCounts": [{"type": "button", "controls": 1, "bindings": 1}],
            "groupNoBindings": 2,
            "groupOutputNotFound": 2,
            "groupCustomNames": 1,
            "groupOtherModes": ["Combat", "Landing"],
        },
        {
            "rowKind": "group",
            "key": "group:c",
            "title": "Empty",
            "groupKey": "c",
            "childCount": 0,
            "groupCounts": [{"type": "button", "controls": 4, "bindings": 0}],
        },
    ]


_GROUP_ON = [
    "groupNoBindings",
    "groupOutputNotFound",
    "groupOutputDevices",
    "groupActionTypes",
    "groupCustomNames",
    "groupOtherModes",
]
_ROW_ON = [
    "rowActionTypes",
    "rowOutputNotFound",
    "rowOtherModes",
    "rowSystemName",
    "rowHasCondition",
    "rowNoBindings",
]


def _tree(s, out: pathlib.Path) -> None:  # noqa: ANN001
    from PySide6 import QtCore

    app, engine, warnings = s._engine(out)  # noqa: F841
    model = _rows_model(_rows())
    engine.rootContext().setContextProperty("rowsModel", model)
    engine.loadData(
        _QML.encode("utf-8"),
        QtCore.QUrl.fromLocalFile(str(_ROOT / "qml" / "Root.qml")),
    )
    if not engine.rootObjects():
        for warning in warnings:
            print("ERROR load: " + warning, flush=True)
        os._exit(1)
    win = engine.rootObjects()[0]
    s._wait(300)
    js = lambda code: s._js(win, code)  # noqa: E731
    put = s._Out.result

    def sets(names: list[str], value: bool) -> None:
        js("; ".join(f"_tree.{n} = {str(value).lower()}" for n in names) + "; 1")
        s._wait(80)

    put("groupDefault", js("group('group:a')"))
    put("rowDefault", js("rowLine('parent:button:5')"))
    sets(_GROUP_ON, True)
    put("groupAll", js("group('group:a')"))
    put("groupStyle", js("style('group:a')"))
    put("groupOther", js("group('group:b')"))
    put("wrapOff", js("wrap('group:a')"))
    put(
        "wrapTip",
        str(js("part('group:a', 'groupDetailsTip').text")).replace("\n", "\\n"),
    )
    js("_tree.groupWrapDetails = true; 1")
    s._wait(150)
    put("wrapOn", js("wrap('group:a')"))
    js("_tree.groupWrapDetails = false; _tree.groupHideEmpty = true; 1")
    s._wait(80)
    put("groupHide", js("group('group:a')"))
    put("groupHideZero", js("group('group:c')"))
    sets(_GROUP_ON + ["groupHideEmpty"], False)
    js("_tree.bindingsBrackets = false; 1")
    s._wait(80)
    put("groupBare", js("group('group:a')"))
    js("_tree.bindingsBrackets = true; 1")
    sets(["groupControlsByType", "groupBindingsByType"], False)
    put("groupOff", js("group('group:a')"))
    sets(_ROW_ON, True)
    put("rowAll", js("rowLine('parent:button:5')"))
    put("rowAfterStrip", js("afterStrip('parent:button:5')"))
    put("rowWarn", js("rowWarn('parent:button:5')"))
    put("rowPlain", js("rowLine('parent:button:2')"))
    put("rowNone", js("rowLine('parent:button:3')"))
    put("column", js("column()"))
    js("_tree.rowWrapDetails = true; 1")
    s._wait(150)
    put("rowWrap", js("lines('parent:button:5', 'rowDetails', 'rowDetail')"))
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
