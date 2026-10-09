# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Tool windows keep their size when they move to another screen
(D-01-TOOL-WINDOW-FIT).

Module Setup, Print & Export and the Device Library bound width and height
to Screen: on another screen the bindings re-ran and resized the window,
undoing the restored size (and ToolWindowMemory then saved that). The size
is now set once, by ToolWindowMemory when the window opens.

Opens the real windows off-screen in their own process with two screens
(800 x 600 and 1920 x 1080), moves each to the second screen and checks
its size stays.
"""

from __future__ import annotations

import sys

sys.path.append(".")

import json
import os
import pathlib
import subprocess

import pytest

_ROOT = pathlib.Path(__file__).parents[2]

_WINDOWS = ["DialogConfigureModule", "PrintExportWindow", "WindowDeviceLibrary"]

_CODE = r"""
import json, os, sys
ROOT = sys.argv[1]
sys.path.insert(0, ROOT)
import importlib.util
spec = importlib.util.spec_from_file_location(
    'fake_hardware', os.path.join(ROOT, 'test', 'fake_hardware.py'))
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake_hardware.install()
from gremlin.ui import ui_scale_option
ui_scale_option.active_scale = lambda: 100
import gremlin.ui.update_model as um
um.UpdateModel.startup = lambda self, *a, **k: None
import joystick_gremlin
from PySide6 import QtCore, QtGui, QtQml, QtQuick, QtTest
app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
win = app.main_window
def screen(width):
    # Looked up each time: the platform may replace its screen objects.
    screens = QtGui.QGuiApplication.screens()
    assert len(screens) == 2, [s.name() for s in screens]
    return next(s for s in screens if s.geometry().width() == width)

QtGui.QCursor.setPos(screen(800).geometry().center())

def run(code):
    expr = QtQml.QQmlExpression(QtQml.qmlContext(win), win, code)
    expr.evaluate()
    assert not expr.hasError(), expr.error().toString()

def tool_windows():
    return [w for w in app.topLevelWindows()
            if w is not win and isinstance(w, QtQuick.QQuickWindow)]

out = {}
for name in sys.argv[2].split(','):
    before = set(tool_windows())
    if name == 'DialogConfigureModule':
        run('_root.openConfigureModule("source", null)')
    elif name == 'PrintExportWindow':
        run('Helpers.createComponent("DialogJoystickButtonMap.qml")')
    else:
        run('Helpers.createComponent("WindowDeviceLibrary.qml")')
    QtTest.QTest.qWait(400)
    new = [w for w in tool_windows() if w not in before]
    if name == 'PrintExportWindow':
        # Made (hidden) with the Button Map, which stays open behind it.
        found = [w for w in new if w.title() == 'Print & Export']
        found[0].setScreen(screen(800))
        found[0].show()
        new = found
    else:
        new = [w for w in new if w.isVisible()]
    w = new[0]
    w.setScreen(screen(800))
    QtTest.QTest.qWait(200)
    opened = [w.width(), w.height()]
    big = screen(1920)
    w.setPosition(big.geometry().topLeft() + QtCore.QPoint(50, 50))
    w.setScreen(big)
    QtTest.QTest.qWait(300)
    # The screen as the window's own Screen bindings see it; the smallest
    # size follows it (those bindings stay) and may push the size up.
    expr = QtQml.QQmlExpression(QtQml.qmlContext(w), w, 'Screen.width')
    seen = expr.evaluate()
    seen = seen[0] if isinstance(seen, tuple) else seen
    moved = [w.width(), w.height(), w.minimumWidth(), w.minimumHeight(), seen]
    out[name] = {'opened': opened, 'moved': moved}
    w.close()
    QtTest.QTest.qWait(100)
print('RESULT ' + json.dumps(out), flush=True)
os._exit(0)  # threads started by the app would keep it alive
"""


@pytest.fixture(scope="module")
def result(tmp_path_factory: pytest.TempPathFactory) -> tuple[dict, str]:
    home = tmp_path_factory.mktemp("home")
    (home / "Gremlin Platforms").mkdir()
    script = home / "size_once.py"
    script.write_text(_CODE, encoding="utf-8")
    screen = {
        "logicalDpiX": 96, "logicalDpiY": 96, "dpr": 1,
    }
    (home / "screens.json").write_text(json.dumps({"screens": [
        dict(screen, name="Small", x=0, y=0, width=800, height=600),
        dict(screen, name="Big", x=800, y=0, width=1920, height=1080),
    ]}), encoding="utf-8")
    # The screen file by a path without a drive colon (the colon separates
    # the platform's options): relative to the folder it runs in.
    env = dict(os.environ, USERPROFILE=str(home),
               QT_QPA_PLATFORM="offscreen:configfile=screens.json")
    proc = subprocess.run(
        [sys.executable, str(script), str(_ROOT), ",".join(_WINDOWS)], cwd=home,
        env=env, capture_output=True, text=True, timeout=120,
    )
    lines = [ln for ln in proc.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, proc.stdout[-1500:] + proc.stderr[-1500:]
    return json.loads(lines[0][len("RESULT "):]), proc.stdout + proc.stderr


@pytest.mark.parametrize("name", _WINDOWS)
def test_the_size_stays_on_another_screen(result: tuple[dict, str], name: str) -> None:
    sizes = result[0]
    assert name in sizes, f"{name} did not open"
    opened, moved = sizes[name]["opened"], sizes[name]["moved"]
    width, height, min_width, min_height, screen_width = moved
    assert screen_width == 1920, f"{name} did not move to the second screen"
    expected = [max(opened[0], min_width), max(opened[1], min_height)]
    assert [width, height] == expected, sizes[name]


def test_no_binding_is_overwritten(result: tuple[dict, str]) -> None:
    assert "Overwriting binding" not in result[1]
