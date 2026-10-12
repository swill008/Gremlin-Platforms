# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Xbox output page (its Output View) shows the ViGEmBus driver only
as one red line when the driver is missing, "ViGEmBus driver not found: the
Xbox pads can't be sent.", with a link "Open Xbox Setup" (D-XBOX-PADS): the
full check (XboxDriverCheck: version, Get ViGEmBus, Test ViGEmBus) moved to
Xbox Setup. The line shows even when nothing is mapped to Xbox yet; then the
page has no pad sections, no Find bar and no list Appearance button. The
Output View's own Appearance button stays hidden on the Xbox tab (vJoy
outputs keep theirs).

XboxDriverStatus (the check's wording) is tested here too. The page is
opened off-screen in its own process with a fresh profile (no Map to Xbox
actions), and the driver is faked so the result doesn't depend on this PC.
"""

from __future__ import annotations

import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)

sys.path.append(".")

import json
import os
import pathlib

import pytest

from gremlin.modules import output
from gremlin.ui import xbox_device_model
from gremlin.ui.xbox_device_model import XboxDriverStatus

_ROOT = pathlib.Path(__file__).parents[2]

_CODE = """
import json, os, sys
sys.path.insert(0, '.')
# Before the app starts: it changes the working folder.
PAGE = os.path.abspath('qml/XboxDevice.qml')
import importlib.util
spec = importlib.util.spec_from_file_location('fake_hardware', 'test/fake_hardware.py')
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake_hardware.install()
from gremlin.modules import output
output.xbox_driver_installed = lambda: False
output.xbox_driver_version = lambda: ''
output.xbox_available = lambda: False
output.xbox_error = lambda: ''
import gremlin.ui.update_model as um
um.UpdateModel.startup = lambda self, *a, **k: None
import joystick_gremlin
from PySide6 import QtQml, QtQuick, QtTest
app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
win = app.main_window

def walk(item):
    yield item
    for c in item.childItems():
        yield from walk(c)

def top(item):
    return round(item.mapToScene(item.boundingRect().topLeft()).y()) if item else -1

def shown_texts(items):
    return [i.property('text') for i in items
            if i.isVisible() and isinstance(i.property('text'), str)]

out = {}
# The Xbox output page: one check above its pads and rows.
from PySide6 import QtCore
host = QtQuick.QQuickWindow()
host.resize(900, 600)
comp = QtQml.QQmlComponent(app.engine, QtCore.QUrl.fromLocalFile(PAGE))
page = comp.create()
assert page is not None, comp.errorString()
page.setParentItem(host.contentItem())
page.setWidth(900)
page.setHeight(600)
host.show()
QtTest.QTest.qWait(400)
items = list(walk(page))
line = next((i for i in items if i.objectName() == 'xboxDriverMissing'), None)
link = next((i for i in items if i.objectName() == 'xboxOpenSetupLink'), None)
out['line'] = line is not None and line.isVisible() and line.height() > 0
out['line-text'] = line.property('text') if line else ''
out['link'] = link.property('text') if link and link.isVisible() else ''
out['line-top'] = top(line)
# The full check is Xbox Setup's now.
out['page-rows'] = len([i for i in items if i.objectName() == 'xboxDriverRow'])
out['texts'] = shown_texts(items)
find = next((i for i in items if i.objectName() == 'xboxOutputFindBar'), None)
out['find-shown'] = bool(find and find.isVisible())
# Nothing bound: no list Appearance on the page bar.
out['list-appearance'] = page.property('pageBar') is not None
appear = next((i for i in items if i.objectName() == 'xboxOutputAppearance'), None)
out['list-appearance-key'] = appear.property('pageKey') if appear else ''

# The header's Appearance button: none on the Xbox page, there on vJoy's.
def appearance_shown(tab):
    ui = QtQml.QQmlExpression(QtQml.qmlContext(win), win, 'uiState').evaluate()[0]
    ui.setCurrentRoom('configuration')
    ui.setCurrentTab(tab)
    dest = '_root.configDirection = "dest"'
    QtQml.QQmlExpression(QtQml.qmlContext(win), win, dest).evaluate()
    QtTest.QTest.qWait(300)
    button = win.findChild(QtQuick.QQuickItem, 'outputAppearanceButton')
    return button.property('visible') if button else None

out['appearance-xbox'] = appearance_shown('xbox')
out['appearance-vjoy'] = appearance_shown('physical')
if len(sys.argv) > 2:
    host.grabWindow().save(sys.argv[2])
print('RESULT ' + json.dumps(out), flush=True)
os._exit(0)  # threads started by the app would keep it alive
"""


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home")
    (home / "Gremlin Platforms").mkdir()
    script = home / "xbox_driver.py"
    script.write_text(_CODE, encoding="utf-8")
    env = dict(os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen",
               HTTPS_PROXY="http://127.0.0.1:9")
    args = [sys.executable, str(script)]
    shot = os.environ.get("GREMLIN_SHOT")
    if shot:
        args += ["", shot + "-page.png"]
    result = proc_tree.run(
        args, cwd=_ROOT, env=env, text=True, timeout=120
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, result.stdout[-1500:] + result.stderr[-1500:]
    return json.loads(lines[0][len("RESULT "):])


def test_one_red_line_with_nothing_mapped(run: dict) -> None:
    assert run["line"] is True
    assert run["line-text"] == (
        "ViGEmBus driver not found: the Xbox pads can't be sent."
    )
    assert run["link"] == "Open Xbox Setup"
    # The full check (Get ViGEmBus, Test ViGEmBus) is in Xbox Setup.
    assert run["page-rows"] == 0
    assert "Get ViGEmBus" not in run["texts"]
    assert "Test ViGEmBus" not in run["texts"]


def test_the_red_line_is_at_the_top(run: dict) -> None:
    assert 0 <= run["line-top"] < 30


def test_nothing_bound_says_so_without_find_or_appearance(run: dict) -> None:
    assert (
        "No Xbox controller has a binding yet. Add a Map to Xbox action on "
        "Device Bindings to see it here."
    ) in run["texts"]
    assert run["find-shown"] is False
    assert run["list-appearance"] is False
    assert run["list-appearance-key"] == "xbox-output"


def test_the_xbox_page_hides_the_output_views_appearance(run: dict) -> None:
    assert run["appearance-xbox"] is False
    assert run["appearance-vjoy"] is True


def _status(
    monkeypatch: pytest.MonkeyPatch, installed: bool, ready: bool, error: str = ""
) -> XboxDriverStatus:
    version = "1.21.442.0" if installed else ""
    monkeypatch.setattr(output, "xbox_driver_installed", lambda: installed)
    monkeypatch.setattr(output, "xbox_driver_version", lambda: version)
    monkeypatch.setattr(output, "xbox_available", lambda: ready)
    monkeypatch.setattr(output, "xbox_error", lambda: error)
    assert xbox_device_model.output is output
    return XboxDriverStatus()


def test_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    s = _status(monkeypatch, True, True)
    assert s.ready is True
    assert s.statusText == "ViGEmBus driver found"
    assert (s.driverVersion, s.hint) == ("1.21.442.0", "")


def test_installed_but_not_running(monkeypatch: pytest.MonkeyPatch) -> None:
    s = _status(monkeypatch, True, False)
    assert s.statusText == "ViGEmBus is installed but not running"
    assert s.driverVersion == "1.21.442.0"
    assert "Restart Windows" in str(s.hint)


def test_a_missing_dll_says_so(monkeypatch: pytest.MonkeyPatch) -> None:
    missing = "ViGEmClient.dll is missing from the program folder"
    s = _status(monkeypatch, True, False, missing)
    assert str(s.statusText).startswith("ViGEmClient.dll is missing")
    assert "Install ViGEmBus" in str(s.hint)


def test_checked_again_on_reload(monkeypatch: pytest.MonkeyPatch) -> None:
    s = _status(monkeypatch, False, False)
    assert s.statusText == "ViGEmBus is not installed"
    monkeypatch.setattr(output, "xbox_driver_installed", lambda: True)
    monkeypatch.setattr(output, "xbox_available", lambda: True)
    s.reload()
    assert s.ready is True and s.statusText == "ViGEmBus driver found"
