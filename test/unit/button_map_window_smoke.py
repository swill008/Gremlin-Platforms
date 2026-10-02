# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Loads the Button Map window off-screen, with stand-ins for the program's
backend, and runs each step given in STEPS: a line of QML JavaScript in the
window's own scope. Prints "ERROR ..." for a failing step and "WARN ..." for
each QML warning, then "done". test_button_map_window.py runs it in its own
process.

    python test/unit/button_map_window_smoke.py <out_dir>
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest.mock
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.setdefault(
    "QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
)
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import gremlin.util  # noqa: E402

# Settings and module files in a folder of their own, never the user's.
gremlin.util.userprofile_path = unittest.mock.Mock(return_value=tempfile.mkdtemp())

import shiboken6  # noqa: E402
from PySide6 import QtCore, QtGui, QtQml, QtQuick, QtTest  # noqa: E402

# Each step: (name, JavaScript run in the window's scope).
STEPS = [
    ("template-name", "_templateNameDlg.open()"),
    ("templates", "_templateNameDlg.close(); _templatesDlg.open()"),
    ("export-modes", "_templatesDlg.close(); _buttonMap.openExportModes()"),
    ("copy",
     "_modesDlg.close(); _buttonMap.openCopyLayout({name: 'Stick R', slug: 'x'})"),
    ("apply-template",
     "_copyDlg.close(); _buttonMap.openCopyLayout({name: 'Mine', template: true})"),
    ("style-name", "_copyDlg.close(); _buttonMap.askStyleName('shape', '{}')"),
    ("library",
     "_styleNameDlg.close();"
     " Qt.createComponent('OptionButtonMapLibrary.qml')"
     ".createObject(_buttonMap.contentItem)"),
    ("photo-adjust", "_photoAdj.open()"),
    ("zoom",
     "_photoAdj.close(); _buttonMap.zoomToPage(); _buttonMap.zoomToSelection()"),
    ("closed", "_photoAdj.close(); _styleNameDlg.close()"),
]


class FakeBackend(QtCore.QObject):
    uiScaleChanged = QtCore.Signal()
    propertyChanged = QtCore.Signal()
    activityChanged = QtCore.Signal()

    uiScale = QtCore.Property(int, fget=lambda self: 100, notify=uiScaleChanged)
    gremlinActive = QtCore.Property(
        bool, fget=lambda self: False, notify=activityChanged
    )
    currentMode = QtCore.Property(
        str, fget=lambda self: "Default", notify=propertyChanged
    )

    @QtCore.Slot(str)
    def noteSave(self, text: str) -> None:
        pass


class FakeUiState(QtCore.QObject):
    modeChanged = QtCore.Signal()
    currentMode = QtCore.Property(str, fget=lambda self: "Default", notify=modeChanged)


def main() -> None:
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
    # The QML types the window uses, registered as the program does.
    import gremlin.ui.backend  # noqa: F401
    import gremlin.ui.button_map_options  # noqa: F401
    import gremlin.ui.device_names  # noqa: F401
    import joystick_gremlin

    joystick_gremlin.register_config_options()

    backend = FakeBackend()
    ui_state = FakeUiState()
    engine = QtQml.QQmlApplicationEngine()
    engine.addImportPath(str(ROOT / "theme"))
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("uiState", ui_state)
    warnings: list[str] = []
    engine.warnings.connect(lambda ws: warnings.extend(w.toString() for w in ws))
    engine.load(
        QtCore.QUrl.fromLocalFile(str(ROOT / "qml" / "DialogJoystickButtonMap.qml"))
    )
    roots = engine.rootObjects()
    if not roots:
        print("ERROR window did not load", flush=True)
    else:
        win = roots[0]
        win.setProperty("width", 1400)
        win.setProperty("height", 900)
        win.setProperty("visible", True)
        QtTest.QTest.qWait(600)
        quick = shiboken6.wrapInstance(
            shiboken6.getCppPointer(win)[0], QtQuick.QQuickWindow
        )
        for name, code in STEPS:
            expr = QtQml.QQmlExpression(QtQml.qmlContext(win), win, code)
            expr.evaluate()
            if expr.hasError():
                print(f"ERROR {name}: {expr.error().toString()}", flush=True)
            QtTest.QTest.qWait(250)
            quick.grabWindow().save(str(out / f"{name}.png"))
    for warning in warnings:
        print("WARN " + warning.encode("ascii", "replace").decode(), flush=True)
    print("done", flush=True)
    # os._exit skips Qt's teardown, which can hang off-screen.
    os._exit(0)


if __name__ == "__main__":
    main()
