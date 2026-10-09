# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""OSC's server settings live in OSC's own file and are edited in OSC's
Module Setup "Server" section (D-09-OSC-FILE point 4): typed there, they
are checked and saved to the file; Options only points there; the Listening
box shows the file's values. The whole program runs off-screen in its own
process with a fresh user folder."""

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
    for item in walk(window.contentItem()):
        if item.objectName() == name and item.isVisible():
            return item
    return None

def type_into(window, field, text):
    field.forceActiveFocus()
    QtCore.QMetaObject.invokeMethod(field, "selectAll")
    if not text:
        QtTest.QTest.keyClick(window, QtCore.Qt.Key.Key_Delete)
    for char in text:
        QtTest.QTest.keyClick(window, char)
    QtTest.QTest.keyClick(window, QtCore.Qt.Key.Key_Tab)
    app.processEvents()

def click(window, item):
    centre = item.mapToScene(QtCore.QPointF(item.width() / 2, item.height() / 2))
    QtTest.QTest.mouseClick(window, QtCore.Qt.MouseButton.LeftButton,
                            QtCore.Qt.KeyboardModifier.NoModifier, centre.toPoint())
    app.processEvents()

out["before"] = osc_device_file.read_server()
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
    type_into(setup, named(setup, "oscServerHost"), "bad host!")
    out["bad-host-message"] = named(setup, "oscServerMessage").property("text")
    out["after-bad-host"] = osc_device_file.read_server()["host"]
    type_into(setup, named(setup, "oscServerHost"), "studio-pc")
    type_into(setup, named(setup, "oscServerPort"), "9123")
    type_into(setup, named(setup, "oscServerDelay"), "400")
    click(setup, named(setup, "oscServerEnabled"))
    click(setup, named(setup, "oscServerPadArgs"))
    out["saved"] = osc_device_file.read_server()
    type_into(setup, named(setup, "oscServerHost"), "")
    out["saved-blank-host"] = osc_device_file.read_server()["host"]
    setup.close()
    app.processEvents()

from gremlin.ui.osc_settings_info import OscSettingsInfo
out["summary"] = OscSettingsInfo().summary()

from gremlin.ui import option
osc = [groups for title, groups in option.main_layout() if title == "OSC"]
out["options-osc"] = [
    [g] + list(k) for g, keys in (osc[0] if osc else []) for k in keys
]
print('RESULT ' + json.dumps(out), flush=True)
os._exit(0)  # threads started by the app would keep it alive
"""


@pytest.fixture(scope="module")
def result(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home")
    (home / "Gremlin Platforms").mkdir()
    script = home / "osc_options.py"
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


def test_module_setup_server_section_saves_to_osc_file(result: dict) -> None:
    assert result["section"] is True, result
    # A host that is neither an IP address nor a computer name is refused.
    assert "not an IP address or a computer name" in result["bad-host-message"]
    assert result["after-bad-host"] == result["before"]["host"]
    saved = result["saved"]
    assert saved["host"] == "studio-pc"
    assert saved["port"] == 9123
    assert saved["autorelease_delay_ms"] == 400
    assert saved["enabled"] is (not result["before"]["enabled"])
    assert saved["pad_args"] is (not result["before"]["pad_args"])
    # Blank: all addresses on this PC.
    assert result["saved-blank-host"] == ""


def test_options_no_longer_edits_osc(result: dict) -> None:
    # One line on an untitled card (not under "Other"): see Module Setup.
    assert result["options-osc"] == [["", "osc", "connection", "module-setup"]]


def test_listening_info_shows_the_file(result: dict) -> None:
    summary = result["summary"]
    assert "Input port: 9123" in summary
    assert "Input host: All addresses on this PC" in summary


def test_osc_friendly_names_are_kept_by_uid() -> None:
    """Module Setup's OSC rows come from the shared list; a friendly name is
    saved under the input's uid, so a renumbered input keeps its name and
    another input given the old number doesn't take it (D-09-OSC-FILE 2)."""
    import json as _json

    from gremlin.modules import store
    from gremlin.osc import OscDevice
    from gremlin.types import InputType
    from gremlin.ui import module_model

    rows = OscDevice().rows
    rows.reset()
    try:
        first = rows.create(InputType.JoystickButton, "/test/first")
        setup = module_model.DriverInputModel()
        setup.loadDevice(module_model.OSC_GUID, "OSC")
        assert setup.isOsc
        assert [setup._rows[i]["uid"] for i in range(setup.rowCount())] == [first.uid]
        setup.setFriendly(0, "Fire")
        assert setup.saveClaim("OSC", "source")
        saved = store.path_for("OSC", module_model.OSC_GUID)
        doc = _json.loads(saved.read_text("utf-8"))
        assert doc["claim"]["friendly"] == {f"osc:{first.uid}": "Fire"}

        # The input gone and another made with its number: no name.
        rows.delete(first.uid)
        second = rows.create(InputType.JoystickButton, "/test/second")
        assert second.input_id == first.input_id
        setup.loadDevice(module_model.OSC_GUID, "OSC")
        assert setup._rows[0]["friendly"] == ""
        setup.deleteLater()
    finally:
        rows.reset()
