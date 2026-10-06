# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Module Setup's import notice turns red when the import or its Undo fails.

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

def notice():
    return {
        'title': ev(dlg, '_importNotice.titleText'),
        'failed': ev(dlg, '_importNotice.failed'),
        'red': ev(dlg, 'String(_importNotice.background.border.color)'
                       ' === String(Style.danger)'),
        'canUndo': ev(dlg, '_importNotice.canUndo'),
    }

def press_undo():
    ev(dlg, '''(function () {
        function find(item) {
            if (item.text === "Undo" && item.clicked && item.visible)
                return item
            for (var i = 0; i < item.children.length; i++) {
                var hit = find(item.children[i])
                if (hit) return hit
            }
            return null
        }
        find(_importNotice.contentItem).clicked()
    })()''')

out = {}
ev(dlg, 'showImportResult("Import failed. The file is not a module file.")')
out['import-failed'] = notice()
ev(dlg, 'showImportResult("Imported pjoy_pro.json.")')
out['imported'] = notice()
undo_answers.append('Undo failed. The previous module file could not be put back.')
press_undo()
out['undo-failed'] = notice()
ev(dlg, 'showImportResult("Imported pjoy_pro.json.")')
undo_answers.append('Undone. The previous module file is back.')
press_undo()
out['undone'] = notice()
ev(dlg, '_importNotice.close()')
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
    assert run["import-failed"] == {
        "title": "Import Failed",
        "failed": True,
        "red": True,
        "canUndo": False,
    }


def test_an_import_is_not_red(run: dict) -> None:
    assert run["imported"] == {
        "title": "Imported",
        "failed": False,
        "red": False,
        "canUndo": True,
    }


def test_a_failed_undo_turns_it_red(run: dict) -> None:
    assert run["undo-failed"] == {
        "title": "Undo Failed",
        "failed": True,
        "red": True,
        "canUndo": False,
    }


def test_an_undo_is_not_red(run: dict) -> None:
    assert run["undone"] == {
        "title": "Undone",
        "failed": False,
        "red": False,
        "canUndo": False,
    }
