# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""qml/SearchBox.qml, the shared search box (01 S141, D-01-SEARCH-BOX):
Ctrl+F goes to it, × clears it, Esc clears it and (01 S134) leaves the box,
Enter is accepted, and the line under it says "N found" / "Nothing matches"
(or the caller's countText), hidden for count -1 or a blank search.

Needs a QGuiApplication with a real (off-screen) window, so the checks run in
a child process (this file run as a script) printing "RESULT name value".
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[2]

_HARNESS = r"""
import QtQuick
import QtQuick.Controls
import Gremlin.Style

ApplicationWindow {
    id: _win
    width: 600
    height: 300
    visible: true

    property int accepts: 0
    property int clears: 0

    SearchBox {
        id: _box
        objectName: "box"
        x: 10; y: 10; width: 400
        placeholder: "Search layers…"
        onAccepted: _win.accepts++
        onCleared: _win.clears++
    }
    Button {
        objectName: "elsewhere"
        x: 450; y: 250; width: 100; height: 30
        text: "Other"
    }
}
"""


def _smoke() -> None:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ["QT_QUICK_CONTROLS_STYLE"] = "GremlinStyle"
    os.environ["QT_FILE_SELECTORS"] = "Universal"
    os.environ.setdefault(
        "QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
    )
    sys.path.insert(0, str(_ROOT))

    import shiboken6
    from PySide6 import QtCore, QtGui, QtQml, QtQuick, QtTest

    import gremlin.ui.leave_text

    class FakeBackend(QtCore.QObject):
        uiScaleChanged = QtCore.Signal()
        uiScale = QtCore.Property(int, fget=lambda self: 100, notify=uiScaleChanged)

    sys.stdout.reconfigure(encoding="utf-8")
    app = QtGui.QGuiApplication(sys.argv[:1])
    keep = gremlin.ui.leave_text.install(app)  # noqa: F841
    QtQml.qmlRegisterSingletonType(
        QtCore.QUrl.fromLocalFile(str(_ROOT / "qml" / "Style.qml")),
        "Gremlin.Style",
        1,
        0,
        "Style",
    )
    engine = QtQml.QQmlApplicationEngine()
    engine.addImportPath(str(_ROOT / "theme"))
    backend = FakeBackend()
    engine.rootContext().setContextProperty("backend", backend)
    warnings: list[str] = []
    engine.warnings.connect(lambda ws: warnings.extend(w.toString() for w in ws))
    here = QtCore.QUrl.fromLocalFile(str(_ROOT / "qml" / "SearchBoxHarness.qml"))
    engine.loadData(_HARNESS.encode("utf-8"), here)
    roots = engine.rootObjects()
    if not roots:
        print("ERROR window did not load", flush=True)
        for w in warnings:
            print(f"WARN {w}", flush=True)
        print("done", flush=True)
        return
    win = roots[0]
    quick = shiboken6.wrapInstance(
        shiboken6.getCppPointer(win)[0], QtQuick.QQuickWindow
    )
    quick.requestActivate()
    QtTest.QTest.qWait(200)

    def ev(code: str) -> object:
        expr = QtQml.QQmlExpression(QtQml.qmlContext(win), win, code)
        value = expr.evaluate()
        if expr.hasError():
            print(f"ERROR {code}: {expr.error().toString()}", flush=True)
        return value[0] if isinstance(value, tuple) else value

    def find(name: str) -> QtQuick.QQuickItem:
        return win.findChild(QtQuick.QQuickItem, name)

    def report(name: str, value: object) -> None:
        print(f"RESULT {name} {value}", flush=True)

    def click(name: str) -> None:
        item = find(name)
        centre = item.mapToScene(QtCore.QPointF(item.width() / 2, item.height() / 2))
        QtTest.QTest.mouseClick(
            quick,
            QtCore.Qt.MouseButton.LeftButton,
            QtCore.Qt.KeyboardModifier.NoModifier,
            centre.toPoint(),
        )
        QtTest.QTest.qWait(50)

    def key(
        code: QtCore.Qt.Key,
        mods: QtCore.Qt.KeyboardModifier = QtCore.Qt.KeyboardModifier.NoModifier,
    ) -> None:
        QtTest.QTest.keyClick(quick, code, mods)
        QtTest.QTest.qWait(50)

    def type_text(text: str) -> None:
        # Real key events with text (QTest.keyClicks takes widgets only).
        for ch in text:
            code = (
                QtCore.Qt.Key.Key_Space if ch == " " else QtCore.Qt.Key(ord(ch.upper()))
            )
            for kind in (QtCore.QEvent.Type.KeyPress, QtCore.QEvent.Type.KeyRelease):
                QtCore.QCoreApplication.sendEvent(
                    quick,
                    QtGui.QKeyEvent(
                        kind, code, QtCore.Qt.KeyboardModifier.NoModifier, ch
                    ),
                )
        QtTest.QTest.qWait(50)

    def visible(name: str) -> bool:
        item = find(name)
        return bool(item is not None and item.isVisible())

    def focused() -> bool:
        return bool(find("searchField").hasActiveFocus())

    def line() -> str:
        return str(find("searchCount").property("text"))

    report("placeholder", find("searchField").property("placeholderText"))
    report("start-focus", focused())

    # Ctrl+F goes to the box; typing fills it.
    key(QtCore.Qt.Key.Key_F, QtCore.Qt.KeyboardModifier.ControlModifier)
    report("ctrlf-focus", focused())
    type_text("ab")
    report("typed", ev("_box.text"))

    # The count line.
    report("line-minus-one", visible("searchCount"))
    ev("_box.count = 3")
    QtTest.QTest.qWait(20)
    report("line-three-visible", visible("searchCount"))
    report("line-three", line())
    ev("_box.count = 0")
    QtTest.QTest.qWait(20)
    report("line-zero", line())
    ev('_box.countText = "2 of 5 layers"')
    QtTest.QTest.qWait(20)
    report("line-override", line())
    ev('_box.countText = ""')
    QtTest.QTest.qWait(20)

    # Enter.
    key(QtCore.Qt.Key.Key_Return)
    report("accepts", ev("_win.accepts"))
    report("enter-kept-focus", focused())

    # × clears (and the line goes with the text).
    report("clear-visible", visible("searchClear"))
    click("searchClear")
    report("clear-text", repr(ev("_box.text")))
    report("clear-signals", ev("_win.clears"))
    report("line-empty-hidden", not visible("searchCount"))
    report("clear-gone", not visible("searchClear"))

    # Esc clears and leaves the box.
    ev("_box.focusField()")
    type_text("mode")
    key(QtCore.Qt.Key.Key_Escape)
    report("esc-text", repr(ev("_box.text")))
    report("esc-signals", ev("_win.clears"))
    report("esc-focus", focused())

    # Ctrl+F off: the shortcut does nothing.
    ev("_box.findShortcut = false")
    key(QtCore.Qt.Key.Key_F, QtCore.Qt.KeyboardModifier.ControlModifier)
    report("ctrlf-off", focused())

    for w in warnings:
        print(f"WARN {w}", flush=True)
    print("done", flush=True)


def _run(tmp_path: pathlib.Path) -> dict[str, str]:
    result = subprocess.run(
        [sys.executable, str(pathlib.Path(__file__).resolve()), "--smoke"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        cwd=str(tmp_path),
        env={
            **os.environ,
            "QT_QPA_PLATFORM": "offscreen",
            "PYTHONIOENCODING": "utf-8",
            "USERPROFILE": str(tmp_path),
        },
    )
    lines = result.stdout.splitlines()
    assert "done" in lines, (result.stderr or "")[-2000:]
    problems = [line for line in lines if line.startswith(("ERROR", "WARN"))]
    assert problems == [], problems
    return {
        line.split(" ", 2)[1]: line.split(" ", 2)[2]
        for line in lines
        if line.startswith("RESULT ") and line.count(" ") >= 2
    }


def test_search_box(tmp_path: pathlib.Path) -> None:
    r = _run(tmp_path)
    assert r["placeholder"] == "Search layers…"
    assert r["start-focus"] == "False"
    assert r["ctrlf-focus"] == "True"
    assert r["typed"] == "ab"
    assert r["line-minus-one"] == "False"
    assert r["line-three-visible"] == "True"
    assert r["line-three"] == "3 found"
    assert r["line-zero"] == "Nothing matches"
    assert r["line-override"] == "2 of 5 layers"
    assert r["accepts"] == "1"
    assert r["enter-kept-focus"] == "True"
    assert r["clear-visible"] == "True"
    assert r["clear-text"] == "''"
    assert r["clear-signals"] == "1"
    assert r["line-empty-hidden"] == "True"
    assert r["clear-gone"] == "True"
    assert r["esc-text"] == "''"
    assert r["esc-signals"] == "2"
    assert r["esc-focus"] == "False"
    assert r["ctrlf-off"] == "False"


if __name__ == "__main__":
    if "--smoke" in sys.argv:
        _smoke()
