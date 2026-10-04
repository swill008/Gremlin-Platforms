# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Starts the program off-screen, opens the Live Log Reader's Debug tab on a
long log scrolled to its end, switches to a short one and prints where the
view is, as JSON. test_live_log_view.py runs it in its own process with a
fresh user folder.

    python test/unit/live_log_view_smoke.py
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

from PySide6 import QtGui, QtQml, QtQuick, QtTest  # noqa: E402

import joystick_gremlin  # noqa: E402
from gremlin.util import logs_dir  # noqa: E402


def main() -> None:
    app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
    QtTest.QTest.qWait(800)
    logs = logs_dir()
    # A long log and a short one (the program's own system.log is kept).
    (logs / "event.log").write_text("".join(
        f"2026-10-04 10:{i // 60:02d}:{i % 60:02d} Button {i} pressed\n"
        for i in range(400)
    ), encoding="utf-8")
    (logs / "qt.log").write_text("".join(
        f"2026-10-04 11:00:0{i} qt line {i}\n" for i in range(4)
    ), encoding="utf-8")

    main_win = app.main_window
    QtQml.QQmlExpression(
        QtQml.qmlContext(main_win), main_win,
        'Helpers.createComponent("DialogLiveLog.qml")'
    ).evaluate()
    QtTest.QTest.qWait(800)
    win = next(
        w for w in QtGui.QGuiApplication.topLevelWindows()
        if isinstance(w, QtQuick.QQuickWindow)
        and w.title().startswith("Live Log Reader")
    )
    win.setWidth(1200)
    win.setHeight(800)

    def ev(code: str) -> object:
        expr = QtQml.QQmlExpression(QtQml.qmlContext(win), win, code)
        value = expr.evaluate()
        if expr.hasError():
            return "error: " + expr.error().toString()
        value = value[0] if isinstance(value, tuple) else value
        return value.toVariant() if hasattr(value, "toVariant") else value

    view = "_debugView.children[0]"

    def lit() -> int:
        """Light pixels drawn in the view (its text)."""
        shot = win.grabWindow()
        ratio = shot.devicePixelRatio()
        box = json.loads(str(ev(
            "(function(){ var v = _debugView; var p = v.mapToItem(null, 0, 0);"
            " return JSON.stringify({x: p.x, y: p.y, w: v.width, h: v.height}) })()"
        )))
        part = shot.copy(round(box["x"] * ratio), round(box["y"] * ratio),
                         round(box["w"] * ratio * 0.5), round(box["h"] * ratio * 0.5))
        count = 0
        for y in range(0, part.height(), 2):
            for x in range(0, part.width(), 2):
                if part.pixelColor(x, y).lightness() > 120:
                    count += 1
        return count

    def where() -> dict:
        return {
            "y": ev(f"{view}.contentY"),
            "content": ev(f"{view}.contentHeight"),
            "height": ev(f"{view}.height"),
            "count": ev("_debug.totalCount"),
            "lit": lit(),
        }

    out: dict = {}
    # Lines drawn while the Debug tab is hidden (its view has no height),
    # then the tab shown.
    ev("_tabs.currentIndex = 0")
    ev("_debug.file = 'qt'")
    QtTest.QTest.qWait(600)
    ev("_tabs.currentIndex = 1")
    QtTest.QTest.qWait(1000)
    out["shown-later"] = where()
    ev("_tabs.currentIndex = 1")
    ev("_debug.file = 'event'")
    QtTest.QTest.qWait(1000)
    out["long"] = where()
    # No click: only the choice of another log.
    ev("_debug.file = 'qt'")
    QtTest.QTest.qWait(1000)
    out["short"] = where()
    # The last tab, Log and Show come back when the window opens again;
    # Find starts empty.
    ev("_tabs.currentIndex = 2")
    ev("_debug.file = 'qt'")
    ev("_debug.level = 'Warning'")
    ev("_debug.find = 'line'")
    QtTest.QTest.qWait(200)
    win.close()
    QtTest.QTest.qWait(600)
    QtQml.QQmlExpression(
        QtQml.qmlContext(main_win), main_win,
        'Helpers.createComponent("DialogLiveLog.qml")',
    ).evaluate()
    QtTest.QTest.qWait(800)
    win = next(
        w for w in QtGui.QGuiApplication.topLevelWindows()
        if isinstance(w, QtQuick.QQuickWindow) and w.isVisible()
        and w.title().startswith("Live Log Reader")
    )
    out["reopened"] = {
        "tab": ev("_tabs.currentIndex"),
        "file": ev("_debug.file"),
        "fileBox": ev("_file.currentText"),
        "level": ev("_debug.level"),
        "levelBox": ev("_level.currentText"),
        "find": ev("_debug.find"),
        "live": ev("_debug.live"),
    }
    print("RESULT " + json.dumps(out), flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()
