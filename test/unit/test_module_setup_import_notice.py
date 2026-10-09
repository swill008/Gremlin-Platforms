# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Module Setup's import message turns red when the import or its Undo fails.

The notice's border was the accent colour whatever happened, so "Import
Failed" and "Undo Failed" looked like success. Its failed flag is now set
from showImportResult and from the notice's Undo button, and the border
follows it.

Opens the real Module Setup window off-screen in its own process. Whether
an import can be undone and what Undo answers are set directly (the import
itself is tested elsewhere); everything else is the window's own code.
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
from gremlin.modules import store
undo_answers = []
# Module Setup asks the store (by device and window) whether an import can
# be undone and to undo it.
store.can_undo_file_import = lambda *a, **k: True
store.undo_file_import = lambda *a, **k: undo_answers.pop(0)
import joystick_gremlin
from PySide6 import QtQml, QtQuick, QtTest
app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
win = app.main_window

def until(pred, ms=10000):
    waited = 0
    while not pred() and waited < ms:
        QtTest.QTest.qWait(20)
        waited += 20

def ev(target, code):
    expr = QtQml.QQmlExpression(QtQml.qmlContext(target), target, code)
    value = expr.evaluate()[0]
    assert not expr.hasError(), expr.error().toString()
    return value

def setup_window():
    for w in app.topLevelWindows():
        if (w is not win and w.isVisible() and isinstance(w, QtQuick.QQuickWindow)
                and 'Module Setup' in w.title()):
            return w
    return None

until(lambda: ev(win, '_moduleModel.visibleCount()') > 0)
ev(win, '_root.openConfigureModule("source", null)')
until(lambda: setup_window() is not None)
dlg = setup_window()
assert dlg is not None, 'Module Setup did not open'

from PySide6 import QtCore

def items():
    found, pending = [], [dlg.contentItem().parentItem() or dlg.contentItem()]
    while pending:
        current = pending.pop()
        found.append(current)
        pending.extend(current.childItems())
    return found

def item(name):
    return next((i for i in items() if i.objectName() == name), None)

def shown(target):
    while target is not None:
        if not target.property("visible"):
            return False
        target = target.parentItem()
    return True

def click(target):
    centre = target.mapToScene(
        QtCore.QPointF(target.width() / 2, target.height() / 2)).toPoint()
    QtTest.QTest.mouseClick(dlg, QtCore.Qt.MouseButton.LeftButton, pos=centre)
    QtTest.QTest.qWait(200)

# 01 S142: the Module File window's message line.
def notice():
    line = item("moduleFileMessage")
    return {
        'shown': bool(line is not None and shown(line)),
        'text': line.property("text") if line else "",
        'failed': bool(line.property("failed")) if line else None,
        'red': ev(dlg, 'String(_fileMessage.color)'
                       ' === String(Style.alpha(Style.danger, 0.18))'),
        'canUndo': bool(shown(item("messageUndo"))),
    }

def press_undo():
    click(item("messageUndo"))

out = {}
ev(dlg, 'showImportResult("Import failed. The file is not a module file.")')
QtTest.QTest.qWait(200)
out['import-failed'] = notice()
ev(dlg, 'showImportResult("Imported pjoy_pro.json.")')
QtTest.QTest.qWait(200)
out['imported'] = notice()
undo_answers.append('Undo failed. The previous module file could not be put back.')
press_undo()
out['undo-failed'] = notice()
ev(dlg, 'showImportResult("Imported pjoy_pro.json.")')
QtTest.QTest.qWait(200)
undo_answers.append('Undone. The previous module file is back.')
press_undo()
out['undone'] = notice()

# 01 S140: Delete File is the red button and asks the shared question;
# Enter answers Cancel and nothing is deleted.
deleted = []
model = ev(dlg, 'moduleModel')
out['delete-red'] = item("moduleDeleteFile") is not None and str(
    item("moduleDeleteFile").property("background").property("color").name()
) == str(ev(dlg, 'Style.danger').name())
click(item("moduleDeleteFile"))
QtTest.QTest.qWait(300)
title = item("confirmTitle")
out['delete-asks'] = bool(title is not None and shown(title))
out['delete-title'] = title.property("text") if title else ""
action = item("confirmAction")
out['delete-action'] = action.property("text") if action else ""
QtTest.QTest.keyClick(dlg, QtCore.Qt.Key.Key_Return)
QtTest.QTest.qWait(300)
title = item("confirmTitle")
out['delete-after-enter'] = bool(title is not None and shown(title))
out['undone-still'] = notice()['text']
ev(dlg, '_moduleFileDialog.close()')

# 01 S143: the Undo / Redo pair says what the last change was.
rows = ev(dlg, '_driver.rowCount()')
out['rows'] = rows
if rows:
    label = ev(dlg, 'rowLabel(0)')
    claimed = ev(dlg, '_driver.data(_driver.index(0, 0), Qt.UserRole + 4)')
    ev(dlg, '_driver.setClaimed(0, %s)' % ('false' if claimed else 'true'))
    QtTest.QTest.qWait(100)
    bar = item("undoBarText")
    out['last-change'] = bar.property("text") if bar else ""
    word = " let go" if claimed else " claimed"
    out['expected-last'] = "Last change: " + label + word
    click(item("undoBarUndo"))
    out['undone-step'] = bar.property("text") if bar else ""
    out['expected-undone'] = "Undone: " + label + word
print('RESULT ' + json.dumps(out), flush=True)
os._exit(0)  # threads started by the app would keep it alive
"""


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home")
    (home / "Gremlin Platforms").mkdir()
    script = home / "import_notice.py"
    script.write_text(_CODE, encoding="utf-8")
    env = dict(
        os.environ,
        USERPROFILE=str(home),
        QT_QPA_PLATFORM="offscreen",
        GREMLIN_OFFLINE="1",
        HTTPS_PROXY="http://127.0.0.1:9",
    )
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, result.stdout[-1500:] + result.stderr[-1500:]
    return json.loads(lines[0][len("RESULT ") :])


def test_a_failed_import_is_red(run: dict) -> None:
    got = run["import-failed"]
    assert got["shown"] and got["failed"] and got["red"]
    assert got["text"] == "Import failed. The file is not a module file."
    assert got["canUndo"] is False


def test_an_import_is_not_red_and_offers_undo(run: dict) -> None:
    got = run["imported"]
    assert got["shown"] and not got["failed"] and not got["red"]
    assert got["text"] == "Imported pjoy_pro.json."
    assert got["canUndo"] is True


def test_a_failed_undo_turns_it_red(run: dict) -> None:
    got = run["undo-failed"]
    assert got["failed"] and got["red"]
    assert got["text"].startswith("Undo failed.")
    assert got["canUndo"] is False


def test_an_undo_is_not_red(run: dict) -> None:
    got = run["undone"]
    assert not got["failed"] and not got["red"]
    assert got["text"].startswith("Undone.")
    assert got["canUndo"] is False


def test_delete_file_asks_the_shared_question(run: dict) -> None:
    assert run["delete-red"]
    assert run["delete-asks"]
    title = run["delete-title"]
    assert title.startswith("Delete ") and title.endswith("?")
    assert run["delete-action"] == "Delete File"
    # Enter cancels: nothing deleted, the message stays.
    assert run["delete-after-enter"] is False
    assert run["undone-still"].startswith("Undone.")


def test_the_undo_bar_names_the_last_change(run: dict) -> None:
    if not run["rows"]:
        pytest.skip("the fake device lists no controls")
    assert run["last-change"] == run["expected-last"]
    assert run["undone-step"] == run["expected-undone"]
