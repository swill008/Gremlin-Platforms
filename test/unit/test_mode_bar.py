# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The bar under the toolbar (01 S58, S58a; 04 S51; D-01-MODE-BAR).

The toolbar holds only Home, Run, vJoy Viewer, Xbox Viewer, Button Map,
Logical Device and Options. Mode, its list and Manage Modes sit on the left
of a bar under it on every page; after a divider the bar shows the open
page's own controls (Home: Device Library…, Compact view, Layout).

Runs the real main window off-screen in its own process (fake hardware, no
update check, a temp USERPROFILE), with real mouse and key events.
"""

from __future__ import annotations

import sys

sys.path.append(".")

import json
import os
import pathlib
import subprocess

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[2]

_SCRIPT = r"""
import json, os, sys, time
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
from PySide6 import QtCore, QtGui, QtQml, QtTest

def pump(check, limit=5.0):
    end = time.monotonic() + limit
    while time.monotonic() < end:
        QtCore.QCoreApplication.processEvents(
            QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 50)
        if check():
            return True
    return bool(check())

app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
win = app.main_window
win.setProperty('visible', True)
pump(lambda: win.isExposed(), 5.0)
pump(lambda: False, 0.5)

def run(code):
    expr = QtQml.QQmlExpression(QtQml.qmlContext(win), win, code)
    value = expr.evaluate()
    assert not expr.hasError(), code + ': ' + expr.error().toString()
    value = value[0] if isinstance(value, tuple) else value
    if isinstance(value, QtQml.QJSValue):
        value = value.toVariant()
    return value

# Finds an item under the window by objectName (null when none).
FIND = ('(function(name) { var top = _root.contentItem; while (top.parent) '
        'top = top.parent; var stack = [top]; while (stack.length) '
        '{ var it = stack.pop(); if (it && it.objectName === name) return it; '
        'var k = (it && it.children) || []; for (var i = 0; i < k.length; i++) '
        'stack.push(k[i]) } return null })')
INSIDE = ('(function(item, outer) { for (var p = item; p; p = p.parent) '
          'if (p === outer) return true; return false })')

def find(name):
    return FIND + '(' + json.dumps(name) + ')'

def bar_state():
    return run('(function() { var bar = ' + find('modeBar') + '; '
               'var loader = ' + find('pageBarLoader') + '; '
               'var inside = ' + INSIDE + '; '
               'if (!bar) return null; '
               'var xs = [_modeLabel, _modeSelector, _manageModesButton]'
               '.map(function(b) { return b.mapToItem(null, 0, 0).x }); '
               'var lx = loader ? loader.mapToItem(null, 0, 0).x : -1; '
               'return { visible: bar.visible && bar.width > 0 && bar.height > 0, '
               'belowToolbar: bar.mapToItem(null, 0, 0).y >= '
               '_toolbarFlick.mapToItem(null, 0, 0).y + _toolbarFlick.height - 1, '
               'holdsMode: inside(_modeLabel, bar) && inside(_modeSelector, bar) '
               '&& inside(_manageModesButton, bar), '
               'modeShown: _modeLabel.visible && _modeSelector.visible '
               '&& _manageModesButton.visible, '
               'modeLeftThenPage: xs[0] < xs[1] && xs[1] < xs[2] && xs[2] < lx, '
               'loaderInBar: !!loader && inside(loader, bar), '
               'loaderItem: !!(loader && loader.item), '
               'libraryButton: ' + find('homeDeviceLibraryButton') + ' !== null } })()')

def click(code):
    pos = run('(function(b) { var p = b.mapToItem(null, b.width / 2, b.height / 2); '
              'return [p.x, p.y] })(' + code + ')')
    QtTest.QTest.mouseClick(win, QtCore.Qt.MouseButton.LeftButton,
                            QtCore.Qt.KeyboardModifier.NoModifier,
                            QtCore.QPoint(int(pos[0]), int(pos[1])))
    pump(lambda: False, 0.3)

out = {'scale': int(sys.argv[1])}
# The toolbar no longer holds Mode, its list or Manage Modes.
out['toolbarHasMode'] = run('(function() { var inside = ' + INSIDE + '; '
                            'return inside(_modeLabel, _toolbarFlick) '
                            '|| inside(_modeSelector, _toolbarFlick) '
                            '|| inside(_manageModesButton, _toolbarFlick) })()')
out['modeLabel'] = run('_modeLabel.text')
out['manageModes'] = run('_manageModesButton.text')
out['home'] = bar_state()

# The fit: at the minimum width everything on the bar is in the window.
run('_root.width = _root.minimumWidth')
pump(lambda: False, 0.5)
out['minW'] = run('_root.minimumWidth')
out['screen'] = app.primaryScreen().availableGeometry().width()
out['fit'] = run('(function() { var right = function(b) { '
                 'return b.mapToItem(null, b.width, 0).x }; '
                 'var lib = ' + find('homeDeviceLibraryButton') + '; '
                 'var loader = ' + find('pageBarLoader') + '; '
                 'return { width: _root.width, '
                 'manage: right(_manageModesButton), '
                 'modeList: _modeSelector.width, '
                 'library: lib ? right(lib) : -1, '
                 # Where the page part scrolls (screen too small for it all):
                 # its view must be in the window and hold the controls.
                 'flick: (function() { for (var p = loader; p; p = p.parent) '
                 'if (p.contentWidth !== undefined && p.contentItem) return { '
                 'right: right(p), content: p.contentWidth, '
                 'lib: lib ? lib.mapToItem(p.contentItem, lib.width, 0).x : -1 }; '
                 'return null })(), '
                 'loader: loader ? right(loader) : -1, '
                 'toolbarScroll: _toolbarScroll.visible } })()')

if out['scale'] == 100 and out['home'] and out['home']['libraryButton']:
    run('_root.width = 1600')
    pump(lambda: False, 0.5)
    lib = find('homeDeviceLibraryButton')
    loader = find('pageBarLoader')
    # Compact view: a real click toggles the Home model.
    out['compactBefore'] = run('_moduleModel.compactView')
    click('(function(l) { var s = [l.item]; while (s.length) { var it = s.pop(); '
          'if (it.text === "Compact view") return it; var k = it.children || []; '
          'for (var i = 0; i < k.length; i++) s.push(k[i]) } return null })('
          + loader + ')')
    out['compactAfter'] = run('_moduleModel.compactView')
    # Layout: arrow down on the list picks the next layout.
    combo = ('(function(l) { var s = [l.item]; while (s.length) { var it = s.pop(); '
             'if (it.find !== undefined && it.popup !== undefined) return it; '
             'var k = it.children || []; for (var i = 0; i < k.length; i++) '
             's.push(k[i]) } return null })(' + loader + ')')
    out['splitBefore'] = run('_moduleModel.splitMode')
    run(combo + '.forceActiveFocus()')
    for kind in (QtCore.QEvent.Type.KeyPress, QtCore.QEvent.Type.KeyRelease):
        QtCore.QCoreApplication.sendEvent(win, QtGui.QKeyEvent(
            kind, QtCore.Qt.Key.Key_Down, QtCore.Qt.KeyboardModifier.NoModifier))
    pump(lambda: run('_moduleModel.splitMode') != out['splitBefore'], 2.0)
    out['splitAfter'] = run('_moduleModel.splitMode')
    # Device Library…: a real click opens the window.
    click(lib)
    pump(lambda: run('Helpers.windowOf("WindowDeviceLibrary.qml") !== null'), 5.0)
    out['libraryOpen'] = run('Helpers.windowOf("WindowDeviceLibrary.qml") !== null')
    # Another page: Profile Settings. The bar stays, its page part is empty.
    run('uiState.setCurrentRoom("settings"); uiState.setCurrentTab("settings")')
    pump(lambda: run('uiState.currentRoom') == 'settings', 3.0)
    pump(lambda: False, 0.5)
    out['settings'] = bar_state()
    # And back Home: the controls come back.
    click('_homeButton')
    pump(lambda: run('uiState.currentRoom') == 'status', 3.0)
    pump(lambda: False, 0.5)
    out['backHome'] = bar_state()

print('RESULT ' + json.dumps(out), flush=True)
os._exit(0)  # threads started by the app would keep it alive
"""


def _run(tmp_path: pathlib.Path, scale: int) -> dict:
    path = tmp_path / "mode_bar_app.py"
    path.write_text(_SCRIPT, encoding="utf-8")
    (tmp_path / "Gremlin Platforms").mkdir(exist_ok=True)
    env = dict(
        os.environ, USERPROFILE=str(tmp_path), QT_QPA_PLATFORM="offscreen",
        GREMLIN_OFFLINE="1",
    )
    env.setdefault(
        "QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
    )
    result = subprocess.run(
        [sys.executable, str(path), str(scale)], cwd=_ROOT, env=env,
        capture_output=True, text=True, timeout=180,
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, result.stdout[-2000:] + result.stderr[-4000:]
    return json.loads(lines[0][len("RESULT "):])


@pytest.fixture(scope="module")
def normal(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return _run(tmp_path_factory.mktemp("mode_bar_100"), 100)


@pytest.fixture(scope="module")
def large(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return _run(tmp_path_factory.mktemp("mode_bar_175"), 175)


def test_the_toolbar_has_no_mode(normal: dict) -> None:
    assert normal["toolbarHasMode"] is False
    assert normal["modeLabel"] == "Mode"
    assert normal["manageModes"] == "Manage Modes"


def test_home_shows_the_bar_with_mode_left_then_its_controls(normal: dict) -> None:
    home = normal["home"]
    assert home is not None, "no modeBar"
    assert home["visible"] and home["belowToolbar"]
    assert home["holdsMode"] and home["modeShown"]
    assert home["loaderInBar"] and home["loaderItem"]
    assert home["libraryButton"]
    assert home["modeLeftThenPage"]


def test_homes_controls_work_from_the_bar(normal: dict) -> None:
    assert normal["compactAfter"] is (not normal["compactBefore"])
    assert normal["splitAfter"] != normal["splitBefore"]
    assert normal["libraryOpen"] is True


def test_another_page_keeps_the_mode_bar_without_page_controls(normal: dict) -> None:
    settings = normal["settings"]
    assert settings is not None, "no modeBar"
    assert settings["visible"] and settings["holdsMode"] and settings["modeShown"]
    assert settings["loaderInBar"] and not settings["loaderItem"]
    assert not settings["libraryButton"]
    back = normal["backHome"]
    assert back["loaderItem"] and back["libraryButton"]


@pytest.mark.parametrize("which", ["normal", "large"])
def test_the_bar_fits_at_the_minimum_width(
    which: str, request: pytest.FixtureRequest
) -> None:
    out = request.getfixturevalue(which)
    assert out["minW"] <= out["screen"] or which == "normal"
    fit = out["fit"]
    assert fit["manage"] <= fit["width"]
    flick = fit["flick"]
    if flick is None or fit["library"] <= fit["width"]:
        assert 0 < fit["library"] <= fit["width"]
    else:  # the page's controls scroll in a view inside the window
        assert flick["right"] <= fit["width"]
        assert 0 < flick["lib"] <= flick["content"]
    assert fit["modeList"] > 0
