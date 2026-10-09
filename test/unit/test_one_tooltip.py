# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""One shared tooltip (01 S136, D-01-ONE-TOOLTIP): every tooltip shows after
the program's one delay (Style.tooltipDelayMs) while the pointer rests on the
item and wraps long text at Style.tooltipMaxWidth; no window sets its own
delay.

The off-screen check runs this file as a script in its own process: it loads
a small window in the program's control style (GremlinStyle), rests the
pointer on items with plain tooltips (no delay set) and prints
"RESULT name value" lines.
"""

from __future__ import annotations

import os
import pathlib
import re
import subprocess
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[2]

# A hand-set delay as a number: "ToolTip.delay: 600" on an item, or
# "delay: 400" on a ToolTip / PointerTip (the only QML users of "delay").
_NUMERIC_DELAY = re.compile(r"(?:ToolTip\.|\b)delay\s*:\s*\d")


def test_no_hand_set_tooltip_delays() -> None:
    """No QML file sets its own tooltip delay as a number."""
    found = []
    for top in ("qml", "theme", "action_plugins"):
        for path in sorted((_ROOT / top).rglob("*.qml")):
            for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if _NUMERIC_DELAY.search(line):
                    rel = path.relative_to(_ROOT).as_posix()
                    found.append(f"{rel}:{n}: {line.strip()}")
    assert found == [], "hand-set tooltip delays:\n" + "\n".join(found)


_HARNESS = r"""
import QtQuick
import QtQuick.Controls
import Gremlin.Style

ApplicationWindow {
    id: _win
    width: 900
    height: 600
    visible: true

    property string longText: "This tooltip text is long on purpose so that it has to "
        + "wrap onto more than one line at the program's one tooltip width, and "
        + "it keeps going for a while longer to make sure of it, well past any "
        + "reasonable single line of text in a small box."

    // A plain attached tooltip: no delay set.
    Rectangle {
        id: _short
        x: 50; y: 200; width: 80; height: 40
        color: "grey"
        HoverHandler { id: _shortHover }
        ToolTip.visible: _shortHover.hovered
        ToolTip.text: "Short tip"
    }

    // A plain attached tooltip with long text.
    Rectangle {
        id: _long
        x: 300; y: 200; width: 80; height: 40
        color: "grey"
        HoverHandler { id: _longHover }
        ToolTip.visible: _longHover.hovered
        ToolTip.text: _win.longText
    }

    // A tooltip object with no delay set.
    Rectangle {
        id: _obj
        x: 600; y: 200; width: 80; height: 40
        color: "grey"
        HoverHandler { id: _objHover }
        property alias tip: _objTip
        ToolTip {
            id: _objTip
            visible: _objHover.hovered
            text: _win.longText
        }
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
    app = QtGui.QGuiApplication(sys.argv[:1])
    font = QtGui.QFont("Segoe UI")
    font.setPixelSize(15)
    app.setFont(font)
    QtQml.qmlRegisterSingletonType(
        QtCore.QUrl.fromLocalFile(str(_ROOT / "qml" / "Style.qml")),
        "Gremlin.Style", 1, 0, "Style",
    )
    engine = QtQml.QQmlApplicationEngine()
    engine.addImportPath(str(_ROOT / "theme"))
    backend = FakeBackend()
    engine.rootContext().setContextProperty("backend", backend)
    warnings: list[str] = []
    engine.warnings.connect(lambda ws: warnings.extend(w.toString() for w in ws))
    here = QtCore.QUrl.fromLocalFile(str(_ROOT / "test" / "unit" / "Harness.qml"))
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
    QtTest.QTest.qWait(300)

    def ev(code: str) -> object:
        expr = QtQml.QQmlExpression(QtQml.qmlContext(win), win, code)
        value = expr.evaluate()
        if expr.hasError():
            print(f"ERROR {code}: {expr.error().toString()}", flush=True)
        return value[0] if isinstance(value, tuple) else value

    def rest_on(x: int, y: int) -> None:
        QtTest.QTest.mouseMove(quick, QtCore.QPoint(x, y))

    def report(name: str, value: object) -> None:
        print(f"RESULT {name} {value}", flush=True)

    report("delay-ms", ev("String(Style.tooltipDelayMs)"))
    report("max-width", ev("String(Style.tooltipMaxWidth)"))

    # Each item: rest the pointer on it, look at ~0.3 s and ~0.85 s, then leave.
    for name, x, tip in (
        ("attached", 90, "_short.ToolTip.toolTip"),
        ("attached-long", 340, "_long.ToolTip.toolTip"),
        ("object", 640, "_obj.tip"),
    ):
        rest_on(10, 10)
        QtTest.QTest.qWait(200)
        rest_on(x, 220)
        QtTest.QTest.qWait(300)
        report(f"{name}-early", ev(f"String(!!{tip} && {tip}.visible)"))
        QtTest.QTest.qWait(550)
        report(f"{name}-late", ev(f"String(!!{tip} && {tip}.visible)"))
        report(f"{name}-width", ev(f"String(Math.round({tip}.width))"))
        report(f"{name}-lines", ev(f"String({tip}.contentItem.lineCount)"))
        rest_on(10, 10)
        QtTest.QTest.qWait(200)

    for w in warnings:
        print(f"WARN {w}", flush=True)
    print("done", flush=True)


def test_plain_tooltip_waits_and_wraps(tmp_path: pathlib.Path) -> None:
    """A tooltip with no delay set appears after Style.tooltipDelayMs while the
    pointer rests on the item and wraps long text at Style.tooltipMaxWidth."""
    result = subprocess.run(
        [sys.executable, str(pathlib.Path(__file__).resolve()), "--smoke"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        cwd=str(tmp_path),
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen", "PYTHONIOENCODING": "utf-8",
             "QT_LOGGING_RULES": "qt.qml.binding.removal.info=true"},
    )
    lines = result.stdout.splitlines()
    assert "done" in lines, (result.stderr or "")[-2000:]
    problems = [line for line in lines if line.startswith(("ERROR", "WARN"))]
    assert problems == []
    # The shared delay is set without overwriting its own binding (the
    # program logged "Overwriting binding on ToolTip ... delay").
    assert "Overwriting binding" not in (result.stderr or ""), result.stderr[-2000:]
    results = {
        line.split(" ", 2)[1]: line.split(" ", 2)[2]
        for line in lines
        if line.startswith("RESULT ") and line.count(" ") >= 2
    }
    assert results["delay-ms"] == "500"
    max_width = int(results["max-width"])
    for name in ("attached", "attached-long", "object"):
        # Not before ~0.3 s of resting, shown by ~0.85 s.
        assert results[f"{name}-early"] == "false", name
        assert results[f"{name}-late"] == "true", name
    assert results["attached-lines"] == "1"
    for name in ("attached-long", "object"):
        assert int(results[f"{name}-width"]) <= max_width, name
        assert int(results[f"{name}-width"]) >= max_width * 0.8, name
        assert int(results[f"{name}-lines"]) > 1, name


if __name__ == "__main__":
    if "--smoke" in sys.argv:
        _smoke()
