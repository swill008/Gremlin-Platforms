# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Pages keep their controls in view at a large UI scale (UI2).

At 175 % the Output Module View's Appearance panel ran off the right edge
(Close All, Reset and Save Appearance out of reach), Logical Device's
filters ran under its Appearance panel (and Find shrank to nothing), and
HidHide cut off "Automatically Start" and could not show Add Program. Now
the Output View scrolls sideways beside the panel, the Find filters wrap
on a line of their own, HidHide's switches wrap and its body scrolls.

Opens the real pages off-screen in their own process (1600 x 1000).
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

_CODE = r"""
import json, os, sys
ROOT = sys.argv[2]
sys.path.insert(0, ROOT)
import importlib.util
spec = importlib.util.spec_from_file_location(
    'fake_hardware', os.path.join(ROOT, 'test', 'fake_hardware.py'))
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake_hardware.install()
from gremlin.ui import ui_scale_option
SCALE = int(sys.argv[1])
ui_scale_option.active_scale = lambda: SCALE
import gremlin.ui.update_model as um
um.UpdateModel.startup = lambda self, *a, **k: None
import joystick_gremlin
import shiboken6
from PySide6 import QtQml, QtQuick, QtTest
app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
win = app.main_window
win.setProperty('visible', True)
main = shiboken6.wrapInstance(shiboken6.getCppPointer(win)[0], QtQuick.QQuickWindow)
main.setWidth(1600)
main.setHeight(1000)
QtTest.QTest.qWait(800)

def run(window, code):
    expr = QtQml.QQmlExpression(QtQml.qmlContext(window), window, code)
    value = expr.evaluate()
    assert not expr.hasError(), expr.error().toString()
    return value[0] if isinstance(value, tuple) else value

def find(item, text):
    # The visible item showing text (a button's or label's), searched depth first.
    if item.isVisible() and str(item.property('text') or '') == text:
        return item
    for child in item.childItems():
        found = find(child, text)
        if found is not None:
            return found
    return None

def box(item):
    p = item.mapToScene(item.boundingRect().topLeft())
    return [p.x(), p.y(), p.x() + item.width(), p.y() + item.height()]

out = {}
run(win, '_root.openLogicalDevice()')
QtTest.QTest.qWait(800)
root = main.contentItem()
out['filter'] = box(find(root, 'No actions in this mode'))
out['logical_panel'] = box(find(root, 'Logical Device — Appearance'))
out['find'] = box(find(root, 'System name, your name, or group') or find(root, ''))

model = run(win, '_moduleModel')
dest = next(r.slug for r in model._rows if getattr(r, 'direction', '') == 'dest')
run(win, f'_root.openConfigurationForCard(_moduleModel.cardMap("{dest}"))')
QtTest.QTest.qWait(1000)
run(win, '_root.outputViewPanel = true')
QtTest.QTest.qWait(600)
out['save'] = box(find(root, 'Save\nAppearance'))
out['window'] = [main.width(), main.height()]

run(win, 'Helpers.createComponent("DialogHardwareHide.qml")')
QtTest.QTest.qWait(800)
for w in app.topLevelWindows():
    if w is not win and w.isVisible() and isinstance(w, QtQuick.QQuickWindow):
        out['hidhide'] = [run(w, '_bodyScroll.height'), run(w, '_bodyScroll.contentHeight')]
        out['start'] = box(find(w.contentItem(), 'Automatically Start'))
        out['hidhide_width'] = w.width()
print('RESULT ' + json.dumps(out), flush=True)
os._exit(0)  # threads started by the app would keep it alive
"""


def _pages(tmp_path: pathlib.Path, scale: int) -> dict:
    (tmp_path / "Gremlin Platforms").mkdir(exist_ok=True)
    script = tmp_path / "pages.py"
    script.write_text(_CODE, encoding="utf-8")
    screen = tmp_path / "screen.json"
    screen.write_text(json.dumps({"screens": [{
        "name": "s", "x": 0, "y": 0, "width": 1600, "height": 1000,
        "logicalDpiX": 96, "logicalDpiY": 96, "dpr": 1,
    }]}), encoding="utf-8")
    # The screen file by a path without a drive colon (the colon separates
    # the platform's options): relative to the folder it runs in.
    env = dict(os.environ, USERPROFILE=str(tmp_path),
               QT_QPA_PLATFORM="offscreen:configfile=screen.json")
    result = subprocess.run(
        [sys.executable, str(script), str(scale), str(_ROOT)], cwd=tmp_path, env=env,
        capture_output=True, text=True, timeout=120,
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, result.stdout[-1500:] + result.stderr[-1500:]
    return json.loads(lines[0][len("RESULT "):])


@pytest.fixture(scope="module")
def large(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return _pages(tmp_path_factory.mktemp("large"), 175)


def test_logical_device_filters_stay_clear_of_the_panel(large: dict) -> None:
    assert large["filter"][2] <= large["logical_panel"][0], large


def test_the_output_view_panel_is_in_view(large: dict) -> None:
    width, height = large["window"]
    left, top, right, bottom = large["save"]
    assert right <= width and bottom <= height, large


def test_hidhide_wraps_and_scrolls_when_short(large: dict) -> None:
    assert large["start"][2] <= large["hidhide_width"], large  # not cut off
    view, content = large["hidhide"]
    assert content > view  # it scrolls, so Add Program can be reached


def test_hidhide_needs_no_scrolling_at_100(tmp_path: pathlib.Path) -> None:
    view, content = _pages(tmp_path, 100)["hidhide"]
    assert content <= view
