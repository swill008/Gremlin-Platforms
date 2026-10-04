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
import os
import sys
from pathlib import Path

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
            "JSON.stringify({chips: _poolFloat.visible, props: _tools.isOpen('props'),"
            " layers: _layersPanel.visible, palette: _palette.opened,"
            " order: _tools.order('bottom')})"
        ))

    def step(code: str, tag: str, wait: int = 250) -> None:
        ev(code)
        QtTest.QTest.qWait(wait)
        look(tag)

    call(win, "enterEdit")
    QtTest.QTest.qWait(800)
    look("0-first-edit")
    # From here as an unpinned, hidden pool (the steps below need one).
    ev("_tools.setPinned('chips', false); _tools.setOpen('chips', false)")
    look("1-edit")
    step("_tools.toggle('chips')", "2-chips-open")
    # A click on the map: the unpinned pool hides.
    step("_ed().mapPressed()", "3-map-click")
    step("_tools.setPinned('chips', true); _tools.setOpen('chips', true);"
         " _tools.setOpen('layers', true)", "4-chips-pinned-layers-open")
    # Pinned stays, unpinned (Layers) hides.
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
    ev("_tools.dropAt('chips', _tools.placeOf('palette') + 4)")
    QtTest.QTest.qWait(200)
    out["chips-onto-palette"] = places()
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

    # The bars: the status line one row of small text, the tool row below
    # the map; the pool docked just above the tool row.
    out["status-height"] = ev("_statusLine.height")
    out["pool-bottom-gap"] = ev(
        "Math.round(_poolFloat.parent.height - _poolFloat.y - _poolFloat.height)")
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
    button = scene_rect("_bottomRow._button('chips')")
    grab = QtCore.QPointF(button["x"] + 10, middle(button).y())
    drag(grab, QtCore.QPointF(top["x"] + top["w"] * 0.25, middle(top).y()))
    out["chips-up"] = [ev("_tools.sideOf('chips')"), ev("_tools.dockOf('chips')"),
                       ev("_tools.order('top')"), ev("_tools.order('bottom')")]
    # The pool joins its tab: it reaches up to the top row, under the tab.
    pool = scene_rect("_poolFloat")
    tab = scene_rect("_topRow._button('chips')")
    out["pool-at-top"] = round(pool["y"] - (top["y"] + top["h"]))
    out["tab-over-pool"] = (pool["x"] <= tab["x"]
                            and tab["x"] + tab["w"] <= pool["x"] + pool["w"])
    # Its edge facing the map makes it taller (unlocked); it can't be dragged
    # away from its tab.
    edge = QtCore.QPointF(pool["x"] + pool["w"] / 2, pool["y"] + pool["h"] - 2)
    drag(edge, edge + QtCore.QPointF(0, 60))
    grown = scene_rect("_poolFloat")
    out["pool-resized"] = round(grown["h"] - pool["h"])
    out["pool-stays"] = [ev("_tools.sideOf('chips')"), round(grown["y"] - pool["y"])]
    # Locked: no resizing.
    ev("_tools.setLocked('chips', true)")
    QtTest.QTest.qWait(100)
    edge = QtCore.QPointF(grown["x"] + grown["w"] / 2, grown["y"] + grown["h"] - 2)
    drag(edge, edge + QtCore.QPointF(0, 60))
    out["pool-locked"] = round(scene_rect("_poolFloat")["h"] - grown["h"])
    ev("_tools.setLocked('chips', false)")
    # Kept: loaded again, the row and the size are as they were.
    ev("_tools._load()")
    QtTest.QTest.qWait(200)
    kept_h = scene_rect("_poolFloat")["h"]
    out["kept"] = [ev("_tools.sideOf('chips')"), round(kept_h - grown["h"])]
    out["saved-top"] = window_placement.tool_row_state("button-map")
    # Reset Tool Rows: every button back on its own row, panels at their
    # first size.
    ev("_tools.resetPlaces()")
    QtTest.QTest.qWait(200)
    out["reset-rows"] = [ev("_tools.order('top').length"),
                         ev("_tools.sizeOf('chips') === null")]

    # --- zoom ------------------------------------------------------------------
    face = "_ed().face"
    ev(f"{face}.zoomToPage()")
    QtTest.QTest.qWait(100)
    out["page-zoom"] = [ev(f"{face}.zoom"), ev(f"{face}.viewPct")]
    for _ in range(12):
        ev(f"{face}.zoomAt(NaN, NaN, 0.8)")
    QtTest.QTest.qWait(100)
    out["out-most"] = ev(f"Math.round({face}.viewPct * 100)")

    # --- the side rows ---------------------------------------------------------
    left = scene_rect("_leftRow")
    right = scene_rect("_rightRow")
    host = scene_rect("_mapHost")
    out["side-rows"] = {
        "visible": [ev("_leftRow.visible"), ev("_rightRow.visible")],
        "width": [round(left["w"]), round(right["w"])],
        "gaps": [round(host["x"] - (left["x"] + left["w"])),
                 round(right["x"] - (host["x"] + host["w"]))],
        # Between the top and bottom rows.
        "between": [round(left["y"] - (top["y"] + top["h"])),
                    round(bottom["y"] - (left["y"] + left["h"]))],
    }
    # Layers dragged from the bottom row onto the left one, by its name.
    ev("_tools.setOpen('layers', false)")
    QtTest.QTest.qWait(100)
    button = scene_rect("_bottomRow._button('layers')")
    grab = QtCore.QPointF(button["x"] + 10, middle(button).y())
    drag(grab, QtCore.QPointF(middle(left).x(), left["y"] + left["h"] * 0.3))
    out["layers-left"] = [ev("_tools.sideOf('layers')"), ev("_tools.order('left')")]
    tab = scene_rect("_leftRow._button('layers')")
    out["tab-upright"] = tab["h"] > tab["w"]
    ev("_tools.setOpen('layers', true)")
    QtTest.QTest.qWait(300)
    pane = scene_rect("_layersPane")
    # Beside its tab, reaching the row, the tab within its height.
    out["layers-pane"] = {
        "joined": round(pane["x"] - (left["x"] + left["w"])),
        "beside-tab": (pane["y"] <= tab["y"] + 0.5
                       and tab["y"] + tab["h"] <= pane["y"] + pane["h"] + 0.5),
    }
    # Its edge facing the map (the right one) makes it wider.
    edge = QtCore.QPointF(pane["x"] + pane["w"] - 2, pane["y"] + pane["h"] / 3)
    drag(edge, edge + QtCore.QPointF(40, 0))
    out["layers-wider"] = round(scene_rect("_layersPane")["w"] - pane["w"])
    ev("_tools.resetPlaces()")
    QtTest.QTest.qWait(300)
    out["layers-reset"] = ev("_tools.sideOf('layers')")
    print("RESULT " + json.dumps(out), flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()
