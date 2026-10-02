# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Drives the Button Map editor off-screen through a fixed session.

Run in its own process (Qt teardown inside the test session can hang):

    python test/unit/rig_editor_harness.py <scenario> <out_dir>

Writes <out_dir>/<scenario>.json (editor state after every step) and a PNG
per checkpoint. test_rig_editor_golden.py compares them with the goldens.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# The offscreen platform finds no fonts by itself; text would draw as boxes.
os.environ.setdefault(
    "QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
)

import shiboken6  # noqa: E402
from PySide6 import (  # noqa: E402
    QtCore,
    QtGui,
    QtQml,
    QtQuick,
    QtTest,
)

ROOT = Path(__file__).resolve().parents[2]
QML = ROOT / "qml"
# Fixed copies of the two Gladiator layouts, so the goldens never move with
# the user's own module files.
LAYOUTS = {
    name: Path(__file__).parent / "rig_editor_golden" / "layouts" / f"{name}.json"
    for name in ("evo_r", "evo_l", "legacy")
}

_HOST = b"""
import QtQuick
import QtQuick.Window

Window {
    id: _win
    width: 1600
    height: 900
    visible: true
    color: "#202020"

    VkbRigFace { id: _face; anchors.fill: parent }

    // The Layers panel, as the Button Map window places it; shown only by
    // scenarios that use it, so other screenshots are unchanged.
    RigLayersPanel {
        id: _layers
        ed: _face.editorItem
        visible: false
        width: 260
        x: parent.width - width - 12
        y: 12
        height: parent.height - 24
        z: 50
    }
    function showLayers(on) { _layers.visible = on }
    function layerLines() {
        return JSON.stringify(_layers.visible ? _layers.describe() : [])
    }
    function layerRowRect(i) { return JSON.stringify(_layers.rowRect(i)) }
    function layerRowIndex(text) {
        var rows = _layers.rows
        for (var i = 0; i < rows.length; i++) {
            if (rows[i].name === text)
                return i
        }
        return -1
    }
    function setLayerFilter(f) { _layers.filter = f }
    function openLayer(id) { _layers.toggleOpen(id) }

    function ed() { return _face.editorItem }
    function setNodes(json) { _face.editorNodes = JSON.parse(json) }
    function setEditing(on) { _face.editing = on }
    // Whole page in view: zoomed fully out, no pan.
    function resetView() {
        _face.zoom = _face.zoomMin
        _face.panX = 0
        _face.panY = 0
        _face.pingEditor()
    }
    // Keys live on the editor's full-size mouse area, which takes focus when
    // the canvas is clicked; focus it the same way.
    function _pointerArea(item) {
        for (var i = 0; i < item.children.length; i++) {
            var c = item.children[i]
            if (c.preventStealing !== undefined && c.hoverEnabled !== undefined)
                return c
            var inner = _pointerArea(c)
            if (inner)
                return inner
        }
        return null
    }
    function focusEditor() {
        var area = _pointerArea(ed())
        if (area)
            area.forceActiveFocus()
    }
    function call(name, argsJson) {
        var e = ed()
        var r = e[name].apply(e, JSON.parse(argsJson))
        return JSON.stringify(r === undefined ? null : r)
    }
    // The open right-click menu as text lines (title, rows, open section);
    // empty when none is open.
    function menuLines() { return ed().menuLines() }
    function closeMenus() { ed().closeMenu() }
    function menuRowRect(text) { return JSON.stringify(ed().menuRowRect(text)) }
    function menuBox() { return JSON.stringify(ed().menuBox()) }
    function resize(w, h) { _win.width = w; _win.height = h }
    // Call with the live node object as the first argument (not a JSON copy).
    function callOnNode(name, id, argsJson) {
        var e = ed()
        var r = e[name].apply(e, [e.nodeAt(id)].concat(JSON.parse(argsJson)))
        return JSON.stringify(r === undefined ? null : r)
    }
    function setProp(name, json) { ed()[name] = JSON.parse(json) }
    function state() {
        var e = ed()
        return JSON.stringify({
            menu: menuLines(),
            layers: JSON.parse(layerLines()),
            photo: [e.photoScale, e.photoOffX, e.photoOffY, e.photoRot],
            nodes: e.nodes,
            selected: e.selectedIds,
            histAt: e.histAt,
            histLen: e.hist ? e.hist.length : 0,
            drawTool: e.drawTool
        })
    }
    // Window position of a page fraction, and of an editor-local point.
    function pagePt(fx, fy) {
        var e = ed()
        var p = e.mapToItem(null, e.fxToX(fx), e.fyToY(fy))
        return JSON.stringify([p.x, p.y])
    }
    function edPt(x, y) {
        var p = ed().mapToItem(null, x, y)
        return JSON.stringify([p.x, p.y])
    }
    function geom(id) { return JSON.stringify(ed().nodeBox(ed().nodeAt(id))) }
    // A drawing's point in its own frame (turned, flipped) in window pixels.
    function drawPt(id, lx, ly) {
        var e = ed()
        var it = e._chipsItem(e.nodeIndex(id))
        var p = it.mapToItem(null, lx, ly)
        return JSON.stringify([p.x, p.y, it.width, it.height])
    }
}
"""


class FakeBackend(QtCore.QObject):
    uiScaleChanged = QtCore.Signal()

    def _scale(self) -> int:
        return 100

    uiScale = QtCore.Property(int, fget=_scale, notify=uiScaleChanged)


class Session:
    def __init__(self, out_dir: Path, name: str) -> None:
        self.out_dir = out_dir
        self.name = name
        self.steps: list[dict] = []
        self.app = QtGui.QGuiApplication(sys.argv[:1])
        # The app's default font (JoystickGremlinApp sets it). Left unset, Qt's
        # fallback choice varies between runs and so would the screenshots.
        font = QtGui.QFont("Segoe UI")
        font.setPixelSize(15)
        self.app.setFont(font)
        # The app loads the icon font at start; the Layers panel uses it.
        QtGui.QFontDatabase.addApplicationFont(
            str(ROOT / "gfx" / "bootstrap-icons.otf")
        )
        QtQml.qmlRegisterSingletonType(
            QtCore.QUrl.fromLocalFile(str(QML / "Style.qml")),
            "Gremlin.Style",
            1,
            0,
            "Style",
        )
        self.backend = FakeBackend()
        self.engine = QtQml.QQmlApplicationEngine()
        self.engine.addImportPath(str(ROOT / "theme"))
        self.engine.rootContext().setContextProperty("backend", self.backend)
        self.warnings: list[str] = []
        # Not qInstallMessageHandler: a Python handler deadlocks while QML
        # compiles on Qt's loader thread.
        self.engine.warnings.connect(self._on_warnings)
        self.engine.loadData(_HOST, QtCore.QUrl.fromLocalFile(str(QML / "_host.qml")))
        roots = self.engine.rootObjects()
        if not roots:
            raise SystemExit("host failed to load: " + "; ".join(self.warnings))
        self.win = shiboken6.wrapInstance(
            shiboken6.getCppPointer(roots[0])[0], QtQuick.QQuickWindow
        )
        self.win.requestActivate()
        QtTest.QTest.qWaitForWindowActive(self.win, 2000)
        self.wait(200)

    def _on_warnings(self, errors: list) -> None:
        self.warnings.extend(e.toString() for e in errors)

    # --- plumbing ---------------------------------------------------------

    def wait(self, ms: int = 120) -> None:
        QtTest.QTest.qWait(ms)

    def js(self, fn: str, *args: object) -> object:
        result = QtCore.QMetaObject.invokeMethod(
            self.win,
            fn,
            QtCore.Q_RETURN_ARG("QVariant"),
            *[QtCore.Q_ARG("QVariant", a) for a in args],
        )
        return result

    def call(self, name: str, *args: object) -> object:
        out = self.js("call", name, json.dumps(list(args)))
        self.wait(30)
        return json.loads(out)

    def call_on_node(self, name: str, id_: str, *args: object) -> object:
        out = self.js("callOnNode", name, id_, json.dumps(list(args)))
        self.wait(30)
        return json.loads(out)

    def set_prop(self, name: str, value: object) -> None:
        self.js("setProp", name, json.dumps(value))
        self.wait(30)

    def point(self, fx: float, fy: float) -> QtCore.QPoint:
        x, y = json.loads(self.js("pagePt", fx, fy))
        return QtCore.QPoint(round(x), round(y))

    def ed_point(self, x: float, y: float) -> QtCore.QPoint:
        wx, wy = json.loads(self.js("edPt", x, y))
        return QtCore.QPoint(round(wx), round(wy))

    def _box(self, id_: str) -> dict:
        return json.loads(self.js("geom", id_))

    def center(self, id_: str, dx: float = 0, dy: float = 0) -> QtCore.QPoint:
        """Window point at the middle of a node's box, moved by dx/dy pixels."""
        b = self._box(id_)
        return self.ed_point(b["x"] + b["w"] / 2 + dx, b["y"] + b["h"] / 2 + dy)

    def corner(self, id_: str, dx: float = 0, dy: float = 0) -> QtCore.QPoint:
        """Window point at a node's bottom-right corner (its resize handle)."""
        b = self._box(id_)
        return self.ed_point(b["x"] + b["w"] + dx, b["y"] + b["h"] + dy)

    def node(self, id_: str) -> dict:
        return next(n for n in self.state()["nodes"] if n["id"] == id_)

    def state(self) -> dict:
        return json.loads(self.js("state"))

    # --- input ------------------------------------------------------------

    def _mouse(
        self,
        kind: str,
        pos: QtCore.QPoint,
        button: QtCore.Qt.MouseButton | None = None,
        mods: QtCore.Qt.KeyboardModifier | None = None,
    ) -> None:
        button = button or QtCore.Qt.MouseButton.LeftButton
        mods = mods or QtCore.Qt.KeyboardModifier.NoModifier
        getattr(QtTest.QTest, kind)(self.win, button, mods, pos)

    def right_click(self, pos: QtCore.QPoint) -> None:
        self._mouse("mouseClick", pos, button=QtCore.Qt.MouseButton.RightButton)
        self.wait(120)

    def close_menus(self) -> None:
        self.js("closeMenus")
        self.wait(120)

    def click_menu_row(self, text: str) -> None:
        """Clicks the open menu's row that shows this text."""
        r = json.loads(self.js("menuRowRect", text))
        assert r, f"no menu row {text!r}"
        self.click(
            QtCore.QPoint(round(r["x"] + r["w"] / 2), round(r["y"] + r["h"] / 2))
        )

    def menu_key(self, key: QtCore.Qt.Key) -> None:
        """A key press while the menu has focus."""
        QtTest.QTest.keyClick(self.win, key)
        self.wait(60)

    def layer_row(self, name: str) -> dict:
        i = self.js("layerRowIndex", name)
        assert i >= 0, f"no layer row {name!r}"
        return json.loads(self.js("layerRowRect", i))

    def click_layer(self, name: str, part: str = "name") -> None:
        """Clicks a Layers panel row: its name, or its "eye" or "lock"."""
        r = self.layer_row(name)
        right = r["x"] + r["w"] - 2
        x = {"lock": right - 11, "eye": right - 35}.get(part, r["x"] + r["w"] / 2)
        self.click(QtCore.QPoint(round(x), round(r["y"] + r["h"] / 2)))

    def type_text(self, text: str) -> None:
        """Types text into whatever has focus (QTest.keyClicks wants a widget)."""
        for ch in text:
            key = QtCore.Qt.Key(ord(ch.upper()))
            for kind in (QtCore.QEvent.Type.KeyPress, QtCore.QEvent.Type.KeyRelease):
                event = QtGui.QKeyEvent(
                    kind, key, QtCore.Qt.KeyboardModifier.NoModifier, ch
                )
                QtCore.QCoreApplication.sendEvent(self.win, event)
        self.wait(60)

    def click(
        self, pos: QtCore.QPoint, mods: QtCore.Qt.KeyboardModifier | None = None
    ) -> None:
        self._mouse("mouseClick", pos, mods=mods)
        self.wait(60)

    def drag(
        self,
        start: QtCore.QPoint,
        end: QtCore.QPoint,
        mods: QtCore.Qt.KeyboardModifier | None = None,
    ) -> None:
        mods = mods or QtCore.Qt.KeyboardModifier.NoModifier
        self._mouse("mousePress", start, mods=mods)
        self.wait(20)
        steps = 6
        for i in range(1, steps + 1):
            p = QtCore.QPoint(
                start.x() + (end.x() - start.x()) * i // steps,
                start.y() + (end.y() - start.y()) * i // steps,
            )
            event = QtGui.QMouseEvent(
                QtCore.QEvent.Type.MouseMove,
                QtCore.QPointF(p),
                QtCore.QPointF(self.win.mapToGlobal(p)),
                QtCore.Qt.MouseButton.NoButton,
                QtCore.Qt.MouseButton.LeftButton,
                mods,
            )
            QtCore.QCoreApplication.sendEvent(self.win, event)
            self.wait(15)
        self._mouse("mouseRelease", end, mods=mods)
        self.wait(80)

    def key(
        self, key: QtCore.Qt.Key, mods: QtCore.Qt.KeyboardModifier | None = None
    ) -> None:
        self.js("focusEditor")
        QtTest.QTest.keyClick(
            self.win, key, mods or QtCore.Qt.KeyboardModifier.NoModifier
        )
        self.wait(60)

    # --- recording --------------------------------------------------------

    def record(self, step: str, image: bool = False) -> None:
        self.wait(150)
        self.steps.append({"step": step, "state": self.state()})
        if image:
            self.win.grabWindow().save(str(self.out_dir / f"{self.name}-{step}.png"))

    def finish(self) -> None:
        doc = {"steps": self.steps, "warnings": sorted(set(self.warnings))}
        path = self.out_dir / f"{self.name}.json"
        path.write_text(json.dumps(doc, indent=1, sort_keys=True), encoding="utf-8")


def _load(s: Session, layout: str) -> None:
    doc = json.loads(LAYOUTS[layout].read_text(encoding="utf-8"))
    s.js("setNodes", json.dumps(doc.get("nodes") or []))
    s.wait(300)
    s.js("resetView")
    s.js("setEditing", True)
    s.wait(300)


def scenario_load_l(s: Session) -> None:
    _load(s, "evo_l")
    s.record("loaded", image=True)


def scenario_session_r(s: Session) -> None:
    """A full editing session on the right stick layout.

    Drawing happens in the empty left (x < 0.28) and right (x > 0.72) thirds of
    the page; chips are aimed at through the editor's own boxes.
    """
    Mod = QtCore.Qt.KeyboardModifier
    Key = QtCore.Qt.Key
    _load(s, "evo_r")
    s.record("loaded", image=True)

    chips = [n["id"] for n in s.state()["nodes"] if n["kind"] == "btn"]
    first, second = chips[0], chips[1]

    # Select by clicking, then drag the chip.
    s.click(s.center(first))
    s.record("click-chip")
    s.drag(s.center(first), s.center(first, dx=40, dy=30))
    s.record("drag-chip")

    # Keyboard nudge, small and grid-sized.
    for _ in range(3):
        s.key(Key.Key_Right)
    s.key(Key.Key_Down, Mod.ShiftModifier)
    s.record("nudge")

    # Shapes: free-drag with the draw tool.
    s.call("setDrawTool", "ellipse")
    s.drag(s.point(0.05, 0.10), s.point(0.15, 0.25))
    s.record("draw-ellipse-drag", image=True)
    ellipse = s.state()["selected"][0]

    s.call("setDrawTool", "rect")
    s.drag(s.point(0.05, 0.35), s.point(0.15, 0.48))
    rect = s.state()["selected"][0]
    s.call("applyField", "fill", "filled")
    s.record("draw-rect-filled")

    # Resize the ellipse from its bottom-right handle.
    s.call("setSelection", [ellipse])
    s.drag(s.corner(ellipse), s.corner(ellipse, dx=60, dy=40))
    s.record("resize-ellipse")

    # Move the rectangle by dragging its body.
    s.call("setSelection", [rect])
    s.drag(s.center(rect), s.center(rect, dx=50, dy=70))
    s.record("move-rect")

    # Style and rotate through the editor's own field setter.
    s.call("applyField", "rot", 90)
    s.call("applyField", "stroke", 4)
    s.call("applyField", "opacity", 0.5)
    s.record("style-rect", image=True)

    # Text box and table with the draw tool.
    s.call("setDrawTool", "text")
    s.drag(s.point(0.75, 0.10), s.point(0.92, 0.18))
    text = s.state()["selected"][0]
    s.record("draw-text")
    s.call("setDrawTool", "table")
    s.drag(s.point(0.74, 0.55), s.point(0.95, 0.85))
    table = s.state()["selected"][0]
    s.record("draw-table", image=True)
    s.call("setDrawTool", "")

    # Right-click menus: chip, text box and table each open their own.
    s.right_click(s.center(second))
    s.record("menu-chip", image=True)
    s.close_menus()
    s.right_click(s.center(text))
    s.record("menu-text")
    s.close_menus()
    s.right_click(s.center(table, dx=-40, dy=-40))
    s.record("menu-table", image=True)
    s.close_menus()

    # Shape around a selected chip.
    s.call("setSelection", [second])
    s.call("addDrawAround", "diamond")
    s.record("draw-around")

    # Group two chips, then break the group.
    s.call("setSelection", [first, second])
    s.call("groupSelection")
    s.record("group")
    s.call("ungroupSelection")
    s.record("ungroup")

    # Duplicate, copy/paste and delete through the editor's keys.
    s.call("setSelection", [rect])
    s.key(Key.Key_D, Mod.ControlModifier)
    s.record("duplicate")
    s.key(Key.Key_C, Mod.ControlModifier)
    s.key(Key.Key_V, Mod.ControlModifier)
    s.record("paste")
    s.key(Key.Key_Delete)
    s.record("delete")

    # Stacking.
    s.call("setSelection", [ellipse])
    s.call("bringForward")
    s.record("bring-forward")
    s.call("sendBack")
    s.record("send-back")

    # Locked items do not move.
    s.call("toggleLock", ellipse)
    s.drag(s.center(ellipse), s.center(ellipse, dx=80))
    s.record("locked-drag")
    s.call("toggleLock", ellipse)

    # Band selection on empty canvas around the ellipse.
    s.call("setSelection", [])
    s.drag(s.point(0.01, 0.02), s.point(0.27, 0.33))
    s.record("band-select")

    # Undo and redo.
    for _ in range(4):
        s.key(Key.Key_Z, Mod.ControlModifier)
    s.record("undo-4")
    s.call("redo")
    s.record("redo-1", image=True)


def scenario_api_sweep(s: Session) -> None:
    """Calls the editor's functions directly, area by area, so code paths the
    mouse session does not reach are covered too."""
    _load(s, "evo_r")
    nodes = s.state()["nodes"]
    chips = [n["id"] for n in nodes if n["kind"] == "btn"]
    stack = next(n["id"] for n in nodes if n["kind"] == "stack")

    # Photo pose.
    s.call("applyPhotoPose", {"scale": 1.5, "offX": 0.1, "offY": -0.1, "rot": 10})
    s.record("photo-pose", image=True)
    s.call("resetPhotoPose")
    s.record("photo-reset")

    # Chip styling.
    s.call("setSelection", [chips[0]])
    s.call("applyField", "color", "#B91C1C")
    s.call("applyField", "chipShape", "square")
    s.call("applyField", "fontSize", 18)
    s.record("chip-style")
    s.call("resetMemberStyle")
    s.record("chip-style-reset")

    # Leaders: add, branch, curve all segments, spines, delete.
    s.call("setSelection", [chips[1]])
    s.call("addLeader")
    s.record("leader-add")
    s.call("addBranch")
    s.record("leader-branch")
    s.call("setAllSegCurve", True)
    s.call_on_node("addCurveSpine", chips[1])
    s.record("leader-curves")
    s.call("clearAllSpines", chips[1])
    s.call("detachEnd", "to")
    s.record("leader-detach")
    s.call("deleteLeader")
    s.record("leader-delete")

    # Group alignment.
    s.call("setSelection", [stack])
    s.call("setAlignH", "center")
    s.record("align-center")
    s.call("setAlignH", "right")
    s.call_on_node("bakeAlignToFree", stack)
    s.record("align-free")

    # Text box formats and themes.
    s.call("setDrawTool", "text")
    s.drag(s.point(0.75, 0.10), s.point(0.92, 0.18))
    s.call("setDrawTool", "")
    text = s.state()["selected"][0]
    s.call("applyTextTheme", "sheet")
    s.call("applyField", "fontSize", 20)
    s.call("copyTextFormat")
    s.call("applyTextBoxSize", 0.2, 0.1)
    s.record("text-theme", image=True)
    s.call("clearTextFormat")
    s.record("text-clear")

    # Tables: rows, columns, id column, theme, font, free cell.
    s.call("setDrawTool", "table")
    s.drag(s.point(0.74, 0.55), s.point(0.95, 0.85))
    s.call("setDrawTool", "")
    table = s.state()["selected"][0]
    s.set_prop("tableRow", 0)
    s.set_prop("tableCol", 0)
    s.call("addTableRow", True)
    s.call("addTableCol", True)
    s.record("table-grow")
    s.call("toggleTableIdCol")
    s.call("setTableTheme", "sheet")
    s.call("setTableFont", 16)
    s.record("table-style", image=True)
    s.call("toggleTableCellFree")
    s.record("table-free-cell")
    s.call("deleteTableRow")
    s.call("deleteTableCol")
    s.record("table-shrink")

    # Image layer with snap points, lock and stacking.
    icon = ROOT / "gfx" / "icon.png"
    s.call("addOverlay", "test/icon", QtCore.QUrl.fromLocalFile(str(icon)).toString())
    overlay = s.state()["selected"][0]
    s.record("overlay-add", image=True)
    b = s._box(overlay)
    s.call_on_node("addSocketAt", overlay, b["x"] + b["w"] / 2, b["y"] + b["h"] / 2)
    s.record("overlay-socket")
    s.call("clearSockets")
    s.call("toggleLock", overlay)
    s.record("overlay-lock")
    s.call("toggleLock", overlay)
    s.call("setSelection", [table])
    s.call("sendBack")
    s.record("table-back")

    # Select everything drawn and delete it.
    s.call("setSelection", [text, table, overlay])
    s.call("deleteSelection")
    s.record("delete-drawn", image=True)


def scenario_arrows(s: Session) -> None:
    """Block arrows, lines and arrows with solid and hollow heads, dashed and
    dotted outlines, dragging a line end and clicking on and beside a line."""
    Mod = QtCore.Qt.KeyboardModifier
    _load(s, "evo_r")

    s.call("setDrawTool", "arrow")
    s.drag(s.point(0.04, 0.06), s.point(0.20, 0.16))
    arrow = s.state()["selected"][0]
    s.call("setDrawTool", "arrow2")
    s.drag(s.point(0.04, 0.24), s.point(0.24, 0.32))
    arrow2 = s.state()["selected"][0]
    s.call("applyField", "fill", "filled")
    s.record("block-arrows", image=True)

    s.call("setDrawTool", "line")
    s.drag(s.point(0.75, 0.08), s.point(0.95, 0.14))
    line = s.state()["selected"][0]
    s.record("line")
    s.call("setDrawTool", "arrowline")
    s.drag(s.point(0.75, 0.24), s.point(0.93, 0.31), Mod.ShiftModifier)
    arrowline = s.state()["selected"][0]
    s.call("setDrawTool", "")
    s.record("arrow-shift-snapped", image=True)

    # Drag the plain line's far end down.
    s.call("setSelection", [line])
    ends = s.call_on_node("lineEndsAt", line)
    s.drag(
        s.ed_point(ends["bx"], ends["by"]),
        s.ed_point(ends["bx"] - 30, ends["by"] + 90),
    )
    s.record("drag-line-end")

    # Heads, outline styles and width.
    s.call("setSelection", [arrowline])
    s.call("applyDrawField", "headStart", "hollow")
    s.call("applyDrawField", "headEnd", "hollow")
    s.call("applyDrawField", "stroke", 6)
    s.record("hollow-heads-thick")
    s.call("applyDrawField", "headEnd", "solid")
    s.call("swapLineHeads")
    s.record("swap-heads")
    s.call("setSelection", [arrow2])
    s.call("applyDrawField", "dash", "dash")
    s.call("setSelection", [line])
    s.call("applyDrawField", "dash", "dot")
    s.call("applyDrawField", "headEnd", "solid")
    s.call("setSelection", [arrow])
    s.call("applyDrawField", "dash", "dot")
    s.record("outlines", image=True)

    # A click on the line selects it; a click inside its box but off the
    # line does not.
    s.call("setSelection", [])
    ends = s.call_on_node("lineEndsAt", line)
    mid_x = (ends["ax"] + ends["bx"]) / 2
    mid_y = (ends["ay"] + ends["by"]) / 2
    s.click(s.ed_point(mid_x, mid_y))
    s.record("click-on-line")
    s.call("setSelection", [])
    box = s._box(line)
    s.click(s.ed_point(box["x"] + box["w"] - 4, box["y"] + 4))
    s.record("click-beside-line")

    s.call("undo")
    s.call("undo")
    s.record("undo-2", image=True)


def scenario_menu(s: Session) -> None:
    """The right-click menu: compact on opening, sections open on a click,
    value rows by keyboard, the last section remembered, canvas tools, and
    staying inside a small window."""
    Key = QtCore.Qt.Key
    _load(s, "evo_r")
    chips = [n["id"] for n in s.state()["nodes"] if n["kind"] == "btn"]

    s.right_click(s.center(chips[0]))
    s.record("chip-compact")
    s.click_menu_row("Chip style")
    s.record("chip-style-open", image=True)
    # Focus starts on the clicked header: down to Size, then step it twice.
    for _ in range(2):
        s.menu_key(Key.Key_Down)
    s.menu_key(Key.Key_Right)
    s.menu_key(Key.Key_Right)
    s.record("chip-size-stepped")
    s.click_menu_row("Hotspot")
    s.record("hotspot-open")
    s.menu_key(Key.Key_Escape)

    # The next chip reopens on the section used last.
    s.right_click(s.center(chips[1]))
    s.record("chip-remembers-section")
    s.close_menus()

    # Canvas: the Draw section, and an action that closes the menu.
    s.right_click(s.point(0.1, 0.5))
    s.record("canvas")
    s.click_menu_row("Draw")
    s.click_menu_row("Import picture…")
    s.record("canvas-action-closes")

    # A line: arrowheads by keyboard.
    s.call("setDrawTool", "arrowline")
    s.drag(s.point(0.05, 0.10), s.point(0.20, 0.10))
    s.call("setDrawTool", "")
    line = s.state()["selected"][0]
    ends = s.call_on_node("lineEndsAt", line)
    s.right_click(s.ed_point((ends["ax"] + ends["bx"]) / 2, ends["ay"]))
    s.record("line")
    s.click_menu_row("Arrowheads")
    s.record("line-heads", image=True)
    s.close_menus()

    # A small window: opened near the bottom-right corner the menu flips to
    # stay inside, and a long section scrolls.
    s.js("resize", 700, 420)
    s.wait(300)
    s.right_click(QtCore.QPoint(690, 410))
    box = json.loads(s.js("menuBox"))
    s.record("small-window", image=True)
    s.steps[-1]["state"]["menuInsideWindow"] = (
        box["open"]
        and box["x"] >= 0
        and box["y"] >= 0
        and box["x"] + box["w"] <= 700
        and box["y"] + box["h"] <= 420
    )
    # It reopens on the remembered Draw section; closing it stays inside too.
    s.click_menu_row("Draw")
    box = json.loads(s.js("menuBox"))
    s.record("small-window-section-closed", image=True)
    s.steps[-1]["state"]["menuInsideWindow"] = (
        box["y"] >= 0 and box["y"] + box["h"] <= 420
    )
    s.close_menus()


def scenario_layers(s: Session) -> None:
    """Stacking from old layouts, and the Layers panel: hide, lock, open a
    chip's hotspot and leaders, restack by dragging, rename, filter."""
    Mod = QtCore.Qt.KeyboardModifier
    Key = QtCore.Qt.Key

    # An old layout: zLayer sorts the stack once, pinned becomes locked.
    _load(s, "legacy")
    s.js("showLayers", True)
    s.record("legacy-normalised", image=True)

    _load(s, "evo_r")
    chips = [n["id"] for n in s.state()["nodes"] if n["kind"] == "btn"]
    # A filled rectangle over the Button 6 to 10 chips: drawn under them.
    s.call("setDrawTool", "rect")
    s.drag(s.point(0.24, 0.33), s.point(0.38, 0.48))
    s.call("setDrawTool", "")
    rect = s.state()["selected"][0]
    s.call("applyField", "fill", "filled")
    s.record("panel", image=True)

    # Hide the rectangle: gone from the map, and a click there selects nothing.
    s.click_layer("Rectangle", "eye")
    s.call("setSelection", [])
    s.click(s.point(0.26, 0.35))
    s.record("hidden-click-through", image=True)
    s.click_layer("Rectangle", "eye")

    # Lock a chip: a click on it, a drag and a band all pass it by.
    first = s.node(chips[0])
    name = s.call_on_node("layerName", chips[0])
    s.click_layer(name, "lock")
    s.call("setSelection", [])
    s.click(s.center(chips[0]))
    s.drag(s.center(chips[0]), s.center(chips[0], dx=60))
    s.record("locked-chip")
    assert s.node(chips[0])["chipFx"] == first["chipFx"]
    # Selected from the panel, Delete and arrow keys leave it alone.
    s.click_layer(name)
    s.key(Key.Key_Delete)
    s.key(Key.Key_Right)
    s.record("locked-chip-keys")

    # Ctrl+L locks the selection, Ctrl+Shift+L unlocks everything.
    s.call("setSelection", [rect])
    s.key(Key.Key_L, Mod.ControlModifier)
    s.record("ctrl-l")
    s.key(Key.Key_L, Mod.ControlModifier | Mod.ShiftModifier)
    s.record("ctrl-shift-l")

    # A chip's own rows: hide a leader, lock the hotspot.
    s.call("toggleLayerFlag", chips[1], "leader:0", "hidden")
    s.call("toggleLayerFlag", chips[1], "hot", "locked")
    s.js("setLayerFilter", "chips")
    s.js("openLayer", chips[1])
    s.record("chip-parts", image=True)
    s.js("setLayerFilter", "all")
    s.wait(100)

    # Drag the rectangle's row to the top: it now covers the chips.
    top = json.loads(s.js("layerRowRect", 0))
    r = s.layer_row("Rectangle")
    s.drag(
        QtCore.QPoint(round(r["x"] + 60), round(r["y"] + r["h"] / 2)),
        QtCore.QPoint(round(top["x"] + 60), round(top["y"] + 2)),
    )
    s.record("restacked", image=True)

    # Rename it by double-clicking its row.
    r = s.layer_row("Rectangle")
    QtTest.QTest.mouseDClick(
        s.win,
        QtCore.Qt.MouseButton.LeftButton,
        QtCore.Qt.KeyboardModifier.NoModifier,
        QtCore.QPoint(round(r["x"] + 80), round(r["y"] + r["h"] / 2)),
    )
    s.wait(150)
    s.type_text("Cover")
    QtTest.QTest.keyClick(s.win, Key.Key_Return)
    s.wait(150)
    s.record("renamed")

    # The photo's own row.
    s.call("setPhotoFlag", "locked", True)
    s.record("photo-locked")


def scenario_transform(s: Session) -> None:
    """Rotate handle, resizing a turned shape, a typed angle, flips, a
    picture keeping its proportions, and undoing a photo change."""
    Mod = QtCore.Qt.KeyboardModifier
    Key = QtCore.Qt.Key
    _load(s, "evo_r")

    def local(id_: str, fx: float, fy: float) -> QtCore.QPoint:
        x, y, w, h = json.loads(s.js("drawPt", id_, 0, 0))
        x, y, w, h = json.loads(s.js("drawPt", id_, w * fx, h * fy))
        return QtCore.QPoint(round(x), round(y))

    def handle(id_: str) -> QtCore.QPoint:
        x, y, w, h = json.loads(s.js("drawPt", id_, 0, 0))
        x, y, _w, _h = json.loads(s.js("drawPt", id_, w / 2, -24))
        return QtCore.QPoint(round(x), round(y))

    s.call("setDrawTool", "arrow")
    s.drag(s.point(0.05, 0.12), s.point(0.20, 0.22))
    s.call("setDrawTool", "")
    arrow = s.state()["selected"][0]
    # Filled, so a click anywhere on it (not only its outline) finds it.
    s.call("applyField", "fill", "filled")
    s.record("arrow", image=True)

    # Drag the rotate handle round to the right: about 90 degrees.
    centre = local(arrow, 0.5, 0.5)
    s.drag(handle(arrow), QtCore.QPoint(centre.x() + 120, centre.y() + 9))
    s.record("rotated-free")
    # With Shift it lands on a 15 degree step.
    s.drag(
        handle(arrow),
        QtCore.QPoint(centre.x() + 100, centre.y() + 60),
        Mod.ShiftModifier,
    )
    s.record("rotated-shift", image=True)

    # Resize the turned arrow from its bottom-right corner: the top-left
    # corner stays where it is on screen.
    before = local(arrow, 0, 0)
    corner = local(arrow, 1, 1)
    s.drag(corner, QtCore.QPoint(corner.x() + 30, corner.y() + 40))
    after = local(arrow, 0, 0)
    s.record("resized-turned", image=True)
    s.steps[-1]["state"]["fixedCornerMoved"] = round(
        abs(after.x() - before.x()) + abs(after.y() - before.y())
    )

    # A typed angle and flips, from the menu.
    s.right_click(local(arrow, 0.5, 0.5))
    s.click_menu_row("Rotate and flip")
    r = json.loads(s.js("menuRowRect", "Angle"))
    s.click(QtCore.QPoint(round(r["x"] + 120), round(r["y"] + r["h"] / 2)))
    QtTest.QTest.keyClick(s.win, Key.Key_A, Mod.ControlModifier)
    s.type_text("30")
    QtTest.QTest.keyClick(s.win, Key.Key_Return)
    s.wait(150)
    s.record("typed-angle")
    s.click_menu_row("Flip horizontally")
    s.record("flipped", image=True)

    # A line flips by moving its ends.
    s.call("setDrawTool", "arrowline")
    s.drag(s.point(0.05, 0.60), s.point(0.20, 0.70))
    s.call("setDrawTool", "")
    s.call("flipSelection", "h")
    s.record("line-flipped")

    # A picture keeps its proportions from a corner; Shift stretches it.
    icon = ROOT / "gfx" / "icon.png"
    s.call("addOverlay", "test/icon", QtCore.QUrl.fromLocalFile(str(icon)).toString())
    pic = s.state()["selected"][0]
    corner = s.corner(pic)
    s.drag(corner, QtCore.QPoint(corner.x() + 80, corner.y() + 10))
    s.record("picture-kept")
    corner = s.corner(pic)
    s.drag(corner, QtCore.QPoint(corner.x() + 60, corner.y() - 30), Mod.ShiftModifier)
    s.record("picture-stretched")

    # The photo: a change is one undo step, and undo puts it back.
    s.call("applyPhotoPose", {"scale": 1.2, "offX": 0.2, "offY": 0.1, "rot": 20})
    s.call("notePhotoChange")
    s.wait(600)
    s.record("photo-changed")
    s.call("undo")
    s.record("photo-undone")
    s.call("redo")
    s.record("photo-redone")


SCENARIOS = {
    "load_l": scenario_load_l,
    "session_r": scenario_session_r,
    "api_sweep": scenario_api_sweep,
    "arrows": scenario_arrows,
    "menu": scenario_menu,
    "layers": scenario_layers,
    "transform": scenario_transform,
}


def main() -> None:
    name, out_dir = sys.argv[1], Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    session = Session(out_dir, name)
    SCENARIOS[name](session)
    session.finish()
    os._exit(0)


if __name__ == "__main__":
    main()
