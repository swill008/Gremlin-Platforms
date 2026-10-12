# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Driven by follows action edits.

An output card's Driven by (and the Output View header) lists the input
devices whose actions send to it. It was worked out only when a profile
loaded or a device came or went, so adding a Map to Xbox action on the
Logical Device left the Xbox card and header at [nothing]. Now the
bindings' owner (input_pairing) sends bindingsChanged for every edit,
undo and Delete Mode (D-01-OWNER-NOTICES 1a), and the list, the Home cards
on screen and the header follow. A full reload (profileChanged) refreshes
the header too, and the Home cards and the Device Bindings page title show
the user's name for a device (10 S7, 2a).

Off-screen in its own process; what the profile's actions send is set
directly (the action walk itself is tested in test_bound_cards).
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
from gremlin.ui import module_model
wires = []
module_model._profile_wire_maps = lambda: list(wires)
import joystick_gremlin
from gremlin.signal import signal
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
    # Qt.callLater on the Home page; under load it can run late.
    waited = 0
    while not pred() and waited < ms:
        QtTest.QTest.qWait(20)
        waited += 20

model = ev('_moduleModel')
role = QtCore.Qt.ItemDataRole.UserRole + 15

def card(name):
    for i in range(model.rowCount()):
        at = model.index(i, 0)
        if model._rows[i].name == name:
            return model.data(at, role)
    return None

until(lambda: any(r.direction == 'source' and r.tab == 'physical' for r in model._rows))
src = next(r for r in model._rows if r.direction == 'source' and r.tab == 'physical')
guid = module_model.guid_key(src.guid)
ev('_root.configDirection = "dest"')
ev('_root.configTitleName = "Xbox 360 Controller"')
ev('_root.refreshDestBound()')
out = {'source': src.name, 'before': [card('Xbox 360 Controller'), card('vJoy 1'),
                                      ev('_destBound.text')]}
# A Map to Xbox and a Map to vJoy added on the stick.
wires[:] = [(guid, 'xbox', 1), (guid, 'vjoy', 1)]
signal.bindingsChanged.emit()
until(lambda: card(src.name) == 'Xbox 360 Controller, vJoy 1'
      and ev('_destBound.text') != 'Driven by: [nothing]')
out['added'] = [card('Xbox 360 Controller'), card('vJoy 1'), card(src.name),
                ev('_destBound.text')]
# The Home card on screen follows (filled by hand: fillCard).
def home_card(slug, prop):
    return ev('(function() { var cards = _statusLoader.item._liveCards.filter('
              f'function(c) {{ return c.slug === {json.dumps(slug)} }}); '
              f'return cards.length ? String(cards[0].{prop}) : null }})()')
until(lambda: home_card('xbox', 'target') == src.name)
out['home'] = home_card('xbox', 'target')
# Removed again (Delete Mode, an undo: the same one notice).
wires[:] = []
signal.bindingsChanged.emit()
until(lambda: card('Xbox 360 Controller') == '' and card('vJoy 1') == ''
      and ev('_destBound.text') == 'Driven by: [nothing]')
out['removed'] = [card('Xbox 360 Controller'), card('vJoy 1'), ev('_destBound.text')]
# Added from the Logical Device's action editor (OK).
wires[:] = [(guid, 'xbox', 1)]
signal.bindingsChanged.emit()
until(lambda: card('Xbox 360 Controller') == src.name
      and ev('_destBound.text') == f'Driven by: [{src.name}]')
out['logical-ok'] = [card('Xbox 360 Controller'), ev('_destBound.text')]
wires[:] = []
signal.bindingsChanged.emit()
until(lambda: card('Xbox 360 Controller') == '')
# A page opening asks afresh, before the timer.
wires[:] = [(guid, 'xbox', 1)]
out['asked'] = model.boundLine('Xbox 360 Controller')
# A full reload (a profile loaded) tells the header at once.
ev('_root.refreshDestBound()')
out['pre-reload'] = ev('_destBound.text')
wires[:] = []
model._reload()
out['reload'] = ev('_destBound.text')
# The user's name for the stick: its Home card and the Device Bindings page
# title (10 S7), following the names' owner's notice.
from gremlin import device_aliases
ev('_root.configDirection = "source"')
ev(f'_root.configTitleName = {json.dumps(src.raw_name)}')
ev(f'uiState.setCurrentDevice({json.dumps(src.guid)})')
device_aliases.set_alias(src.guid, 'My Stick')
signal.deviceNamesChanged.emit()
until(lambda: home_card(src.slug, 'cardName') == 'My Stick')
out['named'] = [card('My Stick') is not None, model.cardMap(src.slug).get('rawName'),
                home_card(src.slug, 'cardName'), ev('_configTitle.text')]
print('RESULT ' + json.dumps(out), flush=True)
os._exit(0)  # threads started by the app would keep it alive
"""


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home")
    (home / "Gremlin Platforms").mkdir()
    script = home / "driven_by.py"
    script.write_text(_CODE, encoding="utf-8")
    env = dict(os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen",
               HTTPS_PROXY="http://127.0.0.1:9")
    result = proc_tree.run(
        [sys.executable, str(script)], cwd=_ROOT, env=env, text=True, timeout=120,
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, smoke_report.explain(result)
    return json.loads(lines[0][len("RESULT "):])


def test_nothing_drives_them_at_first(run: dict) -> None:
    assert run["before"] == ["", "", "Driven by: [nothing]"]


def test_an_added_action_shows_at_once(run: dict) -> None:
    source = run["source"]
    xbox, vjoy, stick, header = run["added"]
    assert xbox == source and vjoy == source
    assert stick == "Xbox 360 Controller, vJoy 1"
    assert header == f"Driven by: [{source}]"


def test_a_removed_action_clears_it(run: dict) -> None:
    assert run["removed"] == ["", "", "Driven by: [nothing]"]


def test_ok_in_the_logical_device_editor_updates_it(run: dict) -> None:
    source = run["source"]
    assert run["logical-ok"] == [source, f"Driven by: [{source}]"]


def test_a_page_opening_asks_afresh(run: dict) -> None:
    assert run["asked"] == f"Driven by: [{run['source']}]"


def test_the_home_card_on_screen_follows(run: dict) -> None:
    assert run["home"] == run["source"]


def test_a_full_reload_refreshes_the_header(run: dict) -> None:
    # The header said the Xbox pad was driven; after the reload nothing is.
    assert run["pre-reload"] == f"Driven by: [{run['source']}]"
    assert run["reload"] == "Driven by: [nothing]"


def test_the_users_name_shows_on_the_card_and_the_title(run: dict) -> None:
    found, raw, home, title = run["named"]
    assert found
    assert raw == run["source"]
    assert home == "My Stick"
    assert title == "My Stick"
