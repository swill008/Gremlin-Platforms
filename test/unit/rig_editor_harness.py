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
    for name in ("evo_r", "evo_l")
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
    function state() {
        var e = ed()
        return JSON.stringify({
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
    s.record("draw-text")
    s.call("setDrawTool", "table")
    s.drag(s.point(0.74, 0.55), s.point(0.95, 0.85))
    s.record("draw-table", image=True)
    s.call("setDrawTool", "")

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


SCENARIOS = {
    "load_l": scenario_load_l,
    "session_r": scenario_session_r,
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
