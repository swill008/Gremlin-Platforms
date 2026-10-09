# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Help's "Show me ›" for a setting: Options shows the page that holds the
setting, scrolls it into view and pulses it (01 S139, D-01-HELP-LINKS)."""

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
from PySide6 import QtCore, QtQml
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

OPT = 'Helpers.windowOf("DialogOptions.qml")'
out = {}
# Labels without any window (what Help's link check uses).
out['modelLabels'] = list(ConfigSectionModel().settingLabels())

run('_optionsButton.clicked()')
pump(lambda: run(OPT + ' !== null'))
options = run(OPT)
pump(lambda: options.isExposed(), 3.0)
out['hasReveal'] = run('typeof ' + OPT + '.revealSetting === "function"')
if not out['hasReveal']:
    print('RESULT ' + json.dumps(out), flush=True)
    os._exit(0)

out['labels'] = run(OPT + '.settingLabels()')
out['unknown'] = run(OPT + '.revealSetting("No such setting at all")')

# Start somewhere else, scrolled down, with a search typed.
run(OPT + '.currentSection = 2')
pump(lambda: False, 0.3)

# Where a card is: on the window, inside the page's view, with a pulse.
CARD = ('(function() { var w = ' + OPT + '; var stack = [w.contentItem]; '
        'while (stack.length) { var it = stack.pop(); '
        'if (it.explanation !== undefined && it.title !== undefined '
        '&& String(it.title).toLowerCase() === %s && it.visible) return it; '
        'var k = it.children || []; for (var i = 0; i < k.length; i++) '
        'stack.push(k[i]) } return null })()')

def card_state(label):
    card = CARD % json.dumps(label.lower())
    return run('(function() { var c = ' + card + '; if (!c) return null; '
        'var w = ' + OPT + '; var p = c.mapToItem(w.contentItem, 0, 0); '
        'var pulse = false; for (var i = 0; i < c.children.length; i++) '
        '{ var k = c.children[i]; if (k.objectName === "helpPulse" '
        '&& k.visible) pulse = true } '
        'return { y: p.y, h: c.height, winH: w.contentItem.height, pulse: pulse, '
        'section: w.currentSection, scrolled: (function() { var f = c.parent; '
        'while (f && f.contentY === undefined) f = f.parent; '
        'return f ? f.contentY : -1 })() } })()')

out['revealed'] = run(OPT + '.revealSetting("minimize to tray")')
pump(lambda: False, 0.4)
out['tray'] = card_state('Minimize to tray')
out['sectionName'] = run('String(' + OPT + '.sectionTitle)')

# A setting far down its page (Folders: the last folder) comes into view.
last = out['labels'][-1] if out['labels'] else ''
out['last'] = last
out['revealedLast'] = run(OPT + '.revealSetting(' + json.dumps(last) + ')')
pump(lambda: False, 0.4)
out['lastState'] = card_state(last)
# The pulse is gone after about 2 s.
pump(lambda: False, 2.6)
out['lastAfter'] = card_state(last)
print('LABELS ' + json.dumps(out['labels']))
print('RESULT ' + json.dumps(out), flush=True)
os._exit(0)  # threads started by the app would keep it alive
"""


@pytest.fixture(scope="module")
def reveal(tmp_path_factory: pytest.TempPathFactory) -> dict:
    tmp_path = tmp_path_factory.mktemp("options_reveal")
    path = tmp_path / "options_reveal_app.py"
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
    return json.loads(lines[0][len("RESULT "):])


def test_options_can_reveal_a_setting(reveal: dict) -> None:
    assert reveal["hasReveal"] is True


def test_labels_list_known_settings(reveal: dict) -> None:
    for label in ("Minimize to tray", "UI scale", "Dark mode", "Plugins folder"):
        assert label in reveal["labels"]
    assert reveal["labels"] == reveal["modelLabels"]


def test_unknown_label_is_refused(reveal: dict) -> None:
    assert reveal["unknown"] is False


def test_reveal_shows_general_with_the_row_pulsing(reveal: dict) -> None:
    assert reveal["revealed"] is True
    tray = reveal["tray"]
    assert tray is not None
    assert tray["section"] == 0
    assert reveal["sectionName"] == "General"
    assert 0 <= tray["y"] and tray["y"] + tray["h"] <= tray["winH"]
    assert tray["pulse"] is True


def test_reveal_scrolls_a_low_row_into_view_and_the_pulse_ends(reveal: dict) -> None:
    assert reveal["revealedLast"] is True
    state = reveal["lastState"]
    assert state is not None
    assert 0 <= state["y"] and state["y"] + state["h"] <= state["winH"]
    assert state["scrolled"] > 0  # it was below the fold
    assert state["pulse"] is True
    assert reveal["lastAfter"]["pulse"] is False
