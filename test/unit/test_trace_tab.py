# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Live Log Reader › Trace (D-01-TRACE): the whole program off-screen with a
fresh user folder and the fake hardware. The Trace tab opens by a click, a
device is ticked by a click, Tracing is turned on by a click; then tracing is
on, red debug mode shows, Debug › Tracing is checked, and it all stays on
when the window closes. trace lines show in the tab, and Save Diagnostics
puts trace.log in its zip. No QML warnings from the new files."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

_ROOT = pathlib.Path(__file__).parents[2]

_CODE = r"""
import json, os, sys, zipfile
sys.path.insert(0, '.')
import importlib.util
spec = importlib.util.spec_from_file_location('fake_hardware', 'test/fake_hardware.py')
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake_hardware.install()

import gremlin.ui.update_model as um
um.UpdateModel.startup = lambda self, *a, **k: None
import joystick_gremlin
from PySide6 import QtCore, QtGui, QtQml, QtQuick, QtTest
app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
win = app.main_window
from gremlin import trace

out = {"on-at-start": trace.enabled()}

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

def named(window, name, prefix=False):
    for item in walk(window.contentItem()):
        n = item.objectName()
        if (n.startswith(name) if prefix else n == name) and shown(item):
            return item
    return None

def click(window, item):
    centre = item.mapToScene(QtCore.QPointF(item.width() / 2, item.height() / 2))
    QtTest.QTest.mouseClick(window, QtCore.Qt.MouseButton.LeftButton,
                            QtCore.Qt.KeyboardModifier.NoModifier, centre.toPoint())
    app.processEvents()

def menu_checked():
    for obj in win.findChildren(QtCore.QObject):
        if obj.property("command") == "debug.tracing":
            QtCore.QMetaObject.invokeMethod(obj, "refresh")
            return bool(obj.property("checked"))
    return None

def debug_frame_shown():
    frame = win.contentItem().findChild(QtQuick.QQuickItem, "gremlinDebugFrame")
    return frame is not None and frame.isVisible()

run('_root.openTool("DialogLiveLog.qml")')
box = {}
def find_reader():
    for w in app.topLevelWindows():
        if w is not win and w.isVisible() and isinstance(w, QtQuick.QQuickWindow) \
                and named(w, "traceTab") is not None:
            box["w"] = w
            return True
    return False
out["opened"] = wait_for(find_reader)
if out["opened"]:
    w = box["w"]
    w.resize(1200, 760)
    wait_for(lambda: False, 300)
    click(w, named(w, "traceTab"))
    out["tree-shown"] = wait_for(lambda: named(w, "traceTree") is not None, 2000)
    tick = None
    wait_for(lambda: named(w, "traceTick_device_", prefix=True) is not None, 2000)
    tick = named(w, "traceTick_device_", prefix=True)
    out["device-tick"] = tick.objectName() if tick is not None else None
    if tick is not None:
        click(w, tick)
        wait_for(lambda: False, 300)
    uid = next(iter(trace.ticked_devices()), None)
    out["ticked"] = uid is not None and trace.ticked(uid, "axis", 1)
    out["status-ticked"] = named(w, "traceStatusTicked").property("text")
    # The device opens to its controls by a click on its name.
    row = named(w, "traceRow_device_", prefix=True)
    if row is not None:
        name = row.objectName()[len("traceRow_device_"):]
        label = [i for i in walk(row) if i.property("text") == name]
        if label:
            click(w, label[0])
            wait_for(lambda: named(w, "traceTick_control_Axis 1") is not None, 1000)
    out["control-row"] = named(w, "traceTick_control_Axis 1") is not None

    out["frame-before"] = debug_frame_shown()
    click(w, named(w, "traceSwitch"))
    wait_for(lambda: trace.enabled(), 2000)
    out["on"] = trace.enabled()
    from gremlin.ui import debug_mode
    out["debug-mode"] = debug_mode.is_active()
    wait_for(debug_frame_shown, 2000)
    out["frame-on"] = debug_frame_shown()
    out["menu-checked"] = menu_checked()
    wait_for(lambda: bool(named(w, "traceSince").property("text")), 2000)
    out["since"] = named(w, "traceSince").property("text")

    trace.event("Probe line from the test")
    lines = named(w, "traceLines")
    def has_line():
        model = lines.property("model")
        rows = [model.data(model.index(i, 0), QtCore.Qt.ItemDataRole.UserRole + 4)
                for i in range(model.rowCount())]
        return "Probe line from the test" in rows
    out["line-shown"] = wait_for(has_line, 2000)
    out["status-lines"] = named(w, "traceStatusLines").property("text")

    w.close()
    wait_for(lambda: False, 400)
    out["on-after-close"] = trace.enabled()
    out["menu-after-close"] = menu_checked()
    out["frame-after-close"] = debug_frame_shown()

    from gremlin import diagnostics
    dest = os.path.join(os.environ["USERPROFILE"], "diag.zip")
    diagnostics.write_zip(diagnostics.collect(False), dest)
    with zipfile.ZipFile(dest) as zf:
        out["zip"] = sorted(zf.namelist())
        name = next((n for n in zf.namelist() if n.endswith("trace.log")), None)
        out["zip-trace-has-probe"] = name is not None and \
            "Probe line from the test" in zf.read(name).decode("utf-8")

    # Debug › Tracing turns it off.
    for obj in win.findChildren(QtCore.QObject):
        if obj.property("command") == "debug.tracing":
            obj.triggered.emit()
            break
    wait_for(lambda: not trace.enabled(), 1000)
    out["off-by-menu"] = not trace.enabled()

    # Grab of the tab for the lead (off-screen), when asked.
    shot = os.environ.get("TRACE_SHOT")
    if shot:
        trace.set_enabled(True)
        trace.warn(trace.OUT_OF_STEP, "pJoy Pro Axis 1",
                   "stick reads -0.02 (polled), vJoy 1 X shows -0.61")
        run('_root.openTool("DialogLiveLog.qml")')
        wait_for(find_reader)
        w = box["w"]
        w.resize(1200, 760)
        click(w, named(w, "traceTab"))
        wait_for(lambda: False, 800)
        w.grabWindow().save(shot)

print('RESULT ' + json.dumps(out), flush=True)
os._exit(0)  # threads started by the app would keep it alive
"""


@pytest.fixture(scope="module")
def result(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home")
    (home / "Gremlin Platforms").mkdir()
    script = home / "trace_tab.py"
    script.write_text(_CODE, encoding="utf-8")
    env = dict(
        os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen",
        GREMLIN_OFFLINE="1",
        QT_LOGGING_RULES="qt.qml.binding.removal.info=true",
    )
    done = subprocess.run(
        [sys.executable, str(script)], cwd=_ROOT, env=env,
        capture_output=True, text=True, timeout=150,
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, done.stdout[-2000:] + done.stderr[-3000:]
    found = json.loads(lines[-1][len("RESULT "):])
    qt_log = home / "Gremlin Platforms" / "logs" / "qt.log"
    logged = qt_log.read_text("utf-8", "replace") if qt_log.is_file() else ""
    found["stderr"] = done.stdout + done.stderr + logged
    return found


def test_tracing_is_off_at_start(result: dict) -> None:
    assert result["on-at-start"] is False


def test_trace_tab_opens_and_a_device_is_ticked_by_a_click(result: dict) -> None:
    assert result["opened"] is True, result
    assert result["tree-shown"] is True, result
    assert result["device-tick"], result
    assert result["ticked"] is True, result
    assert result["status-ticked"].startswith("<b>1</b> device"), result
    assert result["control-row"] is True, result


def test_switch_turns_on_tracing_red_debug_mode_and_menu_check(result: dict) -> None:
    assert result["frame-before"] is False, result
    assert result["on"] is True, result
    assert result["debug-mode"] is True
    assert result["frame-on"] is True
    assert result["menu-checked"] is True
    assert result["since"].startswith("since "), result


def test_tracing_keeps_running_when_the_window_closes(result: dict) -> None:
    assert result["on-after-close"] is True
    assert result["menu-after-close"] is True
    assert result["frame-after-close"] is True


def test_trace_lines_show_in_the_tab(result: dict) -> None:
    assert result["line-shown"] is True, result
    assert "lines" in result["status-lines"]


def test_save_diagnostics_has_trace_log(result: dict) -> None:
    assert "logs/trace.log" in result["zip"], result["zip"]
    assert result["zip-trace-has-probe"] is True


def test_debug_menu_tracing_turns_it_off(result: dict) -> None:
    assert result["off-by-menu"] is True


def test_no_qml_warnings_from_the_trace_tab(result: dict) -> None:
    bad = [
        ln for ln in result["stderr"].splitlines()
        if "LiveLogTrace.qml" in ln or "DialogLiveLog.qml" in ln
        or "main_commands.js" in ln or "trace_model" in ln
    ]
    assert bad == [], "\n".join(bad)
