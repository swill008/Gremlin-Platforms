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
import subprocess
import sys

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
window.show()
tray_memory.enter_tray(window, engine)
print("visible-left-alone", window.property("entered") == 0, flush=True)
window.hide()
tray_memory.enter_tray(window, engine)
print("hidden-trayed", window.property("trayed"), flush=True)
end = time.monotonic() + 30  # generous: a busy PC is slow
while not released and time.monotonic() < end:
    QtTest.QTest.qWait(20)
print("cleaned-up", released == [False], flush=True)
tray_memory.leave_tray(window)
print("shown-again", window.property("trayed") is False, flush=True)
os._exit(0)
"""


def test_hidden_window_unloads_and_reloads() -> None:
    result = subprocess.run(
        [sys.executable, "-c", _SCRIPT, str(_ROOT)],
        capture_output=True,
        text=True,
        timeout=60,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
    )
    out = result.stdout.splitlines()
    lines = dict(line.split(" ", 1) for line in out if " " in line)
    assert lines == {
        "visible-left-alone": "True",
        "hidden-trayed": "True",
        "cleaned-up": "True",
        "shown-again": "True",
    }, result.stderr[-2000:]


def test_working_set_trim_is_safe_to_call() -> None:
    tray_memory.trim_working_set()


def test_pages_load_only_while_needed() -> None:
    main = (_ROOT / "qml" / "Main.qml").read_text(encoding="utf-8")
    # Scripts and Profile Settings load while shown; Home unloads in the tray.
    for page, room in (("ScriptManager", "scripts"), ("ProfileSettings", "settings")):
        assert re.search(
            rf'active: !!uiState && uiState.currentRoom === "{room}"[\s\S]{{0,200}}'
            rf"sourceComponent: {page} \{{",
            main,
        ), page
    home = r"active: !_root.trayed[\s\S]{0,200}sourceComponent: StatusPage"
    assert re.search(home, main)
    # Configuration's panels, one per tab, and none in the tray unless unsaved.
    for panel in ("BindingCatalog", "XboxDevice", "KeyboardInputList",
                  "InputConfiguration"):
        assert f"sourceComponent: {panel} {{" in main, panel
    # The OSC page (09 S129) has a loader of its own, also gone in the tray.
    osc = main[main.index("id: _oscPageLoader"):]
    osc = osc[: osc.index('source: "OscPage.qml"')]
    assert "&& _root._configLive" in osc
    assert main.count("&& _root._configLive") == 4
    tray = (_ROOT / "gremlin" / "ui" / "system_tray.py").read_text(encoding="utf-8")
    assert "tray_memory.enter_tray" in tray and "tray_memory.leave_tray" in tray
