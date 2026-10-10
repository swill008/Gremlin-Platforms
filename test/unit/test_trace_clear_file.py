# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Live Log Reader › Trace (01 S149): Clear Trace File… and the Max size
choice, on the whole program off-screen with a fresh user folder.

Clear Trace File… is off with no trace file; it asks first (01 S140); No
keeps the file; Yes empties trace.log while tracing is on, deletes
trace.log.1, empties the view, and later lines start at the top. Max size
and Axis lines: picked by a click or typed with real keys, saved, applied at
once (the open file's limit; a fast axis's lines per second) and kept over a
restart; out of range or not a number is refused with the reason."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

_ROOT = pathlib.Path(__file__).parents[2]

_START = r"""
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
from PySide6 import QtCore, QtGui, QtQml, QtQuick, QtTest
app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
win = app.main_window
from gremlin import trace
out = {}
"""

_RESTART = _START + r"""
out["max-mb"] = trace.max_mb()
out["axis-rate"] = trace.axis_rate()
print('RESULT ' + json.dumps(out), flush=True)
os._exit(0)
"""

_CODE = _START + r"""
import shiboken6

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

def question(w):
    for q in w.contentItem().findChildren(QtCore.QObject, "confirmDialog"):
        if shiboken6.isValid(q) and q.property("opened"):
            return q
    return None

def answer(w, name):
    q = question(w)
    it = q.findChild(QtQuick.QQuickItem, name)
    click(w, it)
    wait_for(lambda: question(w) is None, 2000)

def shown_lines(w):
    model = named(w, "traceLines").property("model")
    return [model.data(model.index(i, 0), QtCore.Qt.ItemDataRole.UserRole + 4)
            for i in range(model.rowCount())]

def options_open():
    # The panel's content shows only while it is open.
    return named(w, "traceFileDetail") is not None

def open_options():
    # Trace options opens by a real click on Options ▾.
    if not options_open():
        click(w, named(w, "traceOptions"))
        wait_for(options_open, 2000)
    wait_for(lambda: False, 300)

path = trace.file_path()
older = path.with_name(trace.FILE_NAME + ".1")

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
w = box["w"]
w.resize(1300, 760)
wait_for(lambda: False, 300)
click(w, named(w, "traceTab"))
wait_for(lambda: named(w, "traceOptions") is not None, 2000)
open_options()
out["options-open"] = options_open()
button = named(w, "traceClearFile")
out["button"] = button is not None
wait_for(lambda: False, 400)
out["file-before-on"] = path.is_file()
out["enabled-no-file"] = bool(button.property("enabled")) if button else None

click(w, named(w, "traceSwitch"))
wait_for(lambda: trace.enabled(), 2000)
trace.event("Before the clear")
older.write_text("older copy\n", encoding="utf-8")
wait_for(lambda: bool(button.property("enabled")), 2000)
out["enabled-with-file"] = bool(button.property("enabled"))

# No keeps the file.
open_options()
button = named(w, "traceClearFile")
click(w, button)
wait_for(lambda: question(w) is not None, 2000)
q = question(w)
out["question"] = [q.findChild(QtCore.QObject, n).property("text")
                   for n in ("confirmText", "confirmLastLine", "confirmAction")] \
    if q is not None else None
if q is not None:
    answer(w, "confirmCancel")
out["after-no"] = path.read_text("utf-8")
out["older-after-no"] = older.is_file()

# Yes empties it.
open_options()
button = named(w, "traceClearFile")
click(w, button)
wait_for(lambda: question(w) is not None, 2000)
if question(w) is not None:
    answer(w, "confirmAction")
wait_for(lambda: False, 400)
out["after-yes"] = path.read_text("utf-8")
out["older-after-yes"] = older.is_file()
out["view-after-yes"] = shown_lines(w)
out["on-after-yes"] = trace.enabled()
trace.event("After the clear")
wait_for(lambda: False, 300)
out["file-later"] = path.read_text("utf-8")
out["status-file"] = named(w, "traceStatusFile").property("text")

from gremlin import config
cfg = config.Configuration()
Qt = QtCore.Qt

def pick(name, text):
    open_options()
    # Opens the dropdown by its arrow and clicks the item.
    box = named(w, name + "Box")
    click(w, box.property("indicator"))
    def item():
        for it in walk(w.contentItem()):
            if it.property("text") == text and shown(it) and it is not box \
                    and it.metaObject().className().find("Label") < 0 \
                    and it.metaObject().className().find("TextField") < 0:
                return it
        return None
    wait_for(lambda: item() is not None, 2000)
    it = item()
    if it is not None:
        click(w, it)
        wait_for(lambda: False, 300)
    return box.property("editText")

def type_in(name, text):
    open_options()
    # Real keys: into the field, select all, type, Enter.
    box = named(w, name + "Box")
    click(w, box.property("contentItem"))
    QtTest.QTest.keyClick(w, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
    for ch in text:
        QtTest.QTest.keyClick(w, ch)
    QtTest.QTest.keyClick(w, Qt.Key.Key_Return)
    wait_for(lambda: False, 300)
    error = named(w, name + "Error")
    return [box.property("editText"),
            error.property("text") if error is not None else ""]

def handler_mb():
    return trace._handler.maxBytes / (1024 * 1024) if trace._handler else None

# Max size: 25 MB picked, 37 typed, 5000 and abc refused.
out["max-before"] = named(w, "traceMaxSizeBox").property("editText")
out["max-picked"] = pick("traceMaxSize", "25")
out["max-picked-mb"] = [trace.max_mb(), handler_mb(),
                        cfg.value("debug", "trace", "max-mb")]
out["max-typed"] = type_in("traceMaxSize", "37")
out["max-typed-mb"] = [trace.max_mb(), handler_mb(),
                       cfg.value("debug", "trace", "max-mb")]
out["max-5000"] = type_in("traceMaxSize", "5000") + [trace.max_mb(), handler_mb()]
out["max-abc"] = type_in("traceMaxSize", "abc") + [trace.max_mb()]

# Axis lines: a fast-moving axis (every 10 ms) on a ticked device.
uid = trace.ticked_devices()[0] if trace.ticked_devices() else None
if uid is None:
    import uuid as _uuid
    uid = _uuid.UUID("12345678-1234-1234-1234-123456789abc")
    trace.set_device(uid, True)

def axis_lines(seconds):
    trace.clear_view()
    timer = QtCore.QElapsedTimer()
    timer.start()
    v = 0.0
    while timer.elapsed() < seconds * 1000:
        v = -v + 0.01 if v < 0.9 else -0.9
        trace.raw(uid, "axis", 1, v)
        app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 10)
        QtCore.QThread.msleep(10)
    return sum(1 for line in trace.lines() if line[2] == trace.RAW
               and "stick still" not in line[3])

out["rate-before"] = named(w, "traceAxisRateBox").property("editText")
out["rate-picked"] = pick("traceAxisRate", "2")
out["rate-picked-saved"] = [trace.axis_rate(), cfg.value("debug", "trace", "axis-rate")]
out["lines-2"] = axis_lines(3.0)
out["rate-typed"] = type_in("traceAxisRate", "0.5")
out["rate-typed-saved"] = [trace.axis_rate(), cfg.value("debug", "trace", "axis-rate")]
out["lines-half"] = axis_lines(4.0)
shot = os.environ.get("TRACE_SHOT")
if shot:
    open_options()
    w.grabWindow().save(shot)
out["kept"] = named(w, "traceMaxSizeKept").property("text")
out["detail"] = named(w, "traceFileDetail").property("text")
out["status"] = named(w, "traceStatusFile").property("text")
out["rate-abc"] = type_in("traceAxisRate", "abc") + [trace.axis_rate()]
out["rate-99"] = type_in("traceAxisRate", "99") + [trace.axis_rate()]
trace.set_enabled(False)
from gremlin import deferred_write
deferred_write.flush_all()  # what quitting does
app.processEvents()
print('RESULT ' + json.dumps(out), flush=True)
os._exit(0)  # threads started by the app would keep it alive
"""


def _run(home: pathlib.Path, code: str, name: str) -> dict:
    script = home / name
    script.write_text(code, encoding="utf-8")
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
    found = json.loads(lines[-1][len("RESULT "):])
    found["stderr"] = done.stdout + done.stderr
    return found


@pytest.fixture(scope="module")
def result(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home")
    (home / "Gremlin Platforms").mkdir()
    found = _run(home, _CODE, "trace_clear.py")
    found["restart"] = _run(home, _RESTART, "trace_restart.py")
    return found


def test_button_is_off_without_a_trace_file(result: dict) -> None:
    assert result["opened"] is True, result
    assert result["options-open"] is True, result
    assert result["button"] is True, result
    assert result["file-before-on"] is False, result
    assert result["enabled-no-file"] is False, result
    assert result["enabled-with-file"] is True, result


def test_it_asks_first_and_no_keeps_the_file(result: dict) -> None:
    text, last, action = result["question"]
    assert "trace.log" in text and "trace.log.1" in text, result["question"]
    assert "undone" in last, result["question"]
    assert action == "Clear Trace File"
    assert "Before the clear" in result["after-no"]
    assert result["older-after-no"] is True


def test_yes_empties_the_file_while_tracing_and_starts_at_the_top(result: dict) -> None:
    assert result["on-after-yes"] is True
    assert result["older-after-yes"] is False
    assert "Before the clear" not in result["after-yes"], result["after-yes"]
    assert result["after-yes"].splitlines()[0].endswith("Trace file cleared")
    assert result["view-after-yes"] == ["Trace file cleared"], result
    later = result["file-later"].splitlines()
    assert len(later) == 2 and later[1].endswith("After the clear"), later
    assert "one older copy" not in result["status-file"]


def test_max_size_picked_by_a_click_applies_and_is_saved(result: dict) -> None:
    assert result["max-before"] == "5", result
    assert result["max-picked"] == "25", result
    assert result["max-picked-mb"] == [25, 25, 25], result


def test_max_size_typed_applies_and_survives_a_restart(result: dict) -> None:
    assert result["max-typed"] == ["37", ""], result
    assert result["max-typed-mb"] == [37, 37, 37], result
    assert result["restart"]["max-mb"] == 37, result["restart"]
    assert result["kept"] == "Up to 74 MB kept: trace.log plus one older copy"
    assert " of 37 MB" in result["status"], result["status"]
    assert "trace.log.1 —" in result["detail"], result["detail"]


def test_max_size_out_of_range_or_not_a_number_is_refused(result: dict) -> None:
    assert result["max-5000"] == ["37", "Max size is 1 to 1000 MB", 37, 37], result
    assert result["max-abc"] == ["37", "Max size is 1 to 1000 MB", 37], result


def test_axis_lines_picked_limits_a_fast_axis(result: dict) -> None:
    assert result["rate-before"] == "10", result
    assert result["rate-picked"] == "2", result
    assert result["rate-picked-saved"] == [2, 2], result
    # 3 s of a fast axis at 2 per second: about 6 lines (10 per second: ~30).
    assert 3 <= result["lines-2"] <= 8, result


def test_axis_lines_typed_decimal_applies_and_survives_a_restart(result: dict) -> None:
    assert result["rate-typed"] == ["0.5", ""], result
    assert result["rate-typed-saved"] == [0.5, 0.5], result
    # 4 s at one line every 2 s.
    assert 1 <= result["lines-half"] <= 3, result
    assert result["restart"]["axis-rate"] == 0.5, result["restart"]


def test_axis_lines_out_of_range_or_not_a_number_is_refused(result: dict) -> None:
    text = "Axis lines is 0.1 to 50 per second"
    assert result["rate-abc"] == ["0.5", text, 0.5], result
    assert result["rate-99"] == ["0.5", text, 0.5], result


def test_no_qml_warnings_from_the_trace_tab(result: dict) -> None:
    bad = [
        ln for ln in result["stderr"].splitlines()
        if "LiveLogTrace.qml" in ln or "trace_model" in ln
    ]
    assert bad == [], "\n".join(bad)
