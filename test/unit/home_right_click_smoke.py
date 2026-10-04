# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Starts the program off-screen (stand-in hardware) on Home, right-clicks
device cards and prints which card shows as picked, as JSON.
test_home_right_click.py runs it in its own process with a fresh user
folder.

    python test/unit/home_right_click_smoke.py
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location(
    "fake_hardware", ROOT / "test" / "fake_hardware.py"
)
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake = fake_hardware.install()

import gremlin.ui.update_model as um  # noqa: E402

um.UpdateModel.startup = lambda self, *a, **k: None

import shiboken6  # noqa: E402
from PySide6 import QtCore, QtQml, QtQuick, QtTest  # noqa: E402

import joystick_gremlin  # noqa: E402


def main() -> None:
    app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
    # The main window, shown (off-screen): Home makes its cards then.
    win = app.main_window
    win.setProperty("visible", True)
    root = shiboken6.wrapInstance(shiboken6.getCppPointer(win)[0], QtQuick.QQuickWindow)
    root.setWidth(1400)
    root.setHeight(900)
    QtTest.QTest.qWait(1500)
    out: dict = {}

    def ev(code: str) -> object:
        expr = QtQml.QQmlExpression(QtQml.qmlContext(root), root, code)
        value = expr.evaluate()
        if expr.hasError():
            return "error: " + expr.error().toString()
        value = value[0] if isinstance(value, tuple) else value
        return value.toVariant() if hasattr(value, "toVariant") else value

    def items(item: QtQuick.QQuickItem) -> list:
        found = [item]
        for child in item.childItems():
            found += items(child)
        return found

    cards = [
        c for c in items(root.contentItem())
        if c.metaObject().indexOfSignal("cardFocused()") >= 0
        and c.isVisible() and c.width() > 0
    ]
    out["cards"] = len(cards)
    out["rows"] = ev("_moduleModel.rowCount()")
    out["room"] = ev("uiState.currentRoom")

    def centre(card: QtQuick.QQuickItem) -> QtCore.QPoint:
        p = card.mapToScene(QtCore.QPointF(card.width() / 2, card.height() / 2))
        return p.toPoint()

    def click(
        card: QtQuick.QQuickItem,
        button: QtCore.Qt.MouseButton,
        mods: QtCore.Qt.KeyboardModifier = QtCore.Qt.KeyboardModifier.NoModifier,
    ) -> None:
        QtTest.QTest.mouseClick(root, button, mods, centre(card))
        QtTest.QTest.qWait(300)

    def state() -> dict:
        return {
            "focused": [c.property("slug") for c in cards if c.property("focused")],
            "selected": [c.property("slug") for c in cards if c.property("selected")],
        }

    right = QtCore.Qt.MouseButton.RightButton
    left = QtCore.Qt.MouseButton.LeftButton
    escape = QtCore.Qt.Key.Key_Escape
    if len(cards) >= 3:
        a, b, c = cards[0], cards[1], cards[2]
        out["slugs"] = [a.property("slug"), b.property("slug"), c.property("slug")]
        click(a, left)
        out["left-a"] = state()
        # Right-click another card: it shows as picked too.
        click(b, right)
        out["right-b"] = state()
        QtTest.QTest.keyClick(root, escape)
        QtTest.QTest.qWait(200)
        # A Shift selection of two: a right-click on one of them keeps both.
        shift = QtCore.Qt.KeyboardModifier.ShiftModifier
        click(a, left, shift)
        click(c, left, shift)
        before = state()
        click(c, right)
        out["right-in-selection"] = [before, state()]
        QtTest.QTest.keyClick(root, escape)
    print("RESULT " + json.dumps(out), flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()
