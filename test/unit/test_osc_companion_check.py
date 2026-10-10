# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Companion setup check (09 S144, OX4): each line OK and failing, the port
holder named, nothing written; and the Output tab's button shows the lines.
Fake runtime and holder: no network."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

from gremlin import osc_companion_check as cc
from gremlin import osc_device_file as f

_ROOT = pathlib.Path(__file__).parents[2]

GOOD_SERVER = {
    "enabled": True, "host": "", "port": 8001,
    "output_enabled": True, "feedback_enabled": True,
}
COMPANION = {"id": "c", "name": "Companion", "host": "127.0.0.1", "port": 12321}


def _run(
    server: dict | None = None,
    targets: list[dict] | None = None,
    feedback: list[dict] | None = None,
    is_open: bool = True,
    held: tuple[str, int] | None = None,
) -> list[dict]:
    return cc.check(
        server=dict(GOOD_SERVER, **(server or {})),
        targets=[COMPANION] if targets is None else targets,
        feedback=[] if feedback is None else feedback,
        is_open=lambda: is_open,
        holder=lambda port, host: held,
    )


def _faults(lines: list[dict]) -> list[dict]:
    return [ln for ln in lines if not ln["ok"]]


def test_all_good_every_line_ok() -> None:
    lines = _run(feedback=[{"id": "r"}])
    assert lines and not _faults(lines)
    assert not [ln for ln in lines if ln["warn"]]
    text = " ".join(ln["label"] for ln in lines)
    assert "OSC is on" in text and "Port 8001 is open" in text
    assert "OSC output is on" in text and "Feedback is on" in text
    assert "12321" in text
    assert all(set(ln) == {"label", "ok", "warn", "fix"} for ln in lines)


def test_osc_off_fails_with_the_fix() -> None:
    (bad,) = _faults(_run(server={"enabled": False}))
    assert bad["label"] == "OSC is off."
    assert "Listen for OSC messages" in bad["fix"]


def test_port_held_by_another_program_is_named() -> None:
    (bad,) = _faults(_run(is_open=False, held=("python.exe", 4242)))
    assert "Port 8001 is in use by python.exe (PID 4242)" in bad["label"]
    assert bad["fix"]


def test_port_closed_and_free_is_ok() -> None:
    lines = _run(is_open=False, held=None)
    assert not _faults(lines)
    assert any("Port 8001 is free" in ln["label"] for ln in lines)


def test_output_off_fails() -> None:
    (bad,) = _faults(_run(server={"output_enabled": False}))
    assert bad["label"] == "OSC output is off."
    assert "OSC output" in bad["fix"]


def test_no_companion_target_fails_and_skips_the_port_line() -> None:
    lines = _run(targets=[{"id": "d", "name": "Default",
                           "host": "127.0.0.1", "port": 8000}])
    (bad,) = _faults(lines)
    assert bad["label"] == "There is no Companion target."
    assert "Add Companion" in bad["fix"]
    assert not any("listen port" in ln["label"] for ln in lines)


def test_other_port_is_a_warning_not_a_fault() -> None:
    lines = _run(targets=[dict(COMPANION, port=9999)])
    assert not _faults(lines)
    (warn,) = [ln for ln in lines if ln["warn"]]
    assert "9999" in warn["label"] and "12321" in warn["label"]
    assert "Companion's OSC listen port" in warn["fix"]
    assert "12321 by default" in warn["fix"]


def test_feedback_rows_with_feedback_off_fail() -> None:
    (bad,) = _faults(_run(server={"feedback_enabled": False},
                          feedback=[{"id": "r"}]))
    assert bad["label"].startswith("Feedback is off")
    assert "Send feedback to OSC devices" in bad["fix"]


def test_no_feedback_rows_no_feedback_line() -> None:
    lines = _run(server={"feedback_enabled": False})
    assert not _faults(lines)
    assert not any("Feedback" in ln["label"] for ln in lines)


def test_reads_the_file_and_writes_nothing(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(f, "path", lambda: tmp_path / "osc.json")
    lines = cc.check(is_open=lambda: True, holder=lambda p, h: None)
    # No file: defaults (OSC on, output on), the Default target, no Companion.
    assert [ln["label"] for ln in _faults(lines)] == [
        "There is no Companion target."]
    assert not (tmp_path / "osc.json").exists()


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
gosc.port_holder = lambda port, host='': None
import gremlin.osc_companion_check  # registers OscCompanionCheck
import joystick_gremlin
from PySide6 import QtCore, QtQml, QtQuick, QtTest
app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
win = app.main_window
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

guid = str(ids.OSC).upper()
run('_root.openConfigureModule("source", _root._cardForGuid("%s"))' % guid)
setup = {}
def find_setup():
    for w in app.topLevelWindows():
        if w is not win and w.isVisible() and isinstance(w, QtQuick.QQuickWindow) \
                and named(w, "oscServerHost") is not None:
            setup["w"] = w
            return True
    return False
out["opened"] = wait_for(find_setup)
if setup:
    w = setup["w"]
    w.resize(1000, 700)
    wait_for(lambda: False, 300)
    w.requestActivate()
    wait_for(lambda: w.isActive(), 2000)
    click(w, named(w, "oscTabOutput"))
    wait_for(lambda: named(w, "oscCheckCompanion") is not None, 1000)
    wait_for(lambda: False, 300)  # the tab's layout settles
    button = named(w, "oscCheckCompanion")
    out["button"] = button is not None
    if button is not None:
        click(w, button)
        wait_for(lambda: named(w, "oscCheckText0") is not None, 1000)
        out["lines"] = [
            [named(w, "oscCheckMark%d" % i).property("text"),
             named(w, "oscCheckText%d" % i).property("text")]
            for i in range(10) if named(w, "oscCheckText%d" % i) is not None]
    w.close()
    app.processEvents()

print('RESULT ' + json.dumps(out), flush=True)
os._exit(0)
"""


@pytest.fixture(scope="module")
def shown(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home")
    (home / "Gremlin Platforms").mkdir()
    script = home / "osc_check.py"
    script.write_text(_CODE, encoding="utf-8")
    env = dict(os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen",
               GREMLIN_OFFLINE="1")
    done = subprocess.run(
        [sys.executable, str(script)], cwd=_ROOT, env=env,
        capture_output=True, text=True, timeout=150,
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, done.stdout[-2000:] + done.stderr[-3000:]
    return json.loads(lines[-1][len("RESULT "):])


def test_output_tab_button_shows_the_lines(shown: dict) -> None:
    assert shown.get("opened"), shown
    assert shown.get("button"), shown
    lines = shown.get("lines") or []
    # A fresh file: OSC on, port free, output on, no Companion target.
    assert [m for m, _ in lines] == ["OK", "OK", "OK", "Fix"], lines
    assert lines[-1][1] == "There is no Companion target. Click Add Companion."
