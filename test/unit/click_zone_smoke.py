# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Drives the Device Mapping Editor off-screen at the lowest zoom (50 %) and
clicks in the bands of the view outside the map's box: right-click menus,
picking a picture that hangs past the page, box select, middle-drag pan,
Space pan, wheel zoom, a ruler guide drag and the click trace's position.
Prints the results as JSON; test_click_zone.py runs it in its own process.

    python test/unit/click_zone_smoke.py <folder>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from smoke_exit import smoke_exit

sys.path.insert(0, str(Path(__file__).parent))

import rig_editor_harness as h  # noqa: E402
from PySide6 import QtCore, QtGui, QtQml, QtTest  # noqa: E402

Q = QtCore.Qt


class _Trace(QtCore.QObject):
    """Stands in for gremlin.ui.click_trace's clickTrace context object."""

    def __init__(self) -> None:
        super().__init__()
        self.lines: list[str] = []

    @QtCore.Property(bool, constant=True)
    def on(self) -> bool:
        return True

    @QtCore.Slot(str)
    def line(self, text: str) -> None:
        self.lines.append(text)

    @QtCore.Slot(str)
    def closingFor(self, reason: str) -> None:  # noqa: N802
        pass

    @QtCore.Slot(str, str)
    def menu(self, what: str, title: str) -> None:
        pass


def main() -> None:
    folder = Path(sys.argv[1])
    s = h.Session(folder, "click_zone")
    trace = _Trace()
    s.engine.rootContext().setContextProperty("clickTrace", trace)
    s.hold_runs()
    h._load(s, "evo_r")
    out: dict = {}

    def qml(code: str) -> object:
        expr = QtQml.QQmlExpression(QtQml.qmlContext(s.win), s.win, code)
        value = expr.evaluate()
        return value[0] if isinstance(value, tuple) else value

    def ev(code: str) -> object:
        return json.loads(str(qml("JSON.stringify(" + code + ")")))

    def view() -> dict:
        return json.loads(s.js("viewState"))

    def menu_open() -> bool:
        return bool(s.state()["menu"])

    zmin = float(ev("_face.zoomMin"))
    W, H = 1600, 900

    def low_zoom() -> None:
        s.js("setZoom", zmin, 0, 0)
        s.wait(150)

    low_zoom()
    tl = s.ed_point(0, 0)
    br = s.ed_point(W, H)
    out["world"] = [tl.x(), tl.y(), br.x(), br.y()]
    below = QtCore.QPoint(W // 2, (br.y() + H) // 2)
    right = QtCore.QPoint((br.x() + W) // 2, H // 2)
    corner = QtCore.QPoint(W - 8, H - 8)
    out["points"] = [[p.x(), p.y()] for p in (below, right, corner)]

    # Right-click in the bands outside the map's box opens the menu.
    menus = {}
    for name, p in (("below", below), ("right", right), ("corner", corner)):
        s.close_menus()
        s.right_click(p)
        menus[name] = menu_open()
    s.close_menus()
    out["menus"] = menus

    # The click trace logs the press in editor coordinates.
    trace.lines.clear()
    s.right_click(below)
    s.close_menus()
    want = ev(f"[_face.editorX({below.x()}), _face.editorY({below.y()})]")
    out["trace"] = {
        "lines": list(trace.lines),
        "want": [round(want[0]), round(want[1])],
    }

    # A picture that hangs past the page's left edge: a left click on the
    # part outside the map's box selects it.
    s.set_prop("editPlane", "background")
    bg = s.call(
        "addOverlay",
        "test/icon",
        h._file_url(h.ROOT / "test" / "unit" / "fixtures" / "icon_large.png"),
        {"plane": "background", "fitFrame": True, "aspect": 1},
    )
    s.call("setSelection", [bg])
    s.wait(200)
    s.call("setProp", "x", -40)
    s.wait(200)
    b = s._box(bg)
    s.call("setSelection", [])
    s.wait(100)
    # Left of the page, inside the view and on the picture.
    out_pt = s.ed_point(max(b["x"] + 15, -150), b["y"] + b["h"] / 2)
    s.click(out_pt)
    out["picture"] = {
        "box": [b["x"], b["x"] + b["w"]],
        "click": [out_pt.x(), out_pt.y()],
        "selected": s.call_prop("selectedIds"),
        "id": bg,
    }
    s.call("setSelection", [])
    s.set_prop("editPlane", "chips")
    s.wait(100)

    # Box select that starts outside the map's box picks the chips it covers.
    s.call("setSelection", [])
    s.wait(60)
    s.drag(QtCore.QPoint(8, 8), QtCore.QPoint(W // 2, H // 2))
    out["band"] = s.call_prop("selectedIds")
    s.call("setSelection", [])

    # Middle-drag pans from outside the map's box and over it.
    def mid_drag(a: QtCore.QPoint, d: QtCore.QPoint) -> list:
        low_zoom()
        QtTest.QTest.mousePress(
            s.win, Q.MouseButton.MiddleButton, Q.KeyboardModifier.NoModifier, a
        )
        s.wait(20)
        for i in range(1, 9):
            p = QtCore.QPoint(a.x() + d.x() * i // 8, a.y() + d.y() * i // 8)
            e = QtGui.QMouseEvent(
                QtCore.QEvent.Type.MouseMove,
                QtCore.QPointF(p),
                QtCore.QPointF(s.win.mapToGlobal(p)),
                Q.MouseButton.NoButton,
                Q.MouseButton.MiddleButton,
                Q.KeyboardModifier.NoModifier,
            )
            QtCore.QCoreApplication.sendEvent(s.win, e)
            s.wait(15)
        end = QtCore.QPoint(a.x() + d.x(), a.y() + d.y())
        QtTest.QTest.mouseRelease(
            s.win, Q.MouseButton.MiddleButton, Q.KeyboardModifier.NoModifier, end
        )
        s.wait(80)
        return view()["pan"]

    out["midpan"] = {
        "outside": mid_drag(below, QtCore.QPoint(60, -40)),
        "inside": mid_drag(QtCore.QPoint(W // 2, H // 2), QtCore.QPoint(60, -40)),
    }

    # Space + left-drag pans from outside the map's box.
    low_zoom()
    qml("_face.spaceHeld = true")
    s.drag(below, QtCore.QPoint(below.x() + 60, below.y() - 40))
    qml("_face.spaceHeld = false")
    out["spacepan"] = {"pan": view()["pan"], "selected": s.call_prop("selectedIds")}

    # The wheel zooms with the pointer outside the map's box.
    def wheel(at: QtCore.QPoint, dy: int) -> float:
        low_zoom()
        e = QtGui.QWheelEvent(
            QtCore.QPointF(at),
            QtCore.QPointF(s.win.mapToGlobal(at)),
            QtCore.QPoint(0, 0),
            QtCore.QPoint(0, dy),
            Q.MouseButton.NoButton,
            Q.KeyboardModifier.NoModifier,
            Q.ScrollPhase.NoScrollPhase,
            False,
        )
        QtCore.QCoreApplication.sendEvent(s.win, e)
        s.wait(80)
        return view()["zoom"]

    out["wheel"] = {
        "min": round(zmin, 2),
        "outside": wheel(below, 240),
        "inside": wheel(QtCore.QPoint(W // 2, H // 2), 240),
    }

    # Rulers on: a drag out of the top ruler adds a guide.
    low_zoom()
    s.js("setRulers", True)
    s.wait(150)
    before = len(s.call_prop("rulerGuidesY") or [])
    s.drag(QtCore.QPoint(W // 2, 8), QtCore.QPoint(W // 2, H // 2))
    out["ruler"] = [before, len(s.call_prop("rulerGuidesY") or [])]
    s.js("setRulers", False)

    # The Properties panel over the view still takes its own clicks.
    low_zoom()
    s.js("showProps", True)
    s.wait(150)
    chips = [n["id"] for n in s.state()["nodes"] if n["kind"] == "btn"]
    s.call("setSelection", [chips[0]])
    s.wait(100)
    s.click(QtCore.QPoint(150, 40))
    out["panel"] = s.call_prop("selectedIds")
    s.js("showProps", False)

    out["warnings"] = sorted(set(s.warnings))
    print("RESULT " + json.dumps(out), flush=True)
    smoke_exit(0)


if __name__ == "__main__":
    main()
