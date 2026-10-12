# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Starts the program off-screen (stand-in hardware), opens the Device Mapping Editor
for a stick and uses its side panels (Chips on the left, Layers on the
right, 07 S128-S131) with real clicks and drags; prints what shows after
each step as JSON. test_side_panels_e2e.py runs it in its own process with
a fresh user folder.

    python test/unit/side_panels_e2e_smoke.py
"""

from __future__ import annotations

import importlib.util
import json
import sys
import time
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

from PySide6 import QtCore, QtGui, QtQml, QtQuick, QtTest  # noqa: E402

import dill  # noqa: E402
import joystick_gremlin  # noqa: E402

GUID = str(dill.GUID(fake.devices[0].device_guid).uuid)
Button = QtCore.Qt.MouseButton
NONE = QtCore.Qt.KeyboardModifier.NoModifier


def call(obj: QtCore.QObject, name: str, *args: object) -> object:
    return QtCore.QMetaObject.invokeMethod(
        obj, name, QtCore.Q_RETURN_ARG("QVariant"),
        *[QtCore.Q_ARG("QVariant", a) for a in args],
    )


def wait_until(check: Callable[[], object], ms: int = 4000) -> object:
    end = time.monotonic() + ms / 1000
    value = check()
    while not value and time.monotonic() < end:
        QtTest.QTest.qWait(30)
        value = check()
    return value


def ev(win: QtCore.QObject, code: str, scope: QtCore.QObject | None = None) -> object:
    expr = QtQml.QQmlExpression(QtQml.qmlContext(win), scope or win, code)
    value = expr.evaluate()
    if expr.hasError():
        return "error: " + expr.error().toString()
    value = value[0] if isinstance(value, tuple) else value
    return value.toVariant() if hasattr(value, "toVariant") else value


def side_panels(win: QtGui.QWindow) -> dict:
    """The window's SidePanels by side (found by their API, not an id)."""
    found: dict = {}

    def walk(item: QtQuick.QQuickItem) -> None:
        meta = item.metaObject()
        if (meta.indexOfProperty("takenWidth") >= 0
                and meta.indexOfProperty("stripWidth") >= 0):
            found[str(item.property("side"))] = item
        for child in item.childItems():
            walk(child)

    walk(win.contentItem())
    return found


def rect(item: QtQuick.QQuickItem) -> dict:
    p = item.mapToScene(QtCore.QPointF(0, 0))
    return {"x": p.x(), "y": p.y(), "w": item.width(), "h": item.height()}


def part(panel: QtQuick.QQuickItem, name: str) -> QtQuick.QQuickItem:
    found = panel.findChild(QtQuick.QQuickItem, name)
    assert found is not None, name
    return found


def centre(item: QtQuick.QQuickItem) -> QtCore.QPoint:
    r = rect(item)
    return QtCore.QPointF(r["x"] + r["w"] / 2, r["y"] + r["h"] / 2).toPoint()


def main() -> None:
    app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
    QtTest.QTest.qWait(800)
    root = app.engine.rootObjects()[0]
    card = {"rawName": "pJoy Pro", "name": "pJoy Pro", "guid": GUID}
    out: dict = {}

    def open_window() -> QtGui.QWindow:
        call(root, "openDeviceMappingEditorForCard", card)
        win = wait_until(lambda: call(root, "deviceMappingEditorWindow"))
        assert isinstance(win, QtGui.QWindow)
        wait_until(lambda: ev(win, "mapShown") is True)
        win.setProperty("width", 1400)
        win.setProperty("height", 900)
        QtTest.QTest.qWait(300)
        return win

    def edit(win: QtGui.QWindow) -> None:
        call(win, "enterEdit")
        wait_until(lambda: ev(win, "editing && _ed() !== null && _ed().seeded") is True)
        QtTest.QTest.qWait(300)

    def click(win: QtGui.QWindow, at: QtCore.QPoint) -> None:
        QtTest.QTest.mouseClick(win, Button.LeftButton, NONE, at)
        QtTest.QTest.qWait(250)

    def drag(win: QtGui.QWindow, a: QtCore.QPointF, b: QtCore.QPointF) -> None:
        QtTest.QTest.mousePress(win, Button.LeftButton, NONE, a.toPoint())
        QtTest.QTest.qWait(30)
        for i in range(1, 13):
            p = a + (b - a) * (i / 12)
            move = QtGui.QMouseEvent(
                QtCore.QEvent.Type.MouseMove, p, p, Button.NoButton,
                Button.LeftButton, NONE,
            )
            QtCore.QCoreApplication.sendEvent(win, move)
            QtTest.QTest.qWait(15)
        QtTest.QTest.mouseRelease(win, Button.LeftButton, NONE, b.toPoint())
        QtTest.QTest.qWait(300)

    def state(panel: QtQuick.QQuickItem) -> dict:
        return {k: panel.property(k) for k in
                ("available", "open", "pinned", "overlay", "panelWidth",
                 "shownWidth", "takenWidth", "minWidth", "maxWidth")} | {
            "visible": panel.isVisible()}

    def out_and_pinned(panel: QtQuick.QQuickItem) -> bool:
        return bool(panel.property("open") and panel.property("pinned"))

    win = open_window()
    out["dp"] = ev(win, "Style.dp(1)")
    sides = side_panels(win)
    out["found"] = sorted(sides)
    chips, layers = sides.get("left"), sides.get("right")
    if chips is None or layers is None:
        print("RESULT " + json.dumps(out), flush=True)
        smoke_exit(0)
        return
    out["titles"] = [chips.property("title"), layers.property("title")]
    out["layers-holds-panel"] = ev(
        win, "(function(){ var p = _layersPanel;"
        " while (p && p.takenWidth === undefined) p = p.parent;"
        " return !!p && p.side === 'right' })()")

    # --- outside Edit: no strips (S130) ------------------------------------
    out["before-edit"] = [state(chips), state(layers)]

    # --- Edit: the strips come; Chips out and pinned, Layers folded --------
    edit(win)
    out["edit"] = [state(chips), state(layers)]
    # Folded Layers: its own frame ajar on the window's right edge.
    body = part(layers, "sidePanelBody")
    out["layers-ajar"] = [win.width() - rect(body)["x"], rect(body)["w"],
                          layers.property("stripWidth")]
    host = lambda: rect(ev(win, "_mapHost"))  # noqa: E731
    out["host-edit"] = host()

    # Unpinned and folded by its own buttons: the map gets the room back.
    click(win, centre(part(chips, "sidePin")))
    out["unpinned"] = state(chips)
    click(win, centre(part(chips, "sideFold")))
    out["folded"] = state(chips)
    out["host-folded"] = host()

    # Its strip: out at its width, over the map (the map keeps its width).
    click(win, centre(part(chips, "sideStrip")))
    out["strip-open"] = state(chips)
    out["strip-body-w"] = part(chips, "sidePanelBody").width()
    out["host-overlay"] = host()
    # Pinned: beside the map, which narrows.
    click(win, centre(part(chips, "sidePin")))
    out["pinned"] = state(chips)
    out["host-pinned"] = host()

    # --- Layers: unpinned, over the map; a map click folds it --------------
    click(win, centre(part(layers, "sideStrip")))
    out["layers-open"] = state(layers)
    out["layers-body"] = rect(part(layers, "sidePanelBody"))
    out["host-layers"] = host()
    h = host()
    click(win, QtCore.QPointF(h["x"] + h["w"] * 0.35, h["y"] + h["h"] * 0.5).toPoint())
    out["map-click"] = [state(chips), state(layers)]

    # The other drawer's click folds an unpinned panel: Layers out, Chips
    # folded by its arrow (Layers stays), then Chips' drawer clicked.
    click(win, centre(part(layers, "sideStrip")))
    out["layers-again"] = state(layers)["open"]
    click(win, centre(part(chips, "sideFold")))
    out["chips-folded"] = [state(chips), state(layers)]
    click(win, centre(part(chips, "sideStrip")))
    out["other-strip"] = [state(chips), state(layers)]

    # --- resize by the inner edge; kept after closing and reopening --------
    before = chips.property("panelWidth")
    grip = rect(part(chips, "sideGrip"))
    a = QtCore.QPointF(grip["x"] + grip["w"] / 2, grip["y"] + grip["h"] / 2)
    drag(win, a, a + QtCore.QPointF(40, 0))
    out["resized"] = [before, chips.property("panelWidth")]
    # Past its maximum: stops there.
    grip = rect(part(chips, "sideGrip"))
    a = QtCore.QPointF(grip["x"] + grip["w"] / 2, grip["y"] + grip["h"] / 2)
    drag(win, a, a + QtCore.QPointF(2000, 0))
    out["at-max"] = [chips.property("panelWidth"), chips.property("maxWidth")]
    from gremlin.ui import device_map_options

    def saved() -> dict:
        return {p: device_map_options.side_panel_state(p) for p in ("chips", "layers")}

    out["saved-sides"] = saved()

    # --- Background mode folds Chips and brings it back (S130) -------------
    ev(win, "_editorWin.setEditPlane('background')")
    QtTest.QTest.qWait(300)
    out["bg"] = [ev(win, "bgMode"), state(chips)]
    out["bg-saved"] = saved()
    ev(win, "_editorWin.setEditPlane('foreground')")
    QtTest.QTest.qWait(300)
    out["fg"] = [ev(win, "bgMode"), state(chips)]

    # --- a narrow window folds Chips first, then Layers (S131) -------------
    # Wide first, so both fit pinned at their widest.
    win.setProperty("width", 2000)
    QtTest.QTest.qWait(300)
    click(win, centre(part(layers, "sideStrip")))
    if not layers.property("pinned"):
        click(win, centre(part(layers, "sidePin")))
    for p in (chips, layers):
        p.setProperty("panelWidth", p.property("maxWidth"))
    QtTest.QTest.qWait(300)
    out["narrow-start"] = [state(chips), state(layers)]
    sweep = []
    for width in list(range(2000, 799, -100)) + [700, 600, 500]:
        win.setProperty("width", width)
        QtTest.QTest.qWait(250)
        sweep.append({"asked": width, "width": win.width(),
                      "chips": out_and_pinned(chips),
                      "layers": out_and_pinned(layers),
                      "host": host()["w"]})
    out["sweep"] = sweep
    win.setProperty("width", 2000)
    QtTest.QTest.qWait(400)
    out["wide-again"] = [state(chips), state(layers)]
    # Put Layers back as it starts, for the reopen below.
    click(win, centre(part(layers, "sidePin")))
    click(win, centre(part(layers, "sideFold")))
    win.setProperty("width", 1400)
    QtTest.QTest.qWait(200)
    out["kept-width"] = chips.property("panelWidth")

    # --- leave Edit: the strips go ------------------------------------------
    ev(win, "_editorWin.discardEdit()")
    QtTest.QTest.qWait(300)
    out["after-edit"] = [state(chips), state(layers)]

    # --- closed and opened again: as left ----------------------------------
    win.close()
    QtTest.QTest.qWait(800)
    app.engine.collectGarbage()
    QtTest.QTest.qWait(200)
    win = open_window()
    edit(win)
    sides = side_panels(win)
    chips, layers = sides["left"], sides["right"]
    out["reopened"] = [state(chips), state(layers)]

    # --- Reset Panels puts the side panels back as they start (S99) --------
    # View > Reset Panels, the menu item itself.
    items = [o for o in win.findChildren(QtCore.QObject)
             if o.property("text") == "Reset Panels"
             and o.metaObject().indexOfSignal("triggered()") >= 0]
    out["reset-items"] = len(items)
    if items:
        ev(win, "triggered()", items[0])
    QtTest.QTest.qWait(300)
    out["reset"] = [state(chips), state(layers)]
    print("RESULT " + json.dumps(out), flush=True)
    smoke_exit(0)


if __name__ == "__main__":
    main()
