# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Hidden to the tray, the main window unloads its pages and gives memory
back; shown again, it loads them. Pages other than Home load only while
shown.

The clean-up runs on a timer: the test waits until it ran, not a fixed time
(GL-001, AU-119).
"""

from __future__ import annotations

import os
import pathlib
import re
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)

from gremlin.ui import tray_memory

_ROOT = pathlib.Path(__file__).resolve().parents[2]

# Runs off-screen in its own process: the tests' qapp fixture would start
# the whole program (test/conftest.py qapp_cls) and show its window.
_SCRIPT = r"""
import os, sys, time
sys.path.insert(0, sys.argv[1])
from PySide6 import QtGui, QtQml, QtTest
from gremlin.ui import tray_memory

released = []
_release = tray_memory.release
def _counted(window, engine):
    released.append(window.isVisible())
    _release(window, engine)
tray_memory.release = _counted

app = QtGui.QGuiApplication([])
engine = QtQml.QQmlApplicationEngine()
engine.loadData(b'''
import QtQuick
import QtQuick.Window
Window {
    property bool trayed: false
    property int entered: 0
    function enterTray() { entered++; trayed = true }
    function leaveTray() { trayed = false }
}
''')
window = engine.rootObjects()[0]
window.hide()
hidden_result = tray_memory.enter_tray(window, engine)
print("hidden-trayed", window.property("trayed") and hidden_result is True, flush=True)
end = time.monotonic() + 30  # generous: a busy PC is slow
while not released and time.monotonic() < end:
    QtTest.QTest.qWait(20)
print("cleaned-up", released == [False], flush=True)
left_result = tray_memory.leave_tray(window)
shown = window.property("trayed") is False and left_result is True
print("shown-again", shown, flush=True)
os._exit(0)
"""


def test_hidden_window_unloads_and_reloads() -> None:
    result = proc_tree.run(
        [sys.executable, "-c", _SCRIPT, str(_ROOT)],
        text=True,
        timeout=60,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
    )
    out = result.stdout.splitlines()
    lines = dict(line.split(" ", 1) for line in out if " " in line)
    assert lines == {
        "hidden-trayed": "True",
        "cleaned-up": "True",
        "shown-again": "True",
    }, result.stderr[-2000:]


def test_working_set_trim_is_safe_to_call() -> None:
    tray_memory.trim_working_set()


def test_pages_load_only_while_needed() -> None:
    main = (_ROOT / "qml" / "Main.qml").read_text(encoding="utf-8")
    # Scripts and Profile Settings are a window of their own (04 S96), not
    # main-window pages; Home unloads in the tray.
    assert "sourceComponent: ScriptManager" not in main
    assert "sourceComponent: ProfileSettings" not in main
    home = r"active: !_root.trayed[\s\S]{0,200}sourceComponent: StatusPage"
    assert re.search(home, main)
    # The configuration room's pages, one loader per tab, and none in the tray unless
    # unsaved: the Device Bindings and Keyboard pages (05 S121, S128), the OSC
    # page (09 S129), Logical, the output view and Xbox.
    for loader, page in (
        ("_deviceBindingsPageLoader", 'source: "DeviceBindingsPage.qml"'),
        ("_keyboardPageLoader", 'source: "KeyboardPage.qml"'),
        ("_oscPageLoader", 'source: "OscPage.qml"'),
        ("_logicalLoader", 'source: "LogicalPage.qml"'),
        ("_outputLoader", "sourceComponent: OutputModuleView {"),
    ):
        part = main[main.index(f"id: {loader}"):]
        part = part[: part.index(page)]
        assert "&& _root._configLive" in part, loader
    assert "sourceComponent: XboxDevice {" in main
    assert main.count("&& _root._configLive") == 6
    tray = (_ROOT / "gremlin" / "ui" / "system_tray.py").read_text(encoding="utf-8")
    assert "tray_memory.enter_tray" in tray and "tray_memory.leave_tray" in tray
    # One truth for the tray flag (01 S174): every change goes through it.
    assert "def _sync_tray" in tray
