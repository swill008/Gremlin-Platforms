# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Drives the Device Mapping Editor off-screen through drags that wander across
a picture's edge (07 S55a: a drag is one undo step; the hover highlight is
never a step) and prints the results as JSON. test_gesture_undo_core.py
runs it in its own process.

    python test/unit/gesture_undo_core_smoke.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from smoke_exit import smoke_exit

sys.path.insert(0, str(Path(__file__).parent))

import rig_editor_harness as h  # noqa: E402
from PySide6 import QtCore, QtGui  # noqa: E402

Key = QtCore.Qt.Key
Btn = QtCore.Qt.MouseButton


def _move(s: h.Session, p: QtCore.QPoint) -> None:
    event = QtGui.QMouseEvent(
        QtCore.QEvent.Type.MouseMove,
        QtCore.QPointF(p),
        QtCore.QPointF(s.win.mapToGlobal(p)),
        Btn.NoButton,
        Btn.LeftButton,
        QtCore.Qt.KeyboardModifier.NoModifier,
    )
    QtCore.QCoreApplication.sendEvent(s.win, event)
    s.wait(15)


def _wander(s: h.Session, start: QtCore.QPoint, offsets: list[tuple[int, int]]) -> None:
    """Presses at start and moves through start + each offset, held down."""
    s._mouse("mousePress", start)
    s.wait(20)
    for dx, dy in offsets:
        _move(s, QtCore.QPoint(start.x() + dx, start.y() + dy))


def _release(s: h.Session, p: QtCore.QPoint) -> None:
    s._mouse("mouseRelease", p)
    s.wait(80)


def main() -> None:
    s = h.Session(Path(os.environ.get("TEMP", ".")), "gesture_undo_core")
    out: dict[str, object] = {}
    h._load(s, "evo_r")
    s.hold_runs()
    icon = h.ROOT / "gfx" / "icon_large.png"
    s.call("addOverlay", "test/icon", QtCore.QUrl.fromLocalFile(str(icon)).toString())
    pic = s.state()["selected"][0]
    s.end_run()
    box0 = s._box(pic)

    # A corner handle dragged back and forth across the picture's edge.
    at0 = s.call_prop("histAt")
    corner = s.corner(pic)
    path = [(30, 30), (-40, -40), (25, 25), (-30, -30), (35, 35), (-20, -20), (40, 40)]
    _wander(s, corner, path)
    mid = s.call_prop("histAt") - at0
    _release(s, QtCore.QPoint(corner.x() + 40, corner.y() + 40))
    out["corner"] = {"steps-mid": mid, "steps": s.call_prop("histAt") - at0,
                     "resized": s._box(pic) != box0}
    s.call("undo")
    out["corner"]["undo-restores"] = s._box(pic) == box0

    # A chip dragged in and out over the picture (its hover highlight
    # changing many times): one step.
    chip = s.call("placedId", "btn", 6)
    s.call("setSelection", [])
    fx0 = s.node(chip)["chipFx"]
    at0 = s.call_prop("histAt")
    start = s.center(chip)
    pc = s.center(pic)
    dx, dy = pc.x() - start.x(), pc.y() - start.y()
    hops = [(dx, dy), (0, 0), (dx, dy), (0, 0), (dx, dy), (dx // 2, dy // 2)]
    _wander(s, start, hops)
    _release(s, QtCore.QPoint(start.x() + dx // 2, start.y() + dy // 2))
    out["chip"] = {"steps": s.call_prop("histAt") - at0,
                   "moved": s.node(chip)["chipFx"] != fx0}

    # Hovering over the picture with no button down: no step.
    at0 = s.call_prop("histAt")
    for p in (pc, start, pc, start):
        event = QtGui.QMouseEvent(
            QtCore.QEvent.Type.MouseMove, QtCore.QPointF(p),
            QtCore.QPointF(s.win.mapToGlobal(p)), Btn.NoButton, Btn.NoButton,
            QtCore.Qt.KeyboardModifier.NoModifier)
        QtCore.QCoreApplication.sendEvent(s.win, event)
        s.wait(15)
    out["hover-steps"] = s.call_prop("histAt") - at0

    # Esc mid-drag: what the drag did so far is one step, and the drag ends.
    box1 = s._box(pic)
    at0 = s.call_prop("histAt")
    corner = s.corner(pic)
    _wander(s, corner, path)
    s.key(Key.Key_Escape)
    esc_active = s.call_prop("gestureActive")
    _release(s, QtCore.QPoint(corner.x() + 40, corner.y() + 40))
    out["esc"] = {"steps": s.call_prop("histAt") - at0, "active": esc_active,
                  "drag": s.call_prop("dragKind")}
    s.call("undo")
    out["esc"]["undo-restores"] = s._box(pic) == box1

    # Undo mid-drag: the drag ends as its step and Undo takes it back.
    box2 = s._box(pic)
    at0 = s.call_prop("histAt")
    corner = s.corner(pic)
    _wander(s, corner, path)
    s.call("undo")
    _move(s, QtCore.QPoint(corner.x() + 60, corner.y() + 60))
    _release(s, QtCore.QPoint(corner.x() + 60, corner.y() + 60))
    out["undo-mid"] = {"steps": s.call_prop("histAt") - at0,
                       "restored": s._box(pic) == box2,
                       "active": s.call_prop("gestureActive"),
                       "redo": s.call_prop("canRedo")}

    out["warnings"] = s.warnings
    print("RESULT " + json.dumps(out), flush=True)
    smoke_exit(0)


if __name__ == "__main__":
    main()
