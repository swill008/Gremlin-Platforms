# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""OSC's full name under its page title (D-09-OSC-CARD-LINE).

OSC's Device Bindings page shows a small grey "Open Sound Control (OSC)"
line under the title, placed like the output pages' Driven by line. No other
device's page shows it. The Xbox and vJoy Output Views show Driven by and
no "View only" line (removed 2026-10-12). The pages are opened the way a
card click opens them (openDeviceBindingsNow). Off-screen in its own process.
"""

from __future__ import annotations

import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import smoke_report  # pyright: ignore[reportMissingImports]  (test/)

sys.path.append(".")

import json
import os
import pathlib

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
QtTest.QTest.qWait(500)

def ev(code):
    expr = QtQml.QQmlExpression(QtQml.qmlContext(win), win, code)
    value = expr.evaluate()[0]
    assert not expr.hasError(), expr.error().toString()
    return value

def until(pred, ms=10000):
    waited = 0
    while not pred() and waited < ms:
        QtTest.QTest.qWait(20)
        waited += 20

line = win.findChild(QtCore.QObject, 'oscFullName')
model = ev('_moduleModel')
until(lambda: any(r.slug == 'osc' for r in model._rows)
      and any(r.direction == 'source' and r.tab == 'physical' for r in model._rows))
stick = next(r for r in model._rows if r.direction == 'source' and r.tab == 'physical')
out = {'found': line is not None, 'home': bool(line.property('visible'))}

def show(slug):
    ev(f'_root.openDeviceBindingsNow(_moduleModel.cardMap({json.dumps(slug)}))')
    QtTest.QTest.qWait(200)
    return [ev('uiState.currentTab'), bool(line.property('visible')),
            line.property('text')]

out['osc'] = show('osc')
out['stick'] = show(stick.slug)
out['osc-again'] = show('osc')
out['xbox'] = show('xbox')

# The output pages: Driven by shows, the old "View only —" line is gone.
def texts():
    return [str(o.property('text')) for o in win.findChildren(QtCore.QObject)
            if o.property('visible') and isinstance(o.property('text'), str)]

bound = win.findChild(QtCore.QObject, 'destBound')
def is_vjoy(r):
    return r.direction == 'dest' and r.tab != 'xbox'

until(lambda: any(is_vjoy(r) for r in model._rows))
vjoy = next(r for r in model._rows if is_vjoy(r))
for slug, key in (('xbox', 'xbox-page'), (vjoy.slug, 'vjoy-page')):
    tab = show(slug)[0]
    out[key] = [tab, ev('configDirection'), bool(bound.property('visible')),
                any('View only' in t for t in texts())]
print('RESULT ' + json.dumps(out), flush=True)
os._exit(0)  # threads started by the app would keep it alive
"""


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home")
    (home / "Gremlin Platforms").mkdir()
    script = home / "osc_full_name.py"
    script.write_text(_CODE, encoding="utf-8")
    env = dict(os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen",
               HTTPS_PROXY="http://127.0.0.1:9")
    result = proc_tree.run(
        [sys.executable, str(script)], cwd=_ROOT, env=env, text=True, timeout=120,
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, smoke_report.explain(result)
    return json.loads(lines[0][len("RESULT "):])


def test_the_line_exists_and_is_hidden_on_home(run: dict) -> None:
    assert run["found"]
    assert not run["home"]


def test_the_osc_page_shows_the_full_name(run: dict) -> None:
    assert run["osc"] == ["osc", True, "Open Sound Control (OSC)"]
    assert run["osc-again"][1]


def test_another_input_device_page_does_not(run: dict) -> None:
    assert run["stick"][0] == "physical"
    assert not run["stick"][1]


def test_an_output_page_does_not(run: dict) -> None:
    assert not run["xbox"][1]


def test_output_views_show_driven_by_and_no_view_only_line(run: dict) -> None:
    # 15a (user 2026-10-12): the "View only —" header line is gone.
    assert run["xbox-page"] == ["xbox", "dest", True, False]
    assert run["vjoy-page"] == ["physical", "dest", True, False]
