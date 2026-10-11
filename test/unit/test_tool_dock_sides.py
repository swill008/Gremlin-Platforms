# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Button Map's ToolDock after the side panels (07 S99, S128;
D-07-SIDE-PANELS 6a): only the top and bottom tool rows are left, a saved
placement on the old left or right row loads on the bottom row (not
converted), each side panel's width, pin and open state is kept with the
window layout (sideState / setSideState), and Reset Tool Rows puts the side
panels back as they start.

ToolDock is loaded on its own off-screen in a child process with a fresh
user folder; it prints "RESULT {json}".
"""

from __future__ import annotations

import json
import os
import pathlib
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[2]

_CODE = r"""
import json, os, sys
sys.path.insert(0, '.')
import importlib.util
spec = importlib.util.spec_from_file_location('fake_hardware', 'test/fake_hardware.py')
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake_hardware.install()
from PySide6 import QtCore, QtGui, QtQml
import gremlin.util
from gremlin.ui import window_placement

app = QtGui.QGuiApplication([sys.argv[0]])
QtQml.qmlRegisterSingletonType(
    QtCore.QUrl.fromLocalFile(gremlin.util.resource_path("qml/Style.qml")),
    "Gremlin.Style", 1, 0, "Style")
engine = QtQml.QQmlEngine()
engine.addImportPath(gremlin.util.resource_path("theme"))

NAME = "sides-test"
# Saved before the side panels: tools on the old left and right rows.
window_placement.save_tool_row_state(NAME, {
    "order": ["a", "b", "c", "d"],
    "items": {"a": {"side": "left", "pinned": True},
              "b": {"side": "right"},
              "c": {"side": "top"},
              "d": {"side": "bottom"}},
})

QML = b'''
import QtQuick
import Gremlin.Style
ToolDock {
    readonly property real dp260: Style.dp(260)
    readonly property real dp300: Style.dp(300)
    name: "sides-test"
    tools: [{ id: "a", label: "A" }, { id: "b", label: "B" },
            { id: "c", label: "C" }, { id: "d", label: "D" }]
}
'''

def make():
    comp = QtQml.QQmlComponent(engine)
    url = gremlin.util.resource_path("qml/_sides_test.qml")
    comp.setData(QML, QtCore.QUrl.fromLocalFile(url))
    obj = comp.create()
    if obj is None:
        print("RESULT " + json.dumps({"error": comp.errorString()}))
        sys.stdout.flush()
        os._exit(0)
    cpp = QtQml.QQmlEngine.ObjectOwnership.CppOwnership
    QtQml.QQmlEngine.setObjectOwnership(obj, cpp)
    keep.append((comp, obj))
    return obj

keep = []

def ev(obj, code):
    expr = QtQml.QQmlExpression(QtQml.qmlContext(obj), obj, code)
    value = expr.evaluate()
    if expr.hasError():
        return 'error: ' + expr.error().toString()
    value = value[0] if isinstance(value, tuple) else value
    return value.toVariant() if hasattr(value, 'toVariant') else value

def state(obj, tid):
    return ev(obj, 'JSON.stringify(sideState("%s"))' % tid)

out = {}
dock = make()
out["dp260"] = ev(dock, "dp260")
out["dp300"] = ev(dock, "dp300")
out["sides-loaded"] = {t: ev(dock, 'sideOf("%s")' % t) for t in "abcd"}
out["bottom-order"] = ev(dock, 'JSON.stringify(order("bottom"))')
out["chips-default"] = state(dock, "chips")
out["layers-default"] = state(dock, "layers")

ev(dock, 'setSideState("layers", { width: 333, pinned: true, open: true })')
ev(dock, 'setSideState("chips", { open: false })')
out["after-set"] = {"chips": state(dock, "chips"), "layers": state(dock, "layers")}
saved = window_placement.tool_row_state(NAME)
out["saved-sides"] = saved.get("sides")
out["saved-item-sides"] = {t: v.get("side") for t, v in saved.get("items", {}).items()}

# A new window (the next start): read back from the window layout.
again = make()
out["reloaded"] = {"chips": state(again, "chips"), "layers": state(again, "layers")}

ev(again, "resetPlaces()")
out["after-reset"] = {"chips": state(again, "chips"), "layers": state(again, "layers")}
out["saved-after-reset"] = window_placement.tool_row_state(NAME).get("sides")
third = make()
out["reloaded-after-reset"] = {
    "chips": state(third, "chips"), "layers": state(third, "layers")}

print("RESULT " + json.dumps(out))
sys.stdout.flush()
os._exit(0)
"""


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home")
    (home / "Gremlin Platforms").mkdir()
    env = dict(os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen")
    done = proc_tree.run(
        [sys.executable, "-c", _CODE],
        cwd=_ROOT,
        env=env,
        text=True,
        timeout=120,
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, done.stdout[-1500:] + done.stderr[-1500:]
    out = json.loads(lines[0][len("RESULT ") :])
    assert "error" not in out, out["error"]
    return out


# a was on the old left row, b on the right one.
_ROWS = {"a": "bottom", "b": "bottom", "c": "top", "d": "bottom"}


def _defaults(run: dict) -> dict:
    return {
        "chips": {"width": run["dp260"], "pinned": True, "open": True},
        "layers": {"width": run["dp300"], "pinned": False, "open": False},
    }


def _states(pair: dict) -> dict:
    return {k: json.loads(v) for k, v in pair.items()}


def test_a_saved_left_or_right_place_loads_on_the_bottom_row(run: dict) -> None:
    assert run["sides-loaded"] == _ROWS
    assert json.loads(run["bottom-order"]) == ["a", "b", "d"]
    # Saved again as bottom: nothing is converted or kept for the old rows.
    assert run["saved-item-sides"] == _ROWS


def test_side_states_start_with_their_defaults(run: dict) -> None:
    d = _defaults(run)
    assert json.loads(run["chips-default"]) == d["chips"]
    assert json.loads(run["layers-default"]) == d["layers"]


def test_side_state_is_kept_with_the_window_layout(run: dict) -> None:
    want = {
        "chips": {"width": run["dp260"], "pinned": True, "open": False},
        "layers": {"width": 333, "pinned": True, "open": True},
    }
    assert _states(run["after-set"]) == want
    assert run["saved-sides"] == want
    assert _states(run["reloaded"]) == want


def test_reset_tool_rows_resets_the_side_panels(run: dict) -> None:
    d = _defaults(run)
    assert _states(run["after-reset"]) == d
    assert run["saved-after-reset"] == {}
    assert _states(run["reloaded-after-reset"]) == d
