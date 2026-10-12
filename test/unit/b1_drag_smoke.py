# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Drives the Device Mapping Editor off-screen for the 4 px drag dead zone
(D-FIXLIST-B1 item 3): a press on a chip, group member or drawing that moves
less than 4 screen pixels only selects; past 4 px the item follows the
pointer from where it was pressed. Prints the results as JSON;
test_b1_drag.py runs it in its own process.

    python test/unit/b1_drag_smoke.py <folder>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from smoke_exit import smoke_exit

sys.path.insert(0, str(Path(__file__).parent))

import rig_editor_harness as h  # noqa: E402
from PySide6 import QtCore, QtGui  # noqa: E402

Q = QtCore.Qt
P = QtCore.QPoint


def _move(s: h.Session, p: P, mods: Q.KeyboardModifier) -> None:
    ev = QtGui.QMouseEvent(
        QtCore.QEvent.Type.MouseMove,
        QtCore.QPointF(p),
        QtCore.QPointF(s.win.mapToGlobal(p)),
        Q.MouseButton.NoButton,
        Q.MouseButton.LeftButton,
        mods,
    )
    QtCore.QCoreApplication.sendEvent(s.win, ev)
    s.wait(30)


def _snap(s: h.Session) -> dict:
    st = s.state()
    return {
        "nodes": json.dumps(st["nodes"], sort_keys=True),
        "histAt": st["histAt"],
        "histLen": st["histLen"],
    }


def _gesture(
    s: h.Session,
    start: P,
    steps: list[int],
    probe: str = "",
    mods: Q.KeyboardModifier = Q.KeyboardModifier.NoModifier,
) -> dict:
    """Press at start, move right by each of steps (screen px from the
    press), release at the last. probe: a node whose box centre is read
    after each move (window px)."""
    before = _snap(s)
    c0 = s.center(probe) if probe else None
    s._mouse("mousePress", start, mods=mods)
    s.wait(40)
    seen = []
    for dx in steps:
        _move(s, P(start.x() + dx, start.y()), mods)
        if probe:
            c = s.center(probe)
            seen.append([round(c.x() - c0.x(), 2), round(c.y() - c0.y(), 2)])
    end = P(start.x() + (steps[-1] if steps else 0), start.y())
    s._mouse("mouseRelease", end, mods=mods)
    s.wait(120)
    after = _snap(s)
    return {
        "same_nodes": before["nodes"] == after["nodes"],
        "hist_added": after["histLen"] - before["histLen"],
        "histAt_moved": after["histAt"] - before["histAt"],
        "selected": s.state()["selected"],
        "seen": seen,
    }


def _member_point(s: h.Session, gid: str) -> P | None:
    b = s._box(gid)
    for fy in (0.5, 0.3, 0.7, 0.2, 0.8):
        for fx in (0.5, 0.3, 0.7, 0.2, 0.8):
            x, y = b["x"] + b["w"] * fx, b["y"] + b["h"] * fy
            hit = s.call("hitTest", x, y)
            if isinstance(hit, dict) and hit.get("kind") == "member":
                return s.ed_point(x, y)
    return None


def main() -> None:
    folder = Path(sys.argv[1])
    s = h.Session(folder, "b1_drag")
    s.hold_runs()
    out: dict[str, object] = {}
    h._load(s, "evo_r")
    # Zoomed in: 4 screen px is 2 editor px, so the dead zone must be
    # measured on screen, not in map units.
    s.js("setZoom", 2, 0, 0)
    s.wait(200)
    a = s.ed_point(0, 0)
    b = s.ed_point(100, 0)
    out["screen_px_per_editor_px"] = (b.x() - a.x()) / 100
    alt = Q.KeyboardModifier.AltModifier

    # Chips: a plain click, a 3 px wobble, then a real drag (Alt: no snap).
    s.click(s.ed_point(5, 5))
    out["chip_click"] = _gesture(s, s.center("b3"), [])
    out["chip_3px"] = _gesture(s, s.center("b3"), [1, 2, 3])
    out["chip_drag"] = _gesture(s, s.center("b4"), [3, 5, 30], probe="b4", mods=alt)

    # A drawing (rectangle).
    s.call("setDrawTool", "rect")
    s.drag(s.point(0.40, 0.40), s.point(0.48, 0.50))
    rect = s.state()["selected"][0]
    s.call("applyField", "fill", "filled")
    s.call("setDrawTool", "")
    s.end_run()
    s.call("setSelection", [])
    out["draw_click"] = _gesture(s, s.center(rect), [])
    out["draw_3px"] = _gesture(s, s.center(rect), [2, 3])
    out["draw_drag"] = _gesture(s, s.center(rect), [3, 5, 30], probe=rect, mods=alt)

    # A group member (group being edited).
    s.set_prop("groupEditId", "p610")
    s.wait(100)
    mp = _member_point(s, "p610")
    out["member_found"] = mp is not None
    pts = [s.center("b3"), s.center("b4"), s.center(rect)] + ([mp] if mp else [])
    out["points"] = [[q.x(), q.y()] for q in pts]
    if mp is not None:
        out["member_3px"] = _gesture(s, mp, [1, 3])
        out["member_drag"] = _gesture(s, mp, [3, 30], mods=alt)
    s.set_prop("groupEditId", "")

    out["warnings"] = sorted(
        {w for w in s.warnings if "RigPointerArea" in w or "rig_pointer" in w}
    )
    print("RESULT " + json.dumps(out), flush=True)
    smoke_exit(0)


if __name__ == "__main__":
    main()
