# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Drives the Device Mapping Editor off-screen through more of the background
and foreground planes (07 S94, S118, S122; D-07-BACKGROUND-PLANES) and prints
what it saw as one JSON object. test_planes_editor_more.py runs it in its own
process.

    python test/unit/planes_editor_more_smoke.py

It uses the golden harness's window and session (rig_editor_harness.py),
with its own steps; the harness's scenarios are untouched.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PySide6 import QtCore, QtGui, QtQml  # noqa: E402
from rig_editor_harness import ROOT, Session, _load  # noqa: E402
from smoke_exit import smoke_exit  # noqa: E402

SHIFT = QtCore.Qt.KeyboardModifier.ShiftModifier
# b3's first leader's "to" end, as an editor point.
END_PT = (
    "(function(){var p=ed().endPt(ed().leaderList(ed().nodeAt('b3'))[0].to);"
    "return [p.x,p.y]})()"
)
PICTURE = QtCore.QUrl.fromLocalFile(str(ROOT / "gfx" / "icon_large.png")).toString()


def _rect(id_: str, fx: float, fy: float, plane: str = "", fw: float = 0.06) -> dict:
    n = {
        "id": id_,
        "kind": "draw",
        "shape": "rect",
        "fx": fx,
        "fy": fy,
        "fw": fw,
        "fh": 0.06,
        "fill": "filled",
        "color": "#14532D",
        "border": "#22C55E",
        "stroke": 2,
        "rot": 0,
        "opacity": 1,
    }
    if plane:
        n["plane"] = plane
    return n


def _picture(id_: str, fx: float, fy: float, plane: str = "") -> dict:
    n = _rect(id_, fx, fy, plane, fw=0.08)
    n.update(
        {
            "shape": "image",
            "src": "pictures/icon.png",
            "srcUrl": PICTURE,
            "sockets": [{"id": "s1", "ux": 0.5, "uy": 0.5, "chipId": ""}],
        }
    )
    return n


def main() -> None:
    out: dict = {}
    s = Session(Path("."), "planes_more")
    s.hold_runs()

    def qml(code: str) -> object:
        expr = QtQml.QQmlExpression(QtQml.qmlContext(s.win), s.win, code)
        value = expr.evaluate()
        return value[0] if isinstance(value, tuple) else value

    def ev(code: str) -> object:
        return json.loads(str(qml("JSON.stringify(" + code + ")")))

    def box(id_: str) -> dict:
        return s._box(id_)

    _load(s, "evo_r")
    doc = s.state()["nodes"]
    doc = doc + [
        _rect("bgA", 0.30, 0.20, "background"),
        _rect("bgB", 0.45, 0.32, "background", fw=0.10),
        _rect("bgC", 0.62, 0.26, "background"),
        _picture("bgPic", 0.30, 0.55, "background"),
        _rect("fgR", 0.40, 0.42),
        _picture("fgPic", 0.60, 0.55),
    ]
    s.js("setNodes", json.dumps(doc))
    s.wait(400)
    s.call("seedHist")

    # --- S118: Align and Distribute in Background mode ---------------------
    s.set_prop("editPlane", "background")
    s.call("setSelection", [])
    s.click(s.center("bgA"))
    s.click(s.center("bgB"), SHIFT)
    s.click(s.center("bgC"), SHIFT)
    # Shift-clicking a foreground item in Background mode adds nothing.
    s.click(s.center("fgR"), SHIFT)
    out["bg_selected"] = sorted(s.state()["selected"])
    out["can_align"] = s.call("canAlign")
    out["can_distribute"] = s.call("canDistribute")
    # The right-click menu offers Align and Distribute there.
    s.right_click(s.center("bgB"))
    out["menu_has_align"] = any(
        "Align and Distribute" in ln for ln in str(s.state()["menu"]).splitlines()
    )
    s.close_menus()
    fg_before = box("fgR")
    chip_before = (s.node("b3")["chipFx"], s.node("b3")["chipFy"])
    s.call("setSelection", ["bgA", "bgB", "bgC"])
    s.call("alignSelection", "left")
    out["left_xs"] = [round(box(i)["x"], 2) for i in ("bgA", "bgB", "bgC")]
    s.call("alignSelection", "top")
    out["top_ys"] = [round(box(i)["y"], 2) for i in ("bgA", "bgB", "bgC")]
    # Spread them out again, then distribute across.
    for id_, fx in (("bgA", 0.20), ("bgB", 0.32), ("bgC", 0.70)):
        s.call_on_node("moveNodeBy", id_, fx - s.node(id_)["fx"], 0)
    s.call("setSelection", ["bgA", "bgB", "bgC"])
    s.call("distributeSelection", "h")
    bs = sorted((box(i) for i in ("bgA", "bgB", "bgC")), key=lambda b: b["x"])
    out["gaps_h"] = [
        round(bs[1]["x"] - (bs[0]["x"] + bs[0]["w"]), 1),
        round(bs[2]["x"] - (bs[1]["x"] + bs[1]["w"]), 1),
    ]
    out["fg_moved"] = box("fgR") != fg_before
    out["chip_moved"] = (s.node("b3")["chipFx"], s.node("b3")["chipFy"]) != chip_before
    out["planes_after_align"] = [
        s.node(i).get("plane", "") for i in ("bgA", "bgB", "bgC", "fgR")
    ]

    # --- S94: zoom the same in both modes ----------------------------------
    def view() -> dict:
        return json.loads(s.js("viewState"))

    def wheel(at: QtCore.QPoint, dy: int) -> None:
        pt = QtCore.QPointF(at)
        event = QtGui.QWheelEvent(
            pt,
            QtCore.QPointF(s.win.mapToGlobal(at)),
            QtCore.QPoint(0, 0),
            QtCore.QPoint(0, dy),
            QtCore.Qt.MouseButton.NoButton,
            QtCore.Qt.KeyboardModifier.NoModifier,
            QtCore.Qt.ScrollPhase.NoScrollPhase,
            False,
        )
        QtCore.QCoreApplication.sendEvent(s.win, event)
        s.wait(60)

    zoom: dict = {}
    for plane in ("foreground", "background"):
        s.set_prop("editPlane", plane)
        s.call("setSelection", [])
        s.js("zoomToPage")
        s.wait(100)
        page = view()
        at = s.point(0.5, 0.5)
        wheel(at, 120)
        once = view()
        for _ in range(60):
            wheel(s.point(0.5, 0.5), 120)
        top = view()
        for _ in range(120):
            wheel(s.point(0.5, 0.5), -120)
        bottom = view()
        # Zoom to selection on one of this plane's items.
        s.js("zoomToPage")
        s.wait(100)
        s.call("setSelection", ["bgA" if plane == "background" else "fgR"])
        zsel = s.call("zoomToSelection")
        s.wait(100)
        zoom[plane] = {
            "page": page["zoom"],
            "once": once["zoom"],
            "max": top["zoom"],
            "min": bottom["zoom"],
            "to_selection": [zsel, view()["zoom"]],
        }
    out["zoom"] = zoom
    out["zoom_limits"] = ev("[ed().face.zoomMin, ed().face.zoomMax, ed().face.zoomFit]")
    # Switching plane keeps the zoom and the pan.
    s.set_prop("editPlane", "background")
    s.js("setZoom", 3.0, -40, -30)
    s.wait(100)
    before = view()
    s.set_prop("editPlane", "foreground")
    s.wait(100)
    mid = view()
    s.set_prop("editPlane", "background")
    s.wait(100)
    out["zoom_kept"] = [before, mid, view()]
    s.js("resetView")
    s.wait(200)

    # --- S122: a leader end snaps to a picture's snap point -----------------
    s.set_prop("editPlane", "foreground")
    s.call("setSelection", [])

    def drop_end_near(pic: str, end_fx: float, end_fy: float) -> dict:
        nodes = s.state()["nodes"]
        for n in nodes:
            if n["id"] == "b3":
                n.pop("leaders", None)
                n["to"] = {"type": "free", "fx": end_fx, "fy": end_fy}
        s.js("setNodes", json.dumps(nodes))
        s.wait(300)
        sock = ev(
            f"(function(){{var n=ed().nodeAt('{pic}');"
            "var p=ed().socketWorld(n,n.sockets[0]);return [p.x,p.y]})()"
        )
        endp = ev(END_PT)
        hit = s.call("hitTest", endp[0], endp[1])
        start = s.ed_point(endp[0], endp[1])
        target = s.ed_point(sock[0] + 4, sock[1] + 3)
        s._mouse("mousePress", start)
        s.wait(20)
        for i in range(1, 7):
            p = QtCore.QPoint(
                start.x() + (target.x() - start.x()) * i // 6,
                start.y() + (target.y() - start.y()) * i // 6,
            )
            event = QtGui.QMouseEvent(
                QtCore.QEvent.Type.MouseMove,
                QtCore.QPointF(p),
                QtCore.QPointF(s.win.mapToGlobal(p)),
                QtCore.Qt.MouseButton.NoButton,
                QtCore.Qt.MouseButton.LeftButton,
                QtCore.Qt.KeyboardModifier.NoModifier,
            )
            QtCore.QCoreApplication.sendEvent(s.win, event)
            s.wait(15)

        def end_now() -> list:
            p = ev(END_PT)
            return [round(p[0] - sock[0], 1), round(p[1] - sock[1], 1)]

        during = end_now()
        s._mouse("mouseRelease", target)
        s.wait(80)
        after = end_now()
        to = s.node("b3").get("to") or {}
        return {
            "hit": hit.get("kind"),
            "during": during,
            "after": after,
            "to": {k: to.get(k) for k in ("type", "id", "pin")},
        }

    out["leader_bg"] = drop_end_near("bgPic", 0.20, 0.50)
    out["leader_fg"] = drop_end_near("fgPic", 0.50, 0.50)
    out["plane_while_snapping"] = s.state()["editPlane"]

    out["warnings"] = sorted(set(s.warnings))
    print("PLANESMORE " + json.dumps(out))
    smoke_exit(0)


if __name__ == "__main__":
    main()
