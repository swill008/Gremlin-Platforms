# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Starts the program off-screen (stand-in hardware) and checks the 3 Oct
review's usability fixes (UI4-UI9); prints the results as JSON.
test_usability_fixes.py runs it in its own process with a fresh user
folder.

    python test/unit/usability_smoke.py
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
fake_hardware.install()

import gremlin.ui.update_model as um  # noqa: E402

um.UpdateModel.startup = lambda self, *a, **k: None

import shiboken6  # noqa: E402
from PySide6 import QtCore, QtGui, QtQml, QtQuick, QtTest  # noqa: E402

import joystick_gremlin  # noqa: E402

Key = QtCore.Qt.Key


def _keyboard_cards(main_win: QtQuick.QQuickWindow, cards: list, out: dict) -> None:
    main_win.requestActivate()
    cards[0].forceActiveFocus(QtCore.Qt.FocusReason.TabFocusReason)
    QtTest.QTest.qWait(100)
    first = cards[0].property("slug")
    QtTest.QTest.keyClick(main_win, Key.Key_Right)
    QtTest.QTest.qWait(100)
    now = next((c for c in cards if c.hasActiveFocus()), None)
    out["arrow-moves"] = bool(now is not None and now.property("slug") != first)
    if now is None:
        out["enter-opens"] = False
        return
    opened: list[str] = []
    now.openConfiguration.connect(lambda: opened.append("configuration"))
    QtTest.QTest.keyClick(main_win, Key.Key_Return)
    QtTest.QTest.qWait(300)
    out["enter-opens"] = opened == ["configuration"]


def main() -> None:
    app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
    win = app.main_window
    win.setProperty("visible", True)
    main_win = shiboken6.wrapInstance(
        shiboken6.getCppPointer(win)[0], QtQuick.QQuickWindow
    )
    main_win.setWidth(1600)
    main_win.setHeight(1000)
    QtTest.QTest.qWait(800)
    out: dict[str, object] = {}

    def run(window: QtCore.QObject, code: str) -> object:
        expr = QtQml.QQmlExpression(QtQml.qmlContext(window), window, code)
        value = expr.evaluate()
        if expr.hasError():
            raise RuntimeError(expr.error().toString())
        return value[0] if isinstance(value, tuple) else value

    def items(item: QtQuick.QQuickItem) -> list:
        found = [item]
        for child in item.childItems():
            found.extend(items(child))
        return found

    def find(root: QtQuick.QQuickItem, text: str) -> QtQuick.QQuickItem | None:
        return next((i for i in items(root) if i.isVisible()
                     and str(i.property("text") or "") == text), None)

    def windows() -> list:
        return [w for w in app.topLevelWindows()
                if w.isVisible() and isinstance(w, QtQuick.QQuickWindow)]

    def window_titled(title: str) -> QtQuick.QQuickWindow | None:
        return next((w for w in windows() if w.title() == title), None)

    # UI4: Output View over the photo reads the same in the light theme.
    run(win, "Style.isDarkMode = false; 1")
    QtTest.QTest.qWait(300)
    button = find(main_win.contentItem(), "Output View")
    if button is not None:
        bg = button.property("background")
        label = button.property("contentItem")
        out["output-view"] = [
            QtGui.QColor(bg.property("color")).name(QtGui.QColor.NameFormat.HexArgb),
            QtGui.QColor(label.property("color")).name(),
        ]
    run(win, "Style.isDarkMode = true; 1")

    # UI7: Tab reaches the Home cards, the arrow keys move between them and
    # Enter opens Configuration.
    cards = [i for i in items(main_win.contentItem())
             if i.objectName() == "statusCard" and i.isVisible()]
    out["cards"] = len(cards)
    if cards:
        _keyboard_cards(main_win, cards, out)
    for w in windows():
        if w is not main_win:
            w.close()
    QtTest.QTest.qWait(200)

    # UI6: Escape closes these tool windows (an open list closes first).
    closed = {}
    for name, title in (("DialogAbout", None), ("DialogOptions", "Options"),
                        ("DialogHelp", None), ("DialogManageModes", None),
                        ("DialogUpdate", "Check for Updates")):
        before = set(windows())
        run(win, f'Helpers.createComponent("{name}.qml"); 1')
        QtTest.QTest.qWait(500)
        new = [w for w in windows() if w not in before]
        if not new:
            closed[name] = "did not open"
            continue
        w = new[0]
        w.requestActivate()
        QtTest.QTest.qWait(100)
        if name == "DialogOptions":
            combo = next((i for i in items(w.contentItem()) if i.isVisible()
                          and i.inherits("QQuickComboBox")), None)
            if combo is not None:
                combo.forceActiveFocus()
                QtTest.QTest.keyClick(w, Key.Key_Space)  # opens its list
                QtTest.QTest.qWait(300)
                listed = bool(combo.property("down"))
                QtTest.QTest.keyClick(w, Key.Key_Escape)
                QtTest.QTest.qWait(300)
                out["esc-closes-list-first"] = [
                    listed,
                    not bool(combo.property("down")),
                    shiboken6.isValid(w) and w.isVisible(),
                ]
        QtTest.QTest.keyClick(w, Key.Key_Escape)
        QtTest.QTest.qWait(300)
        gone = not shiboken6.isValid(w) or not w.isVisible()
        closed[name] = "closed" if gone else "still open"
    out["escape"] = closed

    # UI9: error details wrap and can be copied.
    details = "Traceback (most recent call last):\n" + "x" * 600
    QtCore.QMetaObject.invokeMethod(
        joystick_gremlin.gremlin.signal.signal, "showError",
        QtCore.Q_ARG(str, "Something failed"), QtCore.Q_ARG(str, details),
    )
    QtTest.QTest.qWait(300)
    copy = find(main_win.contentItem(), "Copy Details")
    out["copy-details-shown"] = copy is not None
    if copy is not None:
        QtGui.QGuiApplication.clipboard().setText("")
        QtCore.QMetaObject.invokeMethod(copy, "clicked")
        QtTest.QTest.qWait(100)
        out["copied"] = QtGui.QGuiApplication.clipboard().text() == details
    area = next((i for i in items(main_win.contentItem()) if i.isVisible()
                 and str(i.property("text") or "") == details), None)
    # Two lines of text; the 600-character one wraps onto several more.
    out["details-wrap"] = bool(area is not None and area.property("lineCount") > 2)
    run(win, "_errorDialog.close(); 1")

    # UI8: Device Pack opens without a layout loop (Qt prints that warning
    # on stderr; the test reads it there).
    # A long name wraps beside the picture; resizing the window used to
    # set off the loop (the picture's width followed the row's height).
    before = set(windows())
    print("DEVICE-PACK-OPEN", file=sys.stderr, flush=True)
    run(win, 'Helpers.createComponent("DialogDevicePack.qml"); 1')
    QtTest.QTest.qWait(800)
    pack = next((w for w in windows() if w not in before), None)
    if pack is not None:
        pack.setProperty("exportName", "Virpil Constellation Alpha Prime Right " * 3)
        pack.setProperty("exportPhoto", QtCore.QUrl.fromLocalFile(
            str(ROOT / "gfx" / "icon.png")).toString())
        for width, height in ((900, 600), (1300, 700), (1000, 900)):
            pack.setWidth(width)
            pack.setHeight(height)
            QtTest.QTest.qWait(300)
    print("DEVICE-PACK-DONE", file=sys.stderr, flush=True)

    print("RESULT " + json.dumps(out), flush=True)
    os._exit(0)


if __name__ == "__main__":
    try:
        main()
    except BaseException:
        import traceback

        traceback.print_exc()
        sys.stdout.flush()
        os._exit(1)  # Qt teardown can hang off-screen
