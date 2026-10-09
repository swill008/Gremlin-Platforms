# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""01 S135 (D-01-ONE-RENAME) in the Button Map editor: the Layers panel's
inline rename and a chip's rename on the map, driven by real key and mouse
events off-screen with the program-wide leave-text filter installed.
Prints RESULT lines as JSON; test_rename_rig.py runs it in its own process.

    python test/unit/rename_rig_smoke.py
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
Ctrl = QtCore.Qt.KeyboardModifier.ControlModifier


def _result(name: str, value: object) -> None:
    print("RESULT", name, json.dumps(value))
    sys.stdout.flush()


def _focus(s: h.Session) -> dict:
    """What has the keys: a text box or not, and what is selected in it."""
    item = s.win.activeFocusItem()
    typing = item is not None and (
        item.inherits("QQuickTextInput") or item.inherits("QQuickTextEdit")
    )
    return {
        "typing": typing,
        "selected": str(item.property("selectedText") or "") if typing else "",
    }


def _hist(s: h.Session) -> int:
    return int(s.call_prop("histAt"))  # type: ignore[arg-type]


def _dclick(s: h.Session, pos: QtCore.QPoint) -> None:
    QtTest.QTest.mouseDClick(
        s.win,
        QtCore.Qt.MouseButton.LeftButton,
        QtCore.Qt.KeyboardModifier.NoModifier,
        pos,
    )
    s.wait(200)


def _layers(s: h.Session, blank: QtCore.QPoint) -> None:
    s.call("setDrawTool", "rect")
    s.drag(s.point(0.05, 0.85), s.point(0.12, 0.92))
    s.call("setDrawTool", "")
    s.wait(150)
    shape = s.state()["selected"][0]
    s.call("seedHist")

    def start(name: str) -> dict:
        # Selected already (selecting rebuilds the rows mid double-click),
        # and not taken as a double-click with the click before.
        s.call("setSelection", [shape])
        s.wait(700)
        r = s.layer_row(name)
        _dclick(s, QtCore.QPoint(round(r["x"] + 80), round(r["y"] + r["h"] / 2)))
        return _focus(s)

    def has(name: str) -> bool:
        return int(s.js("layerRowIndex", name)) >= 0  # type: ignore[arg-type]

    # Opens focused with the whole name selected; Enter saves once.
    opened = start("Rectangle")
    s.type_text("Cover")
    h0 = _hist(s)
    QtTest.QTest.keyClick(s.win, Key.Key_Return)
    s.wait(150)
    h1 = _hist(s)
    s.click(blank)
    s.wait(150)
    _result(
        "layer-enter",
        {
            "opened": opened,
            "renamed": has("Cover"),
            "steps-enter": h1 - h0,
            "steps-leave": _hist(s) - h1,
        },
    )

    # A click away saves once.
    start("Cover")
    s.type_text("Lid")
    h0 = _hist(s)
    s.click(blank)
    s.wait(150)
    h1 = _hist(s)
    s.click(blank)
    s.wait(150)
    _result(
        "layer-click-away",
        {
            "renamed": has("Lid"),
            "typing": _focus(s)["typing"],
            "steps": h1 - h0,
            "steps-after": _hist(s) - h1,
        },
    )

    # One undo step per rename: Ctrl+Z gives back the name before.
    s.key(Key.Key_Z, Ctrl)
    s.wait(150)
    _result("layer-undo", {"back": has("Cover"), "gone": not has("Lid")})

    # Esc cancels; the old name stays.
    start("Cover")
    s.type_text("Zap")
    h0 = _hist(s)
    QtTest.QTest.keyClick(s.win, Key.Key_Escape)
    s.wait(150)
    s.click(blank)
    s.wait(150)
    _result(
        "layer-esc",
        {"kept": has("Cover"), "typed": has("Zap"), "steps": _hist(s) - h0},
    )

    # An empty name isn't saved; the old name stays.
    start("Cover")
    QtTest.QTest.keyClick(s.win, Key.Key_Backspace)
    h0 = _hist(s)
    QtTest.QTest.keyClick(s.win, Key.Key_Return)
    s.wait(150)
    _result(
        "layer-empty",
        {"kept": has("Cover"), "steps": _hist(s) - h0},
    )


def _chip(s: h.Session, blank: QtCore.QPoint) -> None:
    chip = next(n for n in s.state()["nodes"] if n.get("kind") == "btn")["id"]

    def start() -> dict:
        s.call("setSelection", [])
        s.wait(500)
        _dclick(s, s.center(chip))
        out = _focus(s)
        out["draft"] = s.call_prop("renameDraft")
        out["open"] = s.call_prop("renameId") == chip
        return out

    def name() -> str:
        return str(s.node(chip).get("friendly") or "")

    s.call("seedHist")

    # Opens focused with the whole name selected; Enter saves once.
    opened = start()
    s.type_text("Fire")
    h0 = _hist(s)
    QtTest.QTest.keyClick(s.win, Key.Key_Return)
    s.wait(150)
    h1 = _hist(s)
    s.click(blank)
    s.wait(150)
    _result(
        "chip-enter",
        {
            "opened": opened,
            "name": name(),
            "open": s.call_prop("renameId") == chip,
            "steps-enter": h1 - h0,
            "steps-leave": _hist(s) - h1,
        },
    )

    # A click on the map away from it saves once.
    start()
    s.type_text("Jump")
    h0 = _hist(s)
    s.click(blank)
    s.wait(150)
    _result(
        "chip-click-away",
        {
            "name": name(),
            "open": s.call_prop("renameId") == chip,
            "steps": _hist(s) - h0,
        },
    )

    # One undo step per rename.
    s.key(Key.Key_Z, Ctrl)
    s.wait(150)
    _result("chip-undo", {"name": name()})

    # Esc cancels; the old name stays.
    before = name()
    start()
    s.type_text("Zap")
    h0 = _hist(s)
    QtTest.QTest.keyClick(s.win, Key.Key_Escape)
    s.wait(150)
    s.click(blank)
    s.wait(150)
    _result(
        "chip-esc",
        {
            "before": before,
            "name": name(),
            "open": s.call_prop("renameId") == chip,
            "steps": _hist(s) - h0,
        },
    )

    # An empty name brings back the default label (the user, 2026-10-08).
    before = name()
    start()
    QtTest.QTest.keyClick(s.win, Key.Key_Backspace)
    QtTest.QTest.keyClick(s.win, Key.Key_Return)
    s.wait(150)
    _result("chip-empty", {"before": before, "name": name()})


def main() -> None:
    s = h.Session(Path(os.environ.get("TEMP", ".")), "rename_rig")
    keep = gremlin.ui.leave_text.install(s.app)  # noqa: F841
    h._load(s, "evo_r")
    blank = s.point(0.5, 0.97)
    s.js("showLayers", True)

    _layers(s, blank)
    _chip(s, blank)

    _result("warnings", sorted(set(s.warnings)))
    print("done")
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
