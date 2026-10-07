# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Off-screen run of History's highlighted Before/After
(test_history_diff_window.py, 08 S104).

A module file is saved twice with changes in three places, then History
opens on that device and the newest change is picked: each row's tint and
bar, the changed words of a changed row, the two sides lined up, and Next
Change / Previous Change clicked. With a folder as the first argument it
also saves the window in the light and dark theme there. Prints RESULT
{json}.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location(
    "fake_hardware", ROOT / "test" / "fake_hardware.py"
)
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake_hardware.install()

import gremlin.ui.update_model as um  # noqa: E402

um.UpdateModel.startup = lambda self, *a, **k: None

from PySide6 import QtCore, QtGui, QtQml, QtQuick, QtTest  # noqa: E402

import joystick_gremlin  # noqa: E402
from gremlin import history, util  # noqa: E402
from gremlin.modules import module_file  # noqa: E402


def main() -> None:
    app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
    win = app.main_window
    shots = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    out: dict = {}

    def settle() -> None:
        deadline = time.monotonic() + 5
        while history._writer is not None and time.monotonic() < deadline:
            QtTest.QTest.qWait(20)
        history.flush()

    # Button 2 added near the top; Button 40 / Hat 1 become Axis 1 lower down;
    # two settings change at the end (one with characters HTML would eat).
    buttons = list(range(1, 31))
    path = util.modules_dir() / "diff_stick.json"
    module_file.write_json(
        path,
        {
            "device": "Diff Stick",
            "claim": {"buttons": [b for b in buttons if b != 2] + [40], "hats": [1]},
            "alpha": "slow <b>&amp; steady",
            "omega": "one two three",
        },
    )
    settle()
    module_file.write_json(
        path,
        {
            "device": "Diff Stick",
            "claim": {"buttons": buttons, "axes": [1]},
            "alpha": "fast <b>&amp; steady",
            "omega": "one 2 three",
        },
    )
    settle()

    def ev(code: str) -> object:
        expr = QtQml.QQmlExpression(QtQml.qmlContext(win), win, code)
        value = expr.evaluate()[0]
        assert not expr.hasError(), expr.error().toString()
        return value

    ev(
        'Helpers.createComponent("DialogHistory.qml", '
        '{ filter: JSON.stringify({ device: "Diff Stick" }) })'
    )
    QtTest.QTest.qWait(500)
    hist = next(
        w
        for w in app.topLevelWindows()
        if isinstance(w, QtQuick.QQuickWindow)
        and w.title() == "History"
        and w.isVisible()
    )
    hist.resize(1100, 700)
    QtTest.QTest.qWait(200)

    def hv(code: str) -> object:
        expr = QtQml.QQmlExpression(QtQml.qmlContext(hist), hist, code)
        value = expr.evaluate()[0]
        assert not expr.hasError(), expr.error().toString()
        return value

    def item(name: str) -> QtQuick.QQuickItem | None:
        """By name: delegates aren't object children, so walk the items."""
        pending = [hist.contentItem()]
        while pending:
            current = pending.pop()
            if current.objectName() == name:
                return current
            pending.extend(current.childItems())
        return None

    def click(name: str) -> None:
        """A real mouse click in the middle of the named item."""
        target = item(name)
        assert target is not None, name
        centre = target.mapToScene(
            QtCore.QPointF(target.width() / 2, target.height() / 2)
        ).toPoint()
        QtTest.QTest.mouseClick(hist, QtCore.Qt.MouseButton.LeftButton, pos=centre)
        QtTest.QTest.qWait(150)

    def colour(value: object) -> str:
        return value.name(QtGui.QColor.NameFormat.HexArgb) if value is not None else ""

    def row_item(side: str, index: int) -> QtQuick.QQuickItem | None:
        return item(f"historyRow:{side}:{index}")

    def row_text(row: QtQuick.QQuickItem) -> QtQuick.QQuickItem:
        # The row's shown line (the first TextEdit; the second is unseen).
        edits = [c for c in row.childItems() if c.property("readOnly") is not None]
        return edits[0]

    def lists_state() -> dict:
        before, after = item("history:before"), item("history:after")
        top = before.property("contentY")
        first = hv("_beforeList.indexAt(10, _beforeList.contentY + 2)")
        tops = {}
        for side in ("before", "after"):
            row = row_item(side, first)
            tops[side] = row.mapToScene(QtCore.QPointF(0, 0)).y() if row else None
        return {
            "before-y": top,
            "after-y": after.property("contentY"),
            "first-row": first,
            "aligned": tops["before"] is not None and tops["before"] == tops["after"],
            "previous": item("historyPreviousChange").property("enabled"),
            "next": item("historyNextChange").property("enabled"),
        }

    first = hv("_model.data(_model.index(0, 0), Qt.UserRole + 1)")
    hv(f'pick("{first}")')
    QtTest.QTest.qWait(300)
    rows = hv("JSON.stringify(diffRows)")
    rows = json.loads(rows)
    out["blocks"] = json.loads(hv("JSON.stringify(diffBlocks)"))
    out["kinds"] = [r["kind"] for r in rows]
    out["tokens"] = {
        name: colour(hv(f"Style.{name}"))
        for name in (
            "diffRemovedBg",
            "diffAddedBg",
            "diffRemovedWord",
            "diffAddedWord",
            "diffRemovedBar",
            "diffAddedBar",
            "clear",
        )
    }

    # Every row the window has made, each side: its tint, its bar and its text.
    shown_rows: dict = {}
    for index, row in enumerate(rows):
        for side in ("before", "after"):
            delegate = row_item(side, index)
            if delegate is None:
                continue
            bars = [
                c
                for c in delegate.childItems()
                if c.property("readOnly") is None and c.property("visible")
            ]
            text = row_text(delegate)
            shown_rows[f"{side}:{index}"] = {
                "kind": row["kind"],
                "tint": colour(delegate.property("color")),
                "bar": colour(bars[0].property("color")) if bars else "",
                "rich": hv(
                    f"_{side}List.itemAtIndex({index}).children[1].textFormat"
                    " === TextEdit.RichText"
                ),
                "html": text.property("text"),
                "plain": hv(
                    f"(function() {{ var t = _{side}List.itemAtIndex({index}); "
                    "return t ? t.children[1].getText(0, t.children[1].length) : ''"
                    " })()"
                ),
                "line": row[side],
                "height": delegate.height(),
            }
    out["rows"] = shown_rows
    out["start"] = lists_state()
    # The plain text the earlier tests read is still there.
    out["before-text"] = item("history:before").property("text")

    if shots:
        shots.mkdir(parents=True, exist_ok=True)
        for theme, dark in (("light", "false"), ("dark", "true")):
            ev(f"Style.isDarkMode = {dark}; 1")
            QtTest.QTest.qWait(300)
            hist.grabWindow().save(str(shots / f"history_diff_{theme}.png"))
        ev("Style.isDarkMode = false; 1")
        QtTest.QTest.qWait(200)

    steps = []
    for name in ("historyNextChange",) * 3 + ("historyPreviousChange",) * 2:
        click(name)
        steps.append({"clicked": name, "at": hv("diffAt"), **lists_state()})
    out["steps"] = steps

    if shots:
        click("historyNextChange")
        for theme, dark in (("light", "false"), ("dark", "true")):
            ev(f"Style.isDarkMode = {dark}; 1")
            QtTest.QTest.qWait(300)
            hist.grabWindow().save(str(shots / f"history_diff_{theme}_next.png"))
        ev("Style.isDarkMode = false; 1")

    print("RESULT " + json.dumps(out), flush=True)


# Any error ends the run (the app's threads would keep it alive).
try:
    main()
except BaseException:
    traceback.print_exc()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(1)
os._exit(0)
