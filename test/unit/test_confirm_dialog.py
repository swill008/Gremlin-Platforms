# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""qml/ConfirmDialog.qml, qml/confirm.js and qml/DangerButton.qml, the one
question before every delete, remove or clear (01 S140, D-01-CONFIRM): the
title names the action, the text says what goes, the last line says
"You can restore it from Tools › History." / "This can't be undone." (or the
note), a red button named for the action and Cancel. Cancel has the focus;
Enter and Esc cancel; only a click (or Space) on the red button goes ahead;
one question at a time per window. The red button's colours come from Style.

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
import "confirm.js" as Confirm

ApplicationWindow {
    id: _win
    width: 700
    height: 500
    visible: true

    property int accepts: 0
    property int cancels: 0
    property var dlg: null
    property var second: null
    property var innerDlg: null

    function ask(undoable, note) {
        dlg = Confirm.ask(_host, {
            title: "Delete mode Combat?",
            text: "12 bindings go with it.",
            undoable: undoable,
            note: note,
            action: "Delete Mode",
            onAccept: function() { _win.accepts++ },
            onCancel: function() { _win.cancels++ }
        })
    }
    // A Window declared inside another object has a parent (Qt 6.7+): the
    // question must still open in it (the Button Map is such a window).
    function askInner() {
        _inner.visible = true
        innerDlg = Confirm.ask(_inner, { title: "Inner?", action: "Remove" })
    }
    function askAgain() {
        second = Confirm.ask(_win, { title: "Again?", action: "Remove" })
    }

    Item {
        id: _host
        anchors.fill: parent
        Window {
            id: _inner
            width: 320
            height: 240
            visible: false
        }
    }

    DangerButton {
        id: _danger
        objectName: "danger"
        x: 10; y: 10; width: 160; height: 40
        text: "Clear History…"
        // The off-screen platform turns hover off by default.
        hoverEnabled: true
    }
    DangerButton {
        objectName: "dangerOff"
        x: 10; y: 60; width: 160; height: 40
        text: "Remove"
        enabled: false
    }
    Button {
        objectName: "elsewhere"
        x: 500; y: 450; width: 100; height: 30
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

    class FakeBackend(QtCore.QObject):
        uiScaleChanged = QtCore.Signal()
        uiScale = QtCore.Property(int, fget=lambda self: 100, notify=uiScaleChanged)

    sys.stdout.reconfigure(encoding="utf-8")
    app = QtGui.QGuiApplication(sys.argv[:1])  # noqa: F841
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
    here = QtCore.QUrl.fromLocalFile(str(_ROOT / "qml" / "ConfirmDialogHarness.qml"))
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

    def find(name: str) -> QtQuick.QQuickItem | None:
        return win.findChild(QtQuick.QQuickItem, name)

    def report(name: str, value: object) -> None:
        print(f"RESULT {name} {value}", flush=True)

    def centre(name: str) -> QtCore.QPoint:
        item = find(name)
        assert item is not None, name
        return item.mapToScene(
            QtCore.QPointF(item.width() / 2, item.height() / 2)
        ).toPoint()

    def click(name: str) -> None:
        QtTest.QTest.mouseClick(
            quick,
            QtCore.Qt.MouseButton.LeftButton,
            QtCore.Qt.KeyboardModifier.NoModifier,
            centre(name),
        )
        QtTest.QTest.qWait(100)

    def key(code: QtCore.Qt.Key) -> None:
        QtTest.QTest.keyClick(quick, code)
        QtTest.QTest.qWait(100)

    def text_of(name: str) -> str:
        item = find(name)
        return "<missing>" if item is None else str(item.property("text"))

    def is_open() -> bool:
        return bool(ev("_win.dlg !== null && _win.dlg.opened === true"))

    def counts() -> str:
        return f"{ev('_win.accepts')}/{ev('_win.cancels')}"

    def colour(item: QtQuick.QQuickItem | None, prop: str) -> str:
        if item is None:
            return "<missing>"
        return QtGui.QColor(item.property(prop)).name()

    def style(name: str) -> str:
        return QtGui.QColor(str(ev(f"String(Style.{name})"))).name()

    # Undoable: the History line; Cancel has the focus; Enter cancels.
    ev("_win.ask(true, '')")
    QtTest.QTest.qWait(200)
    report("open1", is_open())
    report("title", text_of("confirmTitle"))
    report("text", text_of("confirmText"))
    report("last-undoable", text_of("confirmLastLine"))
    report("action", text_of("confirmAction"))
    report("cancel-label", text_of("confirmCancel"))
    report("cancel-focus", bool(find("confirmCancel").hasActiveFocus()))
    report("action-red", colour(find("confirmAction").property("background"), "color"))
    # One at a time per window: a second question there does nothing.
    ev("_win.askAgain()")
    report("second-null", ev("_win.second === null"))
    key(QtCore.Qt.Key.Key_Return)
    report("enter-counts", counts())
    report("enter-closed", find("confirmDialog") is None and not is_open())

    # Not undoable: the can't-be-undone line; Esc cancels.
    ev("_win.ask(false, '')")
    QtTest.QTest.qWait(200)
    report("last-not-undoable", text_of("confirmLastLine"))
    key(QtCore.Qt.Key.Key_Escape)
    report("esc-counts", counts())
    report("esc-closed", not is_open())

    # A note replaces the last line; the keypad Enter on the red button
    # (Tab to it) still cancels.
    ev("_win.ask(true, 'Your files stay as they are.')")
    QtTest.QTest.qWait(200)
    report("last-note", text_of("confirmLastLine"))
    key(QtCore.Qt.Key.Key_Backtab)
    report("tab-to-action", bool(find("confirmAction").hasActiveFocus()))
    key(QtCore.Qt.Key.Key_Enter)
    report("enter-on-action-counts", counts())

    # A click on Cancel cancels.
    ev("_win.ask(true, '')")
    QtTest.QTest.qWait(200)
    click("confirmCancel")
    report("cancel-click-counts", counts())

    # A click on the red button goes ahead, once.
    ev("_win.ask(true, '')")
    QtTest.QTest.qWait(200)
    click("confirmAction")
    QtTest.QTest.qWait(100)
    report("action-click-counts", counts())
    report("action-click-closed", not is_open())

    # Space on the red button goes ahead.
    ev("_win.ask(true, '')")
    QtTest.QTest.qWait(200)
    key(QtCore.Qt.Key.Key_Backtab)
    key(QtCore.Qt.Key.Key_Space)
    report("space-counts", counts())

    # DangerButton colours from Style: red, darker on hover, white text,
    # greyed when disabled.
    danger = find("danger")
    fill = danger.property("background")
    label = danger.property("contentItem")
    report("fill", colour(fill, "color") == style("danger"))
    report("label", colour(label, "color") == style("onColor"))
    # Real mouse moves (QTest.mouseMove gives the off-screen window no hover).
    for point in (QtCore.QPoint(300, 300), centre("danger")):
        QtCore.QCoreApplication.sendEvent(
            quick,
            QtGui.QMouseEvent(
                QtCore.QEvent.Type.MouseMove,
                QtCore.QPointF(point),
                QtCore.QPointF(quick.mapToGlobal(point)),
                QtCore.Qt.MouseButton.NoButton,
                QtCore.Qt.MouseButton.NoButton,
                QtCore.Qt.KeyboardModifier.NoModifier,
            ),
        )
        QtTest.QTest.qWait(100)
    report("hovered", bool(danger.property("hovered")))
    report("fill-hover", colour(fill, "color") == style("dangerHover"))
    QtTest.QTest.mousePress(
        quick,
        QtCore.Qt.MouseButton.LeftButton,
        QtCore.Qt.KeyboardModifier.NoModifier,
        centre("danger"),
    )
    QtTest.QTest.qWait(50)
    report("fill-pressed", colour(fill, "color") == style("dangerPressed"))
    QtTest.QTest.mouseRelease(
        quick,
        QtCore.Qt.MouseButton.LeftButton,
        QtCore.Qt.KeyboardModifier.NoModifier,
        centre("danger"),
    )
    off = find("dangerOff")
    report(
        "off-label",
        colour(off.property("contentItem"), "color") == style("fgDisabled"),
    )
    report(
        "off-fill-not-red",
        colour(off.property("background"), "color") != style("danger"),
    )

    ev("_win.askInner()")
    QtTest.QTest.qWait(200)
    report("inner-open", ev("_win.innerDlg !== null && _win.innerDlg.opened"
                            " && _win.innerDlg.parent === _inner.contentItem"))

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
    assert "done" in lines, (result.stdout + result.stderr)[-3000:]
    problems = [line for line in lines if line.startswith(("ERROR", "WARN"))]
    assert problems == [], problems
    return {
        line.split(" ", 2)[1]: line.split(" ", 2)[2]
        for line in lines
        if line.startswith("RESULT ") and line.count(" ") >= 2
    }


def test_confirm_question(tmp_path: pathlib.Path) -> None:
    r = _run(tmp_path)
    assert r["open1"] == "True"
    assert r["title"] == "Delete mode Combat?"
    assert r["text"] == "12 bindings go with it."
    assert r["last-undoable"] == "You can restore it from Tools › History."
    assert r["action"] == "Delete Mode"
    assert r["cancel-label"] == "Cancel"
    assert r["cancel-focus"] == "True"
    assert r["second-null"] == "True"
    # Enter cancels: onAccept never called.
    assert r["enter-counts"] == "0/1"
    assert r["enter-closed"] == "True"
    assert r["last-not-undoable"] == "This can't be undone."
    assert r["esc-counts"] == "0/2"
    assert r["esc-closed"] == "True"
    assert r["last-note"] == "Your files stay as they are."
    assert r["tab-to-action"] == "True"
    assert r["enter-on-action-counts"] == "0/3"
    assert r["cancel-click-counts"] == "0/4"
    assert r["action-click-counts"] == "1/4"
    assert r["action-click-closed"] == "True"
    assert r["space-counts"] == "2/4"
    assert r["inner-open"] == "True"


def test_danger_button_colours(tmp_path: pathlib.Path) -> None:
    r = _run(tmp_path)
    assert r["fill"] == "True"
    assert r["label"] == "True"
    assert r["hovered"] == "True"
    assert r["fill-hover"] == "True"
    assert r["fill-pressed"] == "True"
    assert r["off-label"] == "True"
    assert r["off-fill-not-red"] == "True"


if __name__ == "__main__":
    if "--smoke" in sys.argv:
        _smoke()
