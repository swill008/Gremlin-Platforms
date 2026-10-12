# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Drives the Device Mapping Editor off-screen through the background and
foreground planes (07 S111, S112, S116, S117-S122, S57, S62; decisions
D-07-BACKGROUND-PLANES, D-07-PLANES-ANSWERS P1a, P6a, P7a) and prints what it
saw as one JSON object. test_planes_editor.py runs it in its own process.

    python test/unit/planes_editor_smoke.py

It uses the golden harness's window and session (rig_editor_harness.py),
with its own steps; the harness's scenarios are untouched.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PySide6 import QtCore, QtQml  # noqa: E402
from rig_editor_harness import ROOT, Session, _load  # noqa: E402
from smoke_exit import smoke_exit  # noqa: E402

CTRL = QtCore.Qt.KeyboardModifier.ControlModifier
PICTURE = QtCore.QUrl.fromLocalFile(
    str(ROOT / "test" / "unit" / "fixtures" / "icon_large.png")
).toString()


def _rect(id_: str, fx: float, fy: float, plane: str = "") -> dict:
    n = {
        "id": id_,
        "kind": "draw",
        "shape": "rect",
        "fx": fx,
        "fy": fy,
        "fw": 0.08,
        "fh": 0.08,
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
    n = _rect(id_, fx, fy, plane)
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
    s = Session(Path("."), "planes")
    s.hold_runs()

    def qml(code: str) -> object:
        expr = QtQml.QQmlExpression(QtQml.qmlContext(s.win), s.win, code)
        value = expr.evaluate()
        return value[0] if isinstance(value, tuple) else value

    def ev(code: str) -> object:
        return json.loads(str(qml("JSON.stringify(" + code + ")")))

    def order() -> list:
        return [(n["id"], n.get("plane", "")) for n in s.state()["nodes"]]

    def hist() -> int:
        return s.state()["histAt"]

    _load(s, "evo_r")
    doc = s.state()["nodes"]
    # A table and a chip that claim the background, and background items
    # listed after the foreground: loading puts each where it belongs.
    doc = doc + [
        _rect("bgA", 0.02, 0.80, "background"),
        dict(_rect("tbl", 0.30, 0.80, "background"), shape="table"),
        _picture("bgPic", 0.14, 0.80, "background"),
        _rect("fgR", 0.60, 0.80),
    ]
    doc[0] = dict(doc[0], plane="background")
    s.js("setNodes", json.dumps(doc))
    s.wait(400)
    s.call("seedHist")
    first_chip = doc[0]["id"]
    out["loaded_order"] = order()
    out["range_bg"] = s.call("planeRange", "background")
    out["range_fg"] = s.call("planeRange", "foreground")
    out["bottom_picture"] = (s.call("bottomPicture") or {}).get("id")
    out["can_hold"] = {
        "rect": s.call("canHoldBackground", s.node("bgA")),
        "chip": s.call("canHoldBackground", s.node("b3")),
        "table": s.call("canHoldBackground", s.node("tbl")),
    }
    out["chip_lost_plane"] = s.node(first_chip).get("plane", "")

    # Foreground mode: the background shows but takes no click (S116).
    s.call("setSelection", [])
    s.click(s.center("bgA"))
    out["fg_click_bg"] = s.state()["selected"]
    s.click(s.center("fgR"))
    out["fg_click_fg"] = s.state()["selected"]
    out["fg_hit_bg"] = s.call("hitTest", *_mid(s, "bgA"))["id"]
    out["rows_fg"] = [
        (r["id"], r["part"], r["type"])
        for r in s.call("layerRows", {"kinds": [], "query": ""}, {})
    ][-3:]
    out["bg_row"] = s.call("layerRows", {"kinds": [], "query": "zzz"}, {})[-1]
    out["counts_fg"] = s.call("layerCounts", {"kinds": [], "query": ""})

    # Background mode: only the background is hit; the foreground is faint.
    s.set_prop("editPlane", "background")
    out["bg_mode_selection_cleared"] = s.state()["selected"]
    s.click(s.center("bgA"))
    out["bg_click_bg"] = s.state()["selected"]
    s.click(s.center("fgR"))
    out["bg_click_fg"] = s.state()["selected"]
    out["bg_hit_chip"] = s.call("hitTest", *_mid(s, "b3"))["id"]
    idx = {n["id"]: i for i, n in enumerate(s.state()["nodes"])}
    out["faint"] = {
        "chip": ev(f"ed()._chipsItem({idx['b3']}).opacity"),
        "bg": ev(f"ed()._chipsItem({idx['bgA']}).opacity"),
        "leaders": ev("ed().foregroundOpacity()"),
    }
    s.set_prop("showFgFaint", False)
    out["faint_off_chip_visible"] = ev(f"ed()._chipsItem({idx['b3']}).visible")
    s.set_prop("showFgFaint", True)
    out["rows_bg"] = [
        (r["id"], r["type"])
        for r in s.call("layerRows", {"kinds": [], "query": ""}, {})
    ]
    # A band over the whole page takes only background items.
    s.drag(s.point(0.005, 0.005), s.point(0.995, 0.995))
    out["band_bg"] = sorted(s.state()["selected"])

    # A shape drawn in Background mode lands on top of the background (S62).
    s.call("setSelection", [])
    s.call("setDrawTool", "rect")
    s.drag(s.point(0.40, 0.60), s.point(0.46, 0.66))
    s.call("setDrawTool", "")
    drawn = s.state()["selected"][0]
    out["drawn_plane"] = s.node(drawn).get("plane", "")
    out["drawn_top_of_bg"] = s.call("planeRange", "background")["last"] == idx_of(
        s, drawn
    )
    pic_id = s.call(
        "addOverlay", "pictures/x.png", PICTURE, {"fitFrame": True, "aspect": 2}
    )
    out["added_picture"] = {
        k: s.node(pic_id).get(k) for k in ("plane", "fx", "fy", "fw", "fh")
    }

    # Stacking stays inside the plane (S119).
    s.call("setSelection", ["bgA"])
    s.call("bringToFront")
    out["front_in_bg"] = idx_of(s, "bgA") == s.call("planeRange", "background")["last"]
    s.call("moveNodeTo", "bgA", 999)
    out["move_to_clamped"] = (
        idx_of(s, "bgA") == s.call("planeRange", "background")["last"]
    )
    s.set_prop("editPlane", "foreground")
    s.call("setSelection", ["fgR"])
    s.call("sendToBack")
    out["back_in_fg"] = idx_of(s, "fgR") == s.call("planeRange", "foreground")["first"]
    s.call("moveNodeTo", "fgR", 0)
    out["move_to_fg_clamped"] = (
        idx_of(s, "fgR") == s.call("planeRange", "foreground")["first"]
    )

    # Move to Background: several at once, chips refused, one undo step (S121).
    qml("ed().planeMoved.connect(function (p, c) { _win.notPlaced = p + ':' + c })")
    before = hist()
    res = s.call("moveToPlane", ["fgR", "b3"], "background")
    out["plane_moved_signal"] = qml("_win.notPlaced")
    out["move_result"] = res
    out["move_steps"] = hist() - before
    out["fgR_after"] = (
        s.node("fgR").get("plane", ""),
        idx_of(s, "fgR") == s.call("planeRange", "background")["last"],
    )
    s.key(QtCore.Qt.Key.Key_Z, CTRL)
    out["fgR_undone"] = s.node("fgR").get("plane", "")
    s.call("redo")
    res2 = s.call("moveToPlane", ["fgR"], "foreground")
    out["back_to_fg"] = (
        s.node("fgR").get("plane", ""),
        idx_of(s, "fgR") == s.call("planeRange", "foreground")["first"],
    )
    out["back_to_fg_moved"] = res2["moved"]

    # Lock the background: one step; undo snapshots hold nodes, no photo.
    before = hist()
    s.call("setPlaneLocked", "background", True)
    out["lock_steps"] = hist() - before
    out["plane_locked"] = s.call("planeLocked", "background")
    out["bg_row_locked"] = s.call("layerRows", {"kinds": [], "query": ""}, {})[-1][
        "locked"
    ]
    s.call("setPlaneLocked", "background", False)
    out["snap_keys"] = sorted(json.loads(s.call("snapJson")).keys())

    # Look: only keys away from neutral; a slider run is one step (S43, S57).
    qml("ed().lookUrlFor = function (u, l) { return u + '#' + JSON.stringify(l) }")
    before = hist()
    s.call("setPictureLook", "bgPic", "bright", 0.3)
    s.call("setPictureLook", "bgPic", "grey", 0.6)
    s.call("setPictureLook", "bgPic", "grey", 7)
    s.call("setPictureLook", "bgPic", "contrast", 0)
    s.call("setPictureLook", "bgPic", "opacity", 0.6)
    s.end_run()
    out["look"] = [
        s.node("bgPic").get("look"),
        s.node("bgPic").get("opacity"),
        hist() - before,
    ]
    s.wait(300)
    out["look_url"] = s.node("bgPic").get("lookUrl", "")
    n = s.node("bgPic")
    s.js(
        "setNodes",
        json.dumps(
            [
                dict(x, crop={"l": 0.1}, skew=[0.2, 0], flipH=True, rot=30)
                if x["id"] == "bgPic"
                else x
                for x in s.state()["nodes"]
            ]
        ),
    )
    s.wait(300)
    s.call("resetShape", "bgPic")
    n = s.node("bgPic")
    out["reset_shape"] = [n.get("crop"), n.get("skew"), n.get("flipH"), n.get("rot")]

    # A chip on a background picture's snap point follows it, in Background
    # mode too (P6a).
    s.call("setSelection", [])
    box = s._box("bgPic")
    s.call("snapChipToSocket", "b3", box["x"] + box["w"] / 2, box["y"] + box["h"] / 2)
    chip0 = (s.node("b3")["chipFx"], s.node("b3")["chipFy"])
    s.set_prop("editPlane", "background")
    s.drag(s.center("bgPic"), s.center("bgPic", 60, 40))
    chip1 = (s.node("b3")["chipFx"], s.node("b3")["chipFy"])
    out["chip_followed"] = chip1[0] > chip0[0] and chip1[1] > chip0[1]

    # Clear Background: one step, Undo brings it back (S41).
    before = hist()
    s.call("clearPlane", "background")
    out["clear"] = [s.call("planeRange", "background"), hist() - before]
    s.key(QtCore.Qt.Key.Key_Z, CTRL)
    out["clear_undone"] = s.call("planeRange", "background")["last"] >= 0

    # Switching planes is not an undo step (S57).
    before = hist()
    s.set_prop("editPlane", "foreground")
    s.set_prop("bgViewHidden", True)
    out["view_steps"] = hist() - before
    out["bg_hidden_visible"] = ev(f"ed()._chipsItem({idx_of(s, 'bgA')}).visible")
    s.set_prop("bgViewHidden", False)
    s.set_prop("bgViewOpacity", 0.5)
    out["bg_view_opacity"] = ev(f"ed()._chipsItem({idx_of(s, 'bgA')}).opacity")
    s.set_prop("exporting", True)
    out["bg_export_opacity"] = ev(f"ed()._chipsItem({idx_of(s, 'bgA')}).opacity")
    s.set_prop("exporting", False)

    out["warnings"] = sorted(set(s.warnings))
    print("PLANES " + json.dumps(out))
    smoke_exit(0)


def _mid(s: Session, id_: str) -> tuple:
    b = s._box(id_)
    return (b["x"] + b["w"] / 2, b["y"] + b["h"] / 2)


def idx_of(s: Session, id_: str) -> int:
    return [n["id"] for n in s.state()["nodes"]].index(id_)


if __name__ == "__main__":
    main()
