# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The main window fits the screen at a large UI scale.

At 175 % the window's minimum width (1300 at 100 %) was wider than most
screens, so its right side was off the screen, and the minimum height
didn't fit either. Now the minimum size is capped to the screen; when the
toolbar doesn't fit with its captions the buttons show their icons only
(the tooltips still name them), and if even that doesn't fit the toolbar
scrolls sideways. Mode, its list and Manage Modes are on the bar under the
toolbar (01 S58a); the mode list narrows there so Manage Modes stays in
the window.

Runs the real main window off-screen in its own process (fake hardware, no
update check, an empty home).
"""

from __future__ import annotations

import sys

sys.path.append(".")

import json
import os
import pathlib
import subprocess

_ROOT = pathlib.Path(__file__).parents[2]

_CODE = """
import json, os, sys
sys.path.insert(0, '.')
import importlib.util
spec = importlib.util.spec_from_file_location('fake_hardware', 'test/fake_hardware.py')
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake_hardware.install()
from gremlin.ui import ui_scale_option
ui_scale_option.active_scale = lambda: int(sys.argv[1])
import gremlin.ui.update_model as um
um.UpdateModel.startup = lambda self, *a, **k: None
import joystick_gremlin
from PySide6 import QtQml, QtTest
app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
win = app.main_window
win.setProperty('visible', True)
QtTest.QTest.qWait(500)

def run(code):
    expr = QtQml.QQmlExpression(QtQml.qmlContext(win), win, code)
    value = expr.evaluate()
    assert not expr.hasError(), expr.error().toString()
    return value[0] if isinstance(value, tuple) else value

out = {'screen': app.primaryScreen().availableGeometry().width(),
       'screenH': app.primaryScreen().availableGeometry().height(),
       'minW': run('_root.minimumWidth'), 'minH': run('_root.minimumHeight'),
       'widths': {}}
out['full'] = run('Math.ceil(_root._toolbarWidth(true))')
for key in sys.argv[2].split(','):
    # "full-1": one pixel short of the toolbar with its captions.
    width = out['full'] - 1 if key == 'full-1' else int(key)
    win.setProperty('width', width)
    QtTest.QTest.qWait(300)
    out['widths'][key] = {
        'width': width,
        'compact': run('_root.toolbarCompact'),
        'caption': run('_homeButton.contentItem.children[1].visible'),
        'scroll': run('_toolbarScroll.visible'),
        'manageRight': run(
            '_manageModesButton.mapToItem(null, _manageModesButton.width, 0).x'),
        'optionsRight': run(
            '_optionsButton.x + _optionsButton.width + _toolbarRow.x'),
        'content': run('_toolbarFlick.contentWidth'),
        'view': run('_toolbarFlick.width'),
        'modeList': run('_modeSelector.width'),
    }
print('RESULT ' + json.dumps(out), flush=True)
os._exit(0)  # threads started by the app would keep it alive
"""


def _window(tmp_path: pathlib.Path, scale: int, widths: str) -> dict:
    script = tmp_path / "fits.py"
    script.write_text(_CODE, encoding="utf-8")
    (tmp_path / "Gremlin Platforms").mkdir(exist_ok=True)
    # The off-screen platform's screen is 800 x 600.
    env = dict(os.environ, USERPROFILE=str(tmp_path), QT_QPA_PLATFORM="offscreen")
    result = subprocess.run(
        [sys.executable, str(script), str(scale), widths], cwd=_ROOT, env=env,
        capture_output=True, text=True, timeout=120,
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, result.stdout[-1500:] + result.stderr[-1500:]
    return json.loads(lines[0][len("RESULT "):])


def test_at_normal_scale_the_toolbar_is_as_before(tmp_path: pathlib.Path) -> None:
    out = _window(tmp_path, 100, "1600")
    wide = out["widths"]["1600"]
    assert not wide["compact"] and wide["caption"] and not wide["scroll"]
    assert wide["modeList"] == 200
    assert wide["manageRight"] <= 1600
    assert wide["optionsRight"] <= 1600


def test_the_minimum_size_fits_the_screen(tmp_path: pathlib.Path) -> None:
    out = _window(tmp_path, 175, "1600")
    assert out["minW"] <= out["screen"] and out["minH"] <= out["screenH"]


def test_captions_hide_before_anything_goes_off_the_window(
    tmp_path: pathlib.Path,
) -> None:
    out = _window(tmp_path, 175, "full-1,2200")
    # Too narrow for the captions: icons only, and everything still in view.
    narrow = out["widths"]["full-1"]
    assert narrow["compact"] and not narrow["caption"] and not narrow["scroll"]
    assert narrow["optionsRight"] <= narrow["width"]
    assert narrow["manageRight"] <= narrow["width"]
    # Room for the captions: they come back.
    wide = out["widths"]["2200"]
    assert not wide["compact"] and wide["caption"]
    assert wide["manageRight"] <= 2200 and wide["optionsRight"] <= 2200


def test_when_even_the_icons_dont_fit_the_toolbar_scrolls(
    tmp_path: pathlib.Path,
) -> None:
    out = _window(tmp_path, 200, "800")
    small = out["widths"]["800"]
    assert small["compact"] and small["scroll"]
    assert small["view"] == 800
    assert small["optionsRight"] <= small["content"]  # reachable by scrolling
    assert small["manageRight"] <= 800  # the bar under it doesn't scroll
