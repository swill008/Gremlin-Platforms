# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The docked OSC Monitor panel (qml/OscMonitorPanel.qml, OSC rewrite OP6,
OP8, OP13): folded by default and holding no port; unfolding holds OSC's
port, folding or leaving the page releases it; Add as Input… hands the
message's settings to the page and hides while a profile runs; Pop out and
× ask the page.

Runs the real QML off-screen in a child process (this file run as a
script), with the real model and traffic module, printing
"RESULT name value"."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[2]

_HARNESS = r"""
import QtQuick
import QtQuick.Controls

ApplicationWindow {
    id: _win
    width: 1200
    height: 500
    visible: true

    property var added: null
    property int popOuts: 0
    property int closes: 0

    OscMonitorPanel {
        id: _panel
        objectName: "panel"
        anchors.fill: parent
        onAddAsInputRequested: (settings) => _win.added = settings
        onPopOutRequested: _win.popOuts += 1
        onCloseRequested: _win.closes += 1
    }

    function setFolded(on) { _panel.folded = on }
    function setPageOpen(on) { _panel.pageOpen = on }
}
"""


class FakeRuntime:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def hold_open(self, token: str) -> bool:
        self.calls.append("hold")
        return True

    def release_open(self, token: str) -> None:
        self.calls.append("release")


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

    from gremlin import osc_traffic
    from gremlin.ui import osc_monitor_model as mm

    runtime = FakeRuntime()
    mm._runtime = lambda: runtime  # type: ignore[assignment]

    class FakeBackend(QtCore.QObject):
        uiScaleChanged = QtCore.Signal()
        gremlinActiveChanged = QtCore.Signal()

        def __init__(self) -> None:
            super().__init__()
            self._active = False

        def _get_active(self) -> bool:
            return self._active

        def set_active(self, on: bool) -> None:
            self._active = on
            self.gremlinActiveChanged.emit()

        uiScale = QtCore.Property(int, fget=lambda self: 100, notify=uiScaleChanged)
        gremlinActive = QtCore.Property(
            bool, fget=_get_active, notify=gremlinActiveChanged
        )

    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    app = QtGui.QGuiApplication(sys.argv[:1])  # noqa: F841
    QtQml.qmlRegisterSingletonType(
        QtCore.QUrl.fromLocalFile(str(_ROOT / "qml" / "Style.qml")),
        "Gremlin.Style", 1, 0, "Style",
    )
    engine = QtQml.QQmlApplicationEngine()
    engine.addImportPath(str(_ROOT / "theme"))
    backend = FakeBackend()
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("uiState", None)
    warnings: list[str] = []
    engine.warnings.connect(lambda ws: warnings.extend(w.toString() for w in ws))

    def report(name: str, value: object) -> None:
        print(f"RESULT {name} {json.dumps(value)}", flush=True)

    def plain(value: object) -> object:
        if isinstance(value, QtQml.QJSValue):
            value = value.toVariant()
        return value

    def items(quick: QtQuick.QQuickWindow) -> list[QtQuick.QQuickItem]:
        out: list[QtQuick.QQuickItem] = []
        stack = [quick.contentItem()]
        while stack:
            item = stack.pop()
            out.append(item)
            stack.extend(item.childItems())
        return out

    def find(quick: QtQuick.QQuickWindow, name: str) -> QtQuick.QQuickItem | None:
        for item in items(quick):
            if item.objectName() == name and item.isVisible():
                return item
        return None

    def click(quick: QtQuick.QQuickWindow, name: str) -> bool:
        item = find(quick, name)
        if item is None:
            return False
        point = item.mapToScene(
            QtCore.QPointF(item.width() / 2, item.height() / 2)
        ).toPoint()
        QtTest.QTest.mouseClick(
            quick, QtCore.Qt.MouseButton.LeftButton,
            QtCore.Qt.KeyboardModifier.NoModifier, point,
        )
        QtTest.QTest.qWait(150)
        return True

    def call(obj: QtCore.QObject, name: str, value: object) -> None:
        QtCore.QMetaObject.invokeMethod(
            obj, name, QtCore.Qt.ConnectionType.DirectConnection,
            QtCore.Q_RETURN_ARG("QVariant"), QtCore.Q_ARG("QVariant", value),
        )
        QtTest.QTest.qWait(150)

    osc_traffic.clear()
    osc_traffic.note("in", "/known", [1], ("10.0.0.9", 8000), ["OSC Button 1"])
    osc_traffic.note("in", "/fader/3", [0.25], ("10.0.0.9", 8000), [])
    engine.loadData(
        _HARNESS.encode("utf-8"),
        QtCore.QUrl.fromLocalFile(str(_ROOT / "qml" / "OscMonitorPanelHarness.qml")),
    )
    roots = engine.rootObjects()
    if not roots:
        print("ERROR panel did not load", flush=True)
    else:
        win = roots[-1]
        quick = shiboken6.wrapInstance(
            shiboken6.getCppPointer(win)[0], QtQuick.QQuickWindow
        )
        QtTest.QTest.qWait(300)

        # Folded by default: title row only, no port.
        report("folded-calls", list(runtime.calls))
        report("folded-shows", [find(quick, n) is not None for n in (
            "oscMonitorTitle", "oscMonitorFilter", "oscMonitorList",
            "oscMonitorPopOut", "oscMonitorClose")])

        # Clicking the title unfolds it and holds the port.
        report("title-click", click(quick, "oscMonitorTitle"))
        report("unfold-calls", list(runtime.calls))
        lst = find(quick, "oscMonitorList")
        report("list-count", lst.property("count") if lst else None)

        # Folding releases; unfold again holds; leaving the page releases.
        call(win, "setFolded", True)
        report("fold-calls", list(runtime.calls))
        call(win, "setFolded", False)
        call(win, "setPageOpen", False)
        report("leave-calls", list(runtime.calls))
        call(win, "setPageOpen", True)
        QtTest.QTest.qWait(200)

        # Add as Input… on the "no input" row goes to the page.
        report("add-click", click(quick, "oscMonitorAddRow1"))
        report("added", plain(win.property("added")))

        # A running profile hides Add as Input… (OP13).
        backend.set_active(True)
        QtTest.QTest.qWait(150)
        report("add-while-running", find(quick, "oscMonitorAddRow1") is not None)
        backend.set_active(False)
        QtTest.QTest.qWait(150)
        report("add-after-stop", find(quick, "oscMonitorAddRow1") is not None)

        # Pop out and × ask the page.
        click(quick, "oscMonitorPopOut")
        click(quick, "oscMonitorClose")
        report("pop-outs", win.property("popOuts"))
        report("closes", win.property("closes"))

    for w in warnings:
        print(f"WARN {w}", flush=True)
    print("done", flush=True)


def _run(tmp_path: pathlib.Path) -> tuple[dict[str, object], list[str]]:
    result = subprocess.run(
        [sys.executable, __file__],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        cwd=str(_ROOT),
        env={
            **os.environ,
            "QT_QPA_PLATFORM": "offscreen",
            "USERPROFILE": str(tmp_path),
        },
    )
    lines = result.stdout.splitlines()
    assert "done" in lines, result.stdout[-3000:] + result.stderr[-3000:]
    got: dict[str, object] = {}
    for line in lines:
        if line.startswith("RESULT "):
            _, name, value = line.split(" ", 2)
            got[name] = json.loads(value)
    problems = [
        line for line in lines
        if line.startswith("ERROR")
        or (line.startswith("WARN") and ("Osc" in line or "Monitor" in line))
    ]
    return got, problems


def test_docked_panel_folds_holds_port_and_adds(tmp_path: pathlib.Path) -> None:
    got, problems = _run(tmp_path)
    assert problems == [], problems
    assert got["folded-calls"] == []
    assert got["folded-shows"] == [True, False, False, True, True]
    assert got["title-click"] is True
    assert got["unfold-calls"] == ["hold"]
    assert got["list-count"] == 2
    assert got["fold-calls"] == ["hold", "release"]
    assert got["leave-calls"] == ["hold", "release", "hold", "release"]
    assert got["add-click"] is True
    added = got["added"]
    assert isinstance(added, dict)
    assert added["address"] == "/fader/3" and added["mode"] == "axis"
    assert got["add-while-running"] is False
    assert got["add-after-stop"] is True
    assert got["pop-outs"] == 1
    assert got["closes"] == 1


if __name__ == "__main__":
    _smoke()
