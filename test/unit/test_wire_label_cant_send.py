# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
# ruff: noqa: E501 - the QML list rows below read best on one line each

"""A wire whose target can't be sent (D-05-CANT-SEND): the action row's
wire label on the source's page reads "⚠ vJoy N <Control>" in red
(Style.danger), its tooltip the live output.cant_send_text; it replaces the
old grey "(not claimed)". The vJoy Viewer and Module Pair labels are not
part of this.

The label part runs in-process with output.cant_send_text replaced by a
stand-in; the QML part runs off-screen in its own process (this file run as
a script).

Spec: 05 S137 (D-05-CANT-SEND).
"""

from __future__ import annotations

import os
import pathlib
import sys
from types import SimpleNamespace

sys.path.append(".")

import pytest

from gremlin.modules import output, wiring
from gremlin.types import InputType

_HERE = pathlib.Path(__file__).parent
_ROOT = _HERE.parents[1]
TEXT = "vJoy 3's Button 57 is not Found (vJoy 3 has Buttons 1–56)."


@pytest.fixture
def why(monkeypatch: pytest.MonkeyPatch) -> dict:
    """vJoy 3 claims buttons 1-56 (Button 5 named "Fire"); vJoy 4 is off."""
    texts: dict = {(3, 57): TEXT, (4, 1): "vJoy 4 is not Found."}
    claim = {"buttons": list(range(1, 57)), "friendly": {"button:5": "Fire"}}
    monkeypatch.setattr(
        output, "cant_send_text", lambda v, k, i: texts.get((int(v), int(i)))
    )
    monkeypatch.setattr(output, "vjoy_claim", lambda v: claim if v == 3 else {})
    monkeypatch.setattr(
        output, "vjoy_module_name", lambda v: "vJoy 3" if v == 3 else ""
    )
    return texts


def test_a_wire_that_cant_be_sent_names_vjoy_and_control(why: dict) -> None:
    assert wiring.vjoy_dest(3, InputType.JoystickButton, 57) == "⚠ vJoy 3 Button 57"
    assert wiring.vjoy_dest(4, InputType.JoystickButton, 1) == "⚠ vJoy 4 Button 1"
    assert "(not claimed)" not in wiring.vjoy_dest(3, InputType.JoystickButton, 57)


def test_a_sendable_wire_is_unchanged(why: dict) -> None:
    assert (
        wiring.vjoy_dest(3, InputType.JoystickButton, 5) == "vJoy 3 · Button 5 (Fire)"
    )


def test_the_label_follows_the_live_lookup(why: dict) -> None:
    action = SimpleNamespace(
        tag="map-to-vjoy",
        vjoy_device_id=3,
        vjoy_input_type=InputType.JoystickButton,
        vjoy_input_id=57,
    )
    assert wiring.dest_label(action) == "⚠ vJoy 3 Button 57"
    del why[(3, 57)]  # the module now includes it
    assert wiring.dest_label(action) == "vJoy 3 · Button 57"


# -- The row's wire label (off-screen QML) ----------------------------------


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


def test_the_wire_label_is_red_with_the_reason(tmp_path: pathlib.Path) -> None:
    r = _run("tree", tmp_path)
    assert r["bad"] == f"⚠ vJoy 3 Button 57|danger|{TEXT}", r["bad"]
    # A wire that can be sent keeps its colour and has no tooltip.
    assert r["ok"].startswith("vJoy 3 · Button 6|"), r["ok"]
    assert "danger" not in r["ok"] and r["ok"].endswith("|"), r["ok"]


def _tree(s, out: pathlib.Path) -> None:  # noqa: ANN001
    from PySide6 import QtCore

    app, engine, warnings = s._engine(out)  # noqa: F841
    qml = (
        """
import QtQuick
import QtQuick.Window
import Gremlin.Style
Window {
    width: 800; height: 600; visible: true
    ListModel {
        id: _rows
        function keyAt(i) { return get(i).key }
        function setSelection(keys) {}
        property int parentCount: 1
        ListElement { rowKind: "group"; key: "group:"; title: "Ungrouped"; subtitle: ""; parentKey: ""; groupKey: "g"; groupName: ""; systemName: ""; userName: ""; sequenceIndex: -1; childCount: 2; cantSend: "" }
        ListElement { rowKind: "parent"; key: "parent:button:1"; title: "Button 1"; subtitle: ""; parentKey: "parent:button:1"; groupKey: "g"; groupName: ""; systemName: "Button 1"; userName: ""; sequenceIndex: -1; childCount: 2; cantSend: "TEXT" }
        ListElement { rowKind: "child"; key: "child:button:1:0"; title: "Map to vJoy"; subtitle: "⚠ vJoy 3 Button 57"; parentKey: "parent:button:1"; groupKey: "g"; groupName: ""; systemName: "Button 1"; userName: ""; sequenceIndex: 0; childCount: 0; cantSend: "TEXT" }
        ListElement { rowKind: "child"; key: "child:button:1:1"; title: "Map to vJoy"; subtitle: "vJoy 3 · Button 6"; parentKey: "parent:button:1"; groupKey: "g"; groupName: ""; systemName: "Button 1"; userName: ""; sequenceIndex: 1; childCount: 0; cantSend: "" }
    }
    ControlTree {
        id: _tree
        width: 800; height: 500
        layout: _rows
        Component.onCompleted: _tree.opened = { "parent:button:1": true }
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
    function row(key) { return find(_tree, function(i) { return i.rowKind !== undefined && i.key === key && i.shown !== undefined }) }
    function wire(key, text) {
        var r = row(key)
        var l = r ? find(r, function(i) { return i.text === text && i.color !== undefined && i.font !== undefined }) : null
        if (!l || !l.visible) return "missing"
        var tip = ""
        for (var d = 0; d < l.data.length; d++)
            if (l.data[d].objectName === "wireTip") tip = l.data[d].text
        return l.text + "|" + (Qt.colorEqual(l.color, Style.danger) ? "danger" : String(l.color)) + "|" + tip
    }
}
"""
    ).replace("TEXT", TEXT)
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
    s._Out.result("bad", js("wire('child:button:1:0', '⚠ vJoy 3 Button 57')"))
    s._Out.result("ok", js("wire('child:button:1:1', 'vJoy 3 · Button 6')"))
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
