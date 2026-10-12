# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Drives the Device Mapping Editor off-screen at 150 % UI scale and prints
what it saw about a drawing's handles and pictures as one JSON object
(07 S140, S155): handles centred on the box's edges and corners, presses on
the drawn handles of a skewed item hit them, hit radii scaled with the UI,
a picture stretched to fill its box, and Choose Picture… refitting the box
to the new picture's shape. test_ps_drawitem.py runs it in its own process.

    python test/unit/ps_drawitem_smoke.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, cast

sys.path.insert(0, str(Path(__file__).resolve().parent))

import rig_editor_harness  # noqa: E402
from PySide6 import QtCore, QtQml  # noqa: E402
from rig_editor_harness import ROOT, Session, _load  # noqa: E402
from smoke_exit import smoke_exit  # noqa: E402

PICTURE = QtCore.QUrl.fromLocalFile(str(ROOT / "gfx" / "icon_large.png")).toString()
SCALE = 150


class _Backend(QtCore.QObject):
    uiScaleChanged = QtCore.Signal()

    def _scale(self) -> int:
        return SCALE

    uiScale = QtCore.Property(int, fget=_scale, notify=uiScaleChanged)


# The handles found under a drawing's wrapper, by objectName, with their
# centres in the wrapper's and the editor's coordinates.
_FIND = """
(function(id, name) {
    var e = ed()
    var it = e._chipsItem(e.nodeIndex(id))
    var out = []
    function walk(x) {
        for (var i = 0; i < x.children.length; i++) {
            var c = x.children[i]
            if (c.objectName === name && c.visible) {
                var a = c.mapToItem(it, c.width / 2, c.height / 2)
                var b = c.mapToItem(e, c.width / 2, c.height / 2)
                out.push({ index: c.index === undefined ? -1 : c.index,
                           x: a.x, y: a.y, ex: b.x, ey: b.y, size: c.width,
                           fill: c.fillMode === undefined ? -1 : c.fillMode })
            }
            walk(c)
        }
    }
    walk(it)
    out.sort(function(p, q) { return p.index - q.index })
    return { w: it.width, h: it.height, found: out }
})
"""


def _rect(id_: str, fx: float, fy: float) -> dict:
    return {
        "id": id_,
        "kind": "draw",
        "shape": "rect",
        "fx": fx,
        "fy": fy,
        "fw": 0.1,
        "fh": 0.1,
        "fill": "filled",
        "color": "#14532D",
        "border": "#22C55E",
        "stroke": 2,
        "rot": 0,
        "opacity": 1,
    }


def main() -> None:
    rig_editor_harness.FakeBackend = _Backend  # type: ignore[misc]
    out: dict = {}
    s = Session(Path("."), "ps_drawitem")
    s.hold_runs()

    def qml(code: str) -> Any:  # noqa: ANN401
        win: Any = s.win
        ctx = QtQml.qmlContext(win)
        assert ctx is not None
        expr = QtQml.QQmlExpression(ctx, win, code)
        value = expr.evaluate()
        return value[0] if isinstance(value, tuple) else value

    def ev(code: str) -> Any:  # noqa: ANN401
        return json.loads(str(qml("JSON.stringify(" + code + ")")))

    def find(id_: str, name: str) -> dict:
        return ev(_FIND + f"({json.dumps(id_)}, {json.dumps(name)})")

    _load(s, "evo_r")
    pic = dict(
        _rect("p1", 0.5, 0.2),
        shape="image",
        src="pictures/icon.png",
        srcUrl=PICTURE,
        sockets=[],
    )
    s.js("setNodes", json.dumps(s.state()["nodes"] + [_rect("r1", 0.3, 0.4), pic]))
    s.wait(400)
    out["rotate_offset"] = s.call_prop("rotateHandleOffset")

    # Handles centred on the box (S155), at 150 %.
    s.call("setSelection", ["r1"])
    s.wait(150)
    out["handles"] = find("r1", "resizeHandle")
    out["knob"] = find("r1", "rotateKnob")

    # Hit radius scales: 10 px right of the bottom-right corner is on the
    # handle at 150 % (radius 12), off it at a fixed 8.
    b = s._box("r1")
    out["hit_near_se"] = ev(
        f"ed().hitDraw(ed().nodeAt('r1'), {b['x'] + b['w'] + 10}, {b['y'] + b['h']})"
    )

    # Skewed: a press on each drawn handle and on the rotate grip hits it.
    qml(
        "(function() { var n = ed().nodeAt('r1'); n.skew = [0.5, 0.3]; ed().bump() })()"
    )
    s.wait(200)
    sk = find("r1", "resizeHandle")
    out["skew_hits"] = [
        ev(f"ed().hitDraw(ed().nodeAt('r1'), {h['ex']}, {h['ey']})")
        for h in sk["found"]
    ]
    kn = find("r1", "rotateKnob")["found"]
    out["skew_rotate_hit"] = [
        ev(f"ed().hitDraw(ed().nodeAt('r1'), {k['ex']}, {k['ey']})") for k in kn
    ]

    # The picture fills its box: Stretch, not PreserveAspectFit (S140).
    out["pic_fill"] = [f["fill"] for f in find("p1", "pictureImage")["found"]]

    # Choose Picture… with the new picture's aspect: width and centre kept,
    # height from the aspect (contract item 18); a crop's showing part counts.
    space = cast(dict, s.call("spaceRect"))
    out["space"] = [space["w"], space["h"]]
    before = s.node("p1")
    s.call("repointPicture", "p1", "pictures/wide.png", PICTURE, 2.0)
    out["repoint"] = {"before": before, "after": s.node("p1")}
    qml(
        "(function() { var n = ed().nodeAt('p1');"
        " n.crop = { l: 0.25, r: 0.25, t: 0, b: 0 }; ed().bump() })()"
    )
    s.call("repointPicture", "p1", "pictures/wide.png", PICTURE, 2.0)
    out["repoint_crop"] = s.node("p1")
    s.call("repointPicture", "p1", "pictures/other.png", PICTURE)
    out["repoint_no_aspect"] = s.node("p1")

    out["warnings"] = sorted(set(s.warnings))
    print("PSDRAW " + json.dumps(out))
    smoke_exit(0)


if __name__ == "__main__":
    main()
