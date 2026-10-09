# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""OSC's Module Setup "Feedback" section (D-09-OSC-FEEDBACK): it shows for
OSC only; its switches and rows are edited with real key and mouse events
and saved to OSC's file at once. The whole program runs off-screen in its
own process with a fresh user folder."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

_ROOT = pathlib.Path(__file__).parents[2]

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
# Registers OscFeedbackModel even before the program's own import list does.
import gremlin.ui.osc_feedback_model  # noqa: F401
from PySide6 import QtCore, QtQml, QtQuick, QtTest
app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
win = app.main_window
from gremlin import osc_device_file
from gremlin.modules import ids

out = {}

def run(code):
    expr = QtQml.QQmlExpression(QtQml.qmlContext(win), win, code)
    value = expr.evaluate()
    assert not expr.hasError(), expr.error().toString()
    return value

def walk(item):
    found = [item]
    for child in item.childItems():
        found.extend(walk(child))
    return found

def wait_for(done, limit_ms=5000):
    timer = QtCore.QElapsedTimer()
    timer.start()
    while not done() and timer.elapsed() < limit_ms:
        app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 20)
    return done()

def named(window, name):
    # From the root, so popups in the overlay are found too.
    root = window.contentItem()
    while root.parentItem() is not None:
        root = root.parentItem()
    for item in walk(root):
        if item.objectName() == name and item.isVisible():
            return item
    return None

def show(window, item):
    # Scrolls OSC's sections so item is in the window.
    scroll = named(window, "oscSectionsScroll")
    if scroll is None:
        return
    app.processEvents()
    flick = scroll.property("contentItem")
    inner = flick.property("contentItem")
    y = item.mapToItem(inner, QtCore.QPointF(0, 0)).y()
    flick.setProperty("contentY", max(0.0, y - 40))
    app.processEvents()

def type_into(window, field, text):
    show(window, field)
    field.forceActiveFocus()
    QtCore.QMetaObject.invokeMethod(field, "selectAll")
    if not text:
        QtTest.QTest.keyClick(window, QtCore.Qt.Key.Key_Delete)
    for char in text:
        QtTest.QTest.keyClick(window, char)
    QtTest.QTest.keyClick(window, QtCore.Qt.Key.Key_Tab)
    app.processEvents()

def click(window, item):
    show(window, item)
    centre = item.mapToScene(QtCore.QPointF(item.width() / 2, item.height() / 2))
    QtTest.QTest.mouseClick(window, QtCore.Qt.MouseButton.LeftButton,
                            QtCore.Qt.KeyboardModifier.NoModifier, centre.toPoint())
    app.processEvents()

def key(window, item, which):
    item.forceActiveFocus()
    QtTest.QTest.keyClick(window, which)
    app.processEvents()

def open_setup(guid, marker):
    run('_root.openConfigureModule("source", _root._cardForGuid("%s"))' % guid)
    found = []
    def look():
        for w in app.topLevelWindows():
            if w is not win and w.isVisible() and isinstance(w, QtQuick.QQuickWindow) \
                    and named(w, marker) is not None:
                found.append(w)
                return True
        return False
    wait_for(look)
    return found[0] if found else None

# Another device's Module Setup has no Feedback section.
kb = open_setup(str(ids.KEYBOARD).upper(), "moduleUndoBar")
out["keyboard-setup"] = kb is not None
out["keyboard-feedback"] = (
    kb is not None and named(kb, "oscFeedbackSection") is not None
)
if kb is not None:
    kb.close()
    app.processEvents()

out["before"] = osc_device_file.read_server()
setup = open_setup(str(ids.OSC).upper(), "oscFeedbackSection")
out["section"] = setup is not None
if setup is not None:
    setup.requestActivate()
    wait_for(lambda: setup.isActive(), 2000)
    for name in ("oscFeedbackEnabled", "oscFeedbackResendRun",
                 "oscFeedbackResendMode", "oscFeedbackResendProfile"):
        click(setup, named(setup, name))
    type_into(setup, named(setup, "oscFeedbackSyncAddress"), "my/sync")
    out["bad-sync-message"] = named(setup, "oscFeedbackMessage").property("text")
    type_into(setup, named(setup, "oscFeedbackSyncAddress"), "/my/sync")
    type_into(setup, named(setup, "oscFeedbackRate"), "0")
    out["bad-rate-message"] = named(setup, "oscFeedbackMessage").property("text")
    type_into(setup, named(setup, "oscFeedbackRate"), "20")
    out["server"] = osc_device_file.read_server()

    out["rows-before"] = osc_device_file.read_feedback()
    click(setup, named(setup, "oscFeedbackAddRow"))
    out["rows-added"] = osc_device_file.read_feedback()
    wait_for(lambda: named(setup, "oscFeedbackRowAddress") is not None, 2000)
    type_into(setup, named(setup, "oscFeedbackRowAddress"), "/fire")
    type_into(setup, named(setup, "oscFeedbackRowMin"), "-1")
    type_into(setup, named(setup, "oscFeedbackRowMax"), "2.5")
    # Source: one down from Current mode is vJoy button.
    key(setup, named(setup, "oscFeedbackRowKind"), QtCore.Qt.Key.Key_Down)
    wait_for(lambda: named(setup, "oscFeedbackRowNumber") is not None, 2000)
    type_into(setup, named(setup, "oscFeedbackRowNumber"), "5")
    # Target: up from "Reply to sender" is the Default target.
    key(setup, named(setup, "oscFeedbackRowTarget"), QtCore.Qt.Key.Key_Up)
    # Type: Auto -> Int.
    key(setup, named(setup, "oscFeedbackRowType"), QtCore.Qt.Key.Key_Down)
    click(setup, named(setup, "oscFeedbackRowEnabled"))
    out["rows-edited"] = osc_device_file.read_feedback()
    out["targets"] = osc_device_file.read_targets()

    remove = named(setup, "oscFeedbackRowRemove")
    show(setup, remove)
    right = remove.mapToScene(QtCore.QPointF(remove.width(), 0)).x()
    out["row-fits"] = right <= setup.width()
    click(setup, remove)
    wait_for(lambda: named(setup, "confirmAction") is not None, 2000)
    action = named(setup, "confirmAction")
    out["confirm"] = action is not None
    if action is not None:
        click(setup, action)
    wait_for(lambda: not osc_device_file.read_feedback(), 2000)
    out["rows-removed"] = osc_device_file.read_feedback()
    setup.close()
    app.processEvents()

print('RESULT ' + json.dumps(out), flush=True)
os._exit(0)  # threads started by the app would keep it alive
"""


@pytest.fixture(scope="module")
def result(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home")
    (home / "Gremlin Platforms").mkdir()
    script = home / "osc_feedback_ui.py"
    script.write_text(_CODE, encoding="utf-8")
    env = dict(
        os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen",
        GREMLIN_OFFLINE="1",
    )
    done = subprocess.run(
        [sys.executable, str(script)], cwd=_ROOT, env=env,
        capture_output=True, text=True, timeout=150,
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, done.stdout[-2000:] + done.stderr[-3000:]
    return json.loads(lines[-1][len("RESULT "):])


def test_feedback_section_is_for_osc_only(result: dict) -> None:
    assert result["section"] is True, result
    assert result["keyboard-setup"] is True, result
    assert result["keyboard-feedback"] is False


def test_feedback_switches_save_to_osc_file(result: dict) -> None:
    before = result["before"]
    server = result["server"]
    for key in ("feedback_enabled", "resend_run", "resend_mode", "resend_profile"):
        assert server[key] is (not before[key]), key
    assert "starts with /" in result["bad-sync-message"]
    assert "whole number" in result["bad-rate-message"]
    assert server["sync_address"] == "/my/sync"
    assert server["feedback_rate"] == 20


def test_feedback_rows_save_to_osc_file(result: dict) -> None:
    assert result["rows-before"] == []
    assert len(result["rows-added"]) == 1
    (row,) = result["rows-edited"]
    assert row["address"] == "/fire"
    assert row["min"] == -1.0
    assert row["max"] == 2.5
    assert row["source"]["kind"] == "vjoy_button"
    assert isinstance(row["source"]["device"], int)
    assert row["source"]["input"] == 5
    assert row["target"] == result["targets"][0]["id"]
    assert row["type"] == "int"
    assert row["enabled"] is False
    # The row's controls fit in the window (Remove is not cut off).
    assert result["row-fits"] is True
    assert result["confirm"] is True
    assert result["rows-removed"] == []
