# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Opens the Button Map the way the program does (helpers.js), uses its
command palette, closes it, and checks nothing of it is left: the window is
gone and the shared command list holds none of its commands. Prints the
process's memory at each step. test_button_map_lifecycle.py runs it in its
own process.

    python test/unit/button_map_lifecycle_smoke.py

Measured (2026-10-02): about 30 MB while open, all but 1-2 MB of it kept
by Qt after the close; the same after every later open and close, so
nothing piles up. Dropping Qt's compiled QML cache after the close
(trimComponentCache) gave back only 1-2 MB more and makes the next open
compile again, so the program does not do it.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
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

gremlin.util.userprofile_path = unittest.mock.Mock(return_value=tempfile.mkdtemp())

import shiboken6  # noqa: E402
from PySide6 import QtCore, QtGui, QtQml, QtTest  # noqa: E402


class _Counters(ctypes.Structure):
    _fields_ = [
        ("cb", ctypes.wintypes.DWORD),
        ("PageFaultCount", ctypes.wintypes.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
        ("PrivateUsage", ctypes.c_size_t),
    ]


def memory_mb() -> float:
    """The process's private memory, in MB."""
    counters = _Counters()
    counters.cb = ctypes.sizeof(counters)
    current = ctypes.windll.kernel32.GetCurrentProcess
    current.restype = ctypes.wintypes.HANDLE
    info = ctypes.windll.psapi.GetProcessMemoryInfo
    info.argtypes = [
        ctypes.wintypes.HANDLE, ctypes.POINTER(_Counters), ctypes.wintypes.DWORD
    ]
    info.restype = ctypes.wintypes.BOOL
    info(current(), ctypes.byref(counters), counters.cb)
    return counters.PrivateUsage / (1024 * 1024)


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


_ROOT_QML = b"""
import QtQuick
import Gremlin.Menus
import "helpers.js" as Helpers

Item {
    function open() {
        var blank = { startBlank: true, targetName: "", targetGuid: "" }
        return !!Helpers.createComponent("DialogJoystickButtonMap.qml", blank)
    }
    function win() { return Helpers.windowOf("DialogJoystickButtonMap.qml") }
    function leftOver() { return Commands.countOwner("buttonmap") }
}
"""


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    # Kept for the run: the application must outlive the engine.
    app = QtGui.QGuiApplication(sys.argv[:1])  # noqa: F841
    QtQml.qmlRegisterSingletonType(
        QtCore.QUrl.fromLocalFile(str(ROOT / "qml" / "Style.qml")),
        "Gremlin.Style", 1, 0, "Style",
    )
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
    # Based in qml/, so helpers.js and the window load as in the program.
    base = QtCore.QUrl.fromLocalFile(str(ROOT / "qml" / "Root.qml"))
    engine.loadData(_ROOT_QML, base)
    root = engine.rootObjects()[0]

    def run(obj: QtCore.QObject, code: str) -> object:
        expr = QtQml.QQmlExpression(QtQml.qmlContext(obj), obj, code)
        value = expr.evaluate()
        if expr.hasError():
            print(f"ERROR {code[:40]}: {expr.error().toString()}", flush=True)
        return value[0] if isinstance(value, tuple) else value

    def settle(ms: int = 800) -> None:
        QtTest.QTest.qWait(ms)
        engine.collectGarbage()
        QtTest.QTest.qWait(200)

    settle()
    print(f"MEM before {memory_mb():.1f}", flush=True)
    for cycle in range(3):
        print(f"RESULT opened{cycle} {run(root, 'open()')}", flush=True)
        settle(1500)
        win = run(root, "win()")
        print(f"MEM open{cycle} {memory_mb():.1f}", flush=True)
        if cycle == 0:
            # The palette lists the window's menu commands while it is open,
            # and the shared list lets go of them when it closes.
            print("RESULT palette " + str(run(
                win, "_palette.open(); _palette.describe().length > 10")), flush=True)
            print(f"RESULT during {run(root, 'leftOver()')}", flush=True)
            print("RESULT after-palette " + str(run(
                win, "_palette.close(); Commands.countOwner('buttonmap')")), flush=True)
            # Closed with the palette open: still nothing left behind.
            run(win, "_palette.open()")
        run(win, "close()")
        settle()
        print(f"RESULT gone{cycle} {not shiboken6.isValid(win)}", flush=True)
        print(f"RESULT left{cycle} {run(root, 'leftOver()')}", flush=True)
        print(f"MEM closed{cycle} {memory_mb():.1f}", flush=True)
    for w in warnings:
        print(f"WARN {w}", flush=True)
    print("done", flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()
