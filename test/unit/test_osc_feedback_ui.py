# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""OSC's Module Setup "Feedback" section (D-09-OSC-FEEDBACK): it shows for
OSC only; its switches are edited with real key and mouse events and saved
to OSC's file at once. Since batch 2 (09 S154) the rows are added and
edited on the OSC page: the tab lists them read-only, keeps the Custom
variable template (S120) and has "Edit on the OSC page". The whole program
runs off-screen in its own process with a fresh user folder."""

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

def by_text(window, text):
    root = window.contentItem()
    while root.parentItem() is not None:
        root = root.parentItem()
    for item in walk(root):
        if item.isVisible() and item.property("text") == text \
                and "MenuItem" in type(item).__name__ + item.metaObject().className():
            return item
    return None

def show(window, item):
    # Scrolls the Feedback tab's page so item is in the window.
    flick = named(window, "oscFeedbackPage")
    if flick is None:
        return
    app.processEvents()
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
# OSC Setup's tabs: the Feedback tab shows the section.
setup = open_setup(str(ids.OSC).upper(), "oscTabFeedback")
if setup is not None:
    setup.requestActivate()
    wait_for(lambda: setup.isActive(), 2000)
    click(setup, named(setup, "oscTabFeedback"))
    if named(setup, "oscFeedbackSection") is None:
        setup = None
out["section"] = setup is not None
if setup is not None:
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
    # S154: the rows are edited only on the OSC page; the tab lists them.
    out["no-add-row"] = named(setup, "oscFeedbackAddRow") is None
    out["none-text"] = named(setup, "oscFeedbackNone").property("text")

    # S120: the Custom variable template stays on the tab.
    click(setup, named(setup, "oscAddCompanionVariable"))
    wait_for(lambda: named(setup, "oscTemplateAdd") is not None, 2000)
    out["template-dialog"] = named(setup, "oscTemplateAdd") is not None
    if out["template-dialog"]:
        type_into(setup, named(setup, "oscTemplateVariable"), "my_mode")
        click(setup, named(setup, "oscTemplateAdd"))
    wait_for(lambda: len(osc_device_file.read_feedback()) == 1, 2000)
    out["template-rows"] = osc_device_file.read_feedback()
    out["template-targets"] = osc_device_file.read_targets()

    # The read-only list: one line per row, no fields to edit.
    wait_for(lambda: named(setup, "oscFeedbackRow") is not None, 2000)
    line = named(setup, "oscFeedbackRow")
    out["list-texts"] = [
        str(i.property("text")) for i in walk(line) if i.property("text") is not None
    ] if line is not None else []
    out["no-row-fields"] = all(
        named(setup, n) is None
        for n in ("oscFeedbackRowAddress", "oscFeedbackRowKind", "oscFeedbackRowRemove",
                  "oscFeedbackRowEnabled", "oscFeedbackRowMin", "oscFeedbackRowMax")
    )

    # "Edit on the OSC page": the main window shows the OSC page.
    def tab():
        value = run("uiState.currentRoom + '/' + uiState.currentTab")
        return value[0] if isinstance(value, (tuple, list)) else value
    out["tab-before"] = tab()
    click(setup, named(setup, "oscFeedbackEditOnPage"))
    wait_for(lambda: tab() == "configuration/osc", 3000)
    out["tab-after"] = tab()
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


def test_feedback_tab_lists_rows_read_only(result: dict) -> None:
    """S154: no Add Row and no row fields on the tab; each row is one line."""
    assert result["rows-before"] == []
    assert result["no-add-row"] is True
    assert "OSC page" in result["none-text"]
    assert result["no-row-fields"] is True
    texts = result["list-texts"]
    assert "On" in texts
    assert "/custom-variable/my_mode/value" in texts


def test_custom_variable_template_stays_on_the_tab(result: dict) -> None:
    """S120: Custom variable is the one template left on the Feedback tab."""
    assert result["template-dialog"] is True, result
    (row,) = result["template-rows"]
    assert row["address"] == "/custom-variable/my_mode/value"
    assert row["source"]["kind"] == "mode"
    companion = [t for t in result["template-targets"] if t["name"] == "Companion"]
    assert row["target"] == companion[0]["id"]


def test_edit_on_the_osc_page_opens_the_osc_page(result: dict) -> None:
    assert result["tab-before"] != "configuration/osc"
    assert result["tab-after"] == "configuration/osc"
