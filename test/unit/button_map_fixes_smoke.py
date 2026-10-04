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
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import rig_editor_harness as h  # noqa: E402
from PySide6 import QtCore, QtTest  # noqa: E402

Key = QtCore.Qt.Key


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
    for _ in range(5):
        s.call("nudge", 0.01, 0)
    s.wait(700)
    out["nudge-steps"] = s.state()["histAt"] - before
    for _ in range(3):
        s.call("nudge", 0.01, 0)
    s.call("undo")  # within the pause
    out["undo-after-nudges"] = round(s.node(rect)["fx"] - start, 3)

    # BM10: Layers > Delete on a group that is open for editing removes
    # the whole group.
    group = next(n["id"] for n in s.state()["nodes"] if n.get("members"))
    s.call("beginGroupEdit", group)
    s.call("deleteLayer", group, "")
    out["group-deleted"] = all(n["id"] != group for n in s.state()["nodes"])

    # BM19: after clicking a Layers row, the arrow keys nudge what it picked.
    s.js("showLayers", True)
    s.wait(200)
    name = s.call_on_node("layerName", rect)
    s.click_layer(name)
    start = s.node(rect)["fx"]
    QtTest.QTest.keyClick(s.win, Key.Key_Right)
    s.wait(100)
    out["layers-then-arrow"] = s.node(rect)["fx"] > start

    out["warnings"] = s.warnings
    print("RESULT " + json.dumps(out), flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()
