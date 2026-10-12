# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Drives the Device Mapping Editor off-screen in view mode and hovers a
chip at zoom 1, 4 and 8 (the chip centred in the window). For each zoom it
records the pointer and the hover tooltip's place and size in window
pixels. Prints the results as JSON; test_chip_tooltip_zoom.py runs it in its
own process.

    python test/unit/chip_tooltip_zoom_smoke.py <folder>
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from smoke_exit import smoke_exit

sys.path.insert(0, str(Path(__file__).parent))

import rig_editor_harness as h  # noqa: E402
from PySide6 import QtCore, QtQml, QtTest  # noqa: E402


def main() -> None:
    s = h.Session(Path(sys.argv[1]), "chip_tooltip_zoom")
    h._load(s, "evo_r")
    s.js("setEditing", False)
    s.wait(300)

    def qml(code: str) -> object:
        expr = QtQml.QQmlExpression(QtQml.qmlContext(s.win), s.win, code)
        value = expr.evaluate()
        return value[0] if isinstance(value, tuple) else value

    def ev(code: str) -> object:
        return json.loads(str(qml("JSON.stringify(" + code + ")")))

    cid = ev(
        "(function(){var e=ed();var l=e.nodes;for(var i=0;i<l.length;i++){"
        "var n=l[i];if(!e.isDraw(n)&&!e.isGroup(n)&&e.leafKind(n.kind)==='btn')"
        "return n.id;}return null})()"
    )
    tips = [
        o for o in s.win.findChildren(QtCore.QObject)
        if "ToolTip" in o.metaObject().className()
    ]
    out: dict = {"chip": cid, "tips": len(tips), "zooms": []}

    def chip_centre() -> tuple[float, float]:
        r = ev(
            "(function(){var e=ed();var it=e._chipsItem(e.nodeIndex('%s'));"
            "var p=it.mapToItem(null,0,0);var q=it.mapToItem(null,it.width,"
            "it.height);return [p.x,p.y,q.x,q.y]})()" % cid
        )
        return (r[0] + r[2]) / 2, (r[1] + r[3]) / 2

    def opened() -> list:
        return [t for t in tips if t.property("opened")]

    for z in (1.0, 4.0, 8.0):
        s.js("setZoom", z, 0, 0)
        s.wait(200)
        cx, cy = chip_centre()
        s.js("setZoom", z, 800 - cx, 450 - cy)
        s.wait(200)
        cx, cy = chip_centre()
        QtTest.QTest.mouseMove(s.win, QtCore.QPoint(5, 5))
        s.wait(100)
        s.js("call", "setChipTip", json.dumps([-1, -1]))
        s.wait(50)
        m = QtCore.QPoint(round(cx), round(cy))
        QtTest.QTest.mouseMove(s.win, m)
        s.wait(50)
        m = m + QtCore.QPoint(1, 0)
        QtTest.QTest.mouseMove(s.win, m)
        end = time.monotonic() + 5
        while not opened() and time.monotonic() < end:
            s.wait(50)
        s.wait(100)
        shown = opened()
        tip = shown[0] if shown else tips[0]
        item = tip.property("contentItem").parentItem()
        p = item.mapToItem(None, QtCore.QPointF(0, 0))
        w, ht = tip.property("width"), tip.property("height")
        out["zooms"].append({
            "zoom": z, "mouse": [m.x(), m.y()], "opened": bool(tip.property("opened")),
            "label": ev("ed().hoverHwLabel"),
            "w": w, "h": ht, "bottom_centre": [p.x() + w / 2, p.y() + ht],
        })

    out["warnings"] = sorted(set(s.warnings))
    print("RESULT " + json.dumps(out), flush=True)
    smoke_exit(0)


if __name__ == "__main__":
    main()
