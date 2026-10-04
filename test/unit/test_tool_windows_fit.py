# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Tool windows fit the screen at a large UI scale.

At 175 % Module Setup opened 1715 x 1120 (Save below a 1080 screen), and
other windows' smallest sizes were wider or taller than the screen. Every
tool window's size and smallest size are now limited to the screen
(Style.fitWidth / fitHeight); Device Pack set its own size after loading,
past the limit, and now uses them too.

Opens the real windows off-screen in their own process (an 800 x 600
screen, 200 %).
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

_WINDOWS = [
    "DialogConfigureModule", "DialogDevicePack", "DialogCalibration",
    "DialogManageModes", "DialogAutoMapper", "DialogDeviceInformation",
    "DialogOptions", "DialogJoystickButtonMap", "DialogInputViewer",
]

_CODE = """
import json, os, sys
sys.path.insert(0, '.')
import importlib.util
spec = importlib.util.spec_from_file_location('fake_hardware', 'test/fake_hardware.py')
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake_hardware.install()
from gremlin.ui import ui_scale_option
ui_scale_option.active_scale = lambda: 200
import gremlin.ui.update_model as um
um.UpdateModel.startup = lambda self, *a, **k: None
import joystick_gremlin
from PySide6 import QtQml, QtQuick, QtTest
app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
win = app.main_window

def run(code):
    expr = QtQml.QQmlExpression(QtQml.qmlContext(win), win, code)
    expr.evaluate()
    assert not expr.hasError(), expr.error().toString()

out = {}
for name in sys.argv[1].split(','):
    if name == 'DialogConfigureModule':
        run('_root.openConfigureModule("source", null)')
    else:
        run(f'Helpers.createComponent("{name}.qml")')
    QtTest.QTest.qWait(400)
    for w in app.topLevelWindows():
        if w is win or not w.isVisible() or not isinstance(w, QtQuick.QQuickWindow):
            continue
        g = w.screen().availableGeometry()
        out[name] = [w.width(), w.height(), w.minimumWidth(), w.minimumHeight(),
                     g.width(), g.height()]
        w.close()
    QtTest.QTest.qWait(100)
print('RESULT ' + json.dumps(out), flush=True)
os._exit(0)  # threads started by the app would keep it alive
"""


@pytest.fixture(scope="module")
def sizes(tmp_path_factory: pytest.TempPathFactory) -> dict[str, list[int]]:
    home = tmp_path_factory.mktemp("home")
    (home / "Gremlin Platforms").mkdir()
    script = home / "fits.py"
    script.write_text(_CODE, encoding="utf-8")
    env = dict(os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen")
    result = subprocess.run(
        [sys.executable, str(script), ",".join(_WINDOWS)], cwd=_ROOT, env=env,
        capture_output=True, text=True, timeout=120,
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, result.stdout[-1500:] + result.stderr[-1500:]
    return json.loads(lines[0][len("RESULT "):])


@pytest.mark.parametrize("name", _WINDOWS)
def test_the_window_and_its_smallest_size_fit_the_screen(
    sizes: dict[str, list[int]], name: str
) -> None:
    assert name in sizes, f"{name} did not open"
    width, height, min_width, min_height, screen_w, screen_h = sizes[name]
    assert width <= screen_w and height <= screen_h, sizes[name]
    assert min_width <= screen_w and min_height <= screen_h, sizes[name]
