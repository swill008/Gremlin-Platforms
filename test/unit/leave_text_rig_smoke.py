# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""01 S134 (D-01-LEAVE-TEXT) in the Button Map editor's panels: the Layers
panel's inline rename and the Properties panel's number boxes, left by a
click outside or Esc with the program-wide leave-text filter installed.
Prints RESULT lines as JSON; test_leave_text_rig.py runs it in its own
process.

    python test/unit/leave_text_rig_smoke.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import rig_editor_harness as h  # noqa: E402
from PySide6 import QtCore, QtTest  # noqa: E402

import gremlin.ui.leave_text  # noqa: E402

Key = QtCore.Qt.Key


def _result(name: str, value: object) -> None:
    print("RESULT", name, json.dumps(value))
    sys.stdout.flush()


def _typing(s: h.Session) -> bool:
    item = s.win.activeFocusItem()
    return item is not None and item.inherits("QQuickTextInput")


def _start_rename(s: h.Session, name: str, id_: str) -> bool:
    # Selected already (selecting rebuilds the rows mid double-click), and
    # not taken as a double-click with the click before.
    s.call("setSelection", [id_])
    s.wait(700)
    r = s.layer_row(name)
    QtTest.QTest.mouseDClick(
        s.win,
        QtCore.Qt.MouseButton.LeftButton,
        QtCore.Qt.KeyboardModifier.NoModifier,
        QtCore.QPoint(round(r["x"] + 80), round(r["y"] + r["h"] / 2)),
    )
    s.wait(150)
    return _typing(s)


def main() -> None:
    s = h.Session(Path(os.environ.get("TEMP", ".")), "leave_text_rig")
    keep = gremlin.ui.leave_text.install(s.app)  # noqa: F841
    h._load(s, "evo_r")
    blank = s.point(0.5, 0.97)

    # --- Layers panel: inline rename ------------------------------------
    s.js("showLayers", True)
    s.call("setDrawTool", "rect")
    s.drag(s.point(0.05, 0.85), s.point(0.12, 0.92))
    s.call("setDrawTool", "")
    s.wait(150)
    shape = s.state()["selected"][0]

    # Click away: the typed name is kept.
    started = _start_rename(s, "Rectangle", shape)
    s.type_text("Cover")
    s.click(blank)
    s.wait(150)
    _result(
        "rename-click-away",
        {
            "started": started,
            "typing": _typing(s),
            "renamed": s.js("layerRowIndex", "Cover") >= 0,
            "old": s.js("layerRowIndex", "Rectangle") >= 0,
        },
    )

    # Esc still cancels, and the focus loss after it doesn't save.
    name = "Cover" if s.js("layerRowIndex", "Cover") >= 0 else "Rectangle"
    started = _start_rename(s, name, shape)
    s.type_text("Zap")
    QtTest.QTest.keyClick(s.win, Key.Key_Escape)
    s.wait(150)
    _result(
        "rename-esc",
        {
            "started": started,
            "typing": _typing(s),
            "kept": s.js("layerRowIndex", name) >= 0,
            "typed": s.js("layerRowIndex", "Zap") >= 0,
        },
    )

    # Enter still saves.
    started = _start_rename(s, name, shape)
    s.type_text("Lid")
    QtTest.QTest.keyClick(s.win, Key.Key_Return)
    s.wait(150)
    _result(
        "rename-enter",
        {
            "started": started,
            "typing": _typing(s),
            "renamed": s.js("layerRowIndex", "Lid") >= 0,
        },
    )
    s.js("showLayers", False)

    # --- Properties panel: a number box ---------------------------------
    s.js("showProps", True)
    s.call("setDrawTool", "rect")
    s.drag(s.point(0.30, 0.60), s.point(0.40, 0.70))
    s.call("setDrawTool", "")
    s.wait(150)
    rect = s.state()["selected"][0]

    def field(label: str) -> dict:
        r = json.loads(s.js("propFieldRect", label))
        assert r, f"no property {label!r}"
        return r

    def type_into(label: str, text: str) -> bool:
        r = field(label)
        s.click(
            QtCore.QPoint(round(r["x"] + r["w"] / 2), round(r["y"] + r["h"] / 2))
        )
        QtTest.QTest.keyClick(
            s.win, Key.Key_A, QtCore.Qt.KeyboardModifier.ControlModifier
        )
        s.type_text(text)
        return _typing(s)

    def props() -> list:
        s.call("setSelection", [rect])
        s.wait(100)
        return json.loads(s.js("propLines"))

    def hist() -> int:
        return int(s.call_prop("histAt"))  # type: ignore[arg-type]

    # Click away (on the map): the number is applied.
    before = props()
    focused = type_into("X", "5")
    s.click(blank)
    s.wait(150)
    _result(
        "props-click-away",
        {"focused": focused, "typing": _typing(s), "before": before, "after": props()},
    )

    # Esc: the number is applied too.
    focused = type_into("Y", "10")
    QtTest.QTest.keyClick(s.win, Key.Key_Escape)
    s.wait(150)
    _result(
        "props-esc",
        {"focused": focused, "typing": _typing(s), "after": props()},
    )

    # Enter applies once: one undo step, not two.
    h0 = hist()
    focused = type_into("Width", "15")
    QtTest.QTest.keyClick(s.win, Key.Key_Return)
    s.wait(150)
    h1 = hist()
    s.click(blank)
    s.wait(150)
    h2 = hist()
    _result(
        "props-enter",
        {
            "focused": focused,
            "after": props(),
            "steps-enter": h1 - h0,
            "steps-leave": h2 - h1,
        },
    )

    _result("warnings", sorted(set(s.warnings)))
    print("done")
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
