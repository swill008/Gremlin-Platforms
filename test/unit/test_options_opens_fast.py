# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Options opens fast: a section's settings are built the first time it
shows (opened, clicked or found by the search), not all at open (01 S48,
"Options: search box")."""

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
import gremlin.ui.update_model as um
um.UpdateModel.startup = lambda self, *a, **k: None
import joystick_gremlin
from PySide6 import QtCore, QtGui, QtQml, QtTest
from gremlin.ui.option import ConfigSectionModel

def pump(check, limit=10.0):
    end = time.monotonic() + limit
    while time.monotonic() < end:
        QtCore.QCoreApplication.processEvents(
            QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 50)
        if check():
            return True
    return bool(check())

app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
win = app.main_window

def run(code):
    expr = QtQml.QQmlExpression(QtQml.qmlContext(win), win, code)
    value = expr.evaluate()
    assert not expr.hasError(), code + ': ' + expr.error().toString()
    value = value[0] if isinstance(value, tuple) else value
    if isinstance(value, QtQml.QJSValue):
        value = value.toVariant()
    return value

# The sections and their groups, from the model.
model = ConfigSectionModel()
groups = []
for row in range(model.rowCount()):
    gm = model.data(model.index(row), QtCore.Qt.ItemDataRole.UserRole + 2)
    groups.append([gm.data(gm.index(g), QtCore.Qt.ItemDataRole.UserRole + 1)
                   for g in range(gm.rowCount())])

# A word found only in one section other than the first.
term, only = None, None
for row in [r for r in range(1, model.rowCount()) if r != 2]:
    gm = model.data(model.index(row), QtCore.Qt.ItemDataRole.UserRole + 2)
    for g in range(gm.rowCount()):
        em = gm.data(gm.index(g), QtCore.Qt.ItemDataRole.UserRole + 2)
        for r in range(em.rowCount()):
            name = str(em.data(em.index(r), QtCore.Qt.ItemDataRole.UserRole + 5) or '')
            if name and model.matchingSections(name) == [row]:
                term, only = name, row
                break
        if term: break
    if term: break

WALK = ('(function() { var w = Helpers.windowOf("DialogOptions.qml"); '
        'var out = []; var stack = [w.contentItem]; while (stack.length) { '
        'var it = stack.pop(); if (%s) out.push(it); var k = it.children || []; '
        'for (var i = 0; i < k.length; i++) stack.push(k[i]) } return out })()')
GROUPS = WALK % 'it.entryModel !== undefined && it.firstMatch !== undefined'

def group_count():
    return run(GROUPS + '.length')

def shown_groups():
    return sorted(run(GROUPS.replace('return out', 'return out.filter('
        'function(g) { return g.visible }).map(function(g) { return g.groupName })')))

out = {'groups': groups, 'term': term, 'only': only}
start = time.perf_counter()
run('_optionsButton.clicked()')
pump(lambda: run('Helpers.windowOf("DialogOptions.qml") !== null'))
out['openSeconds'] = time.perf_counter() - start
options = run('Helpers.windowOf("DialogOptions.qml")')
pump(lambda: options.isExposed(), 3.0)
out['openCount'] = group_count()
out['openShown'] = shown_groups()

# Click the third section in the sidebar.
pos = run(WALK % ('it.current !== undefined && it.groupModel !== undefined '
                  '&& it.index === 2')
          + '.map(function(b) { var p = b.mapToItem(null, b.width / 2, '
          'b.height / 2); return [p.x, p.y] })[0]')
QtTest.QTest.mouseClick(options, QtCore.Qt.MouseButton.LeftButton,
                        QtCore.Qt.KeyboardModifier.NoModifier,
                        QtCore.QPoint(int(pos[0]), int(pos[1])))
pump(lambda: run('Helpers.windowOf("DialogOptions.qml").currentSection === 2'), 3.0)
out['clickCount'] = group_count()
out['clickShown'] = shown_groups()

# Search a word found only in another section; then clear it.
search = WALK % 'it.placeholderText === "Search options"'
run(search + '[0].forceActiveFocus()')
def key(code, text=''):
    for kind in (QtCore.QEvent.Type.KeyPress, QtCore.QEvent.Type.KeyRelease):
        QtCore.QCoreApplication.sendEvent(options, QtGui.QKeyEvent(
            kind, code, QtCore.Qt.KeyboardModifier.NoModifier, text))

for ch in term:
    key(QtCore.Qt.Key.Key_A if ch.isalpha() else QtCore.Qt.Key.Key_Space, ch)
pump(lambda: False, 0.3)
out['searchText'] = run(search + '[0].text')
out['searchShown'] = shown_groups()
out['noMatchShown'] = run(WALK % ('it.text !== undefined && String(it.text)'
                                  '.indexOf("No setting matches") === 0')
                          + '[0].visible')
run(search + '[0].selectAll()')
key(QtCore.Qt.Key.Key_Delete)
pump(lambda: False, 0.3)
out['clearedShown'] = shown_groups()
print('RESULT ' + json.dumps(out), flush=True)
os._exit(0)  # threads started by the app would keep it alive
"""


@pytest.fixture(scope="module")
def options(tmp_path_factory: pytest.TempPathFactory) -> dict:
    tmp_path = tmp_path_factory.mktemp("options_fast")
    path = tmp_path / "options_fast_app.py"
    path.write_text(_SCRIPT, encoding="utf-8")
    env = dict(
        os.environ, USERPROFILE=str(tmp_path), QT_QPA_PLATFORM="offscreen",
        GREMLIN_OFFLINE="1",
    )
    env.setdefault(
        "QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
    )
    result = subprocess.run(
        [sys.executable, str(path)], cwd=_ROOT, env=env,
        capture_output=True, text=True, timeout=180,
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, result.stdout[-2000:] + result.stderr[-4000:]
    out = json.loads(lines[0][len("RESULT "):])
    print(f"Options open: {out['openSeconds']:.3f} s")
    return out


def test_opening_builds_only_the_open_section(options: dict) -> None:
    groups = options["groups"]
    assert len(groups) > 2
    assert options["openCount"] == len(groups[0])
    assert options["openShown"] == sorted(groups[0])


def test_clicking_a_section_builds_it(options: dict) -> None:
    groups = options["groups"]
    assert options["clickCount"] == len(groups[0]) + len(groups[2])
    assert options["clickShown"] == sorted(groups[2])


def test_search_shows_a_match_in_a_section_not_yet_built(options: dict) -> None:
    groups, only = options["groups"], options["only"]
    assert options["term"] and only not in (0, 2)
    assert options["searchText"] == options["term"]
    assert options["searchShown"]
    assert set(options["searchShown"]) <= set(groups[only])
    assert options["noMatchShown"] is False


def test_clearing_the_search_goes_back_to_the_section(options: dict) -> None:
    assert options["clearedShown"] == sorted(options["groups"][2])
