# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Manage Modes, Auto Mapper, Live Log Reader, Save Diagnostics and HidHide
on the shared pieces (01 S140-S143): each delete / replace / clear / remove
asks the one shared question (Enter cancels, only a click on the red button
goes ahead), Manage Modes' Undo Delete Mode is the shared Undo / Redo pair
(04 S46a), the Live Log's Find boxes are the shared search box (Esc clears),
and the save choosers open in the folder last used for their kind.

The program starts off-screen in a child process with a fresh user folder;
it prints "RESULT {json}".
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[2]

_CODE = r"""
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
from PySide6 import QtCore, QtQml, QtQuick, QtTest
from gremlin import shared_state

app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
main = app.main_window
out = {}

def ev(win, code):
    expr = QtQml.QQmlExpression(QtQml.qmlContext(win), win, code)
    value = expr.evaluate()
    if expr.hasError():
        return 'error: ' + expr.error().toString()
    value = value[0] if isinstance(value, tuple) else value
    return value.toVariant() if hasattr(value, 'toVariant') else value

def open_window(qml, title):
    ev(main, 'Helpers.createComponent("%s")' % qml)
    QtTest.QTest.qWait(600)
    win = [w for w in app.topLevelWindows() if w is not main and w.isVisible()
           and isinstance(w, QtQuick.QQuickWindow) and w.title().startswith(title)][0]
    win.requestActivate()
    QtTest.QTest.qWait(150)
    return win

def items(item):
    yield item
    for child in item.childItems():
        yield from items(child)

def named(win, name):
    return [i for i in items(win.contentItem()) if i.objectName() == name]

def key(win, k):
    QtTest.QTest.keyClick(win, k)
    QtTest.QTest.qWait(150)

def click(win, item):
    p = item.mapToScene(QtCore.QPointF(item.width() / 2, item.height() / 2))
    QtTest.QTest.mouseClick(win, QtCore.Qt.MouseButton.LeftButton,
                            QtCore.Qt.KeyboardModifier.NoModifier, p.toPoint())
    QtTest.QTest.qWait(200)

def question(win):
    return {
        'shown': ev(win, '_question !== null && _question.opened === true'),
        'name': ev(win, '_question ? _question.objectName : ""'),
        'title': ev(win, '_question ? _question.titleText : ""'),
        'text': ev(win, '_question ? _question.bodyText : ""'),
        'last': ev(win, '_question ? _question.lastLine : ""'),
        'action': ev(win, '_question ? _question.actionText : ""'),
    }

# --- Manage Modes: Delete Mode asks; Enter cancels; the red button deletes;
#     Undo (the shared pair) brings it back.
modes = shared_state.current_profile.modes
modes.add_mode('Flight')
win = open_window('DialogManageModes.qml', 'Manage Modes')
ev(win, 'confirmDelete("Flight")')
QtTest.QTest.qWait(200)
out['modes_q'] = question(win)
key(win, QtCore.Qt.Key.Key_Return)
def modes_state():
    return [ev(win, '_question === null'), modes.mode_exists('Flight'),
            win.isVisible()]
out['modes_enter'] = modes_state()
ev(win, 'confirmDelete("Flight")')
QtTest.QTest.qWait(200)
key(win, QtCore.Qt.Key.Key_Escape)
out['modes_esc'] = modes_state()
ev(win, 'confirmDelete("Flight")')
QtTest.QTest.qWait(200)
dialog = named(win, 'confirmAction')
click(win, dialog[0])
out['modes_deleted'] = not modes.mode_exists('Flight')
undo = named(win, 'undoBarUndo')
out['modes_bar'] = [len(undo), ev(win, '_undoBar.shownText'),
                    bool(undo and undo[0].isEnabled())]
if undo:
    click(win, undo[0])
out['modes_back'] = modes.mode_exists('Flight')
win.close()
QtTest.QTest.qWait(200)

# --- Auto Mapper: Overwrite asks; Enter cancels and nothing is made.
win = open_window('DialogAutoMapper.qml', 'Auto Mapper')
ev(win, '_overwriteNonEmpty.checked = true')
create = [i for i in items(win.contentItem())
          if i.property('text') == 'Create 1:1 Actions'][0]
before = ev(win, '_statusMessage.text')
click(win, create)
out['map_q'] = question(win)
key(win, QtCore.Qt.Key.Key_Return)
out['map_enter'] = [ev(win, '_question === null'),
                    ev(win, '_statusMessage.text') == before]
win.close()
QtTest.QTest.qWait(200)

# --- Live Log Reader: Clear Log asks (red button); Find is the search box.
win = open_window('DialogLiveLog.qml', 'Live Log Reader')
ev(win, '_tabs.currentIndex = 0')
QtTest.QTest.qWait(200)
out['log_red'] = [len(named(win, 'dangerButtonFill')) >= 1]
ev(win, '_clearConfig.clicked()')
QtTest.QTest.qWait(200)
out['log_q'] = question(win)
key(win, QtCore.Qt.Key.Key_Enter)
out['log_enter'] = ev(win, '_question === null')
ev(win, '_tabs.currentIndex = 1')
QtTest.QTest.qWait(300)
ev(win, '_debugFind.focusField()')
Key = QtCore.Qt.Key
for k in (Key.Key_Z, Key.Key_Z, Key.Key_Q, Key.Key_Q):
    QtTest.QTest.keyClick(win, k)
QtTest.QTest.qWait(200)
out['find_typed'] = [ev(win, '_debug.find'), ev(win, '_debugFind.count')]
key(win, QtCore.Qt.Key.Key_Escape)
out['find_esc'] = [ev(win, '_debugFind.text'), ev(win, '_debug.find'), win.isVisible()]
out['feed_kind'] = ev(win, '_saveFeed.kind')
win.close()
QtTest.QTest.qWait(200)

# --- Save Diagnostics: the chooser starts on the Desktop, then in the
#     folder last used for diagnostics.
win = open_window('DialogSaveDiagnostics.qml', 'Save Diagnostics')
out['diag_first'] = [ev(win, '_saveDialog.startFolder()'), ev(win, '_diag.desktopUrl')]
folder = os.path.join(os.environ['USERPROFILE'], 'reports')
os.makedirs(folder, exist_ok=True)
url = QtCore.QUrl.fromLocalFile(os.path.join(folder, 'diag.zip')).toString()
ev(win, '_saveDialog._accept(%s)' % json.dumps(url))
for _ in range(100):
    QtTest.QTest.qWait(100)
    if not ev(win, '_diag.busy'):
        break
win.close()
QtTest.QTest.qWait(300)
win = open_window('DialogSaveDiagnostics.qml', 'Save Diagnostics')
out['diag_again'] = [ev(win, '_saveDialog.startFolder()'),
                     QtCore.QUrl.fromLocalFile(folder).toString()]
out['diag_native_hidden'] = ev(win, '_saveDialog.dialog().visible') is False
win.close()
QtTest.QTest.qWait(200)

# --- HidHide: Remove asks; Enter cancels; headings and empty lists shared.
win = open_window('DialogHardwareHide.qml', 'HidHide')
ev(win, 'confirmRemoveGame({ name: "game.exe", path: "C:\\\\Games\\\\game.exe" })')
QtTest.QTest.qWait(200)
out['hide_q'] = question(win)
key(win, QtCore.Qt.Key.Key_Return)
out['hide_enter'] = ev(win, '_question === null')
out['hide_pieces'] = [len(named(win, 'sectionHeadingText')),
                      len(named(win, 'hidHideNoPrograms')),
                      len(named(win, 'hidHideNoDevices'))]
out['pickers'] = [ev(win, '_pickPhoto.kind'), ev(win, '_pickExe.kind')]
print('RESULT ' + json.dumps(out), flush=True)
os._exit(0)  # threads started by the app would keep it alive
"""


def _run(tmp_path: pathlib.Path) -> dict:
    home = tmp_path / "home"
    (home / "Gremlin Platforms").mkdir(parents=True)
    script = home / "tools2.py"
    script.write_text(_CODE, encoding="utf-8")
    env = dict(os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen",
               PYTHONIOENCODING="utf-8")
    result = subprocess.run(
        [sys.executable, str(script)], cwd=_ROOT, env=env,
        capture_output=True, text=True, encoding="utf-8", timeout=180,
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, result.stdout[-2000:] + result.stderr[-2000:]
    return json.loads(lines[0][len("RESULT "):])


def test_tool_windows_use_the_shared_pieces(tmp_path: pathlib.Path) -> None:
    out = _run(tmp_path)

    # Manage Modes (04 S45, S46a; 01 S140, S143).
    q = out["modes_q"]
    assert q["shown"] and q["name"] == "confirmDialog", out
    assert q["title"] == "Delete mode Flight?", q
    assert q["text"] == "It has no bindings. Modes under it move up one level.", q
    assert q["last"] == "You can restore it from Tools › History.", q
    assert q["action"] == "Delete Mode", q
    assert out["modes_enter"] == [True, True, True], out
    assert out["modes_esc"] == [True, True, True], out  # Esc cancels, the window stays
    assert out["modes_deleted"] is True, out
    assert out["modes_bar"] == [1, "Last change: Delete mode Flight", True], out
    assert out["modes_back"] is True, out

    # Auto Mapper (08 S95).
    q = out["map_q"]
    assert q["shown"] and q["name"] == "confirmDialog", out
    assert q["action"] == "Replace Actions", q
    assert q["last"] == (
        "Nothing is saved yet: to undo, load the profile again without saving."
    ), q
    assert out["map_enter"] == [True, True], out

    # Live Log Reader (01 S108, S141, S143).
    assert out["log_red"] == [True], out
    q = out["log_q"]
    assert q["shown"] and q["name"] == "confirmDialog", out
    assert q["action"] == "Clear Log" and q["last"] == "This can't be undone.", q
    assert out["log_enter"] is True, out
    assert out["find_typed"][0] == "zzqq", out
    assert out["find_esc"] == ["", "", True], out
    assert out["feed_kind"] == "log", out

    # Save Diagnostics (01 S132, S143).
    first, desktop = out["diag_first"]
    assert first == desktop, out
    again, folder = out["diag_again"]
    assert again.lower() == folder.lower(), out
    assert out["diag_native_hidden"] is True, out

    # HidHide (01 S140, S143).
    q = out["hide_q"]
    assert q["shown"] and q["name"] == "confirmDialog", out
    assert q["title"] == "Remove game.exe from the program list?", q
    assert q["action"] == "Remove Program", q
    assert out["hide_enter"] is True, out
    assert out["hide_pieces"] == [3, 1, 1], out
    assert out["pickers"] == ["picture", "other"], out
