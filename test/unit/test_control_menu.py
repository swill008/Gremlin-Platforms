# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""qml/control_menu.js, the right-click menu the four list pages share
(to-do 91, Method B, PB1/PB2): fed each page's options, standardMenu gives
exactly the menu that page built itself before the change (rows, order,
labels, danger, enabled), except the Device Bindings page's Row section, which
gains Clear Name (PB2). actionMenu gives the action row's Open / Delete.

control_menu_harness.qml is a stand-in page; control_menu_pages.js holds each
page's options. The expected menus (control_menu_expected.json, ten cases per
page) were captured from the pages' own _layoutMenuModel at commit f4ee3994
run on the same stand-in page
(`python test/unit/test_control_menu.py --smoke --capture` prints both);
they matched in every case but PB2's Clear Name. Since then a single row
also gets Find uses… after History (Search, D-01-SEARCH).

QML needs a QGuiApplication, so the checks run in a child process (this file
run as a script) printing "RESULT <json>".
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_HERE = pathlib.Path(__file__).resolve().parent

_FILES = {
    "logical": "qml/LogicalPage.qml",
    "device-bindings": "qml/ConfigurationPage.qml",  # its old menu at f4ee3994
    "keyboard": "qml/KeyboardPage.qml",
    "osc": "qml/OscPage.qml",
}

_ONE = ["dev:button:1"]
_THREE = ["dev:button:1", "dev:button:2", "dev:axis:3"]

# name: property settings on the stand-in page (picked sets both pickers).
_SCENARIOS: dict[str, dict] = {
    "empty": {},
    "empty-locked": {"editorLocked": True},
    "row": {"_menuOnRow": True, "picked": _ONE},
    "row-no-name": {"_menuOnRow": True, "_menuUser": "", "picked": _ONE},
    "row-many": {"_menuOnRow": True, "picked": _THREE},
    "row-no-delete": {"_menuOnRow": True, "canDel": False, "picked": _ONE},
    "row-axis": {
        "_menuOnRow": True,
        "_menuKey": "dev:axis:3",
        "picked": ["dev:axis:3"],
    },
    "row-locked": {"_menuOnRow": True, "editorLocked": True, "picked": _ONE},
    "row-pane-open": {"_menuOnRow": True, "actionOpen": True, "picked": _ONE},
    "group": {"_menuOnGroup": True},
}


def _builders() -> dict[str, str]:
    text = (_HERE / "control_menu_pages.js").read_text(encoding="utf-8")
    return dict(
        re.findall(r"^// == ([\w-]+) ==\n(.*?)(?=^// == |\Z)", text, re.S | re.M)
    )


def _old_body(page: str) -> str:
    text = subprocess.run(
        ["git", "show", "f4ee3994:" + _FILES[page]],
        cwd=_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout
    start = text.index("    function _layoutMenuModel() {\n")
    start = text.index("\n", start) + 1
    return text[start : text.index("\n    }\n", start)]


def _smoke(capture: bool) -> None:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    sys.stdout.reconfigure(encoding="utf-8")
    from PySide6 import QtCore, QtGui, QtQml

    app = QtGui.QGuiApplication(sys.argv[:1])  # noqa: F841
    engine = QtQml.QQmlEngine()
    engine.addImportPath(str(_ROOT / "theme"))
    template = (_HERE / "control_menu_harness.qml").read_text(encoding="utf-8")
    here = QtCore.QUrl.fromLocalFile(str(_ROOT / "qml" / "ControlMenuHarness.qml"))
    out: dict = {}
    for page, builder in _builders().items():
        old = _old_body(page) if capture else "        return null"
        src = template.replace("%NEW%", builder).replace("%OLD%", old)
        comp = QtQml.QQmlComponent(engine)
        comp.setData(src.encode("utf-8"), here)
        obj = comp.create()
        if obj is None:
            out[page] = {"error": [e.toString() for e in comp.errors()]}
            continue

        def ev(code: str, obj: QtCore.QObject = obj) -> object:
            expr = QtQml.QQmlExpression(QtQml.qmlContext(obj), obj, code)
            value = expr.evaluate()
            if expr.hasError():
                return json.dumps({"error": expr.error().toString()})
            return value[0] if isinstance(value, tuple) else value

        res: dict = {}
        for name, props in _SCENARIOS.items():
            ev("reset()")
            for prop, value in props.items():
                if prop == "picked":
                    ev(f"setPicked({json.dumps(value)})")
                elif prop == "canDel":
                    ev(f"_layout.canDel = {json.dumps(value)}")
                else:
                    obj.setProperty(prop, value)
            entry = {"new": json.loads(ev("dump(newMenu())"))}
            if capture:
                entry["old"] = json.loads(ev("dump(oldMenu())"))
            res[name] = entry
        res["runs"] = json.loads(ev("runRows()"))
        res["action"] = json.loads(ev(f"actionDump({json.dumps(page)})"))
        out[page] = res
    print("RESULT " + json.dumps(out), flush=True)


def _run(tmp_path: pathlib.Path) -> dict:
    import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
    import smoke_report  # pyright: ignore[reportMissingImports]  (test/)
    result = proc_tree.run(
        [sys.executable, str(pathlib.Path(__file__).resolve()), "--smoke"],
        cwd=str(_ROOT),
        text=True,
        encoding="utf-8",
        timeout=120,
        env={
            **os.environ,
            "QT_QPA_PLATFORM": "offscreen",
            "PYTHONIOENCODING": "utf-8",
            "USERPROFILE": str(tmp_path),
        },
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, smoke_report.explain(result)
    return json.loads(lines[-1][len("RESULT ") :])


def test_standard_menu_matches_each_page(tmp_path: pathlib.Path) -> None:
    out = _run(tmp_path)
    path = _HERE / "control_menu_expected.json"
    expected = json.loads(path.read_text(encoding="utf-8"))
    for page in _FILES:
        assert "error" not in out[page], out[page]
        for name in _SCENARIOS:
            assert out[page][name]["new"] == expected[page][name], (page, name)


def test_device_bindings_gains_clear_name(tmp_path: pathlib.Path) -> None:
    # PB2: the only change from today; the rest of its Row section is as before.
    menus = _run(tmp_path)["device-bindings"]
    row = menus["row"]["new"]["sections"][0]
    assert row == [
        "row|Row",
        "action|Clear Name|on",
        "action|Delete actions…|on|danger",
    ]
    many = menus["row-many"]["new"]["sections"][0]
    assert many == ["row|Row", "action|Clear Name|on"]
    unnamed = menus["row-no-name"]["new"]["sections"][0]
    assert unnamed[1] == "action|Clear Name|off"


def test_rows_run_the_page_handlers(tmp_path: pathlib.Path) -> None:
    out = _run(tmp_path)
    for page in _FILES:
        runs = out[page]["runs"]
        assert runs["displayOpen"] is True, page
        calls = runs["calls"]
        for call in ("deleteGroup Weapons", "up Weapons", "sortName", "undo"):
            assert call in calls, (page, calls)
        assert "groupAs Guns" in calls, (page, calls)
        if page == "keyboard":
            assert runs["groupDialog"] is True
            assert "setUserName dev:button:1=" in calls
        else:
            assert "renameGroup" in calls
            assert "clearName dev:button:1 Button 1 Fire" in calls
        assert out[page]["action"] == {
            "menu": {
                "kind": page + "-action",
                "title": "Remap",
                "header": [],
                "quick": ["action|Open|on", "action|Delete|on|danger"],
                "sections": [],
            },
            "calls": ["open", "remove"],
        }


if __name__ == "__main__":
    if "--smoke" in sys.argv:
        _smoke("--capture" in sys.argv)
