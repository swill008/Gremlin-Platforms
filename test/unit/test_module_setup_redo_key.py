# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Module Setup's Redo shortcut works.

Redo listed StandardKey.Redo and "Ctrl+Y"; on Windows StandardKey.Redo is
Ctrl+Y, so the shortcut held Ctrl+Y twice, was ambiguous and Ctrl+Y did
nothing. StandardKey.Redo alone gives both Ctrl+Y and Ctrl+Shift+Z there
(adding "Ctrl+Shift+Z" would make that key ambiguous the same way).

Opens the real window off-screen in its own process and presses the keys.
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

_CODE = """
import json, os, sys
sys.path.insert(0, '.')
import importlib.util
spec = importlib.util.spec_from_file_location('fake_hardware', 'test/fake_hardware.py')
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake_hardware.install()
import gremlin.ui.update_model as um
um.UpdateModel.startup = lambda self, *a, **k: None
import joystick_gremlin
from PySide6 import QtCore, QtQml, QtTest
app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
win = app.main_window

def ev(obj, code):
    expr = QtQml.QQmlExpression(QtQml.qmlContext(obj), obj, code)
    value = expr.evaluate()
    assert not expr.hasError(), expr.error().toString()
    return value[0] if isinstance(value, tuple) else value

ev(win, '_root.openConfigureModule("source", null)')
QtTest.QTest.qWait(400)
from PySide6 import QtQuick
setup = next(w for w in app.topLevelWindows()
             if w is not win and w.isVisible() and isinstance(w, QtQuick.QQuickWindow))
setup.requestActivate()
QtTest.QTest.qWaitForWindowActive(setup, 3000)
QtTest.QTest.qWait(100)

Ctrl = QtCore.Qt.KeyboardModifier.ControlModifier
Shift = QtCore.Qt.KeyboardModifier.ShiftModifier
K = QtCore.Qt.Key

def steps():
    return [bool(ev(setup, '_driver.canUndo')), bool(ev(setup, '_driver.canRedo'))]

def press(key, mods):
    QtTest.QTest.keyClick(setup, key, mods)
    QtTest.QTest.qWait(50)
    return steps()

out = {'rows': int(ev(setup, '_driver.rowCount()'))}
ev(setup, '_driver.setFriendly(0, "Redo key test")')
out['edited'] = steps()
out['ctrlZ'] = press(K.Key_Z, Ctrl)
out['ctrlY'] = press(K.Key_Y, Ctrl)
out['ctrlZ2'] = press(K.Key_Z, Ctrl)
out['ctrlShiftZ'] = press(K.Key_Z, Ctrl | Shift)
print('RESULT ' + json.dumps(out), flush=True)
os._exit(0)  # threads started by the app would keep it alive
"""


@pytest.fixture(scope="module")
def result(tmp_path_factory: pytest.TempPathFactory) -> dict[str, object]:
    home = tmp_path_factory.mktemp("home")
    (home / "Gremlin Platforms").mkdir()
    script = home / "redo_key.py"
    script.write_text(_CODE, encoding="utf-8")
    env = dict(os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen")
    done = subprocess.run(
        [sys.executable, str(script)], cwd=_ROOT, env=env,
        capture_output=True, text=True, timeout=120,
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, done.stdout[-1500:] + done.stderr[-1500:]
    return json.loads(lines[0][len("RESULT "):])


def test_ctrl_z_undoes_the_edit(result: dict[str, object]) -> None:
    assert result["rows"] > 0
    # [can undo, can redo]
    assert result["edited"] == [True, False]
    assert result["ctrlZ"] == [False, True]


def test_ctrl_y_redoes(result: dict[str, object]) -> None:
    assert result["ctrlY"] == [True, False]


def test_ctrl_shift_z_redoes(result: dict[str, object]) -> None:
    assert result["ctrlZ2"] == [False, True]
    assert result["ctrlShiftZ"] == [True, False]
