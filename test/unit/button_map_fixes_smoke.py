# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Drives the Button Map editor off-screen through the 3 Oct review's
Button Map fixes (BM4, BM10, BM14, BM19) and prints the results as JSON.
test_button_map_fixes.py runs it in its own process.

    python test/unit/button_map_fixes_smoke.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from collections.abc import Callable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import rig_editor_harness as h  # noqa: E402
from PySide6 import QtCore, QtTest  # noqa: E402

Key = QtCore.Qt.Key
# Generous: a busy PC is slow, never wrong.
_LIMIT_S = 15.0


def _until(check: Callable[[], object], limit: float = _LIMIT_S) -> object:
    """Runs the event loop until check() is true (its value), up to limit."""
    end = time.monotonic() + limit
    while True:
        value = check()
        if value or time.monotonic() > end:
            return value
        QtTest.QTest.qWait(20)


def _draw(s: h.Session, tool: str, a: tuple, b: tuple) -> str:
    s.call("setDrawTool", tool)
    s.drag(s.point(*a), s.point(*b))
    s.call("setDrawTool", "")
    return s.state()["selected"][0]


def main() -> None:
    s = h.Session(Path(os.environ.get("TEMP", ".")), "fixes")
    out: dict[str, object] = {}
    h._load(s, "evo_r")

    # BM4: Shape on a mixed selection reshapes the plain shapes only, and
    # Arrange > Hide hides the whole selection in one undo step.
    rect = _draw(s, "rect", (0.10, 0.70), (0.20, 0.80))
    s.call("applyField", "fill", "filled")  # clickable in the middle
    text = _draw(s, "text", (0.25, 0.70), (0.40, 0.76))
    line = _draw(s, "line", (0.45, 0.70), (0.55, 0.80))
    s.call("setSelection", [rect, text, line])
    s.set_prop("selectedId", rect)
    s.call("applyField", "shape", "ellipse")
    out["shapes"] = [s.node(i)["shape"] for i in (rect, text, line)]
    before = s.state()["histAt"]
    s.right_click(s.center(rect))
    # BM18: a mixed selection only gets the rows that apply to all of it.
    out["mixed-menu"] = [line.strip("> v").strip() for line in s.state()["menu"]]
    s.open_menu_section("Arrange")
    s.click_menu_row("Hide")
    s.close_menus()
    out["arrange-hide"] = [bool(s.node(i).get("hidden")) for i in (rect, text, line)]
    out["arrange-hide-steps"] = s.state()["histAt"] - before
    s.call("showAll")

    # BM14: Hide Selected on three items is one undo step.
    s.call("setSelection", [rect, text, line])
    s.set_prop("selectedId", rect)
    before = s.state()["histAt"]
    s.right_click(s.center(rect))
    s.click_menu_row("Hide Selected")
    s.close_menus()
    out["hide-selected-steps"] = s.state()["histAt"] - before
    s.call("showAll")

    # BM14: a run of arrow-key nudges is one undo step, and Undo straight
    # after them (before the pause) takes them all back.
    s.call("setSelection", [rect])
    s.set_prop("selectedId", rect)
    start = s.node(rect)["fx"]
    before = s.state()["histAt"]
    # Runs stay open until end_run(): however slow the PC, the nudges are
    # one run and the Undo below comes within its pause.
    s.hold_runs()
    for _ in range(5):
        s.call("nudge", 0.01, 0)
    # The run's step goes into the history when the nudges pause.
    s.end_run()
    out["nudge-steps"] = s.state()["histAt"] - before
    for _ in range(3):
        s.call("nudge", 0.01, 0)
    out["nudge-run-waiting"] = s.call_prop("stepWaiting")
    s.call("undo")  # within the pause
    out["undo-after-nudges"] = round(s.node(rect)["fx"] - start, 3)
    # The normal pause again for the rest.
    s.set_prop("stepPauseMs", 400)

    # BM10: Layers > Delete on a group that is open for editing removes
    # the whole group.
    group = next(n["id"] for n in s.state()["nodes"] if n.get("members"))
    s.call("beginGroupEdit", group)
    s.call("deleteLayer", group, "")
    out["group-deleted"] = all(n["id"] != group for n in s.state()["nodes"])

    # BM19: after clicking a Layers row, the arrow keys nudge what it picked.
    s.js("showLayers", True)
    name = s.call_on_node("layerName", rect)
    _until(lambda: s.js("layerRowIndex", name) >= 0)
    s.click_layer(name)
    start = s.node(rect)["fx"]
    QtTest.QTest.keyClick(s.win, Key.Key_Right)
    out["layers-then-arrow"] = bool(_until(lambda: s.node(rect)["fx"] > start))

    # A right-click on a Layers row picks it, as a left click does, and its
    # menu opens; on a row in a selection, the selection stays.
    def right_click_layer(node: str) -> None:
        r = s.layer_row(s.call_on_node("layerName", node))
        middle = QtCore.QPoint(round(r["x"] + r["w"] / 2), round(r["y"] + r["h"] / 2))
        s.right_click(middle)
        s.wait(200)

    s.call("setSelection", [rect])
    right_click_layer(text)
    from PySide6 import QtQml

    menu = QtQml.QQmlExpression(QtQml.qmlContext(s.win), s.win, "_layers.rowMenuOpen")
    opened = menu.evaluate()
    opened = opened[0] if isinstance(opened, tuple) else opened
    out["layers-right-click"] = [s.state()["selected"], opened, text]
    s.close_menus()
    s.call("setSelection", [rect, text])
    right_click_layer(text)
    kept = sorted(s.state()["selected"]) == sorted([rect, text])
    out["layers-right-click-in-selection"] = kept
    s.close_menus()

    # BM13: mid-drag, only the dragged chip follows the drag tick; it is
    # drawn where its data says, and so is a chip that stays.
    from PySide6 import QtQml

    def ev(code: str) -> object:
        expr = QtQml.QQmlExpression(QtQml.qmlContext(s.win), s.win, code)
        value = expr.evaluate()
        assert not expr.hasError(), expr.error().toString()
        return value[0] if isinstance(value, tuple) else value

    plain = [n["id"] for n in s.state()["nodes"]
             if n["kind"] == "btn" and not n.get("members") and not n.get("hidden")]
    dragged, still = plain[0], plain[-1]
    drawn = ("(function(id) { var e = ed(); var i = e.nodeIndex(id);"
             " var it = e._chipsItem(i); var n = e.nodeAt(id);"
             " return Math.abs(it.x - e.fxToX(n.chipFx)) < 0.5"
             " && Math.abs(it.y - e.fyToY(n.chipFy)) < 0.5 })")
    s.call("setSelection", [])
    start = s.center(dragged)
    QtTest.QTest.mousePress(s.win, QtCore.Qt.MouseButton.LeftButton,
                            QtCore.Qt.KeyboardModifier.NoModifier, start)
    for i in range(1, 6):
        step = QtCore.QPoint(start.x() + i * 8, start.y() + i * 3)
        QtTest.QTest.mouseMove(s.win, step)
        s.wait(20)
    out["mid-drag"] = {
        "dragged-follows": bool(ev(f"{drawn}('{dragged}')")),
        "still-in-place": bool(ev(f"{drawn}('{still}')")),
        "moved": bool(ev(f"ed().nodeAt('{dragged}').chipFx")
                      != s.node(still)["chipFx"]),
        "live-leaders": bool(ev(f"!!ed().liveLeaderIds['{dragged}']")),
    }
    QtTest.QTest.mouseRelease(s.win, QtCore.Qt.MouseButton.LeftButton,
                              QtCore.Qt.KeyboardModifier.NoModifier,
                              QtCore.QPoint(start.x() + 40, start.y() + 15))
    s.wait(100)
    out["after-drag"] = bool(ev(f"{drawn}('{dragged}')"))

    out["warnings"] = s.warnings
    print("RESULT " + json.dumps(out), flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()
