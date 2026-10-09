# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""OSC's Module Setup as tabs (D-09-OSC-TABS, D-09-OSC-COMPANION): Server ·
Output · Feedback · Discovery, each opened by a real click and scrolling on
its own; the page takes the window down to the buttons (no stray Undo bar
text behind them); Add Companion adds (or points back) the target
"Companion" 127.0.0.1:12321 and says what to turn on in Companion; this PC's
addresses never list 0.0.0.0. The whole program runs off-screen in its own
process with a fresh user folder; no network."""

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
import gremlin.osc as gosc
gosc.OscRuntime._bind = lambda self: None
# This PC's addresses as the program finds them: 0.0.0.0 is always among them.
import gremlin.ui.osc_option as oo
oo.local_ipv4_addresses = lambda: ['192.168.1.237', '127.0.0.1', '0.0.0.0']
import joystick_gremlin
from PySide6 import QtCore, QtGui, QtQml, QtQuick, QtTest
app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
win = app.main_window
from gremlin import osc_device_file as f
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

def shown(item):
    # Visible and inside the window (not in a hidden tab).
    return item.isVisible() and item.width() > 0 and item.height() > 0

def named(window, name):
    for item in walk(window.contentItem()):
        if item.objectName() == name and shown(item):
            return item
    return None

def click(window, item):
    centre = item.mapToScene(QtCore.QPointF(item.width() / 2, item.height() / 2))
    QtTest.QTest.mouseClick(window, QtCore.Qt.MouseButton.LeftButton,
                            QtCore.Qt.KeyboardModifier.NoModifier, centre.toPoint())
    app.processEvents()

def text_of(window, name):
    item = named(window, name)
    return None if item is None else item.property("text")

# A target already named "companion" on another port.
f.write_targets(f.read_targets() + [{"id": f.new_id(), "name": "companion",
    "host": "10.0.0.9", "port": 9999}], "test")

guid = str(ids.OSC).upper()
run('_root.openConfigureModule("source", _root._cardForGuid("%s"))' % guid)
setup = None
def find_setup():
    global setup
    for w in app.topLevelWindows():
        if w is not win and w.isVisible() and isinstance(w, QtQuick.QQuickWindow) \
                and named(w, "oscServerHost") is not None:
            setup = w
            return True
    return False
out["opened"] = wait_for(find_setup)
if setup is not None:
    w = setup
    w.resize(1000, 700)
    wait_for(lambda: False, 300)
    w.requestActivate()
    wait_for(lambda: w.isActive(), 2000)

    # Server is open first; the addresses never list 0.0.0.0.
    out["addresses"] = [it.property("text") for it in walk(w.contentItem())
                        if it.objectName().startswith("oscPcAddress") and shown(it)]

    # Each tab by a real click: its own controls show, the others' hide.
    marks = {"Server": "oscServerHost", "Output": "oscTargetNameField",
             "Feedback": "oscFeedbackSection", "Discovery": "oscAnnounce"}
    out["tabs"] = {}
    for tab in ("Output", "Feedback", "Discovery", "Server"):
        bar = named(w, "oscTab" + tab)
        if bar is None:
            out["tabs"][tab] = None
            continue
        click(w, bar)
        wait_for(lambda: named(w, marks[tab]) is not None, 1000)
        out["tabs"][tab] = sorted(
            t for t, m in marks.items() if named(w, m) is not None)

    # Each tab's page scrolls on its own.
    pages = {"Server": "oscServerSection", "Output": "oscOutputTab",
             "Feedback": "oscFeedbackPage", "Discovery": "oscDiscoveryTab"}
    out["flick"] = {}
    for tab, page in pages.items():
        bar = named(w, "oscTab" + tab)
        if bar is not None:
            click(w, bar)
        item = named(w, page)
        out["flick"][tab] = item is not None and item.inherits("QQuickFlickable")

    # The tabs take the window down to the buttons; nothing of the Undo bar
    # sits inside a button.
    hist = named(w, "moduleHistory")
    undo = named(w, "moduleUndoBar")
    out["undo-in-button"] = (hist is not None and undo is not None
                             and undo in walk(hist))
    tabs = named(w, "oscSetupLoader")
    if hist is not None and tabs is not None:
        bottom = hist.mapToScene(QtCore.QPointF(0, hist.height())).y()
        out["gap-below-buttons"] = w.height() - bottom
        out["tabs-share"] = tabs.height() / w.height()

    # Add Companion (Output tab): the "companion" target is pointed back at
    # Companion, then a second click changes nothing more.
    bar = named(w, "oscTabOutput")
    if bar is not None:
        click(w, bar)
    add = named(w, "oscAddCompanion")
    out["add-shown"] = add is not None
    if add is not None:
        click(w, add)
        out["after-add"] = [[t["name"], t["host"], t["port"]] for t in f.read_targets()]
        out["message"] = text_of(w, "oscServerMessage")
        # Removed, then added again: a new target.
        f.write_targets(
            [t for t in f.read_targets() if t["name"] != "Companion"], "test")
        wait_for(lambda: False, 200)
        click(w, named(w, "oscAddCompanion"))
        out["after-readd"] = [
            [t["name"], t["host"], t["port"]] for t in f.read_targets()]
        out["rows"] = [text_of(w, "oscTargetName%d" % i) for i in range(4)]
    setup.close()
    app.processEvents()

print('RESULT ' + json.dumps(out), flush=True)
os._exit(0)  # threads started by the app would keep it alive
"""


@pytest.fixture(scope="module")
def result(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home")
    (home / "Gremlin Platforms").mkdir()
    script = home / "osc_tabs.py"
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


def test_each_tab_opens_by_a_click(result: dict) -> None:
    assert result["opened"] is True, result
    assert result["tabs"] == {
        "Output": ["Output"],
        "Feedback": ["Feedback"],
        "Discovery": ["Discovery"],
        "Server": ["Server"],
    }


def test_each_tab_scrolls_on_its_own(result: dict) -> None:
    assert result["flick"] == {
        "Server": True, "Output": True, "Feedback": True, "Discovery": True,
    }


def test_page_fills_the_window_and_no_undo_bar_behind_the_buttons(result: dict) -> None:
    assert result["undo-in-button"] is False
    # The window's margin only (dp 12), not an empty band.
    assert result["gap-below-buttons"] < 30, result
    assert result["tabs-share"] > 0.4, result


def test_this_pcs_addresses_leave_out_all_addresses(result: dict) -> None:
    assert result["addresses"] == ["192.168.1.237:8001"]


def test_add_companion_adds_or_points_back_the_target(result: dict) -> None:
    assert result["add-shown"] is True
    after = result["after-add"]
    assert ["Companion", "127.0.0.1", 12321] in after
    assert [t for t in after if t[0].casefold() == "companion"] == [
        ["Companion", "127.0.0.1", 12321]
    ]
    assert "Settings › OSC › turn on OSC Listener" in result["message"]
    assert result["after-readd"][-1] == ["Companion", "127.0.0.1", 12321]
    assert "Companion" in result["rows"]
