# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Loads qml/SidePanel.qml off-screen in test/unit/qml/SidePanelHarness.qml
(two side panels round a stand-in map) and drives it with mouse clicks and
drags; prints "RESULT <json>" with what shows after each step, "WARN ..."
for each QML warning, then "done". test_side_panel.py runs it in its own
process.

    python test/unit/side_panel_smoke.py [screenshot.png]
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QT_QUICK_CONTROLS_STYLE"] = "GremlinStyle"
os.environ["QT_FILE_SELECTORS"] = "Universal"
os.environ.setdefault(
    "QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
)
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import shiboken6  # noqa: E402
from PySide6 import QtCore, QtGui, QtQml, QtQuick, QtTest  # noqa: E402
from smoke_exit import smoke_exit  # noqa: E402

Button = QtCore.Qt.MouseButton
NoMod = QtCore.Qt.KeyboardModifier.NoModifier


class FakeBackend(QtCore.QObject):
    uiScaleChanged = QtCore.Signal()
    uiScale = QtCore.Property(int, fget=lambda self: 100, notify=uiScaleChanged)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    app = QtGui.QGuiApplication(sys.argv[:1])  # noqa: F841  (kept alive)
    QtGui.QFontDatabase.addApplicationFont(str(ROOT / "gfx" / "bootstrap-icons.otf"))
    QtQml.qmlRegisterSingletonType(
        QtCore.QUrl.fromLocalFile(str(ROOT / "qml" / "Style.qml")),
        "Gremlin.Style", 1, 0, "Style",
    )
    engine = QtQml.QQmlApplicationEngine()
    engine.addImportPath(str(ROOT / "theme"))
    backend = FakeBackend()
    engine.rootContext().setContextProperty("backend", backend)
    warnings: list[str] = []
    engine.warnings.connect(lambda ws: warnings.extend(w.toString() for w in ws))
    engine.load(QtCore.QUrl.fromLocalFile(
        str(ROOT / "test" / "unit" / "qml" / "SidePanelHarness.qml")))
    roots = engine.rootObjects()
    if not roots:
        for w in warnings:
            print(f"WARN {w}", flush=True)
        print("ERROR window did not load", flush=True)
        smoke_exit(1)
    win = roots[0]
    quick = shiboken6.wrapInstance(
        shiboken6.getCppPointer(win)[0], QtQuick.QQuickWindow
    )
    QtTest.QTest.qWait(300)
    left = win.findChild(QtQuick.QQuickItem, "leftPanel")
    right = win.findChild(QtQuick.QQuickItem, "rightPanel")
    out: dict = {}

    def child(panel: QtQuick.QQuickItem, name: str) -> QtQuick.QQuickItem:
        return panel.findChild(QtQuick.QQuickItem, name)

    def centre(item: QtQuick.QQuickItem) -> QtCore.QPoint:
        mid = QtCore.QPointF(item.width() / 2, item.height() / 2)
        return item.mapToScene(mid).toPoint()

    def click_at(p: QtCore.QPoint) -> None:
        QtTest.QTest.mouseClick(quick, Button.LeftButton, NoMod, p)
        QtTest.QTest.qWait(80)

    def click(item: QtQuick.QQuickItem) -> None:
        click_at(centre(item))

    def drag(item: QtQuick.QQuickItem, dx: int) -> None:
        start = centre(item)
        QtTest.QTest.mousePress(quick, Button.LeftButton, NoMod, start)
        for i in range(1, 11):
            at = QtCore.QPoint(start.x() + dx * i // 10, start.y())
            QtTest.QTest.mouseMove(quick, at)
            QtTest.QTest.qWait(10)
        QtTest.QTest.mouseRelease(quick, Button.LeftButton, NoMod,
                                  QtCore.QPoint(start.x() + dx, start.y()))
        QtTest.QTest.qWait(80)

    def state(panel: QtQuick.QQuickItem) -> dict:
        body = child(panel, "sidePanelBody")
        return {
            "open": panel.property("open"),
            "pinned": panel.property("pinned"),
            "overlay": panel.property("overlay"),
            "visible": panel.isVisible(),
            "panelWidth": round(panel.property("panelWidth")),
            "bodyWidth": round(body.width()) if body.isVisible() else 0,
            "takenWidth": round(panel.property("takenWidth")),
            "x": round(panel.x()),
            "width": round(panel.width()),
        }

    def look(tag: str) -> None:
        mp = win.findChild(QtQuick.QQuickItem, "map")
        out[tag] = {
            "left": state(left), "right": state(right),
            "map": [round(mp.x()), round(mp.width())],
            "leftChanged": win.property("leftChanged"),
            "rightChanged": win.property("rightChanged"),
        }

    # Folded: the strips and their vertical titles.
    look("0-folded")
    lt = child(left, "sideStripTitle")
    rt = child(right, "sideStripTitle")
    out["strip"] = {
        "width": round(child(left, "sideStrip").width()),
        "left": [lt.property("text"), lt.property("rotation"), lt.isVisible()],
        "right": [rt.property("text"), rt.property("rotation"), rt.isVisible()],
    }
    # Click the left strip: Chips (pinned) unfolds beside the map.
    click(child(left, "sideStrip"))
    look("1-left-unfolded")
    # Click the right strip: Layers (unpinned) slides out over the map.
    click(child(right, "sideStrip"))
    look("2-right-overlay")
    # A click on the map: Layers folds, Chips (pinned) stays.
    click_at(QtCore.QPoint(450, 300))
    look("3-map-click")
    # Unpin Chips with its pin; then a map click folds it.
    click(child(left, "sidePin"))
    look("4-left-unpinned")
    click_at(QtCore.QPoint(700, 300))
    look("5-map-click-left")
    # Unfold, pin, then fold with the arrow.
    click(child(left, "sideStrip"))
    click(child(left, "sidePin"))
    look("6-left-pinned")
    click(child(left, "sideFold"))
    look("7-left-fold-arrow")
    # Resize by the inner edge: wider, past the maximum, past the minimum.
    click(child(left, "sideStrip"))
    drag(child(left, "sideGrip"), 60)
    look("8-left-wider")
    drag(child(left, "sideGrip"), 500)
    look("9-left-max")
    drag(child(left, "sideGrip"), -350)
    look("10-left-min")
    # The right panel's inner edge is on its left: dragged left, it widens.
    click(child(right, "sideStrip"))
    drag(child(right, "sideGrip"), -50)
    look("11-right-wider")
    # A press on the open panel's content doesn't reach the map.
    clicks = win.property("mapClicks")
    click(child(right, "sideContent"))
    out["12-content-click"] = {"mapClicks": win.property("mapClicks") - clicks,
                               "open": right.property("open")}
    # Clicking one strip folds the other if it is unpinned.
    left.setProperty("pinned", False)
    QtTest.QTest.qWait(50)
    click(child(left, "sideStrip"))
    look("13-left-strip-folds-right")
    # Setting the properties directly (a restore) doesn't emit changed().
    before = (win.property("leftChanged"), win.property("rightChanged"))
    left.setProperty("open", True)
    left.setProperty("pinned", True)
    left.setProperty("panelWidth", 222)
    right.setProperty("open", True)
    QtTest.QTest.qWait(50)
    out["14-direct-sets"] = [win.property("leftChanged") - before[0],
                             win.property("rightChanged") - before[1]]
    look("14-restored")
    # available false hides it, strip and all, and it takes no width.
    left.setProperty("available", False)
    QtTest.QTest.qWait(50)
    look("15-unavailable")
    left.setProperty("available", True)
    QtTest.QTest.qWait(50)
    look("16-available")
    if len(sys.argv) > 1:
        quick.grabWindow().save(sys.argv[1])
    print("RESULT " + json.dumps(out), flush=True)
    for w in warnings:
        print(f"WARN {w}", flush=True)
    print("done", flush=True)
    smoke_exit(0)


if __name__ == "__main__":
    main()
