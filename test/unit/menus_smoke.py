# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Loads the shared menu pieces (Gremlin.Menus) off-screen in
qml/MenusHarness.qml and runs each step in STEPS: a line of QML JavaScript in
the window's scope. Prints "RESULT name value" for each step's value,
"ERROR ..." for a failing step and "WARN ..." for each QML warning, then
"done". test_menus.py runs it in its own process.

    python test/unit/menus_smoke.py <out_dir>
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
# The program's own control style, as joystick_gremlin.py sets it.
os.environ["QT_QUICK_CONTROLS_STYLE"] = "GremlinStyle"
os.environ["QT_FILE_SELECTORS"] = "Universal"
os.environ.setdefault(
    "QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
)
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import shiboken6  # noqa: E402
from PySide6 import QtCore, QtGui, QtQml, QtQuick, QtTest  # noqa: E402


class FakeBackend(QtCore.QObject):
    uiScaleChanged = QtCore.Signal()
    uiScale = QtCore.Property(int, fget=lambda self: 100, notify=uiScaleChanged)


STEPS = [
    # The menu bar's File menu: only what can be used, no stray separators.
    ("file-menu",
     "_fileMenu.popup(0, 30); _fileMenu.describe().join('|')"),
    ("file-menu-paste",
     "_fileMenu.close(); _win.canPaste = true; _win.snapOn = true;"
     " _fileMenu.popup(0, 30); _fileMenu.describe().join('|')"),
    ("menu-item-runs",
     "_fileMenu.itemAt(0).triggered(); _fileMenu.close(); _win.ran"),
    # The right-click menu.
    ("context",
     "_preview.sample.openBelow(_preview.menuButton);"
     " _preview.sample.describe().join('|')"),
    ("context-section",
     "_preview.sample.activate('Look'); _preview.sample.describe().join('|')"),
    ("context-pick",
     "_preview.sample.activate('Size', 'Large');"
     " _preview.sample.describe().join('|')"),
    ("context-toggle",
     "_preview.sample.activate('Snap'); String(_preview.sampleSnap)"),
    ("context-remembers",
     "_preview.sample.close(); _preview.sample.openBelow(_preview.menuButton);"
     " _preview.sample.describe().join('|')"),
    # Dropdown lists: a long one has a search box that narrows it.
    ("long-list",
     "_preview.sample.close(); _long.popup.open(); String(_long.popup.searching)"),
    ("long-search", "_long.popup.filter = 'slider'; _win.longShown()"),
    ("short-list",
     "_long.popup.close(); _short.popup.open(); String(_short.popup.searching)"),
    # The command palette lists what can be used, best match first.
    ("palette",
     "_short.popup.close(); _palette.open(); _palette.describe().join('|')"),
    ("palette-search", "_palette.search('sav'); _palette.describe().join('|')"),
    ("palette-run", "_palette.runPick(0); 'ok'"),
    ("palette-ran", "_win.ran"),
    # A device card's menu: main actions, then sections.
    ("card",
     "_probe.build = _card.menuModel; _probe.openAt(_card, 20, 20);"
     " _probe.describe().join('|')"),
    ("card-device", "_probe.activate('Device'); _probe.describe().join('|')"),
    ("card-closed", "_probe.close(); 'ok'"),
    # A text box's right-click menu: only the edits that can be made.
    ("text-menu",
     "_field.select(0, 5); var m = _field.ContextMenu.menu; m.popup(_field, 0, 0);"
     " m.describe().join('|')"),
    ("text-menu-empty",
     "_field.ContextMenu.menu.close(); _field.text = '';"
     " var e = _field.ContextMenu.menu;"
     " e.popup(_field, 0, 0); String(e.visible)"),
    ("text-closed", "_field.ContextMenu.menu.close(); 'ok'"),
    # Tooltips sit on the menus' surface.
    ("tooltip",
     "_tip.open(); String(Qt.colorEqual(_tip.background.color, Style.menuBg)"
     " && Qt.colorEqual(_tip.background.border.color, Style.menuLine))"),
]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    app = QtGui.QGuiApplication(sys.argv[:1])
    font = QtGui.QFont("Segoe UI")
    font.setPixelSize(15)
    app.setFont(font)
    QtQml.qmlRegisterSingletonType(
        QtCore.QUrl.fromLocalFile(str(ROOT / "qml" / "Style.qml")),
        "Gremlin.Style", 1, 0, "Style",
    )
    engine = QtQml.QQmlApplicationEngine()
    engine.addImportPath(str(ROOT / "theme"))
    backend = FakeBackend()
    engine.rootContext().setContextProperty("backend", backend)
    warnings: list[str] = []
    engine.warnings.connect(lambda ws: warnings.extend(w.toString() for w in ws))
    harness = ROOT / "test" / "unit" / "qml" / "MenusHarness.qml"
    engine.load(QtCore.QUrl.fromLocalFile(str(harness)))
    roots = engine.rootObjects()
    if not roots:
        print("ERROR window did not load", flush=True)
    else:
        win = roots[0]
        QtTest.QTest.qWait(400)
        quick = shiboken6.wrapInstance(
            shiboken6.getCppPointer(win)[0], QtQuick.QQuickWindow
        )
        for name, code in STEPS:
            expr = QtQml.QQmlExpression(QtQml.qmlContext(win), win, code)
            value = expr.evaluate()
            if expr.hasError():
                print(f"ERROR {name}: {expr.error().toString()}", flush=True)
            elif isinstance(value, tuple) and value[0] not in (None, ""):
                print(f"RESULT {name} {value[0]}", flush=True)
            elif value not in (None, ""):
                print(f"RESULT {name} {value}", flush=True)
            QtTest.QTest.qWait(150)
            quick.grabWindow().save(str(out / f"{name}.png"))
    for w in warnings:
        print(f"WARN {w}", flush=True)
    print("done", flush=True)


if __name__ == "__main__":
    main()
