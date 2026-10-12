# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""05 S125, 01 S58a: the Appearance part shared by the list pages
(qml/PageAppearance.qml, to-do 91, PB1).

- Each page's panel open/closed is remembered under its own pageKey
  (displayPanelOpen(pageKey, "page")); toggling one page leaves another's.
- pageBar holds the Appearance… / Hide Appearance button with the page's
  objectName; clicking it opens and closes the panel.
- requestCloseDisplay asks the panel: with unsaved changes it stays open
  (the unsaved-changes question), with none it closes.

Off-screen, in its own process (this file run as a script).
"""

from __future__ import annotations

import importlib.util
import os
import pathlib
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


def _run(tmp_path: pathlib.Path) -> dict[str, str]:
    import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
    import smoke_report  # pyright: ignore[reportMissingImports]  (test/)
    result = proc_tree.run(
        [sys.executable, str(pathlib.Path(__file__)), str(tmp_path)],
        text=True,
        encoding="utf-8",
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
    assert "done" in lines, smoke_report.explain(result)
    errors = [line for line in lines if line.startswith("ERROR")]
    assert not errors, errors
    ours = [
        line
        for line in lines
        if line.startswith("WARN")
        and any(name in line for name in ("PageAppearance", "ListAppearancePanel"))
    ]
    assert not ours, ours
    return {
        line.split(" ", 2)[1]: line.split(" ", 2)[2]
        for line in lines
        if line.startswith("RESULT ")
    }


def test_page_appearance_toggles_remembers_and_asks(tmp_path: pathlib.Path) -> None:
    r = _run(tmp_path)
    # Read at start, per page: OSC was saved closed, Logical never saved (open).
    assert r["start"] == "true false true false"
    assert r["button"] == "logicalAppearanceButton|Hide Appearance"
    # The button hides Logical's panel and saves it; OSC's is untouched.
    assert r["hidden"] == "false false Appearance…"
    assert r["savedHidden"] == "False False"
    # Toggling OSC opens it and saves only OSC's.
    assert r["oscOpen"] == "true true"
    assert r["savedOscOpen"] == "False True"
    # Unsaved changes: the panel asks, so it stays open.
    assert r["dirtyClose"] == "true"
    # Nothing unsaved: it closes.
    assert r["cleanClose"] == "false"
    assert r["savedClean"] == "False"


def _part(s, out: pathlib.Path) -> None:  # noqa: ANN001
    from PySide6 import QtCore

    from gremlin.ui import window_placement

    app, engine, warnings = s._engine(out)  # noqa: F841
    window_placement.set_display_panel_open("osc", "page", False)
    engine.loadData(
        b"""
import QtQuick
import QtQuick.Layouts
import QtQuick.Window
Window {
    width: 1000; height: 700; visible: true
    RowLayout {
        anchors.fill: parent
        Item { Layout.fillWidth: true; Layout.fillHeight: true }
        PageAppearance {
            id: _logical
            pageKey: "logical"
            buttonName: "logicalAppearanceButton"
            title: "Logical Device - Appearance"
        }
        PageAppearance {
            id: _osc
            pageKey: "osc"
            buttonName: "oscAppearanceButton"
            title: "OSC - Appearance"
        }
    }
    Loader { id: _bar; width: 400; sourceComponent: _logical.pageBar }
    function find(item, test) {
        if (test(item))
            return item
        for (var i = 0; i < item.children.length; i++) {
            var f = find(item.children[i], test)
            if (f) return f
        }
        return null
    }
    function button() {
        var name = "logicalAppearanceButton"
        return find(_bar.item, function(i) { return i.objectName === name })
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
    s._wait(300)
    js = lambda code: s._js(win, code)  # noqa: E731

    def saved() -> str:
        return (
            f"{window_placement.display_panel_open('logical', 'page')} "
            f"{window_placement.display_panel_open('osc', 'page')}"
        )

    s._Out.result(
        "start",
        js(
            "_logical.displayOpen + ' ' + _osc.displayOpen"
            " + ' ' + _logical.visible + ' ' + _osc.visible"
        ),
    )
    s._Out.result("button", js("button().objectName + '|' + button().text"))
    js("button().clicked(); 1")
    s._wait(50)
    s._Out.result(
        "hidden",
        js("_logical.displayOpen + ' ' + _logical.visible + ' ' + button().text"),
    )
    s._Out.result("savedHidden", saved())
    js("_osc.toggleAppearance(); 1")
    s._wait(50)
    s._Out.result("oscOpen", js("_osc.displayOpen + ' ' + _osc.visible"))
    s._Out.result("savedOscOpen", saved())
    js("_osc.parentHeight = _osc.parentHeight + 5; _osc.requestCloseDisplay(); 1")
    s._wait(50)
    s._Out.result("dirtyClose", js("String(_osc.displayOpen)"))
    js("_osc.load(); _osc.requestCloseDisplay(); 1")
    s._wait(50)
    s._Out.result("cleanClose", js("String(_osc.displayOpen)"))
    s._Out.result("savedClean", str(window_placement.display_panel_open("osc", "page")))
    s._report(warnings)


if __name__ == "__main__":
    _s = _screens()
    _s._boot()
    sys.stdout.reconfigure(encoding="utf-8")
    _out_dir = pathlib.Path(sys.argv[1])
    _out_dir.mkdir(parents=True, exist_ok=True)
    try:
        _part(_s, _out_dir)
    except Exception as failed:  # noqa: BLE001
        import traceback

        traceback.print_exc()
        print(f"ERROR part: {failed!r}", flush=True)
        os._exit(1)
