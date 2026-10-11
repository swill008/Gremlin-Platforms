# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Starts the program off-screen (stand-in hardware), opens the Button Map
for a stick and uses its tool row; prints what shows after each step as
JSON. test_button_map_tool_row.py runs it in its own process with a fresh
user folder.

    python test/unit/button_map_tool_row_smoke.py
"""

from __future__ import annotations

import importlib.util
import json
import sys
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

from PySide6 import QtCore, QtGui, QtQml, QtTest  # noqa: E402

import dill  # noqa: E402
import joystick_gremlin  # noqa: E402

GUID = str(dill.GUID(fake.devices[0].device_guid).uuid)
# The side panels (07 S128): Chips on the left, Layers on the right.
_SIDE = ("(function(s){ function f(o){ if (!o) return null;"
         " if (o.takenWidth !== undefined && o.side === s) return o;"
         " var c = o.children || []; for (var i = 0; i < c.length; i++) {"
         " var r = f(c[i]); if (r) return r } return null }"
         " return f(_buttonMap.contentItem) })")
CHIPS = _SIDE + "('left')"
LAYERS = _SIDE + "('right')"


def call(obj: QtCore.QObject, name: str, *args: object) -> object:
    return QtCore.QMetaObject.invokeMethod(
        obj, name, QtCore.Q_RETURN_ARG("QVariant"),
        *[QtCore.Q_ARG("QVariant", a) for a in args],
    )


def main() -> None:
    app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
    QtTest.QTest.qWait(800)
    root = app.engine.rootObjects()[0]
    card = {"rawName": "pJoy Pro", "name": "pJoy Pro", "guid": GUID}
    call(root, "openButtonMapForCard", card)
    QtTest.QTest.qWait(1000)
    win = call(root, "buttonMapWindow")
    win.setProperty("width", 1200)
    win.setProperty("height", 800)
    QtTest.QTest.qWait(300)
    out: dict = {}

    def ev(code: str) -> object:
        expr = QtQml.QQmlExpression(QtQml.qmlContext(win), win, code)
        value = expr.evaluate()
        if expr.hasError():
            return "error: " + expr.error().toString()
        value = value[0] if isinstance(value, tuple) else value
        return value.toVariant() if hasattr(value, "toVariant") else value

    def look(tag: str) -> None:
        out[tag] = json.loads(ev(
            "JSON.stringify({chips: " + CHIPS + ".open, props: _tools.isOpen('props'),"
            " layers: " + LAYERS + ".open, palette: _palette.opened,"
            " order: _tools.order('bottom')})"
        ))

    def step(code: str, tag: str, wait: int = 250) -> None:
        ev(code)
        QtTest.QTest.qWait(wait)
        look(tag)

    call(win, "enterEdit")
    QtTest.QTest.qWait(800)
    look("0-first-edit")
    # From here as an unpinned, hidden Properties (the steps below need one).
    ev("_tools.setPinned('props', false); _tools.setOpen('props', false)")
    look("1-edit")
    step("_tools.toggle('props')", "2-props-open")
    # A click on the map: unpinned Properties hides.
    step("_ed().mapPressed()", "3-map-click")
    step("_tools.setPinned('props', true); _tools.setOpen('props', true);"
         " " + LAYERS + ".unfold()", "4-props-pinned-layers-open")
    # Pinned stays, unpinned (the Layers side panel) folds.
    step("_ed().mapPressed()", "5-map-click")
    step("_tools.moveTo('palette', 0)", "6-moved")
    # Locked: it stays where it is.
    step("_tools.setLocked('palette', true); _tools.moveTo('palette', 3)",
         "7-locked-move")
    step("_tools.setOpen('palette', true)", "8-palette")
    step("_palette.close()", "9-palette-closed")

    # Any place on the row: let go at the left edge (snaps to it), then a
    # button onto it (goes to the nearest free spot), then back to centred.
    ev("_tools.setLocked('palette', false)")

    def places() -> dict:
        return json.loads(ev(
            "(function(){ var o = {}; var ids = _tools.order('bottom');"
            " for (var i = 0; i < ids.length; i++) o[ids[i]] = _tools.placeOf(ids[i]);"
            " return JSON.stringify(o) })()"
        ))

    out["centred"] = places()
    ev("_tools.dropAt('palette', 3)")
    QtTest.QTest.qWait(200)
    out["palette-left"] = places()
    ev("_tools.dropAt('props', _tools.placeOf('palette') + 4)")
    QtTest.QTest.qWait(200)
    out["props-onto-palette"] = places()
    out["widths"] = json.loads(ev(
        "(function(){ var o = {}; var ids = _tools.order('bottom');"
        " for (var i = 0; i < ids.length; i++) { var b = _bottomRow._button(ids[i]);"
        " o[ids[i]] = b.width } return JSON.stringify(o) })()"
    ))
    out["row-width"] = ev("_bottomRow.width")
    out["gap"] = ev("_bottomRow.gap")
    ev("_tools.resetPlaces()")
    QtTest.QTest.qWait(200)
    out["reset"] = places()
    ev("_tools.setLocked('palette', true)")

    # The status line: one row of small text.
    out["status-height"] = ev("_statusLine.height")
    from gremlin.ui import window_placement

    out["saved"] = window_placement.tool_row_state("button-map")

    # --- the top row ---------------------------------------------------------
    Button = QtCore.Qt.MouseButton
    none = QtCore.Qt.KeyboardModifier.NoModifier

    def scene_rect(code: str) -> dict:
        return json.loads(str(ev(
            "(function(){ var o = " + code + "; var p = o.mapToItem(null, 0, 0);"
            " return JSON.stringify({x: p.x, y: p.y, w: o.width, h: o.height}) })()"
        )))

    def drag(a: QtCore.QPointF, b: QtCore.QPointF) -> None:
        QtTest.QTest.mousePress(win, Button.LeftButton, none, a.toPoint())
        QtTest.QTest.qWait(30)
        for i in range(1, 13):
            p = a + (b - a) * (i / 12)
            move = QtGui.QMouseEvent(
                QtCore.QEvent.Type.MouseMove, p, p, Button.NoButton,
                Button.LeftButton, none,
            )
            QtCore.QCoreApplication.sendEvent(win, move)
            QtTest.QTest.qWait(15)
        QtTest.QTest.mouseRelease(win, Button.LeftButton, none, b.toPoint())
        QtTest.QTest.qWait(300)

    def middle(r: dict) -> QtCore.QPointF:
        return QtCore.QPointF(r["x"] + r["w"] / 2, r["y"] + r["h"] / 2)

    top = scene_rect("_topRow")
    host = scene_rect("_mapHost")
    bottom = scene_rect("_bottomRow")
    out["top-row"] = {"visible": ev("_topRow.visible"), "height": top["h"],
                      "tools": ev("_tools.order('top').length")}
    out["gaps"] = [round(host["y"] - (top["y"] + top["h"])),
                   round(bottom["y"] - (host["y"] + host["h"]))]
    out["dp10"] = ev("Style.dp(10)")
    # A button dragged up onto the top row: it moves there, with its panel.
    ev("_tools.setLocked('palette', false)")
    QtTest.QTest.qWait(100)
    # Grabbed by its name (its pin and lock are buttons of their own).
    button = scene_rect("_bottomRow._button('props')")
    grab = QtCore.QPointF(button["x"] + 10, middle(button).y())
    drag(grab, QtCore.QPointF(top["x"] + top["w"] * 0.25, middle(top).y()))
    out["props-up"] = [ev("_tools.sideOf('props')"), ev("_tools.dockOf('props')"),
                       ev("_tools.order('top')"), ev("_tools.order('bottom')")]
    # A panel on the top row (Options) joins its tab: it reaches up to the
    # top row, under the tab.
    ev("_tools.setOpen('options', true); _tools.setSize('options', 0, Style.dp(200))")
    QtTest.QTest.qWait(300)
    pool = scene_rect("_optionsFloat")
    tab = scene_rect("_topRow._button('options')")
    out["pool-at-top"] = round(pool["y"] - (top["y"] + top["h"]))
    out["tab-over-pool"] = (pool["x"] <= tab["x"]
                            and tab["x"] + tab["w"] <= pool["x"] + pool["w"])
    # Its edge facing the map makes it taller (unlocked); it can't be dragged
    # away from its tab.
    edge = QtCore.QPointF(pool["x"] + pool["w"] / 2, pool["y"] + pool["h"] - 2)
    drag(edge, edge + QtCore.QPointF(0, 60))
    grown = scene_rect("_optionsFloat")
    out["pool-resized"] = round(grown["h"] - pool["h"])
    out["pool-stays"] = [ev("_tools.sideOf('options')"), round(grown["y"] - pool["y"])]
    # Locked: no resizing.
    ev("_tools.setLocked('options', true)")
    QtTest.QTest.qWait(100)
    edge = QtCore.QPointF(grown["x"] + grown["w"] / 2, grown["y"] + grown["h"] - 2)
    drag(edge, edge + QtCore.QPointF(0, 60))
    out["pool-locked"] = round(scene_rect("_optionsFloat")["h"] - grown["h"])
    ev("_tools.setLocked('options', false)")
    # Kept: loaded again, the row and the size are as they were.
    ev("_tools._load(); _tools.setOpen('options', true)")
    QtTest.QTest.qWait(200)
    kept_h = scene_rect("_optionsFloat")["h"]
    out["kept"] = [ev("_tools.sideOf('props')"), round(kept_h - grown["h"])]
    out["saved-top"] = window_placement.tool_row_state("button-map")
    # The side panels' width, pin and open state are kept with the rows.
    ev("_tools.setSideState('chips',"
       " {width: Style.dp(400), pinned: false, open: false});"
       " _tools.setSideState('layers',"
       " {width: Style.dp(350), pinned: true, open: true})")
    QtTest.QTest.qWait(100)
    ev("_tools._load()")
    QtTest.QTest.qWait(100)
    out["sides-kept"] = json.loads(ev(
        "JSON.stringify([_tools.sideState('chips'), _tools.sideState('layers')])"))
    out["sides-saved"] = window_placement.tool_row_state("button-map").get("sides")
    # Reset Tool Rows: every button back on its own row, panels at their
    # first size, the side panels as they start.
    ev("_tools.resetPlaces()")
    QtTest.QTest.qWait(200)
    out["reset-rows"] = [ev("_tools.order('top').length"),
                         ev("_tools.sizeOf('options') === null")]
    out["sides-reset"] = json.loads(ev(
        "JSON.stringify([_tools.sideState('chips'), _tools.sideState('layers')])"))

    # --- zoom ------------------------------------------------------------------
    face = "_ed().face"
    ev(f"{face}.zoomToPage()")
    QtTest.QTest.qWait(100)
    out["page-zoom"] = [ev(f"{face}.zoom"), ev(f"{face}.viewPct")]
    for _ in range(12):
        ev(f"{face}.zoomAt(NaN, NaN, 0.8)")
    QtTest.QTest.qWait(100)
    out["out-most"] = ev(f"Math.round({face}.viewPct * 100)")

    # --- no left or right rows (07 S128, S99) ---------------------------------
    rows = []

    def walk(item: object) -> None:
        if item.metaObject().className().startswith("ToolRow"):
            rows.append(str(item.property("side")))
        for child in item.childItems():
            walk(child)

    walk(win.contentItem())
    out["rows"] = sorted(rows)
    out["row-tools"] = [ev("_tools.order('top')"), ev("_tools.order('bottom')")]
    # A saved placement on a removed row is ignored: the tool is on the
    # bottom row.
    saved = window_placement.tool_row_state("button-map")
    saved["items"]["props"]["side"] = "left"
    saved["items"]["palette"]["side"] = "right"
    window_placement.save_tool_row_state("button-map", saved)
    ev("_tools._load()")
    QtTest.QTest.qWait(200)
    out["old-side-rows"] = [ev("_tools.sideOf('props')"),
                            ev("_tools.sideOf('palette')")]
    print("RESULT " + json.dumps(out), flush=True)
    smoke_exit(0)


if __name__ == "__main__":
    main()
