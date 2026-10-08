# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Starts the program off-screen (stand-in hardware) at a UI scale, opens
the Button Map for a stick in Edit with the Layers tool open, and uses the
Layers panel's search box and kind toggles (07 S102). Prints what shows
after each step as JSON. test_layers_panel_search.py runs it in its own
process with a fresh user folder.

    python test/unit/layers_panel_search_smoke.py <scale> <screenshot.png>

The filtering itself belongs to the editor (rig_layers.js); here the panel
is given a stand-in editor that filters a fixed list the same way, so what
is checked is the panel: the state it passes, what it draws, the keys.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location(
    "fake_hardware", ROOT / "test" / "fake_hardware.py"
)
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake = fake_hardware.install()

SCALE = int(sys.argv[1]) if len(sys.argv) > 1 else 100
SHOT = sys.argv[2] if len(sys.argv) > 2 else ""

from gremlin.ui import ui_scale_option  # noqa: E402

ui_scale_option.active_scale = lambda: SCALE

import gremlin.ui.update_model as um  # noqa: E402

um.UpdateModel.startup = lambda self, *a, **k: None

from PySide6 import QtCore, QtGui, QtQml, QtTest  # noqa: E402

import dill  # noqa: E402
import joystick_gremlin  # noqa: E402

NO_MOD = QtCore.Qt.KeyboardModifier.NoModifier
GUID = str(dill.GUID(fake.devices[0].device_guid).uuid)

# A stand-in editor: a fixed list of rows, filtered as the contract says
# (kinds and query on the row; a matching child brings its chip as a
# heading). It records what the panel asks of it.
_FAKE_ED = """
import QtQuick
QtObject {
    property int tick: 0
    property var lastState: null
    property var selected: null
    property int selectCalls: 0
    property var flagged: []
    readonly property var all: [
        { id: "c1", part: "", depth: 0, type: "chip", name: "Fire", ctl: "button 12" },
        { id: "c1", part: "hot", depth: 1, type: "hotspot", name: "Hotspot", ctl: "" },
        { id: "c1", part: "leader:0", depth: 1, type: "leader", name: "Leader 1",
          ctl: "" },
        { id: "c2", part: "", depth: 0, type: "chip", name: "Gear", ctl: "hat 1" },
        { id: "g1", part: "", depth: 0, type: "group", name: "Throttle group",
          ctl: "" },
        { id: "g1", part: "member:0", depth: 1, type: "member", name: "Button 3",
          ctl: "button 3" },
        { id: "s1", part: "", depth: 0, type: "shape", name: "Rectangle", ctl: "" },
        { id: "l1", part: "", depth: 0, type: "line", name: "Line", ctl: "" },
        { id: "p1", part: "", depth: 0, type: "picture", name: "Logo", ctl: "" },
        { id: "t1", part: "", depth: 0, type: "text", name: "Title", ctl: "" },
        { id: "b1", part: "", depth: 0, type: "table", name: "Table", ctl: "" },
        { id: "", part: "photo", depth: 0, type: "photo", name: "Background photo",
          ctl: "" }
    ]
    function _hit(r, st) {
        var ks = (st && st.kinds) || []
        var q = ((st && st.query) || "").toLowerCase()
        if (ks.length && ks.indexOf(r.type) < 0)
            return false
        var words = (r.name + " " + r.ctl + " " + r.type).toLowerCase()
        return q === "" || words.indexOf(q) >= 0
    }
    function layerRows(st, expanded) {
        lastState = (typeof st === "string") ? st : JSON.parse(JSON.stringify(st))
        var out = []
        for (var i = 0; i < all.length; i++) {
            var r = all[i]
            var row = { id: r.id, part: r.part, depth: r.depth, type: r.type,
                        name: r.name, hidden: false, locked: false,
                        hiddenFrom: false, lockedFrom: false,
                        selected: false, canOpen: r.type === "chip" && r.part === "",
                        open: false, index: i, renamable: false }
            var hit = typeof st === "string" ? true : _hit(r, st)
            var childHit = false
            if (r.depth === 0 && typeof st !== "string")
                for (var k = i + 1; k < all.length && all[k].depth > 0; k++)
                    childHit = childHit || _hit(all[k], st)
            if (!hit && !childHit)
                continue
            if (r.depth > 0 && typeof st === "string")
                continue
            row.match = hit
            row.heading = !hit
            out.push(row)
        }
        return out
    }
    function layerCounts(st) {
        var n = 0
        for (var i = 0; i < all.length; i++)
            if (_hit(all[i], st)) n++
        return { matches: n, total: all.length }
    }
    function selectLayerMatches(st) {
        selectCalls++
        selected = JSON.parse(JSON.stringify(st))
        return layerCounts(st).matches
    }
    function canDeleteLayer(id, part) { return part !== "photo" }
    function toggleLayerFlag(id, part, which) {
        flagged = flagged.concat([id + "/" + part + "/" + which])
        tick++
    }
    function setSelection(ids) {}
    function toggleSelected(id) {}
    function bump() { tick++ }
    function focusMap() {}
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
    call(root, "openButtonMapForCard", card)
    assert wait_until(lambda: call(root, "buttonMapWindow") is not None)
    win = call(root, "buttonMapWindow")
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

    def click(r: dict) -> None:
        QtTest.QTest.mouseClick(
            win, QtCore.Qt.MouseButton.LeftButton, NO_MOD,
            QtCore.QPoint(round(r["x"] + r["w"] / 2), round(r["y"] + r["h"] / 2)),
        )
        QtCore.QCoreApplication.processEvents()

    def type_text(text: str) -> None:
        """Types into what has focus (QTest.keyClicks wants a widget)."""
        for ch in text:
            key = QtCore.Qt.Key(ord(ch.upper()))
            for kind in (QtCore.QEvent.Type.KeyPress, QtCore.QEvent.Type.KeyRelease):
                event = QtGui.QKeyEvent(kind, key, NO_MOD, ch)
                QtCore.QCoreApplication.sendEvent(win, event)

    def set_fake_ed(name: str) -> None:
        ev("_layersPanel.ed = Qt.createQmlObject("
           + json.dumps(_FAKE_ED) + f", _layersPanel, '{name}')")

    def settle() -> None:
        QtCore.QCoreApplication.processEvents()
        ev("_layersPanel.forceLayout()")

    call(win, "enterEdit")
    assert wait_until(lambda: ev("editing") is True)
    ev("_tools.setOpen('layers', true)")
    assert wait_until(lambda: ev("_layersPanel.visible") is True)

    out["props"] = js("({kinds: _layersPanel.kinds,"
                      " searchText: _layersPanel.searchText,"
                      " state: _layersPanel.filterState,"
                      " focus: typeof _layersPanel.focusSearch})")
    # With the real editor and no filter: today's rows, no count line.
    out["real-rows"] = js("_layersPanel.rows.length")
    out["real-count-line"] = js("_layersPanel.countText")

    # --- fits at the pane's smallest width ---------------------------------
    ev("_tools.setSize('layers', _layersPane.minW, _layersPane.height)")
    wait_until(lambda: abs(js("_layersPane.width - _layersPane.minW")) < 1, 2000)
    settle()
    out["pane-w"] = js("[_layersPane.width, _layersPane.minW]")
    out["fit"] = js("_layersPanel.clippedParts()")
    if SHOT:
        Path(SHOT).parent.mkdir(parents=True, exist_ok=True)

    # --- the stand-in editor ---------------------------------------------------
    set_fake_ed("fakeEd")
    settle()
    out["0-all"] = js("_layersPanel.describe()")
    out["0-lit"] = js("_layersPanel.litKinds()")
    out["0-count"] = js("_layersPanel.countText")
    out["0-state"] = js("_layersPanel.ed.lastState")

    def toggle(key: str) -> None:
        click(rect(f"_layersPanel.kindButton('{key}')"))
        settle()

    toggle("chip")
    toggle("shape")
    out["1-kinds"] = js("_layersPanel.kinds")
    out["1-lit"] = js("_layersPanel.litKinds()")
    out["1-rows"] = js("_layersPanel.describe()")
    out["1-count"] = js("_layersPanel.countText")
    out["1-state"] = js("_layersPanel.ed.lastState")
    toggle("shape")
    out["2-kinds"] = js("_layersPanel.kinds")
    toggle("chip")
    toggle("hotspot")
    out["3-rows"] = js("_layersPanel.describe()")
    # A chip shown only for its hotspot: a dimmed heading.
    out["3-heading"] = js("_layersPanel.rowLook(0)")
    out["3-match"] = js("_layersPanel.rowLook(1)")
    toggle("all")
    out["4-kinds"] = js("_layersPanel.kinds")
    out["4-lit"] = js("_layersPanel.litKinds()")
    out["4-count"] = js("_layersPanel.countText")

    # Typing filters, as you type.
    ev("_layersPanel.focusSearch()")
    type_text("BUTTON 1")
    settle()
    out["5-search"] = js("_layersPanel.searchText")
    out["5-rows"] = js("_layersPanel.describe()")
    out["5-count"] = js("_layersPanel.countText")
    QtTest.QTest.keyClick(win, QtCore.Qt.Key.Key_Escape)
    settle()
    out["6-esc"] = js("[_layersPanel.searchText, _layersPanel.describe().length,"
                      " _layersPanel.countText]")
    out["6-still-open"] = js("_layersPanel.visible")
    type_text("zzz")
    settle()
    out["7-none"] = js("_layersPanel.countText")
    click(rect("_layersPanel.clearButton()"))
    settle()
    out["8-cleared"] = js("[_layersPanel.searchText, _layersPanel.searchFieldText()]")
    # Enter selects every match.
    ev("_layersPanel.focusSearch()")
    type_text("gear")
    QtTest.QTest.keyClick(win, QtCore.Qt.Key.Key_Return)
    settle()
    out["9-enter"] = js("[_layersPanel.ed.selectCalls, _layersPanel.ed.selected]")
    # Eye on a shown row.
    click(rect("_layersPanel.flagButton(0, 'hidden')"))
    settle()
    out["10-eye"] = js("_layersPanel.ed.flagged")
    # focusSearch selects what is there.
    ev("_layersPanel.focusSearch()")
    out["11-focus"] = js("[_layersPanel.searchHasFocus(),"
                         " _layersPanel.searchSelected()]")

    # A group member found by the search: under its group, which is a
    # heading; its eye and lock are greyed and do nothing.
    ev("_layersPanel.focusSearch()")
    type_text("button 3")
    settle()
    out["13-member"] = js("_layersPanel.describe()")
    out["13-member-look"] = js("[_layersPanel.rowLook(0).heading,"
                               " _layersPanel.flagButton(1, 'hidden').can,"
                               " _layersPanel.flagButton(1, 'locked').can]")
    click(rect("_layersPanel.flagButton(1, 'hidden')"))
    click(rect("_layersPanel.flagButton(1, 'locked')"))
    settle()
    out["13-member-flags"] = js("_layersPanel.ed.flagged")
    ev("_layersPanel.focusSearch()")
    type_text("gear")
    settle()

    # Another editor (another device's map): the kinds and search stay.
    toggle("text")
    set_fake_ed("fakeEd2")
    settle()
    out["12-kept"] = js("[_layersPanel.kinds, _layersPanel.searchText,"
                        " _layersPanel.ed.lastState]")

    # Wrap check with everything lit and a search in (×) at the smallest width.
    for key in ("group", "leader", "line", "picture", "table", "photo"):
        toggle(key)
    settle()
    out["fit-lit"] = js("_layersPanel.clippedParts()")
    if SHOT:
        pane = [round(v) for v in rect("_layersPane").values()]
        win.grabWindow().copy(*pane).save(SHOT)
    print("RESULT " + json.dumps(out), flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()
