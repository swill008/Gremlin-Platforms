# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Loads qml/SidePanel.qml off-screen in test/unit/qml/SidePanelHarness.qml
(two side panels round a stand-in map) and drives it with mouse clicks,
drags and moves (hover); prints "RESULT <json>" with what shows after each
step, "WARN ..." for each QML warning, then "done". test_side_panel.py runs
it in its own process.

    python test/unit/side_panel_smoke.py [folded-hover.png [open.png]]

SIDE_PANEL_HARNESS names another harness file (a copy importing an older
SidePanel, to show the tests fail on it).
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
    harness = os.environ.get("SIDE_PANEL_HARNESS") or str(
        ROOT / "test" / "unit" / "qml" / "SidePanelHarness.qml")
    engine.load(QtCore.QUrl.fromLocalFile(harness))
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
    mp = win.findChild(QtQuick.QQuickItem, "map")
    out: dict = {}

    def child(panel: QtQuick.QQuickItem, name: str) -> QtQuick.QQuickItem:
        return panel.findChild(QtQuick.QQuickItem, name)

    def centre(item: QtQuick.QQuickItem) -> QtCore.QPoint:
        mid = QtCore.QPointF(item.width() / 2, item.height() / 2)
        return item.mapToScene(mid).toPoint()

    def click_at(p: QtCore.QPoint) -> None:
        QtTest.QTest.mouseClick(quick, Button.LeftButton, NoMod, p)
        # Past the panel's slide (about 0.12 s).
        QtTest.QTest.qWait(250)

    def click(item: QtQuick.QQuickItem) -> None:
        click_at(centre(item))

    def tap(item: QtQuick.QQuickItem) -> None:
        # A click with no wait after it: what shows at once.
        QtTest.QTest.mouseClick(quick, Button.LeftButton, NoMod, centre(item))

    def move(p: QtCore.QPoint) -> None:
        QtTest.QTest.mouseMove(quick, p)
        QtTest.QTest.qWait(250)

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

    def scene_x(item: QtQuick.QQuickItem) -> int:
        return round(item.mapToScene(QtCore.QPointF(0, 0)).x())

    def frame(panel: QtQuick.QQuickItem) -> list:
        """The drawer's frame in the scene: [left, right] edges."""
        body = child(panel, "sidePanelBody")
        x = body.mapToScene(QtCore.QPointF(0, 0)).x()
        return [round(x), round(x + body.width())]

    def shown_from_edge(panel: QtQuick.QQuickItem) -> int:
        """How much of the drawer is out of its window edge."""
        lo, hi = frame(panel)
        if panel.property("side") == "right":
            return round(win.property("width")) - max(lo, 0)
        return min(hi, round(win.property("width")))

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
            "out": shown_from_edge(panel),
        }

    def look(tag: str) -> None:
        out[tag] = {
            "left": state(left), "right": state(right),
            "map": [round(mp.x()), round(mp.width())],
            "leftChanged": win.property("leftChanged"),
            "rightChanged": win.property("rightChanged"),
        }

    def safe(fn):  # noqa: ANN001, ANN202
        # A part missing (an older SidePanel): None, so the tests fail on
        # their asserts rather than here.
        def wrapped(*args):  # noqa: ANN002, ANN202
            try:
                return fn(*args)
            except (AttributeError, TypeError, RuntimeError):
                return None
        return wrapped

    @safe
    def edge(panel: QtQuick.QQuickItem) -> dict:
        """The folded drawer: its own frame, ajar on its window edge."""
        fr = panel.findChild(QtQuick.QQuickItem, "sideFrame")
        return {
            "frame": frame(panel),
            "out": shown_from_edge(panel),
            "frameVisible": fr.isVisible(),
            "border": QtQml.QQmlProperty(fr, "border.width").read(),
            "radius": [round(fr.property("topLeftRadius")),
                       round(fr.property("topRightRadius"))],
            "header": child(panel, "sideTitle").isVisible(),
            "slice": round(child(panel, "sideSlice").property("opacity"), 2),
        }

    @safe
    def hover_state(panel: QtQuick.QQuickItem) -> dict:
        title = child(panel, "sideStripTitle")
        pin = child(panel, "sideStripPin")
        return {
            "out": shown_from_edge(panel),
            "hoverWidth": round(panel.property("hoverWidth")),
            "slice": round(child(panel, "sideSlice").property("opacity"), 2),
            "title": [title.property("text"), title.property("font").bold(),
                      title.isVisible()],
            "pin": [pin.property("text"), pin.isVisible()],
            "pinInSlice": shown_from_edge(panel) >= (
                round(pin.mapToScene(QtCore.QPointF(pin.width(), 0)).x())
                if panel.property("side") != "right"
                else round(win.property("width"))
                - round(pin.mapToScene(QtCore.QPointF(0, 0)).x())),
            "areaCursor": int(
                child(panel, "sideStripArea").property("cursorShape").value),
            "windowCursor": int(quick.cursor().shape().value),
            "takenWidth": round(panel.property("takenWidth")),
            "open": panel.property("open"),
            "pinned": panel.property("pinned"),
            "map": [round(mp.x()), round(mp.width())],
        }

    # Folded: each drawer's own frame left ajar on its window edge.
    look("0-folded")
    out["edge"] = {"left": edge(left), "right": edge(right)}

    # Hover each folded drawer with the mouse: it slides out further and
    # shows its bold name and pin, with a hand pointer; the layout stays.
    out["hover"] = {}
    off = QtCore.QPoint(500, 300)
    for name, panel in (("left", left), ("right", right)):
        move(off)
        before = hover_state(panel)
        strip = child(panel, "sideStrip")
        move(centre(strip))
        over = hover_state(panel)
        out["hover"][name] = {"before": before, "over": over}
    if len(sys.argv) > 1:
        quick.grabWindow().save(sys.argv[1])
    # The slice's pin pins without opening (Layers, unpinned): twice, back
    # to unpinned.
    pins = []
    for _ in range(2):
        try:
            click(child(right, "sideStripPin"))
        except AttributeError:
            pass
        pins.append([right.property("pinned"), right.property("open"),
                     round(right.property("takenWidth"))])
    out["hover"]["slicePin"] = pins
    move(off)
    out["hover"]["after"] = hover_state(right)

    # Click the left drawer: Chips (pinned) slides all the way out at its
    # width. What the window reads is final at once; the drawer slides.
    body = child(left, "sidePanelBody")
    move(centre(child(left, "sideStrip")))
    tap(child(left, "sideStrip"))
    slide = {"takenAtOnce": round(left.property("takenWidth")),
             "widthAtOnce": round(left.width()),
             "mapAtOnce": round(mp.x()),
             "bodyX": [scene_x(body)]}
    QtTest.QTest.qWait(40)
    slide["bodyX"].append(scene_x(body))
    slide["takenMid"] = round(left.property("takenWidth"))
    QtTest.QTest.qWait(250)
    slide["bodyX"].append(scene_x(body))
    look("1-left-unfolded")
    out["openHeader"] = {"title": child(left, "sideTitle").isVisible(),
                         "pin": child(left, "sidePin").isVisible(),
                         "fold": child(left, "sideFold").isVisible()}
    # Click the right drawer: Layers (unpinned) slides out over the map.
    rbody = child(right, "sidePanelBody")
    before_open = win.property("rightChanged")
    tap(child(right, "sideStrip"))
    slide["rightXAtOnce"] = round(right.x())
    slide["rightTakenAtOnce"] = round(right.property("takenWidth"))
    slide["rightBodyX"] = [scene_x(rbody)]
    QtTest.QTest.qWait(40)
    slide["rightBodyX"].append(scene_x(rbody))
    QtTest.QTest.qWait(250)
    slide["rightBodyX"].append(scene_x(rbody))
    look("2-right-overlay")
    if len(sys.argv) > 2:
        quick.grabWindow().save(sys.argv[2])
    # A click on the map: Layers folds, Chips (pinned) stays.
    click_at(QtCore.QPoint(450, 300))
    look("3-map-click")
    out["3-map-click"]["rightChangedSinceOpen"] = (
        win.property("rightChanged") - before_open)
    # Unpin Chips with its pin; then a map click folds it.
    click(child(left, "sidePin"))
    look("4-left-unpinned")
    click_at(QtCore.QPoint(700, 300))
    look("5-map-click-left")
    # Unfold, pin, then fold with the arrow: it slides back to the ajar edge.
    click(child(left, "sideStrip"))
    click(child(left, "sidePin"))
    look("6-left-pinned")
    move(off)
    tap(child(left, "sideFold"))
    slide["foldTakenAtOnce"] = round(left.property("takenWidth"))
    slide["foldMapAtOnce"] = round(mp.x())
    QtTest.QTest.qWait(40)
    slide["foldMid"] = frame(left)[1]
    QtTest.QTest.qWait(250)
    slide["foldEnd"] = frame(left)[1]
    slide["foldHeader"] = child(left, "sideTitle").isVisible()
    out["slide"] = slide
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
    # Clicking one drawer folds the other if it is unpinned: Chips folded by
    # its arrow (Layers stays out), then its drawer clicked.
    left.setProperty("pinned", False)
    QtTest.QTest.qWait(50)
    click(child(left, "sideFold"))
    look("13-left-folded-right-stays")
    click(child(left, "sideStrip"))
    look("13-left-strip-folds-right")
    # Setting the properties directly (a restore) doesn't emit changed().
    before = (win.property("leftChanged"), win.property("rightChanged"))
    left.setProperty("open", True)
    left.setProperty("pinned", True)
    left.setProperty("panelWidth", 222)
    right.setProperty("open", True)
    QtTest.QTest.qWait(300)
    out["14-direct-sets"] = [win.property("leftChanged") - before[0],
                             win.property("rightChanged") - before[1]]
    look("14-restored")
    # available false hides it, ajar edge and all, and it takes no width.
    left.setProperty("available", False)
    QtTest.QTest.qWait(50)
    look("15-unavailable")
    left.setProperty("available", True)
    QtTest.QTest.qWait(300)
    look("16-available")
    print("RESULT " + json.dumps(out), flush=True)
    for w in warnings:
        print(f"WARN {w}", flush=True)
    print("done", flush=True)
    smoke_exit(0)


if __name__ == "__main__":
    main()
