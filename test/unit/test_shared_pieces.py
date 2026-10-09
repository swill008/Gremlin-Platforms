# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""01 S143 (D-01-SHARED-PIECES): qml/SectionHeading.qml (bold title, thin
rule), qml/EmptyState.qml (muted text, one button for the next step) and
qml/UndoBar.qml (Undo / Redo with the last change beside it, as the Device
Library's status bar, D-10-STATUS-LAST).

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
    width: 700
    height: 500
    visible: true

    property int undos: 0
    property int redos: 0
    property int actions: 0

    SectionHeading {
        id: _heading
        objectName: "heading"
        x: 10; y: 10; width: 300
        text: "Outputs"
    }

    EmptyState {
        id: _empty
        objectName: "empty"
        x: 10; y: 80; width: 400; height: 150
        text: "No devices to show."
        actionText: "Add Device…"
        onAction: _win.actions++
    }

    UndoBar {
        id: _bar
        objectName: "bar"
        x: 10; y: 300; width: 600
        undoTip: "Rename Stick"
        redoTip: "Swap Sticks"
        lastChange: "Last change: Rename Stick"
        onUndo: _win.undos++
        onRedo: _win.redos++
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
    here = QtCore.QUrl.fromLocalFile(str(_ROOT / "qml" / "SharedPiecesHarness.qml"))
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

    def centre(name: str) -> QtCore.QPoint:
        item = find(name)
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
        QtTest.QTest.qWait(50)

    def visible(name: str) -> bool:
        item = find(name)
        return bool(item is not None and item.isVisible())

    def shown_texts() -> list[str]:
        # Every visible text in the scene, tooltips (in the overlay) included.
        found: list[str] = []

        def walk(item: QtQuick.QQuickItem) -> None:
            if not item.isVisible():
                return
            text = item.property("text")
            if isinstance(text, str) and text and item.inherits("QQuickText"):
                found.append(text)
            for child in item.childItems():
                walk(child)

        walk(quick.contentItem())
        return found

    def tip_after_hover(name: str) -> bool:
        QtTest.QTest.mouseMove(quick, QtCore.QPoint(690, 490))
        QtTest.QTest.qWait(100)
        QtTest.QTest.mouseMove(quick, centre(name))
        QtTest.QTest.qWait(1500)
        return shown_texts()

    # SectionHeading: bold title, thin rule in Style.line under it.
    report("heading-text", find("sectionHeadingText").property("text"))
    report("heading-bold", ev("_heading.children[0].font.bold"))
    rule = find("sectionHeadingRule")
    title = find("sectionHeadingText")
    report("rule-height", rule.height())
    report("rule-below", rule.y() >= title.y() + title.height())
    report("rule-width", rule.width() == 300)
    report("rule-colour", ev("Qt.colorEqual(_heading.children[1].color, Style.line)"))

    # EmptyState: centred muted text and its one button.
    report("empty-text", find("emptyStateText").property("text"))
    report(
        "empty-muted",
        ev("Qt.colorEqual(_empty.children[0].children[0].color, Style.fgMuted)"),
    )
    text_item = find("emptyStateText")
    middle = text_item.mapToScene(QtCore.QPointF(text_item.width() / 2, 0)).x()
    report("empty-centred", abs(middle - (10 + 400 / 2)) <= 2)
    report("empty-action-visible", visible("emptyStateAction"))
    report("empty-action-text", find("emptyStateAction").property("text"))
    click("emptyStateAction")
    report("empty-actions", ev("_win.actions"))
    ev('_empty.actionText = ""')
    QtTest.QTest.qWait(50)
    report("empty-action-hidden", not visible("emptyStateAction"))

    # UndoBar: nothing to undo or redo, both off; clicks do nothing.
    report("bar-text", find("undoBarText").property("text"))
    report("undo-off", find("undoBarUndo").property("enabled"))
    report("redo-off", find("undoBarRedo").property("enabled"))
    click("undoBarUndo")
    click("undoBarRedo")
    report("clicks-while-off", f"{ev('_win.undos')},{ev('_win.redos')}")

    ev("_bar.canUndo = true")
    QtTest.QTest.qWait(50)
    report("undo-on", find("undoBarUndo").property("enabled"))
    report("redo-still-off", find("undoBarRedo").property("enabled"))
    click("undoBarUndo")
    report("undos", ev("_win.undos"))
    report("undo-tip", "Rename Stick" in tip_after_hover("undoBarUndo"))

    # The newest step was an Undo: the text says what Redo puts back.
    ev('_bar.canRedo = true; _bar.undone = "Undone: Swap Sticks"')
    QtTest.QTest.qWait(50)
    report("bar-undone", find("undoBarText").property("text"))
    click("undoBarRedo")
    click("undoBarRedo")
    report("redos", ev("_win.redos"))
    report("redo-tip", "Swap Sticks" in tip_after_hover("undoBarRedo"))
    ev('_bar.undone = ""')
    QtTest.QTest.qWait(50)
    report("bar-back", find("undoBarText").property("text"))
    ev('_bar.lastChange = ""')
    QtTest.QTest.qWait(50)
    report("bar-blank-hidden", not visible("undoBarText"))

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


def test_shared_pieces(tmp_path: pathlib.Path) -> None:
    r = _run(tmp_path)
    # SectionHeading
    assert r["heading-text"] == "Outputs"
    assert r["heading-bold"] == "True"
    assert r["rule-height"] == "1.0"
    assert r["rule-below"] == "True"
    assert r["rule-width"] == "True"
    assert r["rule-colour"] == "True"
    # EmptyState
    assert r["empty-text"] == "No devices to show."
    assert r["empty-muted"] == "True"
    assert r["empty-centred"] == "True"
    assert r["empty-action-visible"] == "True"
    assert r["empty-action-text"] == "Add Device…"
    assert r["empty-actions"] == "1"
    assert r["empty-action-hidden"] == "True"
    # UndoBar
    assert r["bar-text"] == "Last change: Rename Stick"
    assert r["undo-off"] == "False"
    assert r["redo-off"] == "False"
    assert r["clicks-while-off"] == "0,0"
    assert r["undo-on"] == "True"
    assert r["redo-still-off"] == "False"
    assert r["undos"] == "1"
    assert r["undo-tip"] == "True"
    assert r["bar-undone"] == "Undone: Swap Sticks"
    assert r["redos"] == "2"
    assert r["redo-tip"] == "True"
    assert r["bar-back"] == "Last change: Rename Stick"
    assert r["bar-blank-hidden"] == "True"


if __name__ == "__main__":
    if "--smoke" in sys.argv:
        _smoke()
