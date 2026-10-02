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
import math
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
import QtQuick.Controls.Universal as U
import Gremlin.Style

Window {
    id: _win
    width: 1600
    height: 900
    visible: true
    color: "#202020"
    // As the Button Map window: left unset, the controls' theme varied.
    U.Universal.theme: Style.theme

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

    RigPropsPanel {
        id: _props
        ed: _face.editorItem
        visible: false
        width: 300
        x: 12
        y: 12
        height: implicitHeight
        z: 50
    }
    function showProps(on) { _props.visible = on }

    // A stand-in device for press to find: buttons and hats held down.
    QtObject {
        id: _fakeDevice
        property var held: ({})
        function hwButton(id) { return held["btn:" + id] ? 1 : 0 }
        function hwAxis(id) { return held["axis:" + id] || 0 }
        function hwHat(id) { return held["hat:" + id] ? 1 : 0 }
    }
    function useFakeDevice(rowsJson) {
        _face.host = _fakeDevice
        _face.chipRows = JSON.parse(rowsJson)
    }
    function hold(key, value) {
        var h = _fakeDevice.held
        h[key] = value
        _fakeDevice.held = h
        _face.liveStamp++
    }
    property string notPlaced: ""
    property var lastStyleAsk: []
    function styleAsked() { return JSON.stringify(lastStyleAsk) }
    // Text of a few chips and of a group's members, as shown.
    function chipTexts() {
        var e = ed()
        var out = {}
        var list = e.nodes || []
        for (var i = 0; i < list.length; i++) {
            var n = list[i]
            if (e.isDraw(n))
                continue
            if (e.isGroup(n)) {
                var mem = n.members || []
                for (var j = 0; j < mem.length; j++) {
                    var key = e.memberKind(n, mem[j]) + ":" + mem[j].hwId
                    out[key] = e.chipText(n, mem[j])
                }
            } else {
                out[e.leafKind(n.kind) + ":" + n.hwId] = e.chipText(n, null)
            }
        }
        var keep = ["btn:1", "btn:2", "btn:3", "btn:6", "btn:9", "axis:1"]
        var picked = {}
        for (var k = 0; k < keep.length; k++)
            picked[keep[k]] = out[keep[k]]
        return JSON.stringify(picked)
    }
    function findState() {
        return JSON.stringify({
            msg: ed().findMsg,
            notPlaced: _win.notPlaced,
            pan: [Math.round(_face.panX), Math.round(_face.panY)]
        })
    }
    function setPhotoUrl(url) { _face.photoOverride = url }
    function setRulers(on) { _face.rulersOn = on }
    // A transform handle's window point.
    function xfHandlePt(id, name) {
        var e = ed()
        var n = e.nodeAt(id)
        var it = e._chipsItem(e.nodeIndex(id))
        var hs = e.transformHandles(n, it.width, it.height)
        for (var i = 0; i < hs.length; i++) {
            if (hs[i].name !== name)
                continue
            var k = n.skew || [0, 0]
            var dx = hs[i].x - it.width / 2
            var dy = hs[i].y - it.height / 2
            var p = it.mapToItem(null, it.width / 2 + dx + k[0] * dy,
                                 it.height / 2 + dy + k[1] * dx)
            return JSON.stringify([p.x, p.y])
        }
        return "null"
    }
    function setPoolStrip(width) {
        ed().poolHit = function(wx, wy) { return wx < width }
    }
    function getProp(name) { return JSON.stringify(ed()[name]) }
    function zoomToPage() { _face.zoomToPage() }
    function viewState() {
        return JSON.stringify({
            zoom: Math.round(_face.zoom * 100) / 100,
            pan: [Math.round(_face.panX), Math.round(_face.panY)]
        })
    }
    function setZoom(z, px, py) {
        _face.zoom = z
        _face.panX = px
        _face.panY = py
        _face.pingEditor()
    }

    // Paste picture requests (the window saves the clipboard's picture).
    property int pasteRequests: 0
    Connections {
        target: _face.editorItem
        function onPastePictureRequested() { _win.pasteRequests++ }
        function onFindNotPlaced(label) { _win.notPlaced = label }
        function onSaveStyleRequested(kind, fields) {
            _win.lastStyleAsk = [kind, fields]
        }
    }
    function propLines() {
        return JSON.stringify(_props.visible ? _props.describe() : [])
    }
    function propFieldRect(label) { return JSON.stringify(_props.fieldRect(label)) }
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
            props: JSON.parse(propLines()),
            photo: [e.photoScale, e.photoOffX, e.photoOffY, e.photoRot],
            cropId: e.cropId,
            pasteRequests: _win.pasteRequests,
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
    // Export as the Button Map window does it: editing marks off, a frame to
    // redraw, then the editor drawn f times larger. exportDone gets the page
    // rect in the picture's pixels once the file is written.
    property string exportDone: ""
    function exportResult() { return exportDone }
    function exportGrab(path, f) {
        exportDone = ""
        ed().exporting = true
        _exportTimer.path = path
        _exportTimer.f = f
        _exportTimer.restart()
    }
    Timer {
        id: _exportTimer
        property string path: ""
        property real f: 1
        interval: 50
        onTriggered: {
            var e = _win.ed()
            var r = e.spaceRect()
            var f = _exportTimer.f
            var out = _exportTimer.path
            e.grabToImage(function(result) {
                e.exporting = false
                result.saveToFile(out)
                _win.exportDone = JSON.stringify([r.x * f, r.y * f, r.w * f, r.h * f])
            }, Qt.size(Math.round(e.width * f), Math.round(e.height * f)))
        }
    }
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

    def call_prop(self, name: str) -> object:
        return json.loads(self.js("getProp", name))

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

    def open_menu_section(self, title: str) -> None:
        """Opens a menu section unless it is open already (the menu reopens
        on the section used last)."""
        if ("v " + title) not in self.state()["menu"]:
            self.click_menu_row(title)

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

    def set_prop_field(self, label: str, text: str) -> None:
        """Types a value into a Properties field and presses Enter."""
        r = json.loads(self.js("propFieldRect", label))
        assert r, f"no property {label!r}"
        self.click(
            QtCore.QPoint(round(r["x"] + r["w"] / 2), round(r["y"] + r["h"] / 2))
        )
        QtTest.QTest.keyClick(
            self.win, QtCore.Qt.Key.Key_A, QtCore.Qt.KeyboardModifier.ControlModifier
        )
        self.type_text(text)
        QtTest.QTest.keyClick(self.win, QtCore.Qt.Key.Key_Return)
        # Focus back on the map and the mouse off the panel: a blinking text
        # cursor or a hovered box would differ from run to run.
        self.js("focusEditor")
        self._park_mouse()

    def _park_mouse(self) -> None:
        """Moves the mouse to an empty corner and lets hover looks settle."""
        corner = QtCore.QPoint(self.win.width() // 2, self.win.height() - 3)
        event = QtGui.QMouseEvent(
            QtCore.QEvent.Type.MouseMove,
            QtCore.QPointF(corner),
            QtCore.QPointF(self.win.mapToGlobal(corner)),
            QtCore.Qt.MouseButton.NoButton,
            QtCore.Qt.MouseButton.NoButton,
            QtCore.Qt.KeyboardModifier.NoModifier,
        )
        QtCore.QCoreApplication.sendEvent(self.win, event)
        self.wait(300)

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
    # Loading can leave one extra undo step or not, depending on timing:
    # start every scenario from a single one.
    s.call("seedHist")


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


def scenario_props(s: Session) -> None:
    """The Properties panel: typed position, size, angle and opacity for a
    shape, a chip's place, a line's end, several items, and a locked one."""
    _load(s, "evo_r")
    s.js("showProps", True)
    s.record("nothing-selected")

    s.call("setDrawTool", "rect")
    s.drag(s.point(0.30, 0.60), s.point(0.40, 0.70))
    s.call("setDrawTool", "")
    rect = s.state()["selected"][0]
    s.record("rect")
    s.set_prop_field("X", "5")
    s.set_prop_field("Y", "10")
    s.set_prop_field("Width", "15")
    s.set_prop_field("Height", "12.5")
    s.set_prop_field("Angle", "30")
    s.set_prop_field("Opacity", "50")
    s.call("setProp", "fill", "filled")
    s.record("rect-typed", image=True)

    chips = [n["id"] for n in s.state()["nodes"] if n["kind"] == "btn"]
    s.call("setSelection", [chips[0]])
    s.set_prop_field("X", "45")
    s.record("chip-moved")

    s.call("setDrawTool", "arrowline")
    s.drag(s.point(0.05, 0.80), s.point(0.20, 0.85))
    s.call("setDrawTool", "")
    s.set_prop_field("End X", "25")
    s.set_prop_field("End Y", "95")
    s.record("line-end", image=True)

    s.call("setDrawTool", "ellipse")
    s.drag(s.point(0.02, 0.40), s.point(0.10, 0.50))
    s.call("setDrawTool", "")
    ellipse = s.state()["selected"][0]
    s.call("setSelection", [rect, ellipse])
    s.set_prop_field("Opacity", "25")
    s.record("several")

    s.call("setSelection", [rect])
    s.call("toggleLock", rect)
    s.set_prop_field("X", "60")
    s.record("locked")


def scenario_align(s: Session) -> None:
    """Aligning and spacing out shapes and chips, from the menu and directly;
    a locked item stays where it is."""
    Key = QtCore.Qt.Key
    _load(s, "evo_r")
    shapes = []
    # The tool stays on after each shape (setDrawTool toggles it).
    s.call("setDrawTool", "rect")
    corners = [
        (0.03, 0.10, 0.10, 0.16),
        (0.12, 0.30, 0.22, 0.40),
        (0.05, 0.55, 0.11, 0.62),
    ]
    for x0, y0, x1, y1 in corners:
        s.drag(s.point(x0, y0), s.point(x1, y1))
        shapes.append(s.state()["selected"][0])
    s.call("setDrawTool", "")
    s.call("setSelection", shapes)
    s.record("three-shapes", image=True)

    # From the menu: open Align and distribute, Across row, step to Left.
    box = s._box(shapes[1])
    s.right_click(s.ed_point(box["x"] + 2, box["y"] + box["h"] / 2))
    s.click_menu_row("Align and distribute")
    s.menu_key(Key.Key_Down)
    s.menu_key(Key.Key_Right)
    s.record("menu-left")
    s.close_menus()

    s.call("alignSelection", "center")
    s.record("centre")
    s.call("distributeSelection", "v")
    s.record("spaced-down", image=True)
    s.call("alignSelection", "top")
    s.call("distributeSelection", "h")
    s.record("top-and-across", image=True)

    # Chips line up too; a locked one stays put.
    chips = [n["id"] for n in s.state()["nodes"] if n["kind"] == "btn"][:3]
    s.call("toggleLock", chips[2])
    s.call("setSelection", chips)
    s.call("alignSelection", "left")
    s.record("chips-left-one-locked", image=True)


def scenario_picture(s: Session) -> None:
    """Cropping a picture with its handles and by typing, Esc leaving crop
    mode, Reset crop, and the canvas menu's Paste picture."""
    Key = QtCore.Qt.Key
    _load(s, "evo_r")
    s.js("showProps", True)
    icon = ROOT / "gfx" / "icon_large.png"
    s.call("addOverlay", "test/icon", QtCore.QUrl.fromLocalFile(str(icon)).toString())
    pic = s.state()["selected"][0]
    s.record("picture", image=True)

    # Crop mode from the menu, then drag the right and bottom handles in.
    box = s._box(pic)
    s.right_click(s.ed_point(box["x"] + box["w"] / 2, box["y"] + box["h"] / 2))
    s.open_menu_section("Picture")
    s.click_menu_row("Crop")
    s.close_menus()
    s.record("crop-mode")
    right = s.ed_point(box["x"] + box["w"], box["y"] + box["h"] / 2)
    s.drag(right, QtCore.QPoint(right.x() - round(box["w"] * 0.4), right.y()))
    box = s._box(pic)
    bottom = s.ed_point(box["x"] + box["w"] / 2, box["y"] + box["h"])
    s.drag(bottom, QtCore.QPoint(bottom.x(), bottom.y() - round(box["h"] * 0.25)))
    s.record("cropped-by-handles", image=True)

    # Esc leaves crop mode (and runs the editor's whole cancel).
    s.key(Key.Key_Escape)
    s.record("esc")

    # Typed: the left side, then Reset crop from the menu.
    s.call("setSelection", [pic])
    s.set_prop_field("Crop left", "20")
    s.record("crop-left-typed", image=True)
    box = s._box(pic)
    s.right_click(s.ed_point(box["x"] + box["w"] / 2, box["y"] + box["h"] / 2))
    s.open_menu_section("Picture")
    s.click_menu_row("Reset crop")
    s.record("crop-reset", image=True)

    # Paste picture: off with nothing on the clipboard, then on.
    s.right_click(s.point(0.1, 0.9))
    s.open_menu_section("Draw")
    s.record("paste-off")
    s.close_menus()
    s.set_prop("canPastePicture", True)
    s.right_click(s.point(0.1, 0.9))
    s.open_menu_section("Draw")
    s.click_menu_row("Paste picture")
    s.record("paste-requested")


def scenario_find(s: Session) -> None:
    """Press to find: a press selects the chip and scrolls to it; a control
    not on the map is pointed to the pool; axes only when asked; off is off."""
    _load(s, "evo_r")
    rows = [{"kind": "btn", "hwId": i} for i in (1, 3, 5, 40)]
    rows.append({"kind": "axis", "hwId": 1})
    s.js("useFakeDevice", json.dumps(rows))
    s.call("setSelection", [])

    def find_step(name: str, image: bool = False) -> None:
        s.record(name, image=image)
        s.steps[-1]["state"]["find"] = json.loads(s.js("findState"))

    s.js("hold", "btn:3", 1)
    find_step("press-b3", image=True)
    s.js("hold", "btn:3", 0)
    # Zoomed in far from Button 1: the press brings it into view.
    s.js("setZoom", 6, 2500, 1500)
    s.js("hold", "btn:1", 1)
    find_step("press-b1-scrolls")
    s.js("hold", "btn:1", 0)
    s.js("resetView")
    s.js("hold", "btn:40", 1)
    find_step("not-on-map")
    s.js("hold", "btn:40", 0)
    # Axes: ignored by default, found when asked.
    s.call("setSelection", [])
    s.js("hold", "axis:1", 0.9)
    find_step("axis-ignored")
    s.js("hold", "axis:1", 0)
    s.set_prop("findAxes", True)
    s.js("hold", "axis:1", 0.9)
    find_step("axis-found")
    s.js("hold", "axis:1", 0)
    # Off: a press changes nothing.
    s.set_prop("findOn", False)
    s.call("setSelection", [])
    s.js("hold", "btn:5", 1)
    find_step("off")


def scenario_labels(s: Session) -> None:
    """Chip text: name, action, both; unbound controls shown as their name,
    nothing, or a dash; group members too."""
    _load(s, "evo_r")
    s.call("setSelection", [])
    s.set_prop("actionLabels", {
        "btn:3": "Gear up", "btn:1": "Ctrl+G", "btn:6": "→ Combat",
        "axis:1": "vJoy 1 X",
    })

    def label_step(name: str, image: bool = False) -> None:
        s.record(name, image=image)
        texts = json.loads(s.js("chipTexts"))
        s.steps[-1]["state"]["chipTexts"] = texts

    label_step("name")
    s.set_prop("chipTextMode", "Action")
    label_step("action", image=True)
    s.set_prop("chipTextMode", "Name and action")
    label_step("name-and-action", image=True)
    s.set_prop("chipTextMode", "Action")
    s.set_prop("unboundText", "Blank")
    label_step("unbound-blank")
    s.set_prop("unboundText", "Dash")
    label_step("unbound-dash")
    # Export modes: each page carries its mode's name, without editing marks.
    s.call("setSelection", [])
    s.set_prop("exporting", True)
    s.set_prop("exportTitle", "Combat")
    label_step("export-page-title", image=True)
    s.set_prop("exportTitle", "")
    s.set_prop("exporting", False)


def scenario_mirror(s: Session) -> None:
    """Mirror layout: chips, hotspots and leaders to the other side, a block
    arrow and an arrow line pointing the other way; twice is the start."""
    _load(s, "evo_r")
    s.call("setDrawTool", "arrow")
    s.drag(s.point(0.04, 0.06), s.point(0.20, 0.16))
    s.call("setDrawTool", "arrowline")
    s.drag(s.point(0.06, 0.24), s.point(0.22, 0.30))
    s.call("setDrawTool", "")
    s.call("setSelection", [])
    s.record("before", image=True)
    s.call("mirrorLayout", False)
    s.record("mirrored", image=True)
    s.key(QtCore.Qt.Key.Key_Z, QtCore.Qt.KeyboardModifier.ControlModifier)
    s.record("undo")
    s.call("mirrorLayout", False)
    s.call("mirrorLayout", False)
    s.record("twice")


def scenario_turn(s: Session) -> None:
    """Turning several items together with the selection's handle and by a
    typed turn; turning a text box with its own handle."""
    _load(s, "evo_r")
    s.call("setDrawTool", "arrow")
    s.drag(s.point(0.05, 0.10), s.point(0.18, 0.18))
    arrow = s.state()["selected"][0]
    s.call("setDrawTool", "arrowline")
    s.drag(s.point(0.05, 0.26), s.point(0.18, 0.26))
    line = s.state()["selected"][0]
    s.call("setDrawTool", "")
    chip = "b3"
    s.call("setSelection", [arrow, line, chip])
    s.record("three-selected", image=True)

    box = s.call("selectionBounds")
    pivot = s.call("turnPivot")
    centre = s.ed_point(pivot["x"], pivot["y"])
    grip = s.ed_point(box["x"] + box["w"] / 2, box["y"] - 24)
    # Round to the right of the middle: a quarter turn, snapped with Shift.
    s.drag(
        grip,
        QtCore.QPoint(centre.x() + 200, centre.y() + 3),
        QtCore.Qt.KeyboardModifier.ShiftModifier,
    )
    s.record("turned-90", image=True)
    s.call("turnSelectionBy", -90)
    s.record("turned-back")
    s.key(QtCore.Qt.Key.Key_Z, QtCore.Qt.KeyboardModifier.ControlModifier)
    s.record("undo")

    # A text box has its own rotate handle now.
    s.call("setDrawTool", "text")
    s.drag(s.point(0.72, 0.10), s.point(0.90, 0.18))
    text = s.state()["selected"][0]
    s.call("setDrawTool", "")
    s.call("setRotation", 30)
    s.record("text-turned", image=True)
    s.steps[-1]["state"]["textRot"] = s.node(text).get("rot")


def scenario_callout(s: Session) -> None:
    """Callouts: drawn with the tool, the tip dragged onto a chip and following
    it, one added for a chip, the pointer removed and added back."""
    _load(s, "evo_r")
    s.call("setDrawTool", "callout")
    s.drag(s.point(0.12, 0.08), s.point(0.26, 0.14))
    s.call("setDrawTool", "")
    box = s.state()["selected"][0]
    s.record("drawn", image=True)

    # Drag the tip onto Button 3: it follows the chip from then on.
    tip = s.call_on_node("calloutTip", box)
    chip = s._box("b3")
    s.drag(
        s.ed_point(tip["x"], tip["y"]),
        s.ed_point(chip["x"] + chip["w"] / 2, chip["y"] + chip["h"] / 2),
    )
    s.record("tip-on-chip", image=True)
    s.call("setSelection", ["b3"])
    s.key(QtCore.Qt.Key.Key_Down, QtCore.Qt.KeyboardModifier.ShiftModifier)
    s.key(QtCore.Qt.Key.Key_Down, QtCore.Qt.KeyboardModifier.ShiftModifier)
    s.record("chip-moved", image=True)

    # Right-click a chip → Add callout.
    s.call("addCalloutFor", s.call("placedId", "btn", 6))
    added = s.state()["selected"][0]
    s.record("added-for-chip", image=True)
    s.call("removeCalloutTail")
    s.record("pointer-removed")
    s.call("addCalloutTail")
    s.record("pointer-added")
    s.steps[-1]["state"]["tails"] = [s.node(box).get("tail"), s.node(added).get("tail")]


def scenario_paths(s: Session) -> None:
    """The Path tool (clicks, Enter, closing on the first point), the
    Freehand tool, dragging a point, and a path's menu."""
    Key = QtCore.Qt.Key
    _load(s, "evo_r")
    s.call("setDrawTool", "path")
    for fx, fy in ((0.05, 0.08), (0.20, 0.06), (0.24, 0.20)):
        s.click(s.point(fx, fy))
    s.record("path-drafting", image=True)
    s.key(Key.Key_Return)
    s.record("path-open")
    open_path = s.state()["selected"][0]

    # Closed: back on the first point (the tool stays on for the next path).
    corners = ((0.05, 0.40), (0.18, 0.36), (0.22, 0.52), (0.08, 0.56), (0.05, 0.40))
    for fx, fy in corners:
        s.click(s.point(fx, fy))
    closed = s.state()["selected"][0]
    s.call("applyField", "fill", "filled")
    s.record("path-closed", image=True)

    # Freehand: a wavy stroke, simplified and smooth.
    s.call("setDrawTool", "pen")
    start = s.point(0.76, 0.30)
    s._mouse("mousePress", start)
    for i in range(1, 25):
        p = QtCore.QPoint(start.x() + i * 10, start.y() + round(30 * math.sin(i / 3)))
        event = QtGui.QMouseEvent(
            QtCore.QEvent.Type.MouseMove, QtCore.QPointF(p),
            QtCore.QPointF(s.win.mapToGlobal(p)), QtCore.Qt.MouseButton.NoButton,
            QtCore.Qt.MouseButton.LeftButton, QtCore.Qt.KeyboardModifier.NoModifier,
        )
        QtCore.QCoreApplication.sendEvent(s.win, event)
        s.wait(10)
    s._mouse("mouseRelease", p)
    s.wait(80)
    s.call("setDrawTool", "")
    pen = s.state()["selected"][0]
    s.record("freehand", image=True)
    s.steps[-1]["state"]["penPoints"] = len(s.node(pen)["pts"])

    # Drag the open path's middle point down.
    s.call("setSelection", [open_path])
    pts = s.call_on_node("pathPointsAt", open_path)
    mid = s.ed_point(pts[1][0], pts[1][1])
    s.drag(mid, QtCore.QPoint(mid.x(), mid.y() + 80))
    s.record("point-dragged", image=True)

    # Its menu: Path section, then Arrowheads (open) or Fill (closed).
    s.right_click(s.ed_point(pts[0][0], pts[0][1]))
    s.record("menu-open-path")
    s.close_menus()
    s.call("setSelection", [closed])
    s.call("togglePathSmooth")
    s.record("closed-smooth", image=True)


def scenario_styles(s: Session) -> None:
    """Saved styles: offered for the item's kind in its menu, applied to the
    selection as one undo step, and Save this style asks the window."""
    _load(s, "evo_r")
    s.call("setDrawTool", "rect")
    s.drag(s.point(0.05, 0.08), s.point(0.18, 0.18))
    s.call("setDrawTool", "rect")
    s.drag(s.point(0.05, 0.26), s.point(0.18, 0.36))
    s.call("setDrawTool", "")
    shapes = [n["id"] for n in s.state()["nodes"] if n.get("shape") == "rect"]
    s.set_prop("savedStyles", [
        {"name": "Warning", "kind": "shape",
         "fields": {"fill": "filled", "color": "#7C2D12", "border": "#FBBF24",
                    "stroke": 4, "dash": "dash"}},
        {"name": "Weapons", "kind": "chip", "fields": {"color": "#7F1D1D"}},
    ])
    s.call("setSelection", shapes)
    box = s._box(shapes[0])
    s.right_click(s.ed_point(box["x"] + 4, box["y"] + 4))
    s.open_menu_section("Saved styles")
    s.record("menu")
    s.click_menu_row("Apply Warning")
    s.record("applied", image=True)
    s.key(QtCore.Qt.Key.Key_Z, QtCore.Qt.KeyboardModifier.ControlModifier)
    s.record("undone")
    s.call("saveStyleOf", "b3")
    s.record("save-asked")
    s.steps[-1]["state"]["saveAsked"] = json.loads(s.js("styleAsked"))


def scenario_photo_look(s: Session) -> None:
    """The photo's look: brightness, contrast, greyscale and fade, saved with
    its pose, undone in one step, and reset on its own."""
    _load(s, "evo_r")
    # A picture stands in for the photo, which a plain checkout lacks.
    icon = ROOT / "gfx" / "icon_large.png"
    s.js("setPhotoUrl", QtCore.QUrl.fromLocalFile(str(icon)).toString())
    s.call("setSelection", [])
    s.record("plain", image=True)
    s.call("setPhotoLook", "grey", 1)
    s.call("setPhotoLook", "bright", 0.3)
    s.call("setPhotoLook", "fade", 0.5)
    s.wait(500)
    s.record("adjusted", image=True)
    s.steps[-1]["state"]["bag"] = s.call("photoBag")
    s.key(QtCore.Qt.Key.Key_Z, QtCore.Qt.KeyboardModifier.ControlModifier)
    s.record("undone")
    s.steps[-1]["state"]["bag"] = s.call("photoBag")
    s.call("setPhotoLook", "contrast", 0.5)
    s.call("resetPhotoLook")
    s.wait(500)
    s.record("reset")
    s.steps[-1]["state"]["bag"] = s.call("photoBag")


def scenario_light_page(s: Session) -> None:
    """A light page for printing: while exporting, every colour has its
    lightness turned over (shapes, lines, text, callouts, chips, leaders);
    on screen nothing changes."""
    _load(s, "evo_r")
    s.call("setDrawTool", "rect")
    s.drag(s.point(0.05, 0.08), s.point(0.18, 0.18))
    s.call("applyField", "fill", "filled")
    s.call("setDrawTool", "arrowline")
    s.drag(s.point(0.05, 0.26), s.point(0.18, 0.26))
    s.call("setDrawTool", "callout")
    s.drag(s.point(0.05, 0.40), s.point(0.18, 0.46))
    s.call("setDrawTool", "")
    s.call("setSelection", [])
    s.set_prop("gridOn", False)
    s.set_prop("printLight", True)
    s.record("on-screen-unchanged", image=True)
    s.set_prop("exporting", True)
    s.call("repaint")
    s.record("light-export", image=True)
    s.steps[-1]["state"]["ink"] = [s.call("ink", "#18181B"), s.call("ink", "#22C55E")]
    s.set_prop("exporting", False)
    s.set_prop("printLight", False)
    s.call("repaint")
    s.record("back")


def scenario_zoom(s: Session) -> None:
    """Zoom to selection fills the view with the selection; zoom to fit
    shows the whole page."""
    _load(s, "evo_r")
    s.call("setSelection", ["b3"])

    def view_step(name: str) -> None:
        s.record(name, image=True)
        s.steps[-1]["state"]["view"] = json.loads(s.js("viewState"))

    s.call("zoomToSelection")
    view_step("selection")
    s.js("zoomToPage")
    view_step("page")
    s.call("setSelection", [])
    s.steps.append({"step": "nothing-selected", "state": {
        **s.state(), "zoomed": s.call("zoomToSelection")}})


def scenario_rulers(s: Session) -> None:
    """Rulers: a guide dragged out of the top ruler, a shape dragged near it
    snaps to it, the guide dragged off the page goes."""
    _load(s, "evo_r")
    s.js("setRulers", True)
    s.call("setDrawTool", "rect")
    s.drag(s.point(0.05, 0.40), s.point(0.15, 0.50))
    s.call("setDrawTool", "")
    rect = s.state()["selected"][0]
    # Filled, so grabbing its middle takes it.
    s.call("applyField", "fill", "filled")
    s.call("setSelection", [])
    s.record("rulers", image=True)

    # Out of the top ruler, down to a fifth of the page.
    ruler = QtCore.QPoint(s.point(0.5, 0.3).x(), 9)
    s.drag(ruler, s.point(0.5, 0.2))
    s.record("guide-added", image=True)
    s.steps[-1]["state"]["guides"] = [
        s.call_prop("rulerGuidesX"), s.call_prop("rulerGuidesY")]

    # The shape dragged up near the guide lands on it.
    box = s._box(rect)
    grab = s.ed_point(box["x"] + box["w"] / 2, box["y"] + box["h"] / 2)
    guide_y = s.point(0.5, 0.2).y()
    target = QtCore.QPoint(grab.x(), guide_y + round(box["h"] / 2) + 4)
    s.drag(grab, target)
    s.record("shape-on-guide", image=True)
    snapped = s._box(rect)
    s.steps[-1]["state"]["topOnGuide"] = abs(
        s.ed_point(snapped["x"], snapped["y"]).y() - guide_y) <= 1

    # Drag the guide back onto its ruler: gone.
    s.call("setSelection", [])
    on_guide = s.point(0.8, 0.2)
    s.drag(on_guide, QtCore.QPoint(on_guide.x(), 6))
    s.record("guide-removed")
    s.steps[-1]["state"]["guides"] = [
        s.call_prop("rulerGuidesX"), s.call_prop("rulerGuidesY")]


def scenario_to_pool(s: Session) -> None:
    """Dragging chips onto the pool takes them off the map: one chip, several
    selected, a whole group, one member of a group being edited; a locked
    chip stays."""
    _load(s, "evo_r")
    # A stand-in pool: the window's left 120 pixels.
    s.js("setPoolStrip", 120)

    def pool_step(name: str, image: bool = False) -> None:
        s.record(name, image=image)
        s.steps[-1]["state"]["placed"] = {
            key: bool(s.call("placedId", *key.split(":")))
            for key in ("btn:3", "btn:4", "btn:5", "btn:1", "btn:2", "btn:6")
        }

    def drag_to_pool(start: QtCore.QPoint, hover_image: str = "") -> None:
        s._mouse("mousePress", start)
        s.wait(20)
        target = QtCore.QPoint(40, start.y())
        for i in range(1, 7):
            p = QtCore.QPoint(start.x() + (target.x() - start.x()) * i // 6, start.y())
            event = QtGui.QMouseEvent(
                QtCore.QEvent.Type.MouseMove, QtCore.QPointF(p),
                QtCore.QPointF(s.win.mapToGlobal(p)), QtCore.Qt.MouseButton.NoButton,
                QtCore.Qt.MouseButton.LeftButton, QtCore.Qt.KeyboardModifier.NoModifier,
            )
            QtCore.QCoreApplication.sendEvent(s.win, event)
            s.wait(15)
        if hover_image:
            pool_step(hover_image, image=True)
            s.steps[-1]["state"]["poolHover"] = s.call_prop("poolHover")
        s._mouse("mouseRelease", target)
        s.wait(80)

    pool_step("start")
    drag_to_pool(s.center("b3"), hover_image="over-pool")
    pool_step("chip-gone", image=True)
    s.key(QtCore.Qt.Key.Key_Z, QtCore.Qt.KeyboardModifier.ControlModifier)
    pool_step("undo-brings-it-back")

    # Locked: it cannot be dragged, so it stays.
    s.call("setSelection", ["b3"])
    s.key(QtCore.Qt.Key.Key_L, QtCore.Qt.KeyboardModifier.ControlModifier)
    drag_to_pool(s.center("b3"))
    pool_step("locked-stays")
    s.call("setSelection", ["b3"])
    s.key(QtCore.Qt.Key.Key_L, QtCore.Qt.KeyboardModifier.ControlModifier)

    # Several selected: all of them go.
    b4 = s.call("placedId", "btn", 4)
    b5 = s.call("placedId", "btn", 5)
    s.call("setSelection", [b4, b5])
    drag_to_pool(s.center(b4))
    pool_step("several-gone")

    # A whole group (Buttons 1 and 2).
    group = s.call("placedId", "btn", 1)
    s.call("setSelection", [group])
    drag_to_pool(s.center(group))
    pool_step("group-gone")

    # One member of a group being edited (Button 6 in its stack).
    stack = s.call("placedId", "btn", 6)
    s.call("setSelection", [stack])
    s.call("beginGroupEdit", stack)
    members = s.node(stack)["members"]
    s.set_prop("selectedMember", next(
        i for i, m in enumerate(members) if m.get("hwId") == 6))
    s.call("returnToPool")
    pool_step("member-gone")
    s.steps[-1]["state"]["stackSize"] = len(s.node(stack)["members"])


def scenario_shape_tools(s: Session) -> None:
    """Transform handles on a double arrow: shape (head and shaft), tips,
    bend and skew; Reset shape; Edit points on a triangle."""
    _load(s, "evo_r")
    s.call("setDrawTool", "arrow2")
    s.drag(s.point(0.05, 0.10), s.point(0.30, 0.18))
    s.call("setDrawTool", "")
    arrow = s.state()["selected"][0]
    s.record("double-arrow", image=True)

    def handle(name: str) -> QtCore.QPoint:
        x, y = json.loads(s.js("xfHandlePt", arrow, name))
        return QtCore.QPoint(round(x), round(y))

    def xf_step(name: str, image: bool = False) -> None:
        s.record(name, image=image)
        n = s.node(arrow)
        s.steps[-1]["state"]["shaping"] = {
            k: n.get(k) for k in ("adj", "bend", "skew", "rot", "shape")}

    s.call("setTransformMode", "shape")
    h = handle("head")
    s.drag(h, QtCore.QPoint(h.x() - 40, h.y() - 10))
    sh = handle("shaft")
    s.drag(sh, QtCore.QPoint(sh.x(), sh.y() + 8))
    xf_step("shaped", image=True)

    s.call("setTransformMode", "tips")
    tip = handle("tipB")
    s.drag(tip, QtCore.QPoint(tip.x() + 60, tip.y() + 120))
    xf_step("tip-moved", image=True)

    s.call("setTransformMode", "bend")
    bend = handle("bend")
    s.drag(bend, QtCore.QPoint(bend.x() + 20, bend.y() - 40))
    xf_step("bent", image=True)

    s.call("setTransformMode", "skew")
    sk = handle("skewX")
    s.drag(sk, QtCore.QPoint(sk.x() + 30, sk.y()))
    xf_step("skewed", image=True)

    s.call("resetShape")
    xf_step("reset", image=True)

    # Edit points: a skewed triangle becomes a path through its corners.
    s.call("setDrawTool", "triangle")
    s.drag(s.point(0.60, 0.10), s.point(0.75, 0.25))
    s.call("setDrawTool", "")
    tri = s.state()["selected"][0]
    s.call("applyField", "fill", "filled")
    s.call("convertToPath")
    s.record("triangle-points", image=True)
    n = s.node(tri)
    s.steps[-1]["state"]["path"] = [
        n.get("shape"), len(n.get("pts", [])), n.get("closed")]


def scenario_hotspots(s: Session) -> None:
    """Every hotspot shape, fills, line widths, opacity, halo and number;
    highlight on press; kept off the live map."""
    _load(s, "evo_r")
    looks = [
        ("btn", 3, {"hotShape": "square", "hotSize": 14}),
        ("btn", 4, {"hotShape": "diamond", "hotSize": 14, "hotFill": "half"}),
        ("btn", 5, {"hotShape": "triangle", "hotSize": 14}),
        ("btn", 21, {"hotShape": "ring", "hotSize": 16}),
        ("btn", 22, {"hotShape": "target", "hotSize": 16, "hotLine": "thick"}),
        ("btn", 1, {"hotShape": "crosshair", "hotSize": 20}),
        ("btn", 25, {"hotShape": "plus", "hotSize": 14}),
        ("btn", 23, {"hotShape": "x", "hotSize": 14, "hotLine": "thin"}),
        ("btn", 28, {"hotShape": "pin", "hotSize": 12, "hotNumber": True}),
        ("btn", 27, {"hotSize": 12, "hotHalo": True, "hotOpacity": 0.5}),
        ("btn", 29, {"hotShape": "none"}),
    ]
    for kind, hw, fields in looks:
        s.call("setSelection", [s.call("placedId", kind, hw)])
        for key, value in fields.items():
            s.call("applyField", key, value)
    s.call("setSelection", [])
    s.record("shapes", image=True)

    # Pressed: Button 3 lights its hotspot in the pressed colour.
    b3 = s.call("placedId", "btn", 3)
    s.call("setSelection", [b3])
    s.call("applyField", "hotPress", True)
    s.call("applyField", "hotPressColor", "#FF0000")
    s.call("setSelection", [])
    s.js("useFakeDevice", json.dumps([{"kind": "btn", "hwId": 3}]))
    s.set_prop("findOn", False)
    s.js("hold", "btn:3", 1)
    s.record("pressed", image=True)
    s.steps[-1]["state"]["pressed"] = s.call("hotPressed", s.node(b3))
    s.js("hold", "btn:3", 0)

    # Not on the live map: hidden once editing ends.
    s.call("setSelection", [b3])
    s.call("applyField", "hotLive", False)
    s.call("setSelection", [])
    s.js("setEditing", False)
    s.wait(200)
    s.record("live-map-without", image=True)
    s.steps[-1]["state"]["shown"] = s.call("hotShown", s.node(b3))


def scenario_export(s: Session) -> None:
    """Export: the whole page at twice the size, without the selection, its
    handles or the grid, and without hidden items. (The window then crops
    the page out with save_page_image, tested in test_button_map_export.)"""
    _load(s, "evo_r")
    chips = [n["id"] for n in s.state()["nodes"] if n["kind"] == "btn"]
    s.call("setLayerFlag", chips[1], "", "hidden", True)
    s.set_prop("gridOn", True)
    s.call("setSelection", [chips[0]])
    s.record("editing", image=True)

    raw = s.out_dir / "export-raw.png"
    s.js("exportGrab", str(raw), 2)
    for _ in range(100):
        if s.js("exportResult"):
            break
        s.wait(50)
    x, y, w, h = json.loads(s.js("exportResult"))
    page = s.out_dir / f"{s.name}-page.png"
    rect = QtCore.QRect(round(x), round(y), round(w), round(h))
    flat = QtGui.QImage(rect.size(), QtGui.QImage.Format.Format_RGB32)
    flat.fill(QtGui.QColor("#202020"))
    painter = QtGui.QPainter(flat)
    painter.drawImage(0, 0, QtGui.QImage(str(raw)).copy(rect))
    painter.end()
    ok = flat.save(str(page))
    raw.unlink()
    state = s.state()
    state["export"] = {"saved": ok, "size": [round(w), round(h)]}
    s.steps.append({"step": "exported", "state": state})
    # The editor is back as it was, marks and all.
    s.record("after", image=True)


SCENARIOS = {
    "load_l": scenario_load_l,
    "session_r": scenario_session_r,
    "api_sweep": scenario_api_sweep,
    "arrows": scenario_arrows,
    "menu": scenario_menu,
    "layers": scenario_layers,
    "transform": scenario_transform,
    "props": scenario_props,
    "align": scenario_align,
    "picture": scenario_picture,
    "export": scenario_export,
    "find": scenario_find,
    "labels": scenario_labels,
    "mirror": scenario_mirror,
    "turn": scenario_turn,
    "callout": scenario_callout,
    "paths": scenario_paths,
    "styles": scenario_styles,
    "photo_look": scenario_photo_look,
    "light_page": scenario_light_page,
    "zoom": scenario_zoom,
    "rulers": scenario_rulers,
    "to_pool": scenario_to_pool,
    "shape_tools": scenario_shape_tools,
    "hotspots": scenario_hotspots,
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
