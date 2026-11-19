# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The tray follows what Windows shows (01 S85, S87, S174, S175, D-01-TRAY-TRUTH).

Each test runs a real window and the real SystemTrayIcon in its own process
with the Windows platform plugin (the window is far off the screen, fully
transparent and never activated). Only the Shell_NotifyIcon family is
stubbed so no icon is made. The native state is read with IsWindowVisible.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[2]

_SCRIPT = r"""
import ctypes, json, os, sys, time
sys.path.insert(0, sys.argv[1])
scenario = sys.argv[2]
from types import SimpleNamespace
from PySide6 import QtCore, QtGui, QtQml, QtTest

app = QtGui.QGuiApplication([])
from gremlin.ui import system_tray, tray_memory
try:
    from gremlin.ui import window_trace
except ImportError:
    window_trace = None
from gremlin import trace

user32 = ctypes.windll.user32
user32.IsWindowVisible.argtypes = [ctypes.c_void_p]
user32.ShowWindow.argtypes = [ctypes.c_void_p, ctypes.c_int]

gui = system_tray.win32gui
for name, fake in {
    "Shell_NotifyIcon": lambda *a: None, "LoadImage": lambda *a: 101,
    "RegisterWindowMessage": lambda _n: 49999, "RegisterClass": lambda _wc: 7,
    "CreateWindowEx": lambda *a: 55, "DestroyWindow": lambda *a: None,
    "UnregisterClass": lambda *a: None, "DestroyIcon": lambda *a: None,
}.items():
    setattr(gui, name, fake)
system_tray.win32api.GetModuleHandle = lambda _n: 3
system_tray.win32api.GetSystemMetrics = lambda _n: 16

class Backend(QtCore.QObject):
    activityChanged = QtCore.Signal()
    quitRequested = QtCore.Signal()
    gremlinActive = False
    engine = None
backend = Backend()
system_tray.Backend = lambda: backend
values = {("global", "general", "minimize-to-tray"): True,
          ("global", "internal", "tray-notice-shown"): True}
settings = SimpleNamespace(
    exists=lambda *k: tuple(k) in values, value=lambda *k: values[tuple(k)],
    set=lambda *kv: values.__setitem__(tuple(kv[:-1]), kv[-1]))
system_tray.Configuration = lambda: settings

warns = []
if window_trace is not None:
    window_trace.warn = lambda text: warns.append(text)

engine = QtQml.QQmlApplicationEngine()
engine.loadData(b'''
import QtQuick
import QtQuick.Window
Window {
    x: -30000; y: -30000; width: 300; height: 200; opacity: 0
    flags: Qt.Window | Qt.WindowDoesNotAcceptFocus
    property bool trayed: false
    function enterTray() { trayed = true }
    function leaveTray() { trayed = false }
}
''')
window = engine.rootObjects()[0]
window.create()
hwnd = int(window.winId())
icon = system_tray.SystemTrayIcon(window)
icon._icon_present = True

def wait(ms):
    QtTest.QTest.qWait(ms)

def until(fn, ms=3000):
    end = time.monotonic() + ms / 1000
    while time.monotonic() < end:
        if fn():
            return True
        wait(20)
    return fn()

def native():
    return bool(user32.IsWindowVisible(hwnd))

def trayed():
    return bool(window.property("trayed"))

def tray_it():
    window.show()
    wait(200)
    window.hide()
    until(trayed)
    wait(300)

out = {}
if scenario == "start_minimized":
    window.showMinimized()
    until(lambda: not native(), 3000)
    wait(500)
    out = {"native": native(), "qt": window.isVisible(), "trayed": trayed(),
           "py_trayed": icon._trayed}
elif scenario == "behind_back":
    tray_it()
    out["before"] = {"native": native(), "trayed": trayed()}
    user32.ShowWindow(hwnd, 4)  # SW_SHOWNOACTIVATE
    until(lambda: not trayed() and window.isVisible(), 2000)
    out["after"] = {"trayed": trayed(), "qt": window.isVisible(),
                    "py_trayed": icon._trayed}
elif scenario == "steps":
    window.show()
    wait(200)
    window.showMinimized()
    until(trayed)
    wait(300)
    icon._system_tray_event_cb(55, system_tray._WM_TRAY, 0, 0x0202)  # WM_LBUTTONUP
    wait(300)
    out["lines"] = trace.recent_lines() if hasattr(trace, "recent_lines") else None
    window.hide()
    until(trayed)
    wait(300)
    user32.ShowWindow(hwnd, 4)
    until(lambda: bool(warns), 2000)
    out["warns"] = list(warns)
    out["has_window_trace"] = window_trace is not None
elif scenario == "flags_agree":
    window.show()
    wait(300)
    # a hidden notice that arrives while the window is in fact visible
    icon._window_mode_changed_cb(QtGui.QWindow.Visibility.Hidden)
    wait(500)
    out["py"] = icon._trayed
    out["qml"] = trayed()
    out["qt_visible"] = window.isVisible()
print("RESULT " + json.dumps(out), flush=True)
os._exit(0)
"""


def _run(scenario: str, tmp_path: pathlib.Path) -> dict:
    result = proc_tree.run(
        [sys.executable, "-c", _SCRIPT, str(_ROOT), scenario],
        text=True,
        timeout=90,
        env={
            **os.environ,
            "QT_QPA_PLATFORM": "windows",
            "QT_LOGGING_RULES": "*=false",
            "USERPROFILE": str(tmp_path),  # never the real Gremlin folder
        },
    )
    lines = [x for x in result.stdout.splitlines() if x.startswith("RESULT ")]
    assert lines, (result.stdout[-1500:], result.stderr[-2500:])
    return json.loads(lines[-1][7:])


@pytest.mark.skipif(sys.platform != "win32", reason="Windows windows")
def test_start_minimized_to_tray_leaves_no_native_window(
    tmp_path: pathlib.Path,
) -> None:
    out = _run("start_minimized", tmp_path)
    assert out == {"native": False, "qt": False, "trayed": True, "py_trayed": True}


@pytest.mark.skipif(sys.platform != "win32", reason="Windows windows")
def test_window_shown_behind_qts_back_reloads_pages(tmp_path: pathlib.Path) -> None:
    out = _run("behind_back", tmp_path)
    assert out["before"] == {"native": False, "trayed": True}
    assert out["after"] == {"trayed": False, "qt": True, "py_trayed": False}


@pytest.mark.skipif(sys.platform != "win32", reason="Windows windows")
def test_tray_steps_are_recorded(tmp_path: pathlib.Path) -> None:
    out = _run("steps", tmp_path)
    assert out["has_window_trace"], "gremlin.ui.window_trace is missing"
    text = "\n".join(out["lines"] or [])
    assert "tray: entered (minimize)" in text
    assert "tray: left (tray click)" in text
    # S175: the out-of-step case raises the Warning
    assert len(out["warns"]) >= 1 and "shown by Windows" in out["warns"][0]


@pytest.mark.skipif(sys.platform != "win32", reason="Windows windows")
def test_python_and_qml_tray_flags_agree(tmp_path: pathlib.Path) -> None:
    out = _run("flags_agree", tmp_path)
    assert out["qt_visible"] and not out["py"]  # a visible window is not trayed
    assert out["py"] == out["qml"]
