# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""OSC output settings in OSC's Module Setup tabs (Server, Output and
Discovery since D-09-OSC-TABS; D-09-OSC-OUTPUT, D-09-OSC-DISCOVERY): the new
server keys and their defaults, targets (the old output host and port
become "Default"), feedback rows in OSC's file, OSC output and Reply to
sender, the targets list (add, edit, remove with the shared question),
this PC's addresses with Copy, and
the discovery switches with the found list's "Add as Target". The whole
program runs off-screen in its own process with a fresh user folder; a
stand-in discovery module (no network) gives one found device."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

_ROOT = pathlib.Path(__file__).parents[2]

_CODE = r"""
import json, os, sys, types
sys.path.insert(0, '.')
import importlib.util
spec = importlib.util.spec_from_file_location('fake_hardware', 'test/fake_hardware.py')
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake_hardware.install()

calls = []
fake = types.ModuleType('gremlin.osc_discovery')
fake.available = lambda: True
fake.start = lambda *a, **k: None
fake.shutdown = lambda *a, **k: None
fake.service_name = lambda: 'Gremlin'
fake.set_announce = lambda on, port: calls.append(['announce', on, port])
fake.set_find = lambda on: calls.append(['find', on])
fake.found = lambda: [
    {'name': 'TouchOSC on iPad', 'host': '192.168.1.50', 'port': 9000}]
sys.modules['gremlin.osc_discovery'] = fake
import gremlin
gremlin.osc_discovery = fake

import gremlin.ui.update_model as um
um.UpdateModel.startup = lambda self, *a, **k: None
import joystick_gremlin
from PySide6 import QtCore, QtGui, QtQml, QtQuick, QtTest
app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
win = app.main_window
from gremlin import osc_device_file as f
from gremlin.modules import ids, store

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
    for item in walk(window.contentItem()):
        if item.objectName() == name and item.isVisible():
            return item
    return None

def type_into(window, field, text):
    show_item(field)
    field.forceActiveFocus()
    QtCore.QMetaObject.invokeMethod(field, "selectAll")
    QtTest.QTest.keyClick(window, QtCore.Qt.Key.Key_Delete)
    for char in text:
        QtTest.QTest.keyClick(window, char)
    app.processEvents()

def show_item(item):
    # Scrolls the item into view in the Flickable that holds it.
    parent = item.parentItem()
    while parent is not None:
        if parent.inherits("QQuickFlickable"):
            content = parent.property("contentItem")
            y = item.mapToItem(content, QtCore.QPointF(0, 0)).y()
            top = parent.property("contentY")
            if y < top or y + item.height() > top + parent.height():
                parent.setProperty("contentY", max(0.0, y - 40))
                app.processEvents()
        parent = parent.parentItem()

def click(window, item):
    # A message line that just showed moves the tabs: let the layout settle.
    wait_for(lambda: False, 60)
    show_item(item)
    centre = item.mapToScene(QtCore.QPointF(item.width() / 2, item.height() / 2))
    QtTest.QTest.mouseClick(window, QtCore.Qt.MouseButton.LeftButton,
                            QtCore.Qt.KeyboardModifier.NoModifier, centre.toPoint())
    app.processEvents()

def text_of(window, name):
    item = named(window, name)
    return None if item is None else item.property("text")

def message(window):
    return text_of(window, "oscServerMessage")

# The file API on a file that only has old output settings.
store.write_file(f.path(), json.dumps({"server": {
    "output_host": "10.0.0.7", "output_port": 7001}}).encode("utf-8"))
out["server"] = f.read_server()
out["targets-old-file"] = f.read_targets()
out["feedback-none"] = f.read_feedback()
seen = []
from gremlin.signal import signal
for name in ("oscServerSettingsChanged", "oscFeedbackChanged"):
    sig = getattr(signal, name, None)
    if sig is not None:
        sig.connect(lambda name=name: seen.append(name))
out["fb-written"] = f.write_feedback([{"source": {"kind": "vjoy_axis", "device": 1,
    "input": 2}, "target": "reply", "address": "/fader", "max": "2"}], "test")
out["feedback"] = f.read_feedback()
out["fb-same"] = f.write_feedback(f.read_feedback(), "test")
out["signals"] = list(seen)

guid = str(ids.OSC).upper()
run('_root.openConfigureModule("source", _root._cardForGuid("%s"))' % guid)
setup = None
def find_setup():
    global setup
    for w in app.topLevelWindows():
        if w is not win and w.isVisible() and isinstance(w, QtQuick.QQuickWindow) \
                and named(w, "oscServerSection") is not None:
            setup = w
            return True
    return False
out["section"] = wait_for(find_setup)
if setup is not None:
    setup.requestActivate()
    wait_for(lambda: setup.isActive(), 2000)
    w = setup
    # Server tab (open first): this PC's addresses with Copy.
    out["pc-address"] = text_of(w, "oscPcAddress0")
    click(w, named(w, "oscCopyAddress0"))
    out["clipboard"] = QtGui.QGuiApplication.clipboard().text()
    # Output tab: switches and targets.
    click(w, named(w, "oscTabOutput"))
    out["first-target"] = [text_of(w, "oscTargetName0"),
                           text_of(w, "oscTargetAddress0")]
    out["old-output-fields"] = named(w, "oscServerOutputHost") is not None

    click(w, named(w, "oscOutputEnabled"))
    click(w, named(w, "oscReplyToSender"))
    server = f.read_server()
    out["output-off"] = [server["output_enabled"], server["reply_to_sender"]]

    # Add: a bad host is refused, then a good one is added.
    type_into(w, named(w, "oscTargetNameField"), "Mixer")
    type_into(w, named(w, "oscTargetHostField"), "bad host!")
    type_into(w, named(w, "oscTargetPortField"), "9001")
    click(w, named(w, "oscTargetSave"))
    out["bad-host"] = [message(w), len(f.read_targets())]
    type_into(w, named(w, "oscTargetHostField"), "192.168.1.20")
    click(w, named(w, "oscTargetSave"))
    out["added"] = [[t["name"], t["host"], t["port"]] for t in f.read_targets()]
    # Same name twice is refused.
    type_into(w, named(w, "oscTargetNameField"), "mixer")
    type_into(w, named(w, "oscTargetHostField"), "10.1.1.1")
    click(w, named(w, "oscTargetSave"))
    out["dup-name"] = [message(w), len(f.read_targets())]

    # Edit the second target.
    click(w, named(w, "oscTargetEdit1"))
    out["edit-filled"] = text_of(w, "oscTargetNameField")
    type_into(w, named(w, "oscTargetPortField"), "9555")
    click(w, named(w, "oscTargetSave"))
    out["edited"] = [[t["name"], t["port"]] for t in f.read_targets()]

    # Remove asks the shared question; Cancel keeps it, Remove takes it away.
    def question_button(name):
        for item in walk(w.contentItem()):
            if item.objectName() == name and item.isVisible():
                return item
        return None
    click(w, named(w, "oscTargetRemove1"))
    wait_for(lambda: question_button("confirmCancel") is not None, 2000)
    out["question"] = text_of(w, "confirmTitle")
    click(w, question_button("confirmCancel"))
    out["after-cancel"] = len(f.read_targets())
    click(w, named(w, "oscTargetRemove1"))
    wait_for(lambda: question_button("confirmAction") is not None, 2000)
    click(w, question_button("confirmAction"))
    out["after-remove"] = [t["name"] for t in f.read_targets()]

    # Discovery: both off at first; switching them on saves and applies.
    click(w, named(w, "oscTabDiscovery"))
    out["discovery-defaults"] = [named(w, "oscAnnounce").property("checked"),
                                 named(w, "oscFindDevices").property("checked")]
    out["found-hidden"] = named(w, "oscFoundAdd0") is None
    click(w, named(w, "oscAnnounce"))
    click(w, named(w, "oscFindDevices"))
    wait_for(lambda: named(w, "oscFoundAdd0") is not None, 2000)
    server = f.read_server()
    out["discovery-saved"] = [server["announce"], server["find_devices"]]
    out["calls"] = calls
    out["found-name"] = text_of(w, "oscFoundName0")
    click(w, named(w, "oscFoundAdd0"))
    last = f.read_targets()[-1]
    out["found-added"] = [last["name"], last["host"], last["port"]]
    setup.close()
    app.processEvents()

print('RESULT ' + json.dumps(out), flush=True)
os._exit(0)  # threads started by the app would keep it alive
"""


@pytest.fixture(scope="module")
def result(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home")
    (home / "Gremlin Platforms").mkdir()
    script = home / "osc_targets.py"
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


def test_new_server_keys_have_their_defaults(result: dict) -> None:
    server = result["server"]
    assert server["output_enabled"] is True
    assert server["reply_to_sender"] is True
    assert server["announce"] is False
    assert server["find_devices"] is False
    assert server["feedback_enabled"] is True
    assert server["resend_run"] and server["resend_mode"] and server["resend_profile"]
    assert server["sync_enabled"] is True
    assert server["sync_address"] == "/gremlin/sync"
    assert server["feedback_rate"] == 50


def test_old_output_settings_become_the_default_target(result: dict) -> None:
    targets = result["targets-old-file"]
    assert len(targets) == 1
    assert targets[0]["name"] == "Default"
    assert (targets[0]["host"], targets[0]["port"]) == ("10.0.0.7", 7001)
    assert targets[0]["id"]


def test_feedback_rows_are_kept_in_the_file(result: dict) -> None:
    assert result["feedback-none"] == []
    assert result["fb-written"] is True
    row = result["feedback"][0]
    assert row["source"] == {"kind": "vjoy_axis", "device": 1, "input": 2}
    assert row["address"] == "/fader"
    assert row["enabled"] is True
    assert (row["min"], row["max"], row["type"], row["target"]) == (
        0.0, 2.0, "auto", "reply")
    assert row["id"]
    assert result["fb-same"] is False
    assert result["signals"] == ["oscFeedbackChanged"]


def test_section_shows_targets_and_this_pcs_addresses(result: dict) -> None:
    assert result["section"], result
    assert result["first-target"] == ["Default", "10.0.0.7:7001"]
    assert result["old-output-fields"] is False
    assert result["pc-address"].endswith(":8001")
    assert result["clipboard"] == result["pc-address"]


def test_output_and_reply_switches_save(result: dict) -> None:
    assert result["output-off"] == [False, False]


def test_targets_add_edit_remove(result: dict) -> None:
    assert "not an IP address" in result["bad-host"][0]
    assert result["bad-host"][1] == 1
    assert result["added"] == [["Default", "10.0.0.7", 7001],
                               ["Mixer", "192.168.1.20", 9001]]
    assert "already a target" in result["dup-name"][0]
    assert result["dup-name"][1] == 2
    assert result["edit-filled"] == "Mixer"
    assert result["edited"] == [["Default", 7001], ["Mixer", 9555]]
    assert result["question"] == "Remove target Mixer?"
    assert result["after-cancel"] == 2
    assert result["after-remove"] == ["Default"]


def test_discovery_switches_and_add_as_target(result: dict) -> None:
    assert result["discovery-defaults"] == [False, False]
    assert result["found-hidden"] is True
    assert result["discovery-saved"] == [True, True]
    assert ["announce", True, 8001] in result["calls"]
    assert ["find", True] in result["calls"]
    assert result["found-name"] == "TouchOSC on iPad"
    assert result["found-added"] == ["TouchOSC on iPad", "192.168.1.50", 9000]
