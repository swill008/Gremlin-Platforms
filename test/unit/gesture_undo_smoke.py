# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Drives the Device Mapping Editor off-screen through one real mouse gesture of
each kind (07 S55a; D-07-GESTURE-UNDO) and prints, for each, how many undo
steps it made and whether one Undo put the map back exactly, as one JSON
object. test_gesture_undo.py runs it in its own process.

    python test/unit/gesture_undo_smoke.py

Every drag is pressed, moved in several steps (across other items, so the
item under the pointer changes on the way) and let go. It uses the golden
harness's window and session (rig_editor_harness.py) with its own steps.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PySide6 import QtCore, QtGui, QtQml, QtTest  # noqa: E402
from rig_editor_harness import ROOT, Session, _load  # noqa: E402
from smoke_exit import smoke_exit  # noqa: E402

QP = QtCore.QPoint
ALT = QtCore.Qt.KeyboardModifier.AltModifier
PICTURE = QtCore.QUrl.fromLocalFile(str(ROOT / "gfx" / "icon_large.png")).toString()


def _picture(id_: str, fx: float, fy: float, plane: str = "") -> dict:
    n = {
        "id": id_,
        "kind": "draw",
        "shape": "image",
        "fx": fx,
        "fy": fy,
        "fw": 0.07,
        "fh": 0.09,
        "fill": "filled",
        "color": "#14532D",
        "border": "#22C55E",
        "stroke": 2,
        "rot": 0,
        "opacity": 1,
        "src": "pictures/icon.png",
        "srcUrl": PICTURE,
    }
    if plane:
        n["plane"] = plane
    return n


def main() -> None:
    out: dict = {"gestures": {}}
    s = Session(Path("."), "gesture_undo")
    s.hold_runs()

    def qml(code: str) -> object:
        expr = QtQml.QQmlExpression(QtQml.qmlContext(s.win), s.win, code)
        value = expr.evaluate()
        return value[0] if isinstance(value, tuple) else value

    def ev(code: str) -> object:
        return json.loads(str(qml("JSON.stringify(" + code + ")")))

    def snap() -> str:
        return str(qml("ed().snapJson()"))

    def hist_at() -> int:
        return int(s.call_prop("histAt"))

    def hover() -> str:
        return str(qml("ed().overlayHoverId"))

    def ed_xy(fx: float, fy: float) -> list:
        return ev(f"[ed().fxToX({fx}), ed().fyToY({fy})]")

    def move(p: QP, mods: QtCore.Qt.KeyboardModifier, button: bool = True) -> None:
        event = QtGui.QMouseEvent(
            QtCore.QEvent.Type.MouseMove,
            QtCore.QPointF(p),
            QtCore.QPointF(s.win.mapToGlobal(p)),
            QtCore.Qt.MouseButton.NoButton,
            QtCore.Qt.MouseButton.LeftButton
            if button
            else QtCore.Qt.MouseButton.NoButton,
            mods,
        )
        QtCore.QCoreApplication.sendEvent(s.win, event)
        s.wait(15)

    def what_changed(before: str, after: str) -> list:
        """The fields a gesture changed: "<id>.<key>" for items, and the
        print area and guides by name."""
        a, b = json.loads(before), json.loads(after)
        out_ = [k for k in ("printArea", "guidesX", "guidesY") if a.get(k) != b.get(k)]
        na = {n["id"]: n for n in a["nodes"]}
        nb = {n["id"]: n for n in b["nodes"]}
        for id_ in sorted(set(na) | set(nb)):
            x, y = na.get(id_, {}), nb.get(id_, {})
            out_ += [
                f"{id_}.{k}" for k in sorted(set(x) | set(y)) if x.get(k) != y.get(k)
            ]
        return out_

    def restore(before: str) -> None:
        """Puts the map back where a gesture whose Undo fell short started,
        so the next gesture starts from the same map."""
        qml(
            "(function(){var e=ed(); e._restoring=true; e.applySnap("
            + json.dumps(before)
            + "); e.bump(); e._restoring=false; e.seedHist(); return 0})()"
        )
        s.wait(100)

    def gesture(
        name: str,
        start: QP,
        waypoints: list[QP],
        mods: QtCore.Qt.KeyboardModifier | None = None,
        esc_at: int = -1,
    ) -> dict:
        """Press at start, move through every waypoint in small steps, let
        go at the last one; then one Undo. esc_at: press Esc after that
        waypoint (the drag goes on to the end and is let go)."""
        mods = mods or QtCore.Qt.KeyboardModifier.NoModifier
        s._park_mouse()
        s.call("seedHist")
        before = snap()
        at0 = hist_at()
        s._mouse("mousePress", start, mods=mods)
        s.wait(20)
        hovers = [hover()]
        prev = start
        for k, wp in enumerate(waypoints):
            for i in range(1, 5):
                move(
                    QP(
                        prev.x() + (wp.x() - prev.x()) * i // 4,
                        prev.y() + (wp.y() - prev.y()) * i // 4,
                    ),
                    mods,
                )
                hovers.append(hover())
            prev = wp
            if k == esc_at:
                QtTest.QTest.keyClick(s.win, QtCore.Qt.Key.Key_Escape)
                s.wait(30)
        s._mouse("mouseRelease", prev, mods=mods)
        s.wait(80)
        s.end_run()
        after = snap()
        at1 = hist_at()
        s.call("undo")
        s.wait(60)
        undone = snap()
        res = {
            "steps": at1 - at0,
            "changed": after != before,
            "what": what_changed(before, after),
            "undo_exact": undone == before,
            "hover_changes": sum(1 for a, b in zip(hovers, hovers[1:]) if a != b),
        }
        out["gestures"][name] = res
        if undone != before:
            restore(before)
        return res

    _load(s, "evo_r")
    # The window's part (DialogDeviceMappingEditor.noteEditStep): a guide or
    # print area change in Edit is an undo step.
    qml("ed().rulerGuidesEdited.connect(function() { ed().pushHist() })")
    qml("ed().printAreaEdited.connect(function() { ed().pushHist() })")

    def add_draw(shape: str, fx0: float, fy0: float, fx1: float, fy1: float) -> str:
        a, b = ed_xy(fx0, fy0), ed_xy(fx1, fy1)
        s.call("addDrawFree", shape, a[0], a[1], b[0], b[1])
        return s.state()["selected"][0]

    shp = add_draw("rect", 0.04, 0.72, 0.10, 0.78)
    s.call("applyField", "fill", "filled")
    txt = add_draw("text", 0.30, 0.72, 0.40, 0.80)
    tbl = add_draw("table", 0.46, 0.72, 0.58, 0.82)
    arr = add_draw("arrow2", 0.04, 0.88, 0.14, 0.95)
    # Two small pictures (the editor's own size for a new one covers the
    # others): one in front, one behind.
    pic, bgpic = "gPic", "gBgPic"
    s.js(
        "setNodes",
        json.dumps(
            s.state()["nodes"]
            + [
                _picture(pic, 0.17, 0.72),
                _picture(bgpic, 0.66, 0.74, "background"),
                dict(_picture("gBgRect", 0.80, 0.72, "background"), shape="rect"),
            ]
        ),
    )
    s.wait(300)
    s.call("seedHist")
    s.call("setSelection", [])
    s.wait(300)
    out["ids"] = {
        "shp": shp,
        "txt": txt,
        "tbl": tbl,
        "arr": arr,
        "pic": pic,
        "bgpic": bgpic,
    }

    def c(id_: str, dx: float = 0, dy: float = 0) -> QP:
        return s.center(id_, dx, dy)

    def off(p: QP, dx: int, dy: int) -> QP:
        return QP(p.x() + dx, p.y() + dy)

    def edge_e(id_: str) -> QP:
        b = s._box(id_)
        return s.ed_point(b["x"] + b["w"], b["y"] + b["h"] / 2)

    # Over the picture, the text box and the table: the hover changes.
    cross = [c(pic), c(txt), c(tbl)]
    empty = s.point(0.62, 0.93)
    out["empty_hit"] = s.call("hitTest", *ed_xy(0.62, 0.93)).get("kind")

    # --- moves ----------------------------------------------------------
    b3 = s.center("b3")
    gesture("move_chip", b3, cross + [empty])
    s.call("setSelection", ["b4", "b5"])
    gesture("move_multi", s.center("b4"), cross + [empty])
    s.call("setSelection", ["b28", "b29"])
    s.call("groupSelection")
    grp = s.state()["selected"][0]
    s.call("seedHist")
    out["ids"]["grp"] = grp
    # A point on the group that takes the group, not a leader end.
    gb = s._box(grp)
    grab = None
    for gx in (0.25, 0.5, 0.75):
        for gy in (0.3, 0.5, 0.7):
            x, y = gb["x"] + gb["w"] * gx, gb["y"] + gb["h"] * gy
            if s.call("hitTest", x, y).get("kind") == "chip":
                grab = s.ed_point(x, y)
                break
        if grab:
            break
    out["group_grab"] = bool(grab)
    gesture("move_group", grab or s.center(grp), cross + [empty])
    s.call("setSelection", [])
    gesture("move_shape", c(shp), cross + [empty])
    gesture("move_picture", c(pic), [c(txt), c(tbl), empty])

    # --- resize: out past the item's own edge, back in, out again -------
    def to_and_fro(h: QP, horizontal: bool = False) -> list:
        dy = 0 if horizontal else 1
        return [off(h, 30, 22 * dy), off(h, -25, -18 * dy), off(h, 40, 26 * dy)]

    for id_, label in ((pic, "picture"), (txt, "text")):
        s.click(c(id_))
        gesture(f"resize_{label}_corner", s.corner(id_), to_and_fro(s.corner(id_)))
        s.click(c(id_))
        gesture(f"resize_{label}_edge", edge_e(id_), to_and_fro(edge_e(id_), True))

    # --- rotate handle ---------------------------------------------------
    s.click(c(shp))
    x, y, w, h = json.loads(s.js("drawPt", shp, 0, 0))
    hx, hy, _w, _h = json.loads(s.js("drawPt", shp, w / 2, -24))
    out["rotate_hit"] = s.call(
        "hitTest",
        *ev(
            f"(function(){{var p=ed().mapFromItem(null,{hx},{hy});return [p.x,p.y]}})()"
        ),
    ).get("handle")
    gesture("rotate", QP(round(hx), round(hy)), [c(pic), c(txt), off(c(shp), 0, 90)])

    # --- crop handle -----------------------------------------------------
    s.click(c(pic))
    s.call("toggleCrop")
    out["crop_on"] = s.call_prop("cropId") == pic
    corner = s.corner(pic)
    gesture("crop", corner, [off(corner, -20, -15), c(txt), off(corner, -12, -8)])
    s.set_prop("cropId", "")

    # --- skew handle -----------------------------------------------------
    s.call("setSelection", [arr])
    s.call("setTransformMode", "skew")
    kx, ky = json.loads(s.js("xfHandlePt", arr, "skewX"))
    out["skew_hit"] = s.call(
        "hitTest",
        *ev(
            f"(function(){{var p=ed().mapFromItem(null,{kx},{ky});return [p.x,p.y]}})()"
        ),
    ).get("handle")
    gesture(
        "skew",
        QP(round(kx), round(ky)),
        [c(shp), c(pic), QP(round(kx) + 30, round(ky))],
    )
    s.call("setTransformMode", "resize")
    s.call("setSelection", [])

    # --- leader end and bend point --------------------------------------
    fp = ev(
        "(function(){var n=ed().nodeAt('b3');"
        "var p=ed().endPt(ed().leaderList(n)[0].from);return [p.x,p.y]})()"
    )
    out["from_hit"] = s.call("hitTest", fp[0], fp[1]).get("kind")
    gesture("leader_end", s.ed_point(fp[0], fp[1]), cross + [empty])
    s.call("setSelection", ["b3"])
    s.set_prop("selectedLeader", 0)
    s.set_prop("selectedSeg", 0)
    sp = ev(
        "(function(){var L=ed().leaderList(ed().nodeAt('b3'))[0];"
        "return [ed().fxToX(L.spines[0].fx), ed().fyToY(L.spines[0].fy)]})()"
    )
    out["spine_hit"] = s.call("hitTest", sp[0], sp[1]).get("kind")
    gesture("leader_bend", s.ed_point(sp[0], sp[1]), cross + [empty])

    # --- hotspot ---------------------------------------------------------
    s.call("setSelection", [])
    hp = ev("(function(){var p=ed().hotPt(ed().nodeAt('b3'));return [p.x,p.y]})()")
    out["hot_hit"] = s.call("hitTest", hp[0], hp[1]).get("kind")
    gesture("hotspot", s.ed_point(hp[0], hp[1]), cross + [empty])

    # --- ruler guide: dragged out of the ruler, then moved ---------------
    s.js("setRulers", True)
    s.wait(200)
    ruler = QP(s.point(0.5, 0.3).x(), 9)
    gesture("guide_new", ruler, [c(pic), c(txt), s.point(0.5, 0.66)])
    s.call("addRulerGuide", "y", 0.66)
    s.call("seedHist")
    on_guide = s.point(0.97, 0.66)
    gx, gy = ed_xy(0.97, 0.66)
    out["guide_hit"] = bool(ev(f"ed().rulerGuideAt({gx}, {gy})"))
    gesture("guide_move", on_guide, [c(pic), c(txt), s.point(0.97, 0.6)])
    s.js("setRulers", False)
    s.wait(200)

    # --- print area: Alt+drag from an empty part, then its frame moved ---
    s.set_prop("printAreaShown", True)
    s.call("setSelection", [])
    gesture(
        "print_area_draw", empty, [c(tbl), c(txt), c(pic), s.point(0.02, 0.62)], ALT
    )
    s.call("redo")
    out["print_area"] = s.call_prop("printArea")
    r = ev("ed().printAreaRect()")
    top = s.ed_point(r["x"] + r["w"] / 2, r["y"])
    gesture("print_area_move", top, [c(pic), c(txt), off(top, 0, 25)])
    s.set_prop("printAreaShown", False)

    # --- Background mode: the picture moved and resized ------------------
    s.set_prop("editPlane", "background")
    s.call("setSelection", [])
    gesture("bg_move_picture", c(bgpic), [c("gBgRect"), s.point(0.92, 0.90)])
    s.click(c(bgpic))
    gesture("bg_resize_picture", s.corner(bgpic), to_and_fro(s.corner(bgpic)))
    s.set_prop("editPlane", "foreground")

    # --- a hover with no drag saves no step ------------------------------
    s._park_mouse()
    s.call("seedHist")
    at0 = hist_at()
    before = snap()
    hovers = [hover()]
    prev = c(shp)
    for wp in cross + [c(shp), empty]:
        for i in range(1, 5):
            move(
                QP(
                    prev.x() + (wp.x() - prev.x()) * i // 4,
                    prev.y() + (wp.y() - prev.y()) * i // 4,
                ),
                QtCore.Qt.KeyboardModifier.NoModifier,
                button=False,
            )
            hovers.append(hover())
        prev = wp
    s.end_run()
    out["hover_only"] = {
        "steps": hist_at() - at0,
        "changed": snap() != before,
        "hover_changes": sum(1 for a, b in zip(hovers, hovers[1:]) if a != b),
    }

    # --- a run of arrow nudges stays one step -----------------------------
    s.click(c(shp))
    s.call("seedHist")
    at0 = hist_at()
    before = snap()
    for _ in range(5):
        s.key(QtCore.Qt.Key.Key_Right)
    s.key(QtCore.Qt.Key.Key_Down)
    s.end_run()
    at1 = hist_at()
    changed = snap() != before
    s.call("undo")
    out["nudges"] = {
        "steps": at1 - at0,
        "changed": changed,
        "undo_exact": snap() == before,
    }

    # --- Esc during a drag -------------------------------------------------
    s.call("setSelection", [])
    gesture("esc_move_picture", c(pic), [c(txt), c(tbl), empty], esc_at=1)
    out["esc_drag_kind_after"] = s.call_prop("dragKind")

    out["warnings"] = sorted(set(s.warnings))
    print("GESTUREUNDO " + json.dumps(out))
    smoke_exit(0)


if __name__ == "__main__":
    main()
