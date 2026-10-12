# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Starts the program off-screen (stand-in hardware), opens the Device Mapping Editor
for a stick in Edit with the Layers tool open, and checks the Layers panel
with the background and foreground planes (07 S119, S120, S102, S44;
D-07-BACKGROUND-PLANES, D-07-PLANES-ANSWERS P2a, P4a). Prints what shows
after each step as JSON. test_planes_layers_panel.py runs it in its own
process with a fresh user folder.

    python test/unit/planes_layers_panel_smoke.py

Two parts: the real editor (its rows end with the folded Background row in
Foreground mode, the eye and plane switch reach the editor's properties),
then a stand-in editor that records what the panel asks of it (the lock,
the slider, a drop under the last row).
"""

from __future__ import annotations

import importlib.util
import json
import sys
from collections.abc import Callable
from pathlib import Path

from smoke_exit import smoke_exit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location(
    "fake_hardware", ROOT / "test" / "fake_hardware.py"
)
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake = fake_hardware.install()

import gremlin.ui.update_model as um  # noqa: E402

um.UpdateModel.startup = lambda self, *a, **k: None

from PySide6 import QtCore, QtQml, QtTest  # noqa: E402

import dill  # noqa: E402
import joystick_gremlin  # noqa: E402

NO_MOD = QtCore.Qt.KeyboardModifier.NoModifier

# Qt log lines, e.g. "qt.qml.binding.removal" from a Binding the slider
# moves away from while dragged.
qt_messages: list[str] = []


def _capture(mode, context, text: str) -> None:  # noqa: ANN001
    qt_messages.append(f"{context.category}: {text}")


QtCore.qInstallMessageHandler(_capture)
GUID = str(dill.GUID(fake.devices[0].device_guid).uuid)

# Layers is the right side panel (07 S128): the SidePanel holding _layersPanel.
LAYERS_SIDE = ("(function(){ var p = _layersPanel;"
               " while (p && p.takenWidth === undefined) p = p.parent; return p })()")

# A stand-in editor with two planes, rows as rig_layers.layerRows gives
# them (top of the plane first; Foreground mode ends with the Background
# row). It records what the panel asks of it.
_FAKE_ED = """
import QtQuick
QtObject {
    property int tick: 0
    property string editPlane: "foreground"
    property bool bgViewHidden: false
    property real bgViewOpacity: 1.0
    property bool bgLocked: false
    property var calls: []
    property var lastState: null
    // nodes: index 0-1 background (bottom first), 2-4 foreground.
    readonly property var fg: [
        { id: "c1", type: "chip", name: "Fire", index: 4 },
        { id: "s2", type: "shape", name: "Box", index: 3 },
        { id: "t2", type: "text", name: "Label", index: 2 }
    ]
    readonly property var bg: [
        { id: "p1", type: "picture", name: "Stick photo", index: 1 },
        { id: "s1", type: "shape", name: "Panel", index: 0 }
    ]
    function _log(s) { calls = calls.concat([s]) }
    function layerRows(st, expanded) {
        lastState = (typeof st === "string") ? st : JSON.parse(JSON.stringify(st))
        var ks = (st && st.kinds) || []
        var src = editPlane === "background" ? bg : fg
        var out = []
        for (var i = 0; i < src.length; i++) {
            var r = src[i]
            if (ks.length && ks.indexOf(r.type) < 0)
                continue
            out.push({ id: r.id, part: "", depth: 0, type: r.type, name: r.name,
                       hidden: false, locked: false, hiddenFrom: false,
                       lockedFrom: false, selected: false, canOpen: false,
                       open: false, index: r.index, renamable: r.type !== "chip",
                       match: true, heading: false })
        }
        if (editPlane !== "background")
            out.push({ id: "", part: "background", depth: 0, type: "background",
                       name: "Background", hidden: bgViewHidden, locked: bgLocked,
                       hiddenFrom: false, lockedFrom: false, selected: false,
                       canOpen: false, open: false, index: -1, renamable: false,
                       match: true, heading: false })
        return out
    }
    function layerCounts(st) { return { matches: 1, total: 5 } }
    function planeRange(plane) {
        return plane === "background" ? { first: 0, last: 1 } : { first: 2, last: 4 }
    }
    function setPlaneLocked(plane, on) {
        _log("setPlaneLocked " + plane + " " + on)
        if (plane === "background") bgLocked = !!on
        tick++
    }
    function moveNodeTo(id, index) { _log("moveNodeTo " + id + " " + index); tick++ }
    function canDeleteLayer(id, part) { return part === "" }
    function deleteLayer(id, part) { _log("deleteLayer " + id + " " + part) }
    function toggleLayerFlag(id, part, which) {
        _log("flag " + id + " " + which); tick++
    }
    function setSelection(ids) { _log("select " + ids.join(",")) }
    function toggleSelected(id) { _log("toggle " + id) }
    function beginRename(id, m) { _log("rename " + id) }
    function bump() { tick++ }
    function focusMap() {}
    function showAll() {}
    function unlockAll() {}
}
"""


def call(obj: QtCore.QObject, name: str, *args: object) -> object:
    return QtCore.QMetaObject.invokeMethod(
        obj, name, QtCore.Q_RETURN_ARG("QVariant"),
        *[QtCore.Q_ARG("QVariant", a) for a in args],
    )


def wait_until(cond: Callable[[], object], ms: int = 5000) -> bool:
    """Bounded wait: polls cond while events run, up to ms."""
    timer = QtCore.QElapsedTimer()
    timer.start()
    while timer.elapsed() < ms:
        if cond():
            return True
        QtTest.QTest.qWait(20)
    return bool(cond())


def main() -> None:
    app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
    root = app.engine.rootObjects()[0]
    card = {"rawName": "pJoy Pro", "name": "pJoy Pro", "guid": GUID}
    call(root, "openDeviceMappingEditorForCard", card)
    assert wait_until(lambda: call(root, "deviceMappingEditorWindow") is not None)
    win = call(root, "deviceMappingEditorWindow")
    win.setProperty("width", 1400)
    win.setProperty("height", 900)
    out: dict = {"warnings": []}
    app.engine.warnings.connect(
        lambda errs: out["warnings"].extend(
            e.toString() for e in errs if "RigLayersPanel" in e.toString()
        )
    )

    def ev(code: str) -> object:
        expr = QtQml.QQmlExpression(QtQml.qmlContext(win), win, code)
        value = expr.evaluate()
        if expr.hasError():
            return "error: " + expr.error().toString()
        value = value[0] if isinstance(value, tuple) else value
        return value.toVariant() if hasattr(value, "toVariant") else value

    def js(code: str) -> object:
        raw = ev("JSON.stringify(" + code + ")")
        if isinstance(raw, str) and not raw.startswith("error"):
            return json.loads(raw)
        return raw

    def rect(code: str) -> dict:
        return js(f"(function(){{ var i = {code}; var p = i.mapToItem(null, 0, 0);"
                  " return {x: p.x, y: p.y, w: i.width, h: i.height} })()")

    def at(r: dict, fx: float = 0.5) -> QtCore.QPoint:
        return QtCore.QPoint(round(r["x"] + r["w"] * fx), round(r["y"] + r["h"] / 2))

    def click(r: dict, fx: float = 0.5) -> None:
        QtTest.QTest.mouseClick(
            win, QtCore.Qt.MouseButton.LeftButton, NO_MOD, at(r, fx))
        QtCore.QCoreApplication.processEvents()

    def settle() -> None:
        # Events run briefly: the kind toggles re-flow after a mode switch.
        QtTest.QTest.qWait(40)
        ev("_layersPanel.forceLayout()")

    def kinds_shown() -> object:
        return js("_layersPanel.kindToggles.map(function(t) { return t.label })")

    def bg_row() -> object:
        return js("(function(){ var r = _layersPanel.rows;"
                  " var x = r.filter(function(q) { return q.part === 'background' });"
                  " return x.length ? {name: x[0].name,"
                  " last: r.indexOf(x[0]) === r.length - 1}"
                  " : null })()")

    call(win, "enterEdit")
    assert wait_until(lambda: ev("editing") is True)
    ev(LAYERS_SIDE + ".unfold()")
    assert wait_until(lambda: ev("_layersPanel.visible") is True)
    # The drawer slides open (120 ms); clicks land once it is still.
    assert wait_until(lambda: ev(LAYERS_SIDE + "._reveal") == 1)
    settle()

    # --- the real editor ----------------------------------------------------
    out["real-has-planes"] = js("typeof _layersPanel.ed.planeRange === 'function'"
                                " && _layersPanel.ed.editPlane !== undefined")
    out["real-fg-plane"] = js("_layersPanel.ed.editPlane")
    out["real-fg-bgrow"] = bg_row()
    out["real-fg-bgrow-item"] = js("!!_layersPanel.bgRowPart('dmeBgRow')")
    out["real-fg-parts"] = js("['dmeBgRowEye', 'dmeBgRowLock', 'dmeBgRowOpacity']"
                              ".map(function(n) {"
                              " return !!_layersPanel.bgRowPart(n) })")
    out["real-fg-kinds"] = kinds_shown()
    out["real-photo-rows"] = js("_layersPanel.rows.filter(function(r) {"
                                " return r.part === 'photo' }).length")
    if out["real-fg-bgrow-item"] is True:
        hidden0 = js("_layersPanel.ed.bgViewHidden")
        click(rect("_layersPanel.bgRowPart('dmeBgRowEye')"))
        settle()
        out["real-eye"] = [hidden0, js("_layersPanel.ed.bgViewHidden")]
        click(rect("_layersPanel.bgRowPart('dmeBgRowEye')"))
        settle()
        out["real-eye-back"] = js("_layersPanel.ed.bgViewHidden")
        ev("_layersPanel.ed.bgViewOpacity = 0.4")
        settle()
        out["real-slider-follows"] = js(
            "_layersPanel.bgRowPart('dmeBgRowOpacity').value")
        ev("_layersPanel.ed.bgViewOpacity = 1")
        r = rect("_layersPanel.bgRowPart('dmeBgRow')")
        r["h"] = js("_layersPanel.rowH")
        QtTest.QTest.mouseDClick(win, QtCore.Qt.MouseButton.LeftButton, NO_MOD,
                                 at(r, 0.4))
        settle()
        out["real-dblclick-plane"] = js("_layersPanel.ed.editPlane")
    ev("_layersPanel.ed.editPlane = 'background'")
    settle()
    out["real-bg-bgrow"] = bg_row()
    out["real-bg-kinds"] = kinds_shown()
    out["real-bg-groups"] = js("_layersPanel.rows.filter(function(r) {"
                               " return r.type === 'group'"
                               " || r.type === 'chip' }).length")
    ev("_layersPanel.ed.editPlane = 'foreground'")
    settle()

    # A row's right-click menu: Move to Background, clicked (07 S121).
    ev("_layersPanel.ed.addDrawFree('rect', 120, 120, 320, 260)")
    settle()
    sid = js("_layersPanel.ed.selectedIds[0]")
    out["real-menu-has-items"] = js(
        "typeof _layersPanel.ed.planeMoveItems === 'function'")

    def row_of(node_id: str) -> int:
        return js("_layersPanel.rows.findIndex(function(r) {"
                  f" return r.id === '{node_id}' && r.part === '' }})")

    def right_click(i: int) -> None:
        rr = js(f"_layersPanel.rowRect({i})")
        QtTest.QTest.mouseClick(win, QtCore.Qt.MouseButton.RightButton, NO_MOD,
                                at(rr, 0.4))
        wait_until(lambda: js("_layersPanel.rowMenuOpen") is True, 2000)
        wait_until(lambda: False, 150)
        settle()

    right_click(row_of(sid))
    out["real-menu"] = js("_layersPanel.rowMenuLines()")
    wait_until(lambda: False, 150)  # the menu lays its rows out first
    mr = js("_layersPanel.rowMenuRect('Move to Background')")
    if isinstance(mr, dict):
        click(mr)
        wait_until(lambda: js("_layersPanel.rowMenuOpen") is False, 2000)
        settle()
    out["real-moved"] = js("[_layersPanel.ed.isBackground("
                           f"_layersPanel.ed.nodeAt('{sid}')),"
                           " _layersPanel.ed.editPlane]")
    out["real-moved-row"] = row_of(sid)
    # The Background row's menu has no Move items.
    right_click(js("_layersPanel.rows.length - 1"))
    out["real-bg-menu"] = js("_layersPanel.rowMenuLines()")
    QtTest.QTest.keyClick(win, QtCore.Qt.Key.Key_Escape)
    settle()

    # --- the stand-in editor -------------------------------------------------
    ev("_layersPanel.ed = Qt.createQmlObject(" + json.dumps(_FAKE_ED)
       + ", _layersPanel, 'fakeEd')")
    settle()
    out["fg-rows"] = js("_layersPanel.describe()")
    out["fg-kinds"] = kinds_shown()
    out["fg-trash-shown"] = js(
        "(function(){ var r = _layersPanel.bgRowPart('dmeBgRow');"
        " return r ? r.height : -1 })()"
    )
    out["rowH"] = js("_layersPanel.rowH")
    # Eye: the view setting, no Undo step (no editor call).
    click(rect("_layersPanel.bgRowPart('dmeBgRowEye')"))
    settle()
    out["eye"] = js("[_layersPanel.ed.bgViewHidden, _layersPanel.ed.calls,"
                    " _layersPanel.describe()[3]]")
    click(rect("_layersPanel.bgRowPart('dmeBgRowEye')"))
    settle()
    out["eye-back"] = js("_layersPanel.ed.bgViewHidden")
    # Lock: every background layer, through the editor.
    click(rect("_layersPanel.bgRowPart('dmeBgRowLock')"))
    settle()
    click(rect("_layersPanel.bgRowPart('dmeBgRowLock')"))
    settle()
    out["lock"] = js("_layersPanel.ed.calls")
    out["lock-lit"] = js("_layersPanel.bgRowPart('dmeBgRowLock').on")
    # Slider: a click near its left end sets a low opacity.
    ev("_layersPanel.ed.calls = []")
    click(rect("_layersPanel.bgRowPart('dmeBgRowOpacity')"), 0.2)
    settle()
    out["slider-low"] = js("_layersPanel.ed.bgViewOpacity")
    out["slider-calls"] = js("_layersPanel.ed.calls")
    # Drag the handle across the slider in steps: each step sets the
    # editor's opacity; no Qt "binding removal" line.
    del qt_messages[:]
    r = rect("_layersPanel.bgRowPart('dmeBgRowOpacity')")
    start = js("_layersPanel.bgRowPart('dmeBgRowOpacity').visualPosition")
    QtTest.QTest.mousePress(win, QtCore.Qt.MouseButton.LeftButton, NO_MOD,
                            at(r, start))
    for fx in (0.4, 0.5, 0.6, 0.7, 0.8):
        QtTest.QTest.mouseMove(win, at(r, fx), 10)
        QtCore.QCoreApplication.processEvents()
    QtTest.QTest.mouseRelease(win, QtCore.Qt.MouseButton.LeftButton, NO_MOD,
                              at(r, 0.8))
    settle()
    out["slider-dragged"] = js("_layersPanel.ed.bgViewOpacity")
    out["slider-drag-calls"] = js("_layersPanel.ed.calls")
    out["slider-drag-qt-lines"] = [m for m in qt_messages
                                   if "binding" in m.lower()]
    ev("_layersPanel.ed.bgViewOpacity = 0.75")
    settle()
    out["slider-follows"] = js("_layersPanel.bgRowPart('dmeBgRowOpacity').value")
    # A click on the Background row selects nothing.
    r = rect("_layersPanel.bgRowPart('dmeBgRow')")
    r["h"] = js("_layersPanel.rowH")
    click(r, 0.4)
    settle()
    out["bg-click"] = js("_layersPanel.ed.calls")
    # A chip filter in Foreground mode, then Background mode: the chip kind
    # stays for Foreground but Background shows its own toggles only.
    click(rect("_layersPanel.kindButton('chip')"))
    settle()
    out["fg-chip-rows"] = js("_layersPanel.describe()")
    r = rect("_layersPanel.bgRowPart('dmeBgRow')")
    r["h"] = js("_layersPanel.rowH")
    QtTest.QTest.mouseDClick(win, QtCore.Qt.MouseButton.LeftButton, NO_MOD, at(r, 0.4))
    settle()
    out["dbl-plane"] = js("_layersPanel.ed.editPlane")
    out["bg-rows"] = js("_layersPanel.describe()")
    out["bg-kinds"] = kinds_shown()
    out["bg-lit"] = js("_layersPanel.litKinds()")
    out["bg-state"] = js("_layersPanel.ed.lastState")
    out["bg-no-bgrow"] = js("_layersPanel.bgRowPart('dmeBgRow') === null")
    click(rect("_layersPanel.kindButton('picture')"))
    settle()
    out["bg-pic-rows"] = js("_layersPanel.describe()")
    click(rect("_layersPanel.kindButton('all')"))
    settle()
    out["bg-all-kinds"] = js("_layersPanel.kinds")
    # Drag the top background row under the last: bottom of the background.
    ev("_layersPanel.ed.calls = []")
    ev("_layersPanel.drop(0, 2)")
    settle()
    out["bg-drop"] = js("_layersPanel.ed.calls")
    ev("_layersPanel.ed.editPlane = 'foreground'")
    settle()
    ev("_layersPanel.ed.calls = []")
    ev("_layersPanel.drop(0, 3)")
    settle()
    out["fg-drop"] = js("_layersPanel.ed.calls")
    out["fg-kinds-kept"] = js("[_layersPanel.kinds, _layersPanel.litKinds()]")
    print("RESULT " + json.dumps(out), flush=True)
    smoke_exit(0)


if __name__ == "__main__":
    main()
