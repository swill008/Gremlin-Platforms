# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""qml/HelpSearchBar.qml, the Help window's search row (01 S137): typing
filters live with "N topics match" / "No topic mentions 'x'", the Search all
of Help tick box only when Help shows one chapter, "k of n" with previous /
next, Enter for next, and Esc or × clears and (01 S134) leaves the box.

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

    property var lastResults: null
    property int resultSignals: 0
    property int nexts: 0
    property int previouses: 0

    HelpSearchBar {
        id: _bar
        objectName: "bar"
        x: 10; y: 10; width: 400
        topics: [
            { title: "Rename a device", body: "<p>Choose <b>Rename…</b>.</p>",
              chapterId: "device-library", chapter: "Device Library" },
            { title: "Undo a change", body: "<p>Press <b>Ctrl+Z</b> on a device.</p>",
              chapterId: "device-library", chapter: "Device Library" },
            { title: "Modes", body: "<p>A mode for each device.</p>",
              chapterId: "modes", chapter: "Modes" }
        ]
        onResultsChanged: (results) => {
            _win.lastResults = results
            _win.resultSignals++
        }
        onNext: _win.nexts++
        onPrevious: _win.previouses++
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
    here = QtCore.QUrl.fromLocalFile(str(_ROOT / "qml" / "HelpSearchBarHarness.qml"))
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

    def type_text(text: str) -> None:
        # Real key events with text (QTest.keyClicks takes widgets only).
        for ch in text:
            key = (
                QtCore.Qt.Key.Key_Space if ch == " " else QtCore.Qt.Key(ord(ch.upper()))
            )
            for kind in (QtCore.QEvent.Type.KeyPress, QtCore.QEvent.Type.KeyRelease):
                QtCore.QCoreApplication.sendEvent(
                    quick,
                    QtGui.QKeyEvent(
                        kind, key, QtCore.Qt.KeyboardModifier.NoModifier, ch
                    ),
                )
        QtTest.QTest.qWait(20)

    def visible(name: str) -> bool:
        item = find(name)
        return bool(item is not None and item.isVisible())

    def summary() -> str:
        return str(find("helpSearchSummary").property("text"))

    def results() -> str:
        return str(ev("JSON.stringify(_win.lastResults)"))

    # Not scoped: no tick box, nothing shown under the box.
    report("all-box-unscoped", visible("helpSearchAll"))
    ev("_bar.focusField()")
    QtTest.QTest.qWait(50)
    report("field-focused", find("helpSearchField").hasActiveFocus())
    type_text("DEVICE  re")
    QtTest.QTest.qWait(50)
    report("summary-two", summary())
    report("results-two", results())
    type_text("x")
    QtTest.QTest.qWait(50)
    report("summary-none", summary())
    report("results-none", results())
    report("nav-hidden-zero", visible("helpSearchPosition"))

    # Scoped to one chapter: only its topics, then Search all of Help.
    ev('_bar.scopedChapter = "modes"')
    ev("_bar.clear()")
    QtTest.QTest.qWait(50)
    report("results-blank", results())
    report("summary-blank-hidden", not visible("helpSearchSummary"))
    report("all-box-scoped", visible("helpSearchAll"))
    ev("_bar.focusField()")
    type_text("device")
    QtTest.QTest.qWait(50)
    report("scoped-results", results())
    report("summary-scoped", summary())
    click("helpSearchAll")
    report("all-of-help", ev("_bar.allOfHelp"))
    report("all-results", results())
    report("summary-all", summary())

    # k of n, previous / next, Enter.
    ev("_bar.total = 5; _bar.current = 1")
    QtTest.QTest.qWait(50)
    report("position", find("helpSearchPosition").property("text"))
    click("helpSearchNext")
    click("helpSearchPrevious")
    click("helpSearchPrevious")
    ev("_bar.focusField()")
    QtTest.QTest.keyClick(quick, QtCore.Qt.Key.Key_Return)
    QtTest.QTest.qWait(50)
    report("nexts", ev("_win.nexts"))
    report("previouses", ev("_win.previouses"))
    report("field-kept-focus-on-nav", find("helpSearchField").hasActiveFocus())

    # Esc clears and leaves the box.
    QtTest.QTest.keyClick(quick, QtCore.Qt.Key.Key_Escape)
    QtTest.QTest.qWait(50)
    report("esc-text", repr(ev("_bar.text")))
    report("esc-focus", find("helpSearchField").hasActiveFocus())
    report("esc-results", results())

    # × clears too.
    ev("_bar.focusField()")
    type_text("mode")
    QtTest.QTest.qWait(50)
    report("clear-visible", visible("helpSearchClear"))
    click("helpSearchClear")
    report("clear-text", repr(ev("_bar.text")))

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


def test_help_search_bar(tmp_path: pathlib.Path) -> None:
    r = _run(tmp_path)
    assert r["all-box-unscoped"] == "False"
    assert r["field-focused"] == "True"
    # Typed words in any case: both Device Library topics hold "device" and
    # "re" (Rename / Press), Modes doesn't hold "re".
    assert r["summary-two"] == "2 topics match"
    assert r["results-two"] == (
        '[{"index":0,"count":3,"chapterId":"device-library","inScope":true},'
        '{"index":1,"count":2,"chapterId":"device-library","inScope":true}]'
    )
    assert r["summary-none"] == "No topic mentions 'DEVICE  rex'"
    assert r["results-none"] == "[]"
    assert r["nav-hidden-zero"] == "False"
    # Blank search: [] means show every topic; no summary line.
    assert r["results-blank"] == "[]"
    assert r["summary-blank-hidden"] == "True"
    assert r["all-box-scoped"] == "True"
    assert (
        r["scoped-results"]
        == '[{"index":2,"count":1,"chapterId":"modes","inScope":true}]'
    )
    assert r["summary-scoped"] == "1 topic matches"
    assert r["all-of-help"] == "True"
    assert r["all-results"] == (
        '[{"index":0,"count":1,"chapterId":"device-library","inScope":false},'
        '{"index":1,"count":1,"chapterId":"device-library","inScope":false},'
        '{"index":2,"count":1,"chapterId":"modes","inScope":true}]'
    )
    assert r["summary-all"] == "3 topics match"
    assert r["position"] == "2 of 5"
    assert r["nexts"] == "2"
    assert r["previouses"] == "2"
    assert r["field-kept-focus-on-nav"] == "True"
    assert r["esc-text"] == "''"
    assert r["esc-focus"] == "False"
    assert r["esc-results"] == "[]"
    assert r["clear-visible"] == "True"
    assert r["clear-text"] == "''"


if __name__ == "__main__":
    if "--smoke" in sys.argv:
        _smoke()
