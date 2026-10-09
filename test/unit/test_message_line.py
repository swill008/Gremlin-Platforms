# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""qml/MessageLine.qml, the shared message line (01 S142, D-01-MESSAGE-LINE):
plain for done, red for failed, an Undo link only when given (a click runs it
once), stays until the next show() / clear().

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
    height: 200
    visible: true

    property int undos: 0

    MessageLine {
        id: _line
        x: 0; y: 0; width: 600
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
    here = QtCore.QUrl.fromLocalFile(str(_ROOT / "qml" / "MessageLineHarness.qml"))
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

    def shown(name: str) -> bool:
        item = find(name)
        return bool(item is not None and item.isVisible() and item.width() > 0)

    def colour(name: str) -> str:
        return QtGui.QColor(find(name).property("color")).name()

    def colour_of(code: str) -> str:
        return QtGui.QColor(ev(code)).name()

    line = "messageLine"
    report("empty-hidden", not shown(line))

    # Done: plain.
    ev("_line.show('Renamed.')")
    QtTest.QTest.qWait(50)
    report("plain-shown", shown(line))
    report("plain-text", ev("_line.text"))
    report("plain-failed", ev("_line.failed"))
    report("plain-colour", colour("messageText") == colour_of("Style.fg"))
    report("plain-no-undo", not shown("messageUndo"))

    # Failed: the failed colour.
    ev("_line.show('That didn\\'t work.', true)")
    QtTest.QTest.qWait(50)
    report("failed-failed", ev("_line.failed"))
    report("failed-colour", colour("messageText") == colour_of("Style.dangerText"))
    report("failed-no-undo", not shown("messageUndo"))

    # Undo: shown only with undoText; a real click runs it once.
    ev("_line.show('Deleted.', false, '', function() { _win.undos++ })")
    QtTest.QTest.qWait(50)
    report("no-undo-text-hidden", not shown("messageUndo"))
    ev("_line.show('Deleted.', false, 'Undo', function() { _win.undos++ })")
    QtTest.QTest.qWait(50)
    report("undo-shown", shown("messageUndo"))
    report("undo-label", ev("_line.undoText"))
    click("messageUndo")
    click("messageUndo")
    report("undos", ev("_win.undos"))
    # The message stays after the click and with time passing.
    QtTest.QTest.qWait(300)
    report("stays-text", ev("_line.text"))
    report("stays-shown", shown(line))

    # The next show replaces it.
    ev("_line.show('Copied.')")
    QtTest.QTest.qWait(50)
    report("next-text", ev("_line.text"))
    report("next-no-undo", not shown("messageUndo"))

    # clear() empties.
    ev("_line.clear()")
    QtTest.QTest.qWait(50)
    report("clear-text", repr(ev("_line.text")))
    report("clear-failed", ev("_line.failed"))
    report("clear-hidden", not shown(line))

    # The × clears too.
    ev("_line.show('Saved.', true)")
    QtTest.QTest.qWait(50)
    click("messageClose")
    report("close-text", repr(ev("_line.text")))

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


def test_message_line(tmp_path: pathlib.Path) -> None:
    r = _run(tmp_path)
    assert r["empty-hidden"] == "True"
    assert r["plain-shown"] == "True"
    assert r["plain-text"] == "Renamed."
    assert r["plain-failed"] == "False"
    assert r["plain-colour"] == "True"
    assert r["plain-no-undo"] == "True"
    assert r["failed-failed"] == "True"
    assert r["failed-colour"] == "True"
    assert r["failed-no-undo"] == "True"
    assert r["no-undo-text-hidden"] == "True"
    assert r["undo-shown"] == "True"
    assert r["undo-label"] == "Undo"
    assert r["undos"] == "1"
    assert r["stays-text"] == "Deleted."
    assert r["stays-shown"] == "True"
    assert r["next-text"] == "Copied."
    assert r["next-no-undo"] == "True"
    assert r["clear-text"] == "''"
    assert r["clear-failed"] == "False"
    assert r["clear-hidden"] == "True"
    assert r["close-text"] == "''"


if __name__ == "__main__":
    if "--smoke" in sys.argv:
        _smoke()
