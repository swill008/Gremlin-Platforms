# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Unused QML memory is released one delay after a burst of page unloads
and tool window closes, through one helper (01 S199, D-01-RELEASE-UNUSED).

Each test runs off-screen in its own process: the tests' qapp fixture would
start the whole program (test/conftest.py qapp_cls). Waits poll for the
result, never a fixed time (GL-001).
"""

from __future__ import annotations

import os
import pathlib
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)

_ROOT = pathlib.Path(__file__).resolve().parents[2]

# The real PageLoader.qml and helpers.js: the test file sits in qml/ (by
# its URL) so both resolve as they do for Main.qml.
_BURST = r"""
import os, pathlib, sys, tempfile, time
sys.path.insert(0, sys.argv[1])
from PySide6 import QtCore, QtGui, QtQml, QtTest
from gremlin.ui import memory_release

calls = []
_real = memory_release.release_unused
def _counted(engine):
    calls.append(time.monotonic())
    return _real(engine)
memory_release.release_unused = _counted

tool = pathlib.Path(tempfile.mkdtemp()) / "ToolWindow.qml"
tool.write_text("import QtQuick\nimport QtQuick.Window\nWindow { width: 50 }\n")
tool_url = QtCore.QUrl.fromLocalFile(str(tool)).toString()

app = QtGui.QGuiApplication([])
engine = QtQml.QQmlApplicationEngine()
memory_release.expose(engine)
qml = pathlib.Path(sys.argv[1]) / "qml" / "_memory_release_test.qml"
engine.loadData(b'''
import QtQuick
import QtQuick.Window
import "helpers.js" as Helpers
Window {
    property bool pagesOn: true
    Component { id: _item; Item {} }
    function openTools(url) {
        var w = []
        for (var i = 0; i < 3; i++)
            w.push(Helpers.createComponent(url + "?" + i))
        return w.length
    }
    function closeTools(url) {
        for (var i = 0; i < 3; i++)
            Helpers.windowOf(url + "?" + i).close()
    }
    PageLoader { traceName: "A"; active: pagesOn; sourceComponent: _item }
    PageLoader { traceName: "B"; active: pagesOn; sourceComponent: _item }
    PageLoader { traceName: "C"; active: pagesOn; sourceComponent: _item }
}
''', QtCore.QUrl.fromLocalFile(str(qml)))
roots = engine.rootObjects()
print("loaded", bool(roots), flush=True)
root = roots[0]
QtCore.QMetaObject.invokeMethod(root, "openTools", QtCore.Q_ARG("QVariant", tool_url))
QtTest.QTest.qWait(50)
calls.clear()
started = time.monotonic()
root.setProperty("pagesOn", False)
QtCore.QMetaObject.invokeMethod(root, "closeTools", QtCore.Q_ARG("QVariant", tool_url))
QtTest.QTest.qWait(memory_release.DELAY_MS // 3)
print("none-yet", calls == [], flush=True)
end = time.monotonic() + 30  # generous: a busy PC is slow
while not calls and time.monotonic() < end:
    QtTest.QTest.qWait(20)
QtTest.QTest.qWait(memory_release.DELAY_MS + 300)
print("once", len(calls) == 1, flush=True)
late = bool(calls) and calls[0] - started >= memory_release.DELAY_MS / 1000 - 0.05
print("after-delay", late, flush=True)
os._exit(0)
"""

# A page loaded, the cache trimmed, the page loaded again.
_RELOAD = r"""
import os, pathlib, sys, tempfile, time
sys.path.insert(0, sys.argv[1])
from PySide6 import QtCore, QtGui, QtQml, QtTest
from gremlin.ui import memory_release

folder = pathlib.Path(tempfile.mkdtemp())
(folder / "Inner.qml").write_text("import QtQuick\nRectangle { property int n: 7 }\n")
(folder / "Page.qml").write_text(
    "import QtQuick\nItem { property int total: inner.n + 1\n Inner { id: inner } }\n")
app = QtGui.QGuiApplication([])
engine = QtQml.QQmlApplicationEngine()
memory_release.expose(engine)
qml = pathlib.Path(sys.argv[1]) / "qml" / "_memory_release_test.qml"
page = QtCore.QUrl.fromLocalFile(str(folder / "Page.qml")).toString()
engine.loadData(('''
import QtQuick
import QtQuick.Window
Window {
    property bool pageOn: true
    property int total: loader.item ? loader.item.total : -1
    PageLoader { id: loader; traceName: "P"; active: pageOn; source: "%s" }
}
''' % page).encode(), QtCore.QUrl.fromLocalFile(str(qml)))
root = engine.rootObjects()[0]
print("first", root.property("total") == 8, flush=True)
root.setProperty("pageOn", False)
QtTest.QTest.qWait(50)
print("released", memory_release.release_unused(engine), flush=True)
root.setProperty("pageOn", True)
end = time.monotonic() + 30
while root.property("total") != 8 and time.monotonic() < end:
    QtTest.QTest.qWait(20)
print("again", root.property("total") == 8, flush=True)
os._exit(0)
"""


def _run(script: str) -> dict[str, str]:
    result = proc_tree.run(
        [sys.executable, "-c", script, str(_ROOT)],
        text=True,
        timeout=90,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
    )
    out = result.stdout.splitlines()
    lines = dict(line.split(" ", 1) for line in out if " " in line)
    lines["stderr"] = result.stderr[-2000:]
    return lines


def test_a_burst_of_unloads_and_closes_releases_once_after_the_delay() -> None:
    lines = _run(_BURST)
    err = lines.pop("stderr")
    assert lines == {
        "loaded": "True",
        "none-yet": "True",
        "once": "True",
        "after-delay": "True",
    }, err


def test_a_page_loads_again_after_a_trim() -> None:
    lines = _run(_RELOAD)
    err = lines.pop("stderr")
    assert lines == {"first": "True", "released": "True", "again": "True"}, err


def test_release_unused_does_nothing_without_an_engine() -> None:
    from gremlin.ui import memory_release

    assert memory_release.release_unused(None) is False


def test_main_window_exposes_it_before_main_qml() -> None:
    # Next to windowTrace, which is set before Main.qml loads.
    text = (_ROOT / "joystick_gremlin.py").read_text(encoding="utf-8")
    trace = text.index("window_trace.expose(self.engine)")
    expose = text.index("memory_release.expose(self.engine)")
    assert 0 < expose - trace < 400
