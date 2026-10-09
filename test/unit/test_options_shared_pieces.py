# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Options on the shared pieces (01 S140, S141, S143): the search box is the
shared SearchBox (Ctrl+F, "N found" / "Nothing matches", Esc clears); an
auto-load entry's remove button is the red one and asks the shared question
(Enter cancels, the red button removes); the auto-load profile chooser opens
in the last folder used for profiles. The real app runs off-screen in its
own process with real key and mouse events."""

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
from PySide6 import QtCore, QtGui, QtQml, QtQuick, QtTest
import gremlin.config

PICKED = sys.argv[1]

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
cfg = gremlin.config.Configuration()
AUTO = ('profile', 'automation', 'entries-auto-loading')
cfg.set('profile', 'automation', 'entries-auto-loading',
        [['C:/Profiles/Combat.xml', 'C:/Games/Sim.exe', True]])

def run(code, on=None):
    on = on or win
    expr = QtQml.QQmlExpression(QtQml.qmlContext(on), on, code)
    value = expr.evaluate()
    assert not expr.hasError(), code + ': ' + expr.error().toString()
    value = value[0] if isinstance(value, tuple) else value
    if isinstance(value, QtQml.QJSValue):
        value = value.toVariant()
    return value

OPT = 'Helpers.windowOf("DialogOptions.qml")'
out = {}
run('_optionsButton.clicked()')
pump(lambda: run(OPT + ' !== null'))
options = run(OPT)
pump(lambda: options.isExposed(), 3.0)
options.requestActivate()
pump(lambda: QtGui.QGuiApplication.focusWindow() is options, 3.0)

# Visual items (Repeater delegates have no QObject parent: findChild misses them).
def items():
    out, stack = [], [options.contentItem()]
    for top in (options.contentItem().parentItem(),):
        if top is not None:
            stack = [top]
    while stack:
        it = stack.pop()
        out.append(it)
        stack.extend(it.childItems())
    return out

def find(name):
    hits = [i for i in items() if i.objectName() == name]
    return hits[0] if hits else None

def finds(name):
    return [i for i in items() if i.objectName() == name and i.isVisible()]

def click(item):
    p = item.mapToScene(QtCore.QPointF(item.width() / 2, item.height() / 2))
    QtTest.QTest.mouseClick(options, QtCore.Qt.MouseButton.LeftButton,
                            QtCore.Qt.KeyboardModifier.NoModifier, p.toPoint())
    pump(lambda: False, 0.2)

def key(k, mod=QtCore.Qt.KeyboardModifier.NoModifier):
    QtTest.QTest.keyClick(options, k, mod)
    pump(lambda: False, 0.2)

def type_text(text):
    for ch in text:
        k = QtCore.Qt.Key(ord(ch.upper()))
        for kind in (QtCore.QEvent.Type.KeyPress, QtCore.QEvent.Type.KeyRelease):
            QtCore.QCoreApplication.sendEvent(options, QtGui.QKeyEvent(
                kind, k, QtCore.Qt.KeyboardModifier.NoModifier, ch))
    pump(lambda: False, 0.4)

# Search: the shared box.
box = find('optionsSearch')
out['isSearchBox'] = box is not None and find('searchField') is not None
if out['isSearchBox']:
    key(QtCore.Qt.Key.Key_F, QtCore.Qt.KeyboardModifier.ControlModifier)
    out['ctrlF'] = find('searchField').hasActiveFocus()
    type_text('scale')
    count = find('searchCount')
    out['countShown'] = bool(count and count.isVisible())
    out['countText'] = str(count.property('text')) if count else None
    out['rows'] = run('(function() { var w = ' + OPT + '; var n = 0; '
        'var stack = [w.contentItem]; while (stack.length) { var it = stack.pop(); '
        'if (!it.visible) continue; '
        'if (it.explanation !== undefined && it.title !== undefined) { n++; continue } '
        'var k = it.children || []; for (var i = 0; i < k.length; i++) '
        'stack.push(k[i]) } return n })()')
    type_text('zzqx')
    out['nothing'] = str(count.property('text'))
    key(QtCore.Qt.Key.Key_Escape)
    out['escText'] = str(find('searchField').property('text'))
    out['escFocus'] = find('searchField').hasActiveFocus()
    out['escOpen'] = options.isVisible()

# Auto-load: the red remove button and the shared question.
run(OPT + '.revealSetting("Programs and their profiles")')
pump(lambda: bool(finds('autoLoadRemove')), 3.0)
removes = finds('autoLoadRemove')
out['removeButtons'] = len(removes)
if removes:
    click(removes[0])
    out['asked'] = bool(pump(lambda: bool(finds('confirmTitle')), 2.0))
    if out['asked']:
        out['title'] = str(find('confirmTitle').property('text'))
        out['text'] = str(find('confirmText').property('text'))
        out['action'] = str(find('confirmAction').property('text'))
        key(QtCore.Qt.Key.Key_Return)
        pump(lambda: not finds('confirmTitle'), 2.0)
        out['afterEnter'] = len(cfg.value(*AUTO))
        click(finds('autoLoadRemove')[0])
        pump(lambda: bool(finds('confirmAction')), 2.0)
        click(finds('confirmAction')[0])
        pump(lambda: False, 0.3)
        out['afterRemove'] = len(cfg.value(*AUTO))

# The profile chooser opens in the last folder used for profiles.
picker = find('autoLoadProfilePicker')
out['hasPicker'] = picker is not None
if picker is not None:
    from gremlin.ui import folder_memory
    folder_memory.remember('profile', QtCore.QUrl.fromLocalFile(
        os.path.join(PICKED, 'x.xml')).toString())
    # Sets the dialog up as open() does, without showing a native dialog.
    url = run('String(prepare().currentFolder)', on=picker)
    out['startFolder'] = QtCore.QUrl(str(url)).toLocalFile()
    out['picked'] = PICKED
print('RESULT ' + json.dumps(out), flush=True)
os._exit(0)  # threads started by the app would keep it alive
"""


@pytest.fixture(scope="module")
def opts(tmp_path_factory: pytest.TempPathFactory) -> dict:
    tmp_path = tmp_path_factory.mktemp("options_pieces")
    picked = tmp_path / "My Profiles"
    picked.mkdir()
    path = tmp_path / "options_pieces_app.py"
    path.write_text(_SCRIPT, encoding="utf-8")
    env = dict(
        os.environ, USERPROFILE=str(tmp_path), QT_QPA_PLATFORM="offscreen",
        GREMLIN_OFFLINE="1",
    )
    env.setdefault(
        "QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
    )
    result = subprocess.run(
        [sys.executable, str(path), str(picked)], cwd=_ROOT, env=env,
        capture_output=True, text=True, timeout=180,
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, result.stdout[-2000:] + result.stderr[-4000:]
    return json.loads(lines[0][len("RESULT "):])


def test_search_is_the_shared_box(opts: dict) -> None:
    assert opts["isSearchBox"] is True
    assert opts["ctrlF"] is True
    assert opts["countShown"] is True
    assert opts["rows"] > 0
    assert opts["countText"] == f"{opts['rows']} found"
    assert opts["nothing"] == "Nothing matches"
    # Esc clears and leaves the box; the window stays open (01 S134).
    assert opts["escText"] == ""
    assert opts["escFocus"] is False
    assert opts["escOpen"] is True


def test_auto_load_remove_asks_the_shared_question(opts: dict) -> None:
    assert opts["removeButtons"] == 1
    assert opts["asked"] is True
    assert opts["title"] == "Remove auto-load entry?"
    assert "Combat.xml" in opts["text"] and "Sim.exe" in opts["text"]
    assert opts["action"] == "Remove Entry"
    # Enter cancels; only the red button removes.
    assert opts["afterEnter"] == 1
    assert opts["afterRemove"] == 0


def test_profile_chooser_opens_in_the_remembered_folder(opts: dict) -> None:
    assert opts["hasPicker"] is True
    assert os.path.normcase(os.path.normpath(opts["startFolder"])) == os.path.normcase(
        os.path.normpath(opts["picked"])
    )
