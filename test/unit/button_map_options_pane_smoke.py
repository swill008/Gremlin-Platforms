# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Starts the program off-screen (stand-in hardware), opens the Button Map
and its Options pane (Edit > Button Map Options...) and prints what it shows
and does as JSON (a screenshot too when a folder is given).
test_button_map_options_pane.py runs it in its own process with a fresh
user folder.

    python test/unit/button_map_options_pane_smoke.py [folder]
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

from PySide6 import QtCore, QtGui, QtQml, QtQuick, QtTest  # noqa: E402

import dill  # noqa: E402
import joystick_gremlin  # noqa: E402
from gremlin.ui import button_map_options  # noqa: E402

GUID = str(dill.GUID(fake.devices[0].device_guid).uuid)


def call(obj: QtCore.QObject, name: str, *args: object) -> object:
    return QtCore.QMetaObject.invokeMethod(
        obj, name, QtCore.Q_RETURN_ARG("QVariant"),
        *[QtCore.Q_ARG("QVariant", a) for a in args],
    )


def main() -> None:
    shots = Path(sys.argv[1]) if len(sys.argv) > 1 else None
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

    def items(item: QtQuick.QQuickItem) -> list:
        found = [item]
        for c in item.childItems():
            found += items(c)
        return found

    def child(name: str) -> QtQuick.QQuickItem | None:
        # By the item tree (a Repeater's rows are not QObject children).
        found = (c for c in items(win.contentItem()) if c.objectName() == name)
        return next(found, None)

    out["tool"] = [ev("_tools.sideOf('options')"), ev("_tools.isOpen('options')")]
    # Edit > Button Map Options... opens the pane (on the live map too).
    menu = ev("(function(){ var m = _editMenu; for (var i = 0; i < m.count; i++) {"
              " var it = m.itemAt(i); if (it && it.text === 'Button Map Options…')"
              " { it.triggered(); return true } } return false })()")
    QtTest.QTest.qWait(400)
    out["menu"] = menu
    pane = child("optionsPane")
    top_row = child("toolRowTop")
    out["open"] = [ev("_tools.isOpen('options')"), pane.isVisible()]
    # Joined to its tab: reaching the row, starting where the tab does, and
    # only as wide as its settings need.
    tab = child("tool:options")
    pane_at = pane.mapToScene(QtCore.QPointF(0, 0))
    tab_at = tab.mapToScene(QtCore.QPointF(0, 0))
    out["under-top-row"] = round(
        pane_at.y() - top_row.mapToScene(QtCore.QPointF(0, top_row.height())).y())
    # Under its tab (shifted left to stay in the window when the tab is near
    # the right side).
    out["at-tab"] = (pane_at.x() <= tab_at.x() + 0.5
                     and tab_at.x() + tab.width() <= pane_at.x() + pane.width() + 0.5)
    out["narrower"] = pane.width() < win.width() - 40
    out["groups"] = [
        g for g in ("labels", "editing", "autosave", "view", "colours", "library")
        if child("optionsGroup:" + g) is not None
    ]

    def rows() -> list:
        return sorted(
            c.objectName()[len("option:"):]
            for c in items(pane)
            if c.objectName().startswith("option:") and c.isVisible()
        )

    out["labels-rows"] = rows()
    # A switch changes and keeps its setting.
    before = ev("_opts.values['description-first']")
    row = child("option:description-first")
    switch = next(c for c in row.childItems()
                  if c.metaObject().className().startswith("Switch") and c.isVisible())
    centre = switch.mapToScene(QtCore.QPointF(switch.width() / 2, switch.height() / 2))
    QtTest.QTest.mouseClick(win, QtCore.Qt.MouseButton.LeftButton,
                            QtCore.Qt.KeyboardModifier.NoModifier, centre.toPoint())
    QtTest.QTest.qWait(300)
    out["switch"] = [before, ev("_opts.values['description-first']"),
                     button_map_options.value("description-first")]
    # Another group: its settings; kept for next time.
    group = child("optionsGroup:editing")
    centre = group.mapToScene(QtCore.QPointF(group.width() / 2, group.height() / 2))
    QtTest.QTest.mouseClick(win, QtCore.Qt.MouseButton.LeftButton,
                            QtCore.Qt.KeyboardModifier.NoModifier, centre.toPoint())
    QtTest.QTest.qWait(300)
    out["editing-rows"] = rows()
    out["kept-group"] = button_map_options.ButtonMapOptions().paneGroup
    if shots is not None:
        shots.mkdir(parents=True, exist_ok=True)
        win.grabWindow().save(str(shots / "options-pane.png"))
    ev("_opts.paneGroup = 'library'")
    QtTest.QTest.qWait(300)
    library = [c for c in items(pane)
               if c.metaObject().className().startswith("OptionButtonMapLibrary")]
    out["library"] = bool(library) and library[0].isVisible()

    # Its right edge makes it wider (unlocked), kept for next time.
    ev("_opts.paneGroup = 'labels'")
    QtTest.QTest.qWait(300)
    before = pane.width()
    at = pane.mapToScene(QtCore.QPointF(pane.width() - 2, pane.height() / 2))
    Button = QtCore.Qt.MouseButton
    none = QtCore.Qt.KeyboardModifier.NoModifier
    QtTest.QTest.mousePress(win, Button.LeftButton, none, at.toPoint())
    for i in range(1, 9):
        p = at + QtCore.QPointF(5 * i, 0)
        move = QtGui.QMouseEvent(QtCore.QEvent.Type.MouseMove, p, p, Button.NoButton,
                                 Button.LeftButton, none)
        QtCore.QCoreApplication.sendEvent(win, move)
        QtTest.QTest.qWait(15)
    QtTest.QTest.mouseRelease(win, Button.LeftButton, none,
                              (at + QtCore.QPointF(40, 0)).toPoint())
    QtTest.QTest.qWait(300)
    out["wider"] = round(pane.width() - before)
    out["size-kept"] = ev("JSON.stringify(_tools.sizeOf('options'))")
    # --- floating ---------------------------------------------------------------
    def drag(a: QtCore.QPointF, b: QtCore.QPointF, steps: int = 10) -> None:
        QtTest.QTest.mousePress(win, Button.LeftButton, none, a.toPoint())
        QtTest.QTest.qWait(30)
        for i in range(1, steps + 1):
            p = a + (b - a) * (i / steps)
            move = QtGui.QMouseEvent(QtCore.QEvent.Type.MouseMove, p, p,
                                     Button.NoButton, Button.LeftButton, none)
            QtCore.QCoreApplication.sendEvent(win, move)
            QtTest.QTest.qWait(15)
        QtTest.QTest.mouseRelease(win, Button.LeftButton, none, b.toPoint())
        QtTest.QTest.qWait(300)

    def rect(item: QtQuick.QQuickItem) -> list:
        p = item.mapToScene(QtCore.QPointF(0, 0))
        return [round(p.x()), round(p.y()), round(item.width()), round(item.height())]

    def at(item: QtQuick.QQuickItem, fx: float, fy: float) -> QtCore.QPointF:
        return item.mapToScene(QtCore.QPointF(item.width() * fx, item.height() * fy))

    host = child("_mapHost") or pane.parentItem()
    ev("_tools.setOpen('options', false)")
    QtTest.QTest.qWait(200)
    # The tab dragged off its row onto the map: its panel floats there.
    tab = child("tool:options")
    drop = at(host, 0.4, 0.45)
    drag(tab.mapToScene(QtCore.QPointF(10, tab.height() / 2)), drop)
    out["floated"] = [ev("_tools.isFloating('options')"), pane.isVisible(),
                      ev("_tools.sideOf('options')")]
    title = child("paneTitle")
    out["title"] = [title.isVisible(), child("panePin") is not None,
                    child("paneLock") is not None, child("paneClose") is not None]
    first = rect(pane)
    # Where it was let go (kept inside the map area).
    out["near-drop"] = [first[0] <= drop.x() <= first[0] + first[2],
                        first[1] <= drop.y() <= first[1] + first[3]]
    # Its title bar moves it.
    start = at(title, 0.3, 0.5)
    drag(start, start + QtCore.QPointF(-50, 30))
    moved = rect(pane)
    out["moved"] = [moved[0] - first[0], moved[1] - first[1]]
    # Its corner and its left edge resize it.
    corner = child("floatGripBottomRight")
    start = at(corner, 0.5, 0.5)
    drag(start, start + QtCore.QPointF(40, 30))
    grown = rect(pane)
    out["corner"] = [grown[2] - moved[2], grown[3] - moved[3]]
    edge = child("floatGripLeft")
    start = at(edge, 0.5, 0.5)
    drag(start, start - QtCore.QPointF(30, 0))
    left = rect(pane)
    out["left-edge"] = [left[0] - grown[0], left[2] - grown[2]]
    # Locked: the title bar doesn't move it.
    ev("_tools.setLocked('options', true)")
    QtTest.QTest.qWait(100)
    start = at(title, 0.3, 0.5)
    drag(start, start + QtCore.QPointF(60, 0))
    out["locked-still"] = rect(pane) == left
    ev("_tools.setLocked('options', false)")
    # Closed and opened again from its tab: in the same place.
    close = child("paneClose")
    QtTest.QTest.mouseClick(win, Button.LeftButton, none, at(close, 0.5, 0.5).toPoint())
    QtTest.QTest.qWait(200)
    out["closed"] = [pane.isVisible(), ev("_tools.isFloating('options')")]
    tab = child("tool:options")
    on_tab = tab.mapToScene(QtCore.QPointF(10, tab.height() / 2)).toPoint()
    QtTest.QTest.mouseClick(win, Button.LeftButton, none, on_tab)
    QtTest.QTest.qWait(300)
    out["reopened-same"] = pane.isVisible() and rect(pane) == left
    out["tab-mark"] = child("floatMark") is not None and child("floatMark").isVisible()
    # Kept: loaded again, still floating where it was.
    ev("_tools._load()")
    QtTest.QTest.qWait(200)
    out["kept-floating"] = [ev("_tools.isFloating('options')"),
                            ev("JSON.stringify(_tools.floatPos('options'))")]
    ev("_tools.setOpen('options', true)")
    QtTest.QTest.qWait(200)
    # Its title bar dropped on the bottom row: docked there.
    bottom_row = child("toolRowBottom")
    start = at(title, 0.3, 0.5)
    drag(start, at(bottom_row, 0.2, 0.5), 14)
    def place() -> list:
        return [ev("_tools.isFloating('options')"), ev("_tools.sideOf('options')")]

    out["docked-bottom"] = place()
    # Float from its tab's menu, then double-click the title: back to its row.
    ev("_tools.setFloating('options', true)")
    QtTest.QTest.qWait(300)
    title = child("paneTitle")
    on_title = at(title, 0.3, 0.5).toPoint()
    QtTest.QTest.mouseDClick(win, Button.LeftButton, none, on_title)
    QtTest.QTest.qWait(300)
    out["double-click"] = place()
    # Print Area has no panel: it never floats.
    out["print-area"] = [ev("_tools.canFloat('printArea')"),
                         ev("_tools.canFloat('layers')")]
    ev("_tools.setFloating('printArea', true)")
    out["print-area-floating"] = ev("_tools.isFloating('printArea')")
    # Reset Tool Rows: nothing floats.
    ev("_tools.setFloating('options', true)")
    ev("_tools.resetPlaces()")
    QtTest.QTest.qWait(200)
    out["reset"] = [ev("_tools.isFloating('options')"), ev("_tools.sideOf('options')")]
    print("RESULT " + json.dumps(out), flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()
