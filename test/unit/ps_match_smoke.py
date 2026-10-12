# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Drives the Device Mapping Editor off-screen through the Photoshop-match
keys and handles (07 S140-S155) with real mouse and key events, and prints
what it measured as JSON; test_ps_match.py runs it in its own process.

Every drag is measured where things are drawn: the eight handles and the
picture as painted, in window pixels, through the real QML items.

    python test/unit/ps_match_smoke.py <folder> [section,section,...]
"""

from __future__ import annotations

import json
import math
import sys
import traceback
from pathlib import Path
from typing import Any, cast

from smoke_exit import smoke_exit

sys.path.insert(0, str(Path(__file__).parent))

import rig_editor_harness as h  # noqa: E402
from PySide6 import QtCore, QtGui, QtQuick, QtTest  # noqa: E402

Q = QtCore.Qt
Mod = Q.KeyboardModifier
Key = Q.Key
P = QtCore.QPoint


def _c(s: h.Session, name: str, *args: object) -> Any:  # noqa: ANN401
    """An editor call; its JSON result, untyped."""
    return s.call(name, *args)


def _cn(s: h.Session, name: str, id_: str, *args: object) -> Any:  # noqa: ANN401
    return s.call_on_node(name, id_, *args)


def _prop_of(s: h.Session, name: str) -> Any:  # noqa: ANN401
    return s.call_prop(name)


def _js(s: h.Session, fn: str, *args: object) -> Any:  # noqa: ANN401
    return s.js(fn, *args)


def _win(s: h.Session) -> QtQuick.QQuickWindow:
    return cast(QtQuick.QQuickWindow, s.win)


# Where things are drawn, read from the real items (window pixels).
_EXTRA = b"""
    function _psFind(o) {
        if (!o)
            return null
        if (o.bigSide !== undefined && o.screenSide !== undefined)
            return o
        if (o.item !== undefined && o.item) {
            var r0 = _psFind(o.item)
            if (r0)
                return r0
        }
        for (var i = 0; i < o.children.length; i++) {
            var r = _psFind(o.children[i])
            if (r)
                return r
        }
        return null
    }
    function _psImage(o) {
        if (o.paintedWidth !== undefined && o.fillMode !== undefined
                && o.sourceSize !== undefined)
            return o
        for (var i = 0; i < o.children.length; i++) {
            var r = _psImage(o.children[i])
            if (r)
                return r
        }
        return null
    }
    // A drawing's box corners, its resize handles (centre and place as a
    // fraction of the box) and, for a picture, the part painted on screen.
    function psDrawn(id) {
        var e = ed()
        var it = e._chipsItem(e.nodeIndex(id))
        var root = it ? _psFind(it) : null
        if (!root)
            return "null"
        function pt(item, x, y) {
            var p = item.mapToItem(null, x, y)
            return [p.x, p.y]
        }
        var W = root.width, H = root.height
        var out = { box: [pt(root, 0, 0), pt(root, W, 0),
                          pt(root, W, H), pt(root, 0, H)],
                    handles: [], pic: null, status: -1,
                    rot: pt(root, W / 2, -e.rotateHandleOffset) }
        for (var i = 0; i < root.children.length; i++) {
            var c = root.children[i]
            if (!c.visible || c.z !== 4 || c.width <= 0 || c.height <= 0)
                continue
            var cx = c.x + c.width / 2, cy = c.y + c.height / 2
            out.handles.push({ fx: W ? cx / W : 0, fy: H ? cy / H : 0,
                               at: pt(root, cx, cy) })
        }
        var im = _psImage(root)
        if (im && im.parent && im.parent.visible) {
            var box = im.parent
            out.status = im.status
            var pw = im.paintedWidth, ph = im.paintedHeight
            var x0 = im.x + (im.width - pw) / 2, y0 = im.y + (im.height - ph) / 2
            var x1 = x0 + pw, y1 = y0 + ph
            if (box.clip) {
                x0 = Math.max(x0, 0); y0 = Math.max(y0, 0)
                x1 = Math.min(x1, box.width); y1 = Math.min(y1, box.height)
            }
            out.pic = [pt(box, x0, y0), pt(box, x1, y0),
                       pt(box, x1, y1), pt(box, x0, y1)]
        }
        return JSON.stringify(out)
    }
    function psWinEd(x, y) {
        var p = ed().mapFromItem(null, x, y)
        return JSON.stringify([p.x, p.y])
    }
    // The Properties link button's middle in window pixels, or null. It
    // sits in a Repeater row, which findChild can't reach.
    function psLinkCentre() {
        function find(o) {
            if (o.objectName === "propLinkSize" && o.visible)
                return o
            for (var i = 0; i < o.children.length; i++) {
                var r = find(o.children[i])
                if (r)
                    return r
            }
            return null
        }
        var link = find(_props)
        if (!link)
            return "null"
        var p = link.mapToItem(null, link.width / 2, link.height / 2)
        return JSON.stringify([p.x, p.y])
    }
    function psSetAspectFn(a) {
        ed().imageAspectFn = a > 0 ? function(rel) { return a } : null
    }
}
"""
h._HOST = h._HOST.rstrip()[:-1] + _EXTRA

SIDES = ("nw", "ne", "sw", "se", "n", "s", "w", "e")


# --- set-up -----------------------------------------------------------------


def _load(s: h.Session) -> None:
    """The right-hand layout with one chip (b3) left on it, snapping off."""
    doc = json.loads(h.LAYOUTS["evo_r"].read_text(encoding="utf-8"))
    nodes = [n for n in doc.get("nodes") or [] if n.get("id") == "b3"]
    s.js("setNodes", json.dumps(nodes))
    s.wait(200)
    s.js("resetView")
    s.js("setEditing", True)
    s.wait(200)
    _c(s, "seedHist")
    s.set_prop("snapOn", False)
    s.set_prop("snapEntOn", False)
    _c(s, "setTransformMode", "resize")


def _image(folder: Path, w: int, hgt: int) -> Path:
    p = folder / f"ps_pic_{w}x{hgt}.png"
    if not p.exists():
        img = QtGui.QImage(w, hgt, QtGui.QImage.Format.Format_RGB32)
        img.fill(QtGui.QColor("#d04040"))
        img.save(str(p))
    return p


def _url(p: Path) -> str:
    return QtCore.QUrl.fromLocalFile(str(p)).toString()


def add_picture(
    s: h.Session, folder: Path, kind: str = "2to1", fx: float = 0.5, fy: float = 0.45
) -> str:
    """kind "2to1": a 400 x 200 picture given its 2:1 shape; "import": a
    300 x 400 picture added as Import Picture adds it, its shape read from
    the file (as the window's imageAspect does)."""
    if kind == "2to1":
        p = _image(folder, 400, 200)
        aspect = 2.0
    else:
        p = _image(folder, 300, 400)
        size = QtGui.QImageReader(str(p)).size()
        aspect = size.width() / max(1, size.height())
    _c(s, "addOverlay", "ps/" + p.name, _url(p), {"aspect": aspect, "fx": fx, "fy": fy})
    pid = s.state()["selected"][0]
    deadline = QtCore.QDeadlineTimer(4000)
    while (drawn(s, pid) or {}).get("status") != 1 and not deadline.hasExpired():
        s.wait(30)
    _c(s, "setSelection", [pid])
    s.wait(60)
    return pid


def add_rect(s: h.Session, x: int, y: int, w: int, hgt: int, tool: str = "rect") -> str:
    """A shape drawn with its tool, from window point (x, y), w x hgt pixels."""
    _c(s, "setDrawTool", tool)
    s.drag(P(x, y), P(x + w, y + hgt))
    _c(s, "setDrawTool", "")
    rid = s.state()["selected"][0]
    _c(s, "applyField", "fill", "filled")
    _c(s, "setSelection", [rid])
    s.wait(60)
    return rid


# --- reading ----------------------------------------------------------------


def drawn(s: h.Session, id_: str) -> Any:  # noqa: ANN401
    return json.loads(_js(s, "psDrawn", id_))


def _name(hd: dict) -> str:
    fx, fy = hd["fx"], hd["fy"]
    return ("n" if fy < 0.25 else "s" if fy > 0.75 else "") + (
        "w" if fx < 0.25 else "e" if fx > 0.75 else ""
    )


def handles(s: h.Session, id_: str) -> dict[str, list[float]]:
    d = drawn(s, id_) or {}
    return {_name(hd): hd["at"] for hd in d.get("handles") or []}


def handle_pt(s: h.Session, id_: str, name: str) -> P:
    x, y = handles(s, id_)[name]
    return P(round(x), round(y))


def box(s: h.Session, id_: str) -> dict:
    return s._box(id_)


def win_ed(s: h.Session, p: P) -> tuple[float, float]:
    x, y = json.loads(_js(s, "psWinEd", p.x(), p.y()))
    return x, y


def _seg_dist(p: list[float], a: list[float], b: list[float]) -> float:
    ax, ay, bx, by = a[0], a[1], b[0], b[1]
    dx, dy = bx - ax, by - ay
    ll = dx * dx + dy * dy
    t = (
        0.0
        if ll == 0
        else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / ll))
    )
    return math.hypot(p[0] - (ax + t * dx), p[1] - (ay + t * dy))


def edge_off(d: dict) -> float:
    """The largest distance from a drawn handle to the drawn picture's edge
    (a corner handle: to the picture's nearest corner)."""
    quad = d.get("pic") or d["box"]
    worst = 0.0
    for hd in d.get("handles") or []:
        p = hd["at"]
        if len(_name(hd)) == 2:
            off = min(math.hypot(p[0] - q[0], p[1] - q[1]) for q in quad)
        else:
            off = min(_seg_dist(p, quad[i], quad[(i + 1) % 4]) for i in range(4))
        worst = max(worst, off)
    return round(worst, 2)


def hist(s: h.Session) -> list[int]:
    st = s.state()
    return [st["histLen"], st["histAt"]]


def node(s: h.Session, id_: str) -> dict:
    return s.node(id_)


def ratio(b: dict) -> float:
    return b["w"] / max(1e-9, b["h"])


def centre(b: dict) -> list[float]:
    return [b["x"] + b["w"] / 2, b["y"] + b["h"] / 2]


def quad_centre(q: list[list[float]]) -> list[float]:
    return [sum(p[0] for p in q) / 4, sum(p[1] for p in q) / 4]


def _r(v: float) -> float:
    return round(v, 3)


# --- input ------------------------------------------------------------------


def press(s: h.Session, p: P, mods: Q.KeyboardModifier = Mod.NoModifier) -> None:
    s._mouse("mousePress", p, mods=mods)
    s.wait(40)


def move(s: h.Session, p: P, mods: Q.KeyboardModifier = Mod.NoModifier) -> None:
    ev = QtGui.QMouseEvent(
        QtCore.QEvent.Type.MouseMove,
        QtCore.QPointF(p),
        QtCore.QPointF(_win(s).mapToGlobal(p)),
        Q.MouseButton.NoButton,
        Q.MouseButton.LeftButton,
        mods,
    )
    QtCore.QCoreApplication.sendEvent(_win(s), ev)
    s.wait(25)


def release(s: h.Session, p: P, mods: Q.KeyboardModifier = Mod.NoModifier) -> None:
    s._mouse("mouseRelease", p, mods=mods)
    s.wait(100)


def drag(
    s: h.Session,
    start: P,
    dx: int,
    dy: int,
    mods: Q.KeyboardModifier = Mod.NoModifier,
    steps: int = 6,
    press_mods: Q.KeyboardModifier | None = None,
) -> P:
    press(s, start, mods if press_mods is None else press_mods)
    end = P(start.x() + dx, start.y() + dy)
    for i in range(1, steps + 1):
        move(s, P(start.x() + dx * i // steps, start.y() + dy * i // steps), mods)
    release(s, end, mods)
    return end


def esc(s: h.Session) -> None:
    QtTest.QTest.keyClick(_win(s), Key.Key_Escape)
    s.wait(60)


# --- 07 S140: handles on the picture's edges, every step ---------------------


def _skew(s: h.Session, pid: str) -> None:
    _c(s, "setTransformMode", "skew")
    g = _c(s, "drawGeom", _c(s, "nodeAt", pid))
    _cn(s, "dragTransform", pid, "skewX", g["x"] + g["w"] / 2 - 40, g["y"])
    _cn(s, "dragTransform", pid, "skewY", g["x"] + g["w"], g["y"] + g["h"] / 2 + 30)
    _c(s, "setTransformMode", "resize")
    _c(s, "setSelection", [pid])
    _c(s, "bump")
    s.wait(80)


def _steps(name: str) -> list[tuple[int, int]]:
    ox = 1 if "e" in name else (-1 if "w" in name else 0)
    oy = 1 if "s" in name else (-1 if "n" in name else 0)
    out = []
    for k in (3, 8, 15, 25, 40, 30, 12, -6):
        out.append(
            (ox * k + (k // 4 if ox == 0 else 0), oy * k + (k // 5 if oy == 0 else 0))
        )
    return out


def s140(s: h.Session, folder: Path, pic: str) -> dict:
    """One picture kind (2to1 or import), each variant, every handle."""
    res: dict = {}
    for variant in ("plain", "rot30", "skew"):
        _load(s)
        pid = add_picture(s, folder, pic)
        if variant == "rot30":
            _c(s, "setRotation", 30)
        elif variant == "skew":
            _skew(s, pid)
        s.wait(80)
        d0 = drawn(s, pid)
        row: dict = {
            "at_rest": edge_off(d0),
            "handles": len(d0["handles"]),
            "skew": node(s, pid).get("skew"),
            "rot": node(s, pid).get("rot"),
        }
        for name in SIDES:
            start = handle_pt(s, pid, name)
            b0 = box(s, pid)
            press(s, start)
            kind = _prop_of(s, "dragKind")
            worst = 0.0
            n_steps = 0
            for dx, dy in _steps(name):
                move(s, P(start.x() + dx, start.y() + dy))
                worst = max(worst, edge_off(drawn(s, pid)))
                n_steps += 1
            last = _steps(name)[-1]
            b1 = box(s, pid)
            release(s, P(start.x() + last[0], start.y() + last[1]))
            worst = max(worst, edge_off(drawn(s, pid)))
            moved = max(abs(b1[k] - b0[k]) for k in ("x", "y", "w", "h"))
            row[name] = {
                "dragKind": kind,
                "max_off": worst,
                "steps": n_steps,
                "moved": _r(moved),
            }
            _c(s, "undo")
            _c(s, "setSelection", [pid])
            s.wait(40)
        res[f"{pic}/{variant}"] = row
    return res


# --- 07 S141: corner keeps proportions, side stretches, Alt from the centre --


def s141(s: h.Session, folder: Path) -> dict:
    res: dict = {}
    _load(s)
    pid = add_picture(s, folder, "2to1")
    b0 = box(s, pid)
    drag(s, handle_pt(s, pid, "se"), 60, 10)
    res["pic_corner"] = {
        "before": _r(ratio(b0)),
        "after": _r(ratio(box(s, pid))),
        "w_grew": _r(box(s, pid)["w"] - b0["w"]),
    }
    b0 = box(s, pid)
    drag(s, handle_pt(s, pid, "se"), 60, -25, Mod.ShiftModifier)
    res["pic_corner_shift"] = {"before": _r(ratio(b0)), "after": _r(ratio(box(s, pid)))}
    b0 = box(s, pid)
    drag(s, handle_pt(s, pid, "e"), 50, 15)
    b1 = box(s, pid)
    res["pic_side"] = {
        "dw": _r(b1["w"] - b0["w"]),
        "dh": _r(b1["h"] - b0["h"]),
        "dx": _r(b1["x"] - b0["x"]),
        "dy": _r(b1["y"] - b0["y"]),
        "edge_off": edge_off(drawn(s, pid)),
    }

    _load(s)
    o = s.point(0.12, 0.3)
    rid = add_rect(s, o.x(), o.y(), 140, 60)
    b0 = box(s, rid)
    drag(s, handle_pt(s, rid, "se"), 50, 5)
    res["shape_corner"] = {"before": _r(ratio(b0)), "after": _r(ratio(box(s, rid)))}
    b0 = box(s, rid)
    drag(s, handle_pt(s, rid, "se"), 50, -20, Mod.ShiftModifier)
    res["shape_corner_shift"] = {
        "before": _r(ratio(b0)),
        "after": _r(ratio(box(s, rid))),
    }
    for label, mods in (
        ("shape_side", Mod.NoModifier),
        ("shape_side_shift", Mod.ShiftModifier),
    ):
        b0 = box(s, rid)
        drag(s, handle_pt(s, rid, "e"), 40, 12, mods)
        b1 = box(s, rid)
        res[label] = {
            "dw": _r(b1["w"] - b0["w"]),
            "dh": _r(b1["h"] - b0["h"]),
            "dx": _r(b1["x"] - b0["x"]),
            "dy": _r(b1["y"] - b0["y"]),
        }
        _c(s, "undo")
        _c(s, "setSelection", [rid])

    # Alt: the centre at press stays put.
    b0 = box(s, rid)
    drag(s, handle_pt(s, rid, "se"), 40, 20, Mod.AltModifier)
    b1 = box(s, rid)
    res["alt_corner"] = {
        "centre_moved": _r(math.dist(centre(b0), centre(b1))),
        "dw": _r(b1["w"] - b0["w"]),
        "ratio_before": _r(ratio(b0)),
        "ratio_after": _r(ratio(b1)),
    }
    _c(s, "undo")
    _c(s, "setSelection", [rid])
    b0 = box(s, rid)
    drag(s, handle_pt(s, rid, "se"), 40, 20, Mod.AltModifier | Mod.ShiftModifier)
    b1 = box(s, rid)
    res["alt_shift_corner"] = {
        "centre_moved": _r(math.dist(centre(b0), centre(b1))),
        "dw": _r(b1["w"] - b0["w"]),
        "dh": _r(b1["h"] - b0["h"]),
    }
    _c(s, "undo")
    _c(s, "setSelection", [rid])
    b0 = box(s, rid)
    drag(s, handle_pt(s, rid, "e"), 30, 0, Mod.AltModifier)
    b1 = box(s, rid)
    res["alt_side"] = {
        "centre_moved": _r(math.dist(centre(b0), centre(b1))),
        "dw": _r(b1["w"] - b0["w"]),
        "dh": _r(b1["h"] - b0["h"]),
    }
    _c(s, "undo")
    _c(s, "setSelection", [rid])
    _c(s, "setRotation", 30)
    s.wait(60)
    c0 = quad_centre(drawn(s, rid)["box"])
    drag(s, handle_pt(s, rid, "se"), 30, 25, Mod.AltModifier)
    c1 = quad_centre(drawn(s, rid)["box"])
    res["alt_rotated"] = {
        "centre_moved": _r(math.dist(c0, c1)),
        "grew": _r(box(s, rid)["w"] - b0["w"]),
    }
    return res


# --- 07 S142: Ctrl skips snapping --------------------------------------------


def s142(s: h.Session, _folder: Path) -> dict:
    _load(s)
    o = s.point(0.12, 0.3)
    rid = add_rect(s, o.x(), o.y(), 120, 60)
    s.set_prop("snapOn", True)
    # A grid about 40 px wide, so a snapped and a free edge are far apart.
    px_per_unit = abs(_c(s, "worldToX", 1000) - _c(s, "worldToX", 0)) / 1000
    s.set_prop("gridSize", max(1, round(40 / max(1e-6, px_per_unit))))
    res: dict = {}

    def off_grid_target() -> P:
        b = box(s, rid)
        right = b["x"] + b["w"] + 60
        on_grid = _c(s, "snapPx", right)
        tx = on_grid + 15
        p = s.ed_point(tx, b["y"] + b["h"] / 2)
        return p

    for label, mods in (("plain", Mod.NoModifier), ("ctrl", Mod.ControlModifier)):
        tgt = off_grid_target()
        start = handle_pt(s, rid, "e")
        press(s, start, mods)
        move(s, P((start.x() + tgt.x()) // 2, start.y()), mods)
        move(s, tgt, mods)
        held = _prop_of(s, "snapOffHeld")
        release(s, tgt, mods)
        b = box(s, rid)
        right = b["x"] + b["w"]
        tx, _ty = win_ed(s, tgt)
        res[label] = {
            "edge_to_pointer": _r(abs(right - tx)),
            "edge_to_grid": _r(abs(right - _c(s, "snapPx", right))),
            "snapOffHeld": held,
        }
        _c(s, "undo")
        _c(s, "setSelection", [rid])
    s.set_prop("snapOn", False)
    return res


# --- 07 S143: Alt-drag copies; duplicateInPlace ------------------------------


def s143(s: h.Session, _folder: Path) -> dict:
    res: dict = {}
    _load(s)
    o = s.point(0.12, 0.3)
    rid = add_rect(s, o.x(), o.y(), 120, 60)
    ids0 = [n["id"] for n in s.state()["nodes"]]
    b0 = box(s, rid)
    h0 = hist(s)
    drag(s, s.center(rid), 60, 30, Mod.AltModifier)
    st = s.state()
    ids1 = [n["id"] for n in st["nodes"]]
    new = [i for i in ids1 if i not in ids0]
    res["alt_drag"] = {
        "new": new,
        "selected": st["selected"],
        "original_moved": _r(math.dist(centre(b0), centre(box(s, rid)))),
        "copy_moved": _r(math.dist(centre(b0), centre(box(s, new[0]))))
        if new
        else None,
        "copy_above": bool(new) and ids1.index(new[0]) > ids1.index(rid),
        "hist_steps": hist(s)[1] - h0[1],
    }
    _c(s, "undo")
    res["alt_drag_undo"] = {
        "ids": [n["id"] for n in s.state()["nodes"]] == ids0,
        "original_moved": _r(math.dist(centre(b0), centre(box(s, rid)))),
    }

    # duplicateInPlace: new ids above the originals, same plane, selected.
    _c(s, "setSelection", [rid])
    before = s.state()["nodes"]
    _c(s, "duplicateInPlace")
    st = s.state()
    after_ids = [n["id"] for n in st["nodes"]]
    new = [i for i in after_ids if i not in [n["id"] for n in before]]
    orig = node(s, rid)
    res["in_place"] = {
        "new": new,
        "selected": st["selected"],
        "above": bool(new)
        and all(after_ids.index(i) > after_ids.index(rid) for i in new),
        "same_plane": bool(new)
        and all(node(s, i).get("plane") == orig.get("plane") for i in new),
        "same_box": bool(new) and all(box(s, i) == box(s, rid) for i in new),
    }
    return res


# --- 07 S144: Shift locks a move; S145: Shift+arrow 10 px --------------------


def s144_145(s: h.Session, _folder: Path) -> dict:
    res: dict = {}
    _load(s)
    o = s.point(0.12, 0.3)
    rid = add_rect(s, o.x(), o.y(), 120, 60)
    b0 = box(s, rid)
    c = s.center(rid)
    press(s, c)
    move(s, P(c.x() + 6, c.y() + 1))
    for label, dx, dy in (
        ("horizontal", 80, 9),
        ("diagonal", 60, 55),
        ("vertical", 5, 70),
    ):
        move(s, P(c.x() + dx, c.y() + dy), Mod.ShiftModifier)
        b = box(s, rid)
        res[label] = {"dx": _r(b["x"] - b0["x"]), "dy": _r(b["y"] - b0["y"])}
    release(s, P(c.x() + 5, c.y() + 70), Mod.ShiftModifier)
    _c(s, "undo")
    _c(s, "setSelection", [rid])

    b0 = box(s, rid)
    s.key(Key.Key_Right)
    b1 = box(s, rid)
    s.key(Key.Key_Right, Mod.ShiftModifier)
    b2 = box(s, rid)
    s.key(Key.Key_Down, Mod.ShiftModifier)
    b3 = box(s, rid)
    res["nudge"] = {
        "plain": _r(b1["x"] - b0["x"]),
        "shift": _r(b2["x"] - b1["x"]),
        "shift_down": _r(b3["y"] - b2["y"]),
    }
    return res


# --- 07 S146: lines on 45 degree steps; Alt draws from the centre ------------


def _angle(a: list[float], b: list[float]) -> float:
    return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))


def _off45(deg: float) -> float:
    r = deg % 45
    return round(min(r, 45 - r), 2)


def s146(s: h.Session, _folder: Path) -> dict:
    res: dict = {}
    for tool in ("line", "arrowline"):
        _load(s)
        p0 = s.point(0.1, 0.3)
        _c(s, "setDrawTool", tool)
        drag(s, p0, 100, 58, Mod.ShiftModifier, press_mods=Mod.NoModifier)
        _c(s, "setDrawTool", "")
        lid = s.state()["selected"][0]
        pts = [hd["at"] for hd in (drawn(s, lid) or {}).get("handles") or []]
        a = _angle(pts[0], pts[1]) if len(pts) == 2 else None
        row = {
            "ends": len(pts),
            "angle": None if a is None else round(a, 2),
            "off45": None if a is None else _off45(a),
        }
        # The end farther from the press, dragged with Shift to about 20 degrees.
        if len(pts) == 2:
            far = max(pts, key=lambda q: math.hypot(q[0] - p0.x(), q[1] - p0.y()))
            near = pts[0] if far is pts[1] else pts[1]
            start = P(round(far[0]), round(far[1]))
            tgt = P(round(near[0] + 120), round(near[1] + 44))
            press(s, start, Mod.ShiftModifier)
            kind = _prop_of(s, "dragKind")
            for i in range(1, 7):
                move(
                    s,
                    P(
                        start.x() + (tgt.x() - start.x()) * i // 6,
                        start.y() + (tgt.y() - start.y()) * i // 6,
                    ),
                    Mod.ShiftModifier,
                )
            release(s, tgt, Mod.ShiftModifier)
            pts2 = [hd["at"] for hd in (drawn(s, lid) or {}).get("handles") or []]
            if len(pts2) == 2:
                a2 = _angle(pts2[0], pts2[1])
                row["end_drag"] = {
                    "dragKind": kind,
                    "angle": round(a2, 2),
                    "off45": _off45(a2),
                }
        res[tool] = row

    # Alt: the press point is the centre; Shift+Alt a perfect shape.
    for label, mods in (
        ("alt", Mod.AltModifier),
        ("alt_shift", Mod.AltModifier | Mod.ShiftModifier),
    ):
        _load(s)
        c = s.point(0.15, 0.4)
        _c(s, "setDrawTool", "rect")
        drag(s, c, 50, 30, mods)
        _c(s, "setDrawTool", "")
        sel = s.state()["selected"]
        if not sel:
            res[label] = {"drawn": False}
            continue
        b = box(s, sel[0])
        cx, cy = win_ed(s, c)
        res[label] = {
            "drawn": True,
            "centre_off": _r(math.dist(centre(b), [cx, cy])),
            "w": _r(b["w"]),
            "h": _r(b["h"]),
        }
    return res


# --- 07 S147: Ctrl+Shift on a side handle skews along that side -------------


def s147(s: h.Session, _folder: Path) -> dict:
    res: dict = {}
    both = Mod.ControlModifier | Mod.ShiftModifier
    for variant in ("plain", "rot30"):
        _load(s)
        o = s.point(0.12, 0.3)
        rid = add_rect(s, o.x(), o.y(), 140, 70)
        if variant == "rot30":
            _c(s, "setRotation", 30)
            s.wait(60)
        for side, fixed, dxy in (
            ("e", ("w", "nw", "sw"), (0, 40)),
            ("n", ("s", "sw", "se"), (40, 0)),
        ):
            hs0 = handles(s, rid)
            h0 = hist(s)
            start = handle_pt(s, rid, side)
            press(s, start, both)
            kind = _prop_of(s, "dragKind")
            worst = 0.0
            for i in range(1, 7):
                move(
                    s, P(start.x() + dxy[0] * i // 6, start.y() + dxy[1] * i // 6), both
                )
                hs = handles(s, rid)
                for f in fixed:
                    worst = max(worst, math.dist(hs0[f], hs[f]))
            release(s, P(start.x() + dxy[0], start.y() + dxy[1]), both)
            sk = node(s, rid).get("skew") or [0, 0]
            res[f"{variant}/{side}"] = {
                "dragKind": kind,
                "fixed_moved": _r(worst),
                "skew": [_r(sk[0]), _r(sk[1])],
                "hist_steps": hist(s)[1] - h0[1],
            }
            _c(s, "undo")
            _c(s, "setSelection", [rid])
    # Not for lines.
    _load(s)
    p0 = s.point(0.1, 0.3)
    _c(s, "setDrawTool", "line")
    s.drag(p0, P(p0.x() + 120, p0.y() + 30))
    _c(s, "setDrawTool", "")
    lid = s.state()["selected"][0]
    g = _c(s, "drawGeom", _c(s, "nodeAt", lid))
    began = _cn(s, "beginSideSkew", lid, "e", g["x"] + g["w"], g["y"] + g["h"] / 2)
    if began:
        _c(s, "applySideSkew", g["x"] + g["w"], g["y"] + g["h"] / 2 + 40)
    res["line"] = {"began": bool(began), "skew": node(s, lid).get("skew")}
    return res


# --- 07 S148: crop keys -------------------------------------------------------


def _crop(n: dict) -> dict | None:
    c = n.get("crop")
    return {k: round(c.get(k) or 0, 4) for k in ("l", "t", "r", "b")} if c else None


def s148(s: h.Session, folder: Path) -> dict:
    res: dict = {}
    _load(s)
    pid = add_picture(s, folder, "2to1")
    _c(s, "toggleCrop")
    res["entered"] = s.state()["cropId"] == pid
    b0 = box(s, pid)
    drag(s, handle_pt(s, pid, "se"), -50, -10, Mod.ShiftModifier)
    b1 = box(s, pid)
    res["shift_corner"] = {
        "before": _r(ratio(b0)),
        "after": _r(ratio(b1)),
        "shrank": _r(b0["w"] - b1["w"]),
        "crop": _crop(node(s, pid)),
    }
    s.key(Key.Key_Return)
    res["enter"] = {"cropId": s.state()["cropId"], "crop": _crop(node(s, pid))}

    _c(s, "setSelection", [pid])
    _c(s, "toggleCrop")
    at_enter = _crop(node(s, pid))
    b_enter = box(s, pid)
    h_enter = hist(s)
    drag(s, handle_pt(s, pid, "e"), -40, 0)
    changed = _crop(node(s, pid)) != at_enter
    s.key(Key.Key_Escape)
    res["esc"] = {
        "changed_first": changed,
        "cropId": s.state()["cropId"],
        "crop_back": _crop(node(s, pid)) == at_enter,
        "box_back": _r(max(abs(box(s, pid)[k] - b_enter[k]) for k in "xywh")),
        "hist_before": h_enter,
        "hist_after": hist(s),
    }

    # Flipped: the side you see is the side that moves.
    _load(s)
    pid = add_picture(s, folder, "2to1")
    _c(s, "flipSelection", "h")
    _c(s, "toggleCrop")
    q0 = drawn(s, pid)["pic"]
    drag(s, handle_pt(s, pid, "e"), -40, 0)
    q1 = drawn(s, pid)["pic"]
    res["flipped"] = {
        "right_moved": _r(max(p[0] for p in q1) - max(p[0] for p in q0)),
        "left_moved": _r(min(p[0] for p in q1) - min(p[0] for p in q0)),
        "edge_off": edge_off(drawn(s, pid)),
    }
    s.key(Key.Key_Escape)
    return res


# --- 07 S149: past the edge mirrors ------------------------------------------


def s149(s: h.Session, folder: Path) -> dict:
    res: dict = {}
    _load(s)
    o = s.point(0.12, 0.3)
    rid = add_rect(s, o.x(), o.y(), 120, 60)
    b0 = box(s, rid)
    drag(s, handle_pt(s, rid, "e"), -(round(b0["w"]) + 40), 0)
    n = node(s, rid)
    b1 = box(s, rid)
    res["shape_e"] = {
        "flipH": bool(n.get("flipH")),
        "flipV": bool(n.get("flipV")),
        "w": _r(b1["w"]),
        "right_edge_now_left": _r(b1["x"] + b1["w"] - b0["x"]),
    }
    _c(s, "undo")
    _c(s, "setSelection", [rid])
    drag(s, handle_pt(s, rid, "s"), 0, -(round(b0["h"]) + 30))
    n = node(s, rid)
    res["shape_s"] = {
        "flipH": bool(n.get("flipH")),
        "flipV": bool(n.get("flipV")),
        "h": _r(box(s, rid)["h"]),
    }

    _load(s)
    pid = add_picture(s, folder, "2to1")
    b0 = box(s, pid)
    drag(s, handle_pt(s, pid, "w"), round(b0["w"]) + 40, 0)
    n = node(s, pid)
    res["picture_w"] = {
        "flipH": bool(n.get("flipH")),
        "w": _r(box(s, pid)["w"]),
        "edge_off": edge_off(drawn(s, pid)),
    }
    return res


# --- 07 S150: Esc during a drag ----------------------------------------------


def s150(s: h.Session, _folder: Path) -> dict:
    res: dict = {}
    _load(s)
    o = s.point(0.12, 0.3)
    rid = add_rect(s, o.x(), o.y(), 120, 60)
    for label in ("resize", "move", "rotate"):
        _c(s, "setSelection", [rid])
        s.wait(40)
        b0 = box(s, rid)
        n0 = node(s, rid)
        h0 = hist(s)
        if label == "resize":
            start = handle_pt(s, rid, "se")
        elif label == "move":
            start = s.center(rid)
        else:
            rx, ry = drawn(s, rid)["rot"]
            start = P(round(rx), round(ry))
        press(s, start)
        kind = _prop_of(s, "dragKind")
        for i in (1, 2, 3):
            move(s, P(start.x() + 20 * i, start.y() + 15 * i))
        changed = node(s, rid) != n0
        esc(s)
        kind_after = _prop_of(s, "dragKind")
        b_esc = box(s, rid)
        move(s, P(start.x() + 90, start.y() + 70))
        release(s, P(start.x() + 90, start.y() + 70))
        b1 = box(s, rid)
        res[label] = {
            "dragKind": kind,
            "changed_mid": changed,
            "dragKind_after_esc": kind_after,
            "back_at_esc": _r(max(abs(b_esc[k] - b0[k]) for k in "xywh")),
            "back_after_release": _r(max(abs(b1[k] - b0[k]) for k in "xywh")),
            "rot_same": (node(s, rid).get("rot") or 0) == (n0.get("rot") or 0),
            "hist_before": h0,
            "hist_after": hist(s),
            "selected": s.state()["selected"],
        }
    return res


# --- 07 S153: group resize ---------------------------------------------------


def s153(s: h.Session, _folder: Path) -> dict:
    res: dict = {}
    _load(s)
    a = s.point(0.08, 0.2)
    b = s.point(0.12, 0.55)
    r1 = add_rect(s, a.x(), a.y(), 100, 50)
    r2 = add_rect(s, b.x(), b.y(), 60, 80)
    ids = [r1, r2, "b3"]
    for label, hname, dxy in (("corner", "se", (60, 20)), ("side", "e", (60, 0))):
        _c(s, "setSelection", ids)
        s.wait(60)
        g0 = _c(s, "selectionBounds")
        boxes0 = {i: box(s, i) for i in ids}
        h0 = hist(s)
        fx = 1 if "e" in hname else (0 if "w" in hname else 0.5)
        fy = 1 if "s" in hname else (0 if "n" in hname else 0.5)
        ex, ey = g0["x"] + g0["w"] * fx, g0["y"] + g0["h"] * fy
        found = _c(s, "onGroupResizeHandle", ex, ey)
        start = s.ed_point(ex, ey)
        press(s, start)
        kind = _prop_of(s, "dragKind")
        for i in range(1, 7):
            move(s, P(start.x() + dxy[0] * i // 6, start.y() + dxy[1] * i // 6))
        release(s, P(start.x() + dxy[0], start.y() + dxy[1]))
        g1 = _c(s, "selectionBounds")
        boxes1 = {i: box(s, i) for i in ids}
        kx = g1["w"] / max(1e-9, g0["w"])
        ky = g1["h"] / max(1e-9, g0["h"])
        res[label] = {
            "handle": found,
            "dragKind": kind,
            "bounds_ratio": [_r(ratio(g0)), _r(ratio(g1))],
            "kx": _r(kx),
            "ky": _r(ky),
            "rect_kx": [_r(boxes1[i]["w"] / boxes0[i]["w"]) for i in (r1, r2)],
            "rect_ky": [_r(boxes1[i]["h"] / boxes0[i]["h"]) for i in (r1, r2)],
            "chip_size": [
                _r(boxes1["b3"]["w"] - boxes0["b3"]["w"]),
                _r(boxes1["b3"]["h"] - boxes0["b3"]["h"]),
            ],
            "chip_moved": _r(math.dist(centre(boxes0["b3"]), centre(boxes1["b3"]))),
            "hist_steps": hist(s)[1] - h0[1],
        }
        _c(s, "undo")
    return res


# --- 07 S154: Reset Shape restores the picture's proportions -----------------


def s154(s: h.Session, folder: Path) -> dict:
    res: dict = {}
    _load(s)
    pid = add_picture(s, folder, "2to1")
    s.js("psSetAspectFn", 2.0)
    res["aspect"] = _cn(s, "pictureAspect", pid)
    drag(s, handle_pt(s, pid, "e"), 80, 0)
    b1 = box(s, pid)
    _c(s, "resetShape", pid)
    b2 = box(s, pid)
    res["with_hook"] = {
        "stretched": _r(ratio(b1)),
        "after": _r(ratio(b2)),
        "dw": _r(b2["w"] - b1["w"]),
        "centre_moved": _r(math.dist(centre(b1), centre(b2))),
    }
    s.js("psSetAspectFn", 0)
    res["aspect_no_hook"] = _cn(s, "pictureAspect", pid)
    _c(s, "setSelection", [pid])
    drag(s, handle_pt(s, pid, "e"), 60, 0)
    b1 = box(s, pid)
    _c(s, "resetShape", pid)
    b2 = box(s, pid)
    res["no_hook"] = {"dw": _r(b2["w"] - b1["w"]), "dh": _r(b2["h"] - b1["h"])}
    return res


# --- 07 S155: Properties link ------------------------------------------------


def _prop(s: h.Session, label: str) -> float:
    for line in json.loads(_js(s, "propLines")):
        if line.startswith(label + ": "):
            return float(line[len(label) + 2 :].rstrip("%"))
    raise AssertionError(f"no {label} in Properties")


def s155(s: h.Session, _folder: Path) -> dict:
    res: dict = {}
    _load(s)
    s.js("showProps", True)
    o = s.point(0.12, 0.6)
    rid = add_rect(s, o.x(), o.y(), 120, 60)
    _c(s, "setSelection", [rid])
    s.wait(60)
    res["default_on"] = _prop_of(s, "linkSize")
    w0, h0 = _prop(s, "Width"), _prop(s, "Height")
    hs0 = hist(s)
    s.set_prop_field("Width", str(round(w0 * 2, 1)))
    w1, h1 = _prop(s, "Width"), _prop(s, "Height")
    res["linked"] = {
        "w0": w0,
        "h0": h0,
        "w1": w1,
        "h1": h1,
        "hist_steps": hist(s)[1] - hs0[1],
    }
    _c(s, "undo")
    _c(s, "setSelection", [rid])
    s.wait(60)
    res["undo"] = {"w": _prop(s, "Width"), "h": _prop(s, "Height")}

    link = json.loads(_js(s, "psLinkCentre"))
    res["link_found"] = link is not None
    if link is not None:
        s.click(P(round(link[0]), round(link[1])))
        s.wait(60)
    res["after_click"] = _prop_of(s, "linkSize")
    w0, h0 = _prop(s, "Width"), _prop(s, "Height")
    s.set_prop_field("Width", str(round(w0 * 1.5, 1)))
    res["unlinked"] = {
        "w0": w0,
        "h0": h0,
        "w1": _prop(s, "Width"),
        "h1": _prop(s, "Height"),
    }
    s.js("showProps", False)
    s.set_prop("linkSize", True)
    return res


# A name with "/" is part of a section: its rows go into that section.
SECTIONS = {
    "s140/2to1": lambda s, folder: s140(s, folder, "2to1"),
    "s140/import": lambda s, folder: s140(s, folder, "import"),
    "s141": s141,
    "s142": s142,
    "s143": s143,
    "s144_145": s144_145,
    "s146": s146,
    "s147": s147,
    "s148": s148,
    "s149": s149,
    "s150": s150,
    "s153": s153,
    "s154": s154,
    "s155": s155,
}


def main() -> None:
    folder = Path(sys.argv[1])
    s = h.Session(folder, "ps_match")
    s.hold_runs()
    # The sections to run (comma separated), else all: the test runs them
    # in a few programs, each well inside the hang limit for one program.
    names = sys.argv[2].split(",") if len(sys.argv) > 2 else list(SECTIONS)
    out: dict[str, Any] = {}
    for name in names:
        fn = SECTIONS[name]
        try:
            res = fn(s, folder)
        except Exception:
            res = {"error": traceback.format_exc()[-2000:]}
            # A drag cut short: let go of the mouse and of any mode.
            s._mouse("mouseRelease", P(5, _win(s).height() - 5))
            _c(s, "setDrawTool", "")
        out.setdefault(name.split("/")[0], {}).update(res)
        print(f"SECTION {name} done", flush=True)
    out["warnings"] = sorted(
        {w for w in s.warnings if "Rig" in w or "rig_" in w or "VkbRig" in w}
    )
    print("RESULT " + json.dumps(out), flush=True)
    smoke_exit(0)


if __name__ == "__main__":
    main()
